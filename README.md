# 🏥 MediBridge — AI-Powered Patient Discharge Summarizer & Follow-Up Coach

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square&logo=fastapi)
![Groq](https://img.shields.io/badge/LLM-Groq%20%7C%20LLaMA%203.3-orange?style=flat-square)
![Supabase](https://img.shields.io/badge/Database-Supabase-3ECF8E?style=flat-square&logo=supabase)

> An end-to-end LLM pipeline that parses hospital discharge documents, translates clinical instructions into plain language, and conducts automated patient follow-up — reducing information loss at the point of care.

> 🚀 **[Live Demo → medibridge-zhg4.onrender.com](https://medibridge-zhg4.onrender.com)**

---

## 🚨 The Problem

When patients leave hospitals, they receive dense discharge papers filled with medical jargon. Studies show **40–50% of patients don't understand their discharge instructions**, leading to:

- Medication errors
- Missed follow-up appointments
- Preventable hospital readmissions (~$26B/year in the US alone)

MediBridge solves this with a three-stage AI pipeline that makes discharge information accessible, actionable, and continuously monitored.

---

## ✨ Features

- **📄 Document Processing** — Accepts discharge documents from PDF uploads, raw text, or the MTSamples medical dataset
- **🗣 Plain Language Translation** — Converts medical jargon to 6th-grade reading level using LLaMA 3.3 via Groq
- **📋 Structured Care Plan Extraction** — Pulls medications, dosages, restrictions, follow-ups, and red flag symptoms into clean JSON
- **🛡 AI Confidence Scoring** — Flags any field where the LLM was uncertain, preventing silent hallucinations in safety-critical output
- **💬 SMS Check-In Bot** — Daily automated patient follow-up via Twilio SMS, with red flag detection
- **📊 Caregiver Dashboard** — Real-time web UI showing all patients, flagged alerts, and check-in history
- **📄 PDF Report Generation** — Weekly caregiver reports summarizing the patient's recovery progress

---

## 🏗 Architecture

```
User / Clinician
      │
      ▼
┌─────────────────┐
│  FastAPI Backend │  ← main.py (REST API + file serving)
└────────┬────────┘
         │
   ┌─────┴──────────────────────────────┐
   │                                    │
   ▼                                    ▼
┌──────────────┐              ┌──────────────────┐
│ LLM Pipeline │              │  Supabase (DB)   │
│  summarizer  │              │  patients        │
│  - translate │              │  discharge_records│
│  - extract   │              │  checkin_responses│
│  - confidence│              └──────────────────┘
└──────┬───────┘
       │
  ┌────┴─────────────┐
  │                  │
  ▼                  ▼
Groq API          PDF Report
LLaMA 3.3-70B     Generator
                  (WeasyPrint)
       │
       ▼
  Twilio SMS
  Check-In Bot
```

---

## 🗂 Project Structure

```
medibridge/
├── main.py                  # FastAPI backend — all REST endpoints
├── parser/
│   ├── data_loader.py       # MTSamples dataset loader and cleaner
│   └── db.py                # Supabase database operations
├── llm/
│   └── summarizer.py        # Groq LLM pipeline (translate → extract → confidence check)
├── bot/
│   └── checkin_bot.py       # SMS check-in bot with red flag detection
├── reports/
│   └── pdf_generator.py     # HTML/PDF caregiver report generator
├── frontend/
│   └── index.html           # Single-page caregiver dashboard
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
└── README.md
```

---

## 🧠 LLM Pipeline (3 Stages)

### Stage 1 — Plain Language Translation
Rewrites clinical notes at a 6th-grade reading level using a safety-tuned prompt. Avoids adding any information not present in the original. Flags uncertain passages with "Ask your doctor about: [topic]".

### Stage 2 — Structured Care Plan Extraction
Extracts a JSON care plan with:
- Primary diagnosis
- Medications (name, dose, frequency, duration)
- Activity and dietary restrictions
- Follow-up appointments
- Red flag symptoms

### Stage 3 — Confidence Check (Safety Layer)
A separate LLM call reviews the extracted care plan and flags any field that was inferred rather than explicitly stated. This prevents hallucinated medical instructions from reaching patients.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | API health check |
| POST | `/patients/create` | Register a new patient |
| GET | `/patients/all` | List all patients |
| GET | `/patients/{id}` | Get patient by ID |
| POST | `/process/from-dataset` | Process MTSamples record |
| POST | `/process/from-text` | Process raw text |
| POST | `/process/from-pdf` | Upload and process PDF |
| GET | `/discharge/{patient_id}/latest` | Get latest discharge record |
| POST | `/checkin/respond` | Patient sends check-in message |
| GET | `/checkin/{patient_id}/history` | Get check-in history |
| GET | `/checkin/flagged/all` | All flagged check-ins (caregiver) |
| POST | `/report/generate` | Generate and download PDF report |
| GET | `/dataset/sample/{index}` | Preview dataset record |

Full interactive docs available at `http://localhost:8000/docs` (Swagger UI).

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A [Groq API key](https://console.groq.com) (free)
- A [Supabase](https://supabase.com) project (free)
- A [Twilio](https://twilio.com) account (free trial) — optional for SMS

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/medibridge.git
cd medibridge
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with your actual keys:

```env
GROQ_API_KEY=your_groq_api_key_here
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE=+1xxxxxxxxxx
```

### 5. Set Up Supabase Tables

Run this SQL in your Supabase SQL Editor:

```sql
CREATE TABLE patients (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL,
  phone TEXT,
  age INTEGER,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE discharge_records (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  patient_id UUID REFERENCES patients(id),
  original_transcription TEXT,
  plain_language_summary TEXT,
  care_plan JSONB,
  confidence_check JSONB,
  specialty TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE checkin_responses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  patient_id UUID REFERENCES patients(id),
  discharge_id UUID REFERENCES discharge_records(id),
  day_number INTEGER,
  patient_message TEXT,
  ai_response TEXT,
  flagged BOOLEAN DEFAULT FALSE,
  flag_reason TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 6. Download the Dataset

Download [MTSamples](https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions) from Kaggle and place `mtsamples.csv` in the `data/` folder.

```
medibridge/data/mtsamples.csv
```

### 7. Run the Application

```bash
python main.py
```

Open your browser at:
- **`http://localhost:8000`** — Caregiver Dashboard
- **`http://localhost:8000/docs`** — Swagger API Explorer

---

## 🖥 Using the Dashboard

Follow this flow to test end-to-end:

1. **Patients tab** → Register a patient → Copy the UUID shown
2. **Process Record tab** → Paste UUID → Select a dataset record → Click **Run AI Pipeline**
3. **Check-In Bot tab** → Paste UUID → Click **Start Check-In** → Type patient responses
4. **Generate Report tab** → Paste UUID → Download caregiver PDF
5. **Alerts tab** → View all flagged responses across all patients

---

## 🧪 Testing Individual Modules

```bash
# Test dataset loading
python parser/data_loader.py

# Test LLM pipeline
python llm/summarizer.py

# Test SMS check-in bot (simulated)
python bot/checkin_bot.py

# Test PDF report generator
python reports/pdf_generator.py

# Test database connection
python parser/db.py
```

---

## 📊 Dataset

**MTSamples — Medical Transcription Samples**  
Source: [Kaggle](https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions)  
Records: 4,999 real medical transcriptions across 40+ specialties  
Used for: Simulating discharge documents without requiring real patient data

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM Inference | Groq API — LLaMA 3.3-70B-Versatile |
| Backend | FastAPI + Uvicorn |
| Database | Supabase (PostgreSQL) |
| PDF Parsing | PyMuPDF (fitz) |
| Report Generation | WeasyPrint |
| SMS | Twilio |
| Frontend | Vanilla HTML/CSS/JS |
| Dataset | MTSamples (Kaggle) |

---

## 🔮 Future Improvements

- [ ] Multilingual support (Spanish, French, Mandarin) using translation layer
- [ ] WhatsApp integration for broader patient reach
- [ ] EHR system integration (Epic, Cerner)
- [ ] Voice call check-ins using Twilio Voice + TTS
- [ ] Mobile app for caregivers (React Native)
- [ ] Analytics dashboard with readmission risk scoring

---

## ⚠️ Disclaimer

MediBridge is a portfolio project built for educational purposes. It is **not a certified medical device** and should not be used for real patient care without review by qualified healthcare professionals. All AI-generated summaries should be verified by a licensed clinician before use.

---
