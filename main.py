from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import fitz  # PyMuPDF
import io
import os
from dotenv import load_dotenv

load_dotenv()

# Import our modules
from parser.data_loader import load_mtsamples, get_sample_record
from parser.db import (
    create_patient, get_patient_by_id, get_all_patients,
    save_discharge_record, get_discharge_by_patient, get_latest_discharge,
    save_checkin_response, get_checkins_by_patient, get_flagged_checkins
)
from llm.summarizer import process_full_pipeline
from bot.checkin_bot import (
    generate_checkin_message, respond_to_patient,
    check_if_flagged, run_daily_checkin
)
from reports.pdf_generator import generate_patient_report

app = FastAPI(
    title="MediBridge API",
    description="AI-powered patient discharge summarizer and follow-up coach",
    version="1.0.0"
)

# Allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ─── Request Models ──────────────────────────────────────────────────

class PatientCreate(BaseModel):
    name: str
    phone: str
    age: int

class ProcessFromDataset(BaseModel):
    patient_id: str
    dataset_index: int = 0

class ProcessFromText(BaseModel):
    patient_id: str
    transcription: str
    specialty: str = "General Medicine"

class CheckinRequest(BaseModel):
    patient_id: str
    patient_message: str
    day_number: int

class ReportRequest(BaseModel):
    patient_id: str


# ─── Root ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse("frontend/index.html")

@app.get("/health")
def health():
    return {"status": "MediBridge is running ✅", "version": "1.0.0"}


# ─── Patient Endpoints ───────────────────────────────────────────────

@app.post("/patients/create")
def api_create_patient(data: PatientCreate):
    """Register a new patient."""
    try:
        patient = create_patient(data.name, data.phone, data.age)
        return {"success": True, "patient": patient}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/patients/all")
def api_get_all_patients():
    """Get all patients."""
    try:
        patients = get_all_patients()
        return {"success": True, "patients": patients, "count": len(patients)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/patients/{patient_id}")
def api_get_patient(patient_id: str):
    """Get a single patient by ID."""
    patient = get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"success": True, "patient": patient}


# ─── Processing Endpoints ────────────────────────────────────────────

@app.post("/process/from-dataset")
def api_process_from_dataset(data: ProcessFromDataset):
    """
    Process a record from the MTSamples dataset.
    Great for demo and testing.
    """
    try:
        df = load_mtsamples()
        record = get_sample_record(df, index=data.dataset_index)
        transcription = record["transcription"]
        specialty = record["specialty"]

        # Run LLM pipeline
        result = process_full_pipeline(transcription)

        # Save to DB
        discharge = save_discharge_record(
            patient_id=data.patient_id,
            transcription=transcription,
            plain_summary=result["plain_language_summary"],
            care_plan=result["care_plan"],
            confidence=result["confidence_check"],
            specialty=specialty
        )

        return {
            "success": True,
            "discharge_id": discharge["id"],
            "specialty": specialty,
            "description": record["description"],
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/from-text")
def api_process_from_text(data: ProcessFromText):
    """Process a raw transcription text directly."""
    try:
        result = process_full_pipeline(data.transcription)

        discharge = save_discharge_record(
            patient_id=data.patient_id,
            transcription=data.transcription,
            plain_summary=result["plain_language_summary"],
            care_plan=result["care_plan"],
            confidence=result["confidence_check"],
            specialty=data.specialty
        )

        return {
            "success": True,
            "discharge_id": discharge["id"],
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/from-pdf")
async def api_process_from_pdf(patient_id: str, file: UploadFile = File(...)):
    """Upload a PDF discharge document and process it."""
    try:
        contents = await file.read()
        pdf = fitz.open(stream=contents, filetype="pdf")
        text = ""
        for page in pdf:
            text += page.get_text()
        pdf.close()

        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        result = process_full_pipeline(text)

        discharge = save_discharge_record(
            patient_id=patient_id,
            transcription=text,
            plain_summary=result["plain_language_summary"],
            care_plan=result["care_plan"],
            confidence=result["confidence_check"],
            specialty="PDF Upload"
        )

        return {
            "success": True,
            "discharge_id": discharge["id"],
            "pages_extracted": len(pdf),
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Discharge Endpoints ─────────────────────────────────────────────

@app.get("/discharge/{patient_id}")
def api_get_discharge(patient_id: str):
    """Get all discharge records for a patient."""
    records = get_discharge_by_patient(patient_id)
    return {"success": True, "records": records, "count": len(records)}


@app.get("/discharge/{patient_id}/latest")
def api_get_latest_discharge(patient_id: str):
    """Get the most recent discharge record."""
    record = get_latest_discharge(patient_id)
    if not record:
        raise HTTPException(status_code=404, detail="No discharge records found")
    return {"success": True, "record": record}


# ─── Check-in Endpoints ──────────────────────────────────────────────

@app.post("/checkin/respond")
def api_checkin_respond(data: CheckinRequest):
    """
    Patient sends a message → AI responds and flags if needed.
    This is the core SMS webhook handler.
    """
    try:
        patient = get_patient_by_id(data.patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        discharge = get_latest_discharge(data.patient_id)
        if not discharge:
            raise HTTPException(status_code=404, detail="No discharge record found")

        care_plan = discharge.get("care_plan", {})

        # Check for red flags
        flagged, flag_reason = check_if_flagged(data.patient_message, care_plan)

        # Generate AI response
        ai_response = respond_to_patient(data.patient_message, care_plan)

        # Save to DB
        checkin = save_checkin_response(
            patient_id=data.patient_id,
            discharge_id=discharge["id"],
            day=data.day_number,
            patient_msg=data.patient_message,
            ai_response=ai_response,
            flagged=flagged,
            flag_reason=flag_reason
        )

        return {
            "success": True,
            "ai_response": ai_response,
            "flagged": flagged,
            "flag_reason": flag_reason,
            "checkin_id": checkin["id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/checkin/{patient_id}/history")
def api_checkin_history(patient_id: str):
    """Get all check-in history for a patient."""
    checkins = get_checkins_by_patient(patient_id)
    return {"success": True, "checkins": checkins, "count": len(checkins)}


@app.get("/checkin/flagged/all")
def api_flagged_checkins():
    """Get all flagged check-ins across all patients — for caregiver dashboard."""
    flagged = get_flagged_checkins()
    return {"success": True, "flagged": flagged, "count": len(flagged)}


# ─── Report Endpoints ────────────────────────────────────────────────

@app.post("/report/generate")
def api_generate_report(data: ReportRequest):
    """Generate and return a PDF/HTML report for a patient."""
    try:
        patient = get_patient_by_id(data.patient_id)
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        discharge = get_latest_discharge(data.patient_id)
        if not discharge:
            raise HTTPException(status_code=404, detail="No discharge record found")

        checkins = get_checkins_by_patient(data.patient_id)

        report_path = generate_patient_report(patient, discharge, checkins)

        return FileResponse(
            path=report_path,
            filename=os.path.basename(report_path),
            media_type="application/pdf" if report_path.endswith(".pdf") else "text/html"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Dataset Explorer ────────────────────────────────────────────────

@app.get("/dataset/sample/{index}")
def api_dataset_sample(index: int = 0):
    """Preview a record from the MTSamples dataset without processing."""
    try:
        df = load_mtsamples()
        if index >= len(df):
            raise HTTPException(status_code=404, detail=f"Index out of range. Max: {len(df)-1}")
        record = get_sample_record(df, index=index)
        return {
            "success": True,
            "index": index,
            "total_records": len(df),
            "record": {
                "specialty": record["specialty"],
                "description": record["description"],
                "transcription_preview": record["transcription"][:500] + "..."
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)