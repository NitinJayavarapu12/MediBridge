import os
from groq import Groq
from twilio.rest import Client as TwilioClient
from dotenv import load_dotenv

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_twilio_client():
    return TwilioClient(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )


CHECKIN_SYSTEM_PROMPT = """
You are MediBridge, a caring and friendly AI health assistant helping patients 
after they leave the hospital.

You are checking in on a patient who was recently discharged. Their care plan is:
{care_plan}

Your job:
1. Ask how they are feeling today in a warm, friendly way
2. Listen to their response and assess if anything sounds like a red flag symptom
3. Encourage them to follow their care plan
4. Keep responses SHORT — under 3 sentences — since this is an SMS conversation
5. Never diagnose. If you detect a red flag, tell them to call 911 or their doctor immediately.

Red flag symptoms from their care plan: {red_flags}
"""

FLAG_CHECK_PROMPT = """
A patient recovering from {diagnosis} sent this message: "{message}"

Their red flag symptoms are: {red_flags}

Does this message indicate a potential medical emergency or red flag symptom?

Respond with JSON only:
{{"flagged": true or false, "reason": "brief explanation or null"}}
"""


def generate_checkin_message(patient_name: str, care_plan: dict, 
                              day_number: int) -> str:
    """Generate the daily check-in opening message to send to patient."""
    red_flags = ", ".join(care_plan.get("red_flags", []))
    diagnosis = care_plan.get("diagnosis", "your recent condition")
    
    prompt = f"""
    Generate a warm, brief SMS check-in message for {patient_name} on day {day_number} 
    of their recovery from {diagnosis}. 
    Ask one simple question about how they are feeling.
    Keep it under 2 sentences. Be warm and human, not clinical.
    """
    
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=100
    )
    return response.choices[0].message.content.strip()


def respond_to_patient(patient_message: str, care_plan: dict) -> str:
    """Generate AI response to patient's check-in message."""
    red_flags = ", ".join(care_plan.get("red_flags", []))
    
    system = CHECKIN_SYSTEM_PROMPT.format(
        care_plan=str(care_plan),
        red_flags=red_flags
    )
    
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": patient_message}
        ],
        temperature=0.4,
        max_tokens=150
    )
    return response.choices[0].message.content.strip()


def check_if_flagged(patient_message: str, care_plan: dict) -> tuple[bool, str]:
    """Check if the patient message contains red flag symptoms."""
    import json
    
    red_flags = ", ".join(care_plan.get("red_flags", []))
    diagnosis = care_plan.get("diagnosis", "unknown condition")
    
    prompt = FLAG_CHECK_PROMPT.format(
        diagnosis=diagnosis,
        message=patient_message,
        red_flags=red_flags
    )
    
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=100
    )
    
    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    
    try:
        result = json.loads(raw)
        return result.get("flagged", False), result.get("reason", None)
    except:
        return False, None


def send_sms(to_phone: str, message: str):
    """Send SMS via Twilio."""
    try:
        client = get_twilio_client()
        msg = client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_PHONE"),
            to=to_phone
        )
        print(f"✅ SMS sent to {to_phone}: SID {msg.sid}")
        return msg.sid
    except Exception as e:
        print(f"⚠️ SMS failed (Twilio not configured): {e}")
        return None


def run_daily_checkin(patient: dict, care_plan: dict, 
                       day_number: int, simulate: bool = True):
    """
    Run a full daily check-in cycle.
    If simulate=True, skips actual SMS and uses console input.
    """
    patient_name = patient.get("name", "there")
    phone = patient.get("phone")
    
    # Generate opening message
    opening = generate_checkin_message(patient_name, care_plan, day_number)
    print(f"\n📱 MediBridge → Patient (Day {day_number}):\n{opening}")
    
    if not simulate:
        send_sms(phone, opening)
    
    # Simulate patient response (in real app this comes from Twilio webhook)
    if simulate:
        patient_response = input("\n💬 Patient response (type here): ")
    else:
        patient_response = "[waiting for SMS reply via webhook]"
    
    # Check for red flags
    flagged, flag_reason = check_if_flagged(patient_response, care_plan)
    
    # Generate AI response
    ai_response = respond_to_patient(patient_response, care_plan)
    print(f"\n🤖 MediBridge Response:\n{ai_response}")
    
    if flagged:
        print(f"\n🚨 FLAGGED: {flag_reason}")
    
    if not simulate:
        send_sms(phone, ai_response)
    
    return {
        "patient_message": patient_response,
        "ai_response": ai_response,
        "flagged": flagged,
        "flag_reason": flag_reason
    }


if __name__ == "__main__":
    dummy_patient = {"name": "John Doe", "phone": "+1234567890"}
    dummy_care_plan = {
        "diagnosis": "Acute Myocardial Infarction",
        "red_flags": ["chest pain", "shortness of breath", "left arm pain"],
        "medications": [{"name": "Aspirin", "dose": "81mg", "frequency": "Daily", "duration": "Ongoing"}]
    }
    
    result = run_daily_checkin(dummy_patient, dummy_care_plan, day_number=1, simulate=True)
    print(f"\n✅ Check-in complete. Flagged: {result['flagged']}")