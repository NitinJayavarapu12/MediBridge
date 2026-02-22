import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


# ─── Patient Operations ──────────────────────────────────────────────

def create_patient(name: str, phone: str, age: int) -> dict:
    """Insert a new patient and return their record."""
    supabase = get_supabase_client()
    result = supabase.table("patients").insert({
        "name": name,
        "phone": phone,
        "age": age
    }).execute()
    return result.data[0]


def get_patient_by_id(patient_id: str) -> dict:
    supabase = get_supabase_client()
    result = supabase.table("patients").select("*").eq("id", patient_id).execute()
    return result.data[0] if result.data else None


def get_all_patients() -> list:
    supabase = get_supabase_client()
    result = supabase.table("patients").select("*").order("created_at", desc=True).execute()
    return result.data


# ─── Discharge Record Operations ─────────────────────────────────────

def save_discharge_record(patient_id: str, transcription: str, 
                           plain_summary: str, care_plan: dict, 
                           confidence: dict, specialty: str) -> dict:
    """Save the full processed discharge record."""
    supabase = get_supabase_client()
    result = supabase.table("discharge_records").insert({
        "patient_id": patient_id,
        "original_transcription": transcription,
        "plain_language_summary": plain_summary,
        "care_plan": care_plan,
        "confidence_check": confidence,
        "specialty": specialty
    }).execute()
    return result.data[0]


def get_discharge_by_patient(patient_id: str) -> list:
    supabase = get_supabase_client()
    result = (supabase.table("discharge_records")
              .select("*")
              .eq("patient_id", patient_id)
              .order("created_at", desc=True)
              .execute())
    return result.data


def get_latest_discharge(patient_id: str) -> dict:
    records = get_discharge_by_patient(patient_id)
    return records[0] if records else None


# ─── Check-in Operations ─────────────────────────────────────────────

def save_checkin_response(patient_id: str, discharge_id: str, day: int,
                           patient_msg: str, ai_response: str,
                           flagged: bool = False, flag_reason: str = None) -> dict:
    supabase = get_supabase_client()
    result = supabase.table("checkin_responses").insert({
        "patient_id": patient_id,
        "discharge_id": discharge_id,
        "day_number": day,
        "patient_message": patient_msg,
        "ai_response": ai_response,
        "flagged": flagged,
        "flag_reason": flag_reason
    }).execute()
    return result.data[0]


def get_checkins_by_patient(patient_id: str) -> list:
    supabase = get_supabase_client()
    result = (supabase.table("checkin_responses")
              .select("*")
              .eq("patient_id", patient_id)
              .order("day_number")
              .execute())
    return result.data


def get_flagged_checkins() -> list:
    """Get all flagged responses across all patients — for caregiver dashboard."""
    supabase = get_supabase_client()
    result = (supabase.table("checkin_responses")
              .select("*, patients(name, phone)")
              .eq("flagged", True)
              .order("created_at", desc=True)
              .execute())
    return result.data


if __name__ == "__main__":
    # Test the database connection
    print("Testing Supabase connection...")
    
    # Create a test patient
    patient = create_patient("John Doe", "+1234567890", 65)
    print(f"✅ Created patient: {patient['name']} with ID: {patient['id']}")
    
    # Fetch all patients
    all_patients = get_all_patients()
    print(f"✅ Total patients in DB: {len(all_patients)}")