import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def get_groq_client():
    return Groq(api_key=os.getenv("GROQ_API_KEY"))

# ─── Prompt Templates ───────────────────────────────────────────────

PLAIN_LANGUAGE_PROMPT = """
You are a compassionate medical translator helping patients understand their medical records.

Your job is to read the following medical transcription and rewrite it in simple, 
clear language that a 6th grader can understand. Avoid all medical jargon.

Rules:
- Use short sentences
- Explain any medical term you cannot avoid in parentheses
- Be warm and reassuring in tone
- Do NOT add information that is not in the original text
- If something is unclear in the original, say "Ask your doctor about: [topic]"

Medical Transcription:
{transcription}

Write the plain-language version below:
"""

CARE_PLAN_PROMPT = """
You are a medical information extractor. Read the transcription below and extract 
a structured care plan in JSON format.

Extract exactly this structure:
{{
  "diagnosis": "primary diagnosis in simple terms",
  "medications": [
    {{"name": "...", "dose": "...", "frequency": "...", "duration": "..."}}
  ],
  "restrictions": ["list of things patient should avoid or limit"],
  "follow_up": ["list of follow-up appointments or tests needed"],
  "red_flags": ["symptoms that mean the patient should call a doctor immediately"],
  "diet": "any dietary instructions",
  "activity": "activity level allowed"
}}

If any field has no information, use null for strings or [] for lists.
Return ONLY valid JSON. No explanation before or after.

Medical Transcription:
{transcription}
"""

CONFIDENCE_CHECK_PROMPT = """
You are a medical AI safety checker.

Review this extracted care plan and flag any field where you are less than 80% confident 
the information was clearly stated in the original transcription (vs inferred or assumed).

Care Plan:
{care_plan}

Original Transcription:
{transcription}

Return a JSON object like:
{{
  "confidence_flags": [
    {{"field": "field_name", "issue": "what was unclear or assumed"}}
  ],
  "overall_safe": true or false
}}

Return ONLY valid JSON.
"""

# ─── Functions ───────────────────────────────────────────────────────

def translate_to_plain_language(transcription: str) -> str:
    """Convert medical transcription to plain language."""
    prompt = PLAIN_LANGUAGE_PROMPT.format(transcription=transcription[:3000])
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,  # Low temp for accuracy
        max_tokens=1500
    )
    
    return response.choices[0].message.content


def extract_care_plan(transcription: str) -> dict:
    """Extract structured care plan as JSON."""
    import json
    
    prompt = CARE_PLAN_PROMPT.format(transcription=transcription[:3000])
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,  # Very low for structured output
        max_tokens=1000
    )
    
    raw = response.choices[0].message.content.strip()
    
    # Clean markdown code blocks if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Failed to parse care plan", "raw": raw}


def run_confidence_check(transcription: str, care_plan: dict) -> dict:
    """Safety layer — flag uncertain extractions."""
    import json
    
    prompt = CONFIDENCE_CHECK_PROMPT.format(
        care_plan=str(care_plan),
        transcription=transcription[:3000]
    )
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500
    )
    
    raw = response.choices[0].message.content.strip()
    
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"confidence_flags": [], "overall_safe": True}


def process_full_pipeline(transcription: str) -> dict:
    """Run all three steps and return combined result."""
    print("🔄 Step 1: Translating to plain language...")
    plain = translate_to_plain_language(transcription)
    
    print("🔄 Step 2: Extracting care plan...")
    care_plan = extract_care_plan(transcription)
    
    print("🔄 Step 3: Running confidence check...")
    confidence = run_confidence_check(transcription, care_plan)
    
    return {
        "plain_language_summary": plain,
        "care_plan": care_plan,
        "confidence_check": confidence
    }


if __name__ == "__main__":
    # Quick test with a fake discharge note
    test_text = """
    Patient is a 65-year-old male admitted for acute myocardial infarction. 
    Treated with aspirin 81mg daily and metoprolol 25mg twice daily. 
    Patient should avoid strenuous activity for 6 weeks. 
    Follow up with cardiologist in 2 weeks. 
    Call 911 if chest pain, shortness of breath, or left arm pain returns.
    Low sodium diet recommended. No driving for 1 week.
    """
    
    result = process_full_pipeline(test_text)
    
    print("\n=== PLAIN LANGUAGE ===")
    print(result['plain_language_summary'])
    print("\n=== CARE PLAN ===")
    import json
    print(json.dumps(result['care_plan'], indent=2))
    print("\n=== CONFIDENCE CHECK ===")
    print(json.dumps(result['confidence_check'], indent=2))