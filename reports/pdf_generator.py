import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def generate_patient_report(patient: dict, discharge: dict, checkins: list) -> str:
    """
    Generate a weekly HTML/PDF summary report for caregivers.
    Returns the path to the saved PDF file.
    """
    care_plan = discharge.get("care_plan", {})
    confidence = discharge.get("confidence_check", {})
    flags = confidence.get("confidence_flags", [])

    # Build medications table rows
    medications_html = ""
    meds = care_plan.get("medications", [])
    if meds:
        for med in meds:
            medications_html += f"""
            <tr>
                <td>{med.get('name', 'N/A')}</td>
                <td>{med.get('dose', 'N/A')}</td>
                <td>{med.get('frequency', 'N/A')}</td>
                <td>{med.get('duration', 'N/A')}</td>
            </tr>"""
    else:
        medications_html = "<tr><td colspan='4'>No medications recorded</td></tr>"

    # Build checkin history rows
    checkins_html = ""
    if checkins:
        for c in checkins:
            flag_badge = '<span class="badge-danger">⚠ FLAGGED</span>' if c.get('flagged') else '<span class="badge-safe">✓ OK</span>'
            checkins_html += f"""
            <tr>
                <td>Day {c.get('day_number', '?')}</td>
                <td>{c.get('patient_message', '')}</td>
                <td>{c.get('ai_response', '')[:120]}...</td>
                <td>{flag_badge}</td>
            </tr>"""
    else:
        checkins_html = "<tr><td colspan='4'>No check-ins recorded yet</td></tr>"

    # Build confidence flags
    flags_html = ""
    if flags:
        for f in flags:
            flags_html += f"<li><strong>{f.get('field', '')}</strong>: {f.get('issue', '')}</li>"
    else:
        flags_html = "<li style='color:green'>All fields extracted with high confidence ✓</li>"

    # Build restrictions list
    restrictions = care_plan.get("restrictions", [])
    restrictions_html = "".join([f"<li>{r}</li>" for r in restrictions]) or "<li>None specified</li>"

    # Build red flags list
    red_flags = care_plan.get("red_flags", [])
    red_flags_html = "".join([f"<li>{r}</li>" for r in red_flags]) or "<li>None specified</li>"

    # Build follow-up list
    follow_ups = care_plan.get("follow_up", [])
    follow_ups_html = "".join([f"<li>{f}</li>" for f in follow_ups]) or "<li>None specified</li>"

    overall_safe = confidence.get("overall_safe", True)
    safety_banner = (
        '<div class="banner-safe">✅ AI Safety Check Passed — Care plan extracted with high confidence</div>'
        if overall_safe else
        '<div class="banner-warning">⚠️ AI Safety Check: Some fields flagged for review — see below</div>'
    )

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e; background: #f4f7fb; padding: 40px; }}
        .header {{ background: linear-gradient(135deg, #0f3460, #16213e); color: white; padding: 30px 40px; border-radius: 12px; margin-bottom: 30px; }}
        .header h1 {{ font-size: 26px; letter-spacing: 1px; }}
        .header p {{ opacity: 0.8; margin-top: 6px; font-size: 14px; }}
        .meta {{ display: flex; gap: 30px; margin-top: 16px; }}
        .meta span {{ background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: 20px; font-size: 13px; }}
        .section {{ background: white; border-radius: 10px; padding: 24px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .section h2 {{ font-size: 16px; color: #0f3460; border-bottom: 2px solid #e8f0fe; padding-bottom: 10px; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .diagnosis-box {{ background: #e8f4fd; border-left: 4px solid #0f3460; padding: 14px 18px; border-radius: 6px; font-size: 15px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
        th {{ background: #0f3460; color: white; padding: 10px 14px; text-align: left; }}
        td {{ padding: 10px 14px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }}
        tr:last-child td {{ border-bottom: none; }}
        tr:nth-child(even) td {{ background: #f9fbff; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 6px; font-size: 14px; line-height: 1.5; }}
        .red-flag-list li {{ color: #c0392b; }}
        .badge-danger {{ background: #ffe0e0; color: #c0392b; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
        .badge-safe {{ background: #e0f5e9; color: #27ae60; padding: 3px 10px; border-radius: 12px; font-size: 12px; }}
        .banner-safe {{ background: #d4edda; border: 1px solid #28a745; color: #155724; padding: 12px 18px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }}
        .banner-warning {{ background: #fff3cd; border: 1px solid #ffc107; color: #856404; padding: 12px 18px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; }}
        .plain-text {{ font-size: 14px; line-height: 1.8; color: #333; white-space: pre-line; }}
        .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #888; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 MediBridge — Patient Care Report</h1>
        <p>AI-assisted discharge summary and follow-up tracker</p>
        <div class="meta">
            <span>👤 {patient.get('name', 'Unknown')}</span>
            <span>🎂 Age: {patient.get('age', 'N/A')}</span>
            <span>📱 {patient.get('phone', 'N/A')}</span>
            <span>📅 Report Date: {datetime.now().strftime('%B %d, %Y')}</span>
        </div>
    </div>

    {safety_banner}

    <div class="section">
        <h2>📋 Diagnosis</h2>
        <div class="diagnosis-box">{care_plan.get('diagnosis', 'Not specified')}</div>
    </div>

    <div class="section">
        <h2>💊 Medications</h2>
        <table>
            <thead><tr><th>Medication</th><th>Dose</th><th>Frequency</th><th>Duration</th></tr></thead>
            <tbody>{medications_html}</tbody>
        </table>
    </div>

    <div class="two-col">
        <div class="section">
            <h2>🚫 Restrictions</h2>
            <ul>{restrictions_html}</ul>
        </div>
        <div class="section">
            <h2>📅 Follow-Up Required</h2>
            <ul>{follow_ups_html}</ul>
        </div>
    </div>

    <div class="section">
        <h2>🚨 Red Flag Symptoms</h2>
        <ul class="red-flag-list">{red_flags_html}</ul>
    </div>

    <div class="section">
        <h2>🥗 Diet & Activity</h2>
        <p><strong>Diet:</strong> {care_plan.get('diet', 'No specific instructions')}</p>
        <p style="margin-top:10px"><strong>Activity:</strong> {care_plan.get('activity', 'No specific instructions')}</p>
    </div>

    <div class="section">
        <h2>🤖 AI Confidence Flags</h2>
        <ul>{flags_html}</ul>
    </div>

    <div class="section">
        <h2>💬 Plain Language Summary (Patient Version)</h2>
        <div class="plain-text">{discharge.get('plain_language_summary', 'Not available')}</div>
    </div>

    <div class="section">
        <h2>📆 Daily Check-In History</h2>
        <table>
            <thead><tr><th>Day</th><th>Patient Message</th><th>AI Response</th><th>Status</th></tr></thead>
            <tbody>{checkins_html}</tbody>
        </table>
    </div>

    <div class="footer">
        <p>Generated by MediBridge AI • {datetime.now().strftime('%Y-%m-%d %H:%M')} • For caregiver use only</p>
        <p style="margin-top:4px">⚠️ This report is AI-assisted and should be reviewed by a qualified healthcare professional</p>
    </div>
</body>
</html>
"""

    # Save HTML first
    os.makedirs("reports/output", exist_ok=True)
    patient_name_clean = patient.get('name', 'patient').replace(' ', '_').lower()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    html_path = f"reports/output/{patient_name_clean}_{timestamp}.html"
    pdf_path = f"reports/output/{patient_name_clean}_{timestamp}.pdf"

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Try to generate PDF
    try:
        from weasyprint import HTML
        HTML(filename=html_path).write_pdf(pdf_path)
        print(f"✅ PDF report saved: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"⚠️ WeasyPrint failed ({e}), HTML report saved instead: {html_path}")
        return html_path


if __name__ == "__main__":
    # Test with dummy data
    dummy_patient = {"name": "John Doe", "age": 65, "phone": "+1234567890"}
    dummy_discharge = {
        "plain_language_summary": "You had a heart attack. Take your aspirin every morning. Rest for 6 weeks.",
        "care_plan": {
            "diagnosis": "Acute Myocardial Infarction (Heart Attack)",
            "medications": [
                {"name": "Aspirin", "dose": "81mg", "frequency": "Daily", "duration": "Ongoing"},
                {"name": "Metoprolol", "dose": "25mg", "frequency": "Twice daily", "duration": "3 months"}
            ],
            "restrictions": ["No strenuous exercise", "No driving for 1 week", "No heavy lifting"],
            "follow_up": ["Cardiologist in 2 weeks", "Blood test in 1 month"],
            "red_flags": ["Chest pain", "Shortness of breath", "Left arm pain"],
            "diet": "Low sodium diet",
            "activity": "Light walking only for 6 weeks"
        },
        "confidence_check": {
            "confidence_flags": [],
            "overall_safe": True
        }
    }
    dummy_checkins = [
        {"day_number": 1, "patient_message": "Feeling okay, a bit tired", "ai_response": "That's normal after discharge. Make sure to take your aspirin.", "flagged": False},
        {"day_number": 2, "patient_message": "Had chest pain this morning", "ai_response": "This is a red flag symptom. Please call 911 immediately.", "flagged": True}
    ]

    path = generate_patient_report(dummy_patient, dummy_discharge, dummy_checkins)
    print(f"Report at: {path}")