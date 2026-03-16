"""
FastAPI routes for the voice triage chatbot.
Mounted at /chatbot in server.py.

Supports two modes:
  - Legacy: /message, /transcribe, /speak  (Whisper + GPT-4o text)
  - Realtime: /realtime-session, /score     (OpenAI Realtime API via WebRTC)
"""

import io
import os
import sys
import tempfile
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

# Resolve paths
CHATBOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CHATBOT_DIR)
ROOT_DIR = os.path.dirname(BACKEND_DIR)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from chatbot.chatbot_agent import TriageChatbotAgent, client, _API_KEY
from agents.urgency_scoring_agent import UrgencyScoringAgent

router = APIRouter()
_agent = TriageChatbotAgent()
_scorer = UrgencyScoringAgent()

# ---------------------------------------------------------------------------
# Realtime API — system prompt & tool definition
# ---------------------------------------------------------------------------

REALTIME_SYSTEM_PROMPT = """You are an experienced emergency department triage nurse conducting an initial patient assessment via voice.
The patient is physically present in the Emergency Department (ER) and is currently at the triage desk talking to you.

Your job is to gather enough clinical information to determine the patient's urgency level using the CTAS (Canadian Triage and Acuity Scale), then call the complete_triage function.

RULES:
1. Ask ONE question at a time. Never combine questions.
2. Start by asking what brought them to the ER today.
3. Collect these details through natural conversation:
   - Chief complaint / main symptom
   - Pain level (0 to 10)
   - When it started (sudden or gradual)
   - Level of consciousness (are they alert, confused, barely responding)
   - Breathing difficulty
   - Any heart racing, very low blood pressure, fainting
   - Fever or signs of infection
   - Any active seizure or uncontrolled bleeding
   - Age
   - Relevant medical history (chronic disease, pregnancy, weakened immune system, prior stroke)
4. Ask follow-up questions when something sounds serious or unclear.
5. Speak in plain, calm, empathetic language. This is a voice call — no lists, no bullet points.
6. Do NOT diagnose. Only collect information.

WHEN YOU HAVE ENOUGH INFORMATION (minimum: chief complaint, pain level, consciousness, and 2 or 3 supporting details):
- Say something like: "Thank you. I now have enough information to calculate your urgency level."
- Then immediately call the complete_triage function with your best clinical estimates for all required fields.
- Use safe defaults for any values the patient could not provide (e.g. spo2=98.0, heart_rate=80).
"""

COMPLETE_TRIAGE_TOOL = {
    "type": "function",
    "name": "complete_triage",
    "description": (
        "Call this function when you have collected enough information to complete "
        "the triage assessment. Provide your best clinical estimates for all fields."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "primary_complaint":          {"type": "string",  "description": "Chief complaint as a short phrase"},
            "pain_score":                 {"type": "integer", "description": "Pain level 0-10"},
            "consciousness":              {"type": "string",  "enum": ["alert", "verbal", "pain", "unresponsive"]},
            "spo2":                       {"type": "number",  "description": "Oxygen saturation %, default 98.0"},
            "heart_rate":                 {"type": "integer", "description": "Heart rate bpm, default 80"},
            "systolic_bp":                {"type": "integer", "description": "Systolic blood pressure mmHg, default 120"},
            "respiratory_rate":           {"type": "integer", "description": "Breaths per minute, default 16"},
            "temperature":                {"type": "number",  "description": "Body temperature Celsius, default 37.0"},
            "active_seizure":             {"type": "boolean"},
            "uncontrollable_hemorrhage":  {"type": "boolean"},
            "resp_distress":              {"type": "string",  "enum": ["none", "mild", "moderate", "severe"]},
            "age":                        {"type": "integer"},
            "history": {
                "type": "array",
                "items": {"type": "string", "enum": ["chronic_disease", "immunocompromised", "pregnancy", "stroke_history"]},
                "description": "Relevant medical history flags"
            },
            "summary": {"type": "string", "description": "One sentence summarising the patient's presentation"}
        },
        "required": [
            "primary_complaint", "pain_score", "consciousness",
            "age", "summary", "active_seizure", "uncontrollable_hemorrhage", "resp_distress"
        ]
    }
}

CTAS_DESCRIPTIONS = {
    1: ("Resuscitation",  "Immediate life-threatening — requires resuscitation now."),
    2: ("Emergent",       "High risk — must be seen within 15 minutes."),
    3: ("Urgent",         "Should be seen within 30 minutes."),
    4: ("Less Urgent",    "Should be seen within 1 hour."),
    5: ("Non-Urgent",     "Can wait up to 2 hours. Not immediately life-threatening."),
}
CTAS_COLORS = {1: "#c0392b", 2: "#e67e22", 3: "#f1c40f", 4: "#27ae60", 5: "#2980b9"}

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class MessageRequest(BaseModel):
    message: str
    history: List[Dict[str, Any]] = []

class MessageResponse(BaseModel):
    reply: str
    history: List[Dict[str, Any]]
    result: Optional[Dict[str, Any]] = None

class ScoreRequest(BaseModel):
    clinical_data: Dict[str, Any]

_UI_FILE = os.path.join(CHATBOT_DIR, "static", "index.html")

# ---------------------------------------------------------------------------
# Routes — UI
# ---------------------------------------------------------------------------

@router.get("/ui")
@router.get("/ui/")
async def serve_chatbot_ui():
    """Serve the voice chatbot HTML page."""
    return FileResponse(_UI_FILE)


# ---------------------------------------------------------------------------
# Routes — OpenAI Realtime API (WebRTC)
# ---------------------------------------------------------------------------

@router.post("/realtime-session")
async def create_realtime_session():
    """
    Creates a short-lived ephemeral token for the OpenAI Realtime API.
    The browser uses this token to connect directly via WebRTC.
    """
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers={
                "Authorization": f"Bearer {_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-realtime-2025-08-28",
                "voice": "alloy",
                "instructions": REALTIME_SYSTEM_PROMPT,
                "modalities": ["audio", "text"],
                "turn_detection": {"type": "server_vad"},
                "tools": [COMPLETE_TRIAGE_TOOL],
                "tool_choice": "auto",
            },
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI session creation failed: {resp.text}"
        )
    return resp.json()


@router.post("/score")
async def score_triage(body: ScoreRequest):
    """
    Runs UrgencyScoringAgent on clinical data collected by GPT
    and returns a CTAS result.
    Called by the browser after a complete_triage function call.
    """
    try:
        data = body.clinical_data

        # Save the clinical data to a JSON file
        try:
            records_dir = os.path.join(ROOT_DIR, "data", "triage_records")
            os.makedirs(records_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"triage_realtime_{timestamp}.json"
            file_path = os.path.join(records_dir, filename)
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"DEBUG: Saved realtime assessment to {file_path}")
        except Exception as e:
            print(f"WARNING: Could not save realtime assessment JSON: {e}")

        ctas_level = _scorer.calculate_urgency(data)
        name, description = CTAS_DESCRIPTIONS.get(ctas_level, ("Unknown", ""))
        color = CTAS_COLORS.get(ctas_level, "#7f8c8d")
        # Run the real-time simulation allocation
        sim_result = _agent.sim_manager.process_new_patient(ctas_level)
        
        return {
            "ctas_level":        ctas_level,
            "ctas_name":         name,
            "ctas_description":  description,
            "color":             color,
            "summary":           data.get("summary", "Assessment complete."),
            "clinical_data":     data,
            "recommendation":    sim_result["recommended_bed"],
            "recommendation_explanation": sim_result["explanation"],
            "hospital_state":    sim_result["hospital_state"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring error: {str(e)}")


# ---------------------------------------------------------------------------
# Routes — Legacy (Whisper + GPT-4o text, kept as fallback)
# ---------------------------------------------------------------------------

@router.post("/message", response_model=MessageResponse)
async def chat_message(body: MessageRequest):
    try:
        reply, result = _agent.chat(body.message, body.history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {str(e)}")
    updated_history = list(body.history)
    updated_history.append({"role": "user",      "content": body.message})
    updated_history.append({"role": "assistant",  "content": reply})
    return MessageResponse(reply=reply, history=updated_history, result=result)


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    tmp_path = None
    try:
        audio_bytes = await audio.read()
        content_type = audio.content_type or ""
        if "webm" in content_type or (audio.filename or "").endswith(".webm"):
            suffix = ".webm"
        elif "ogg" in content_type:
            suffix = ".ogg"
        elif "mp4" in content_type or "m4a" in content_type:
            suffix = ".m4a"
        else:
            suffix = ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", file=f, response_format="text"
            )
        return {"transcript": transcript.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription error: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/speak")
async def text_to_speech(body: dict):
    text = body.get("text", "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")
    try:
        response = client.audio.speech.create(
            model="tts-1", voice="alloy", input=text, response_format="mp3"
        )
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=reply.mp3"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")
