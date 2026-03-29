"""FastAPI routes for the triage chatbot.
Mounted at /chatbot in server.py.
"""

from __future__ import annotations

import io
import os
import tempfile
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

try:
    from fastapi import File, UploadFile
    import multipart  # type: ignore  # noqa: F401
    MULTIPART_AVAILABLE = True
except ImportError:  # pragma: no cover
    File = None  # type: ignore[assignment]
    UploadFile = None  # type: ignore[assignment]
    MULTIPART_AVAILABLE = False

from backend import database
from backend.api.schemas import ChatbotTriageRequest, ClinicalData, NurseVitals
from backend.api.services import run_triage_pipeline
from backend.chatbot.chatbot_agent import (
    TriageChatbotAgent,
    build_triage_reason,
    merge_nurse_vitals,
    require_openai_client,
    urgency_band,
    get_openai_api_key,
)


router = APIRouter()
_agent = TriageChatbotAgent()
CHATBOT_DIR = os.path.dirname(os.path.abspath(__file__))
_UI_FILE = os.path.join(CHATBOT_DIR, "static", "index.html")
CHATBOT_UI_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip().lower() in _TRUE_VALUES


def _realtime_enabled() -> bool:
    return _env_flag("ENABLE_OPENAI_REALTIME", default=False) and bool(get_openai_api_key())


def _audio_enabled() -> bool:
    if not get_openai_api_key():
        return False
    raw = os.getenv("ENABLE_OPENAI_AUDIO") or os.getenv("ENABLE_AUDIO_TRANSCRIPTION")
    if raw is None or not str(raw).strip():
        return True
    return str(raw).strip().lower() not in _FALSE_VALUES


def _transcription_model() -> str:
    return os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe").strip() or "gpt-4o-mini-transcribe"


def _realtime_model() -> str:
    return os.getenv("OPENAI_REALTIME_MODEL", "gpt-realtime-2025-08-28").strip() or "gpt-realtime-2025-08-28"


def _realtime_voice() -> str:
    return os.getenv("OPENAI_REALTIME_VOICE", "alloy").strip() or "alloy"


REALTIME_SYSTEM_PROMPT = """You are an emergency department triage intake assistant using short, realistic ED questioning.

Ask the patient to briefly describe the main symptoms and when they started.
Do not ask for name, gender, address, health card number, email, phone number, or exact date of birth.
Use a one-shot style whenever possible and ask no more than 1 or 2 short clarification questions before calling complete_triage.
If local nurse-entered vitals are supplied separately, use them instead of asking for them again.
Do not invent normal clinical values. If a measured vital or detail is unknown, return null.
Keep responses brief, direct, and clinically relevant.
"""

COMPLETE_TRIAGE_TOOL = {
    "type": "function",
    "name": "complete_triage",
    "description": "Call this function when enough clinical detail has been collected to complete triage.",
    "parameters": {
        "type": "object",
        "properties": {
            "primary_complaint": {"type": "string"},
            "pain_score": {"type": ["integer", "null"]},
            "consciousness": {"type": ["string", "null"], "enum": ["alert", "verbal", "pain", "unresponsive", None]},
            "spo2": {"type": ["number", "null"]},
            "heart_rate": {"type": ["integer", "null"]},
            "systolic_bp": {"type": ["integer", "null"]},
            "respiratory_rate": {"type": ["integer", "null"]},
            "temperature": {"type": ["number", "null"]},
            "active_seizure": {"type": ["boolean", "null"]},
            "uncontrollable_hemorrhage": {"type": ["boolean", "null"]},
            "resp_distress": {"type": ["string", "null"], "enum": ["none", "mild", "moderate", "severe", None]},
            "age": {"type": ["integer", "null"]},
            "history": {
                "type": "array",
                "items": {"type": "string", "enum": ["chronic_disease", "immunocompromised", "pregnancy", "stroke_history"]},
            },
            "summary": {"type": "string"},
        },
        "required": [
            "primary_complaint",
            "pain_score",
            "consciousness",
            "age",
            "summary",
            "active_seizure",
            "uncontrollable_hemorrhage",
            "resp_distress",
        ],
    },
}


class MessageRequest(BaseModel):
    message: str
    history: List[Dict[str, Any]] = []
    nurse_vitals: Optional[NurseVitals] = None


class MessageResponse(BaseModel):
    reply: str
    history: List[Dict[str, Any]]
    result: Optional[Dict[str, Any]] = None


def _nurse_vitals_payload(nurse_vitals: Optional[NurseVitals]) -> Optional[Dict[str, Any]]:
    if nurse_vitals is None:
        return None
    payload = nurse_vitals.model_dump(exclude_none=True)
    return payload or None


def _clinical_data_with_nurse_vitals(clinical_data: ClinicalData, nurse_vitals: Optional[NurseVitals]) -> ClinicalData:
    payload = merge_nurse_vitals(clinical_data.model_dump(), _nurse_vitals_payload(nurse_vitals))
    return ClinicalData(**payload)


def _legacy_result_from_pipeline(pipeline, reason: Optional[str] = None) -> Dict[str, Any]:
    clinical_payload = pipeline.clinical_data.model_dump()
    ctas_level = pipeline.ctas.level
    return {
        "patient_id": pipeline.patient_id,
        "scenario": pipeline.scenario,
        "ctas_level": ctas_level,
        "ctas_name": pipeline.ctas.name,
        "ctas_description": pipeline.ctas.description,
        "color": pipeline.ctas.color,
        "summary": pipeline.clinical_data.summary,
        "clinical_data": clinical_payload,
        "allocation": pipeline.allocation.model_dump(),
        "urgency": urgency_band(ctas_level),
        "reason": reason or build_triage_reason(clinical_payload, ctas_level),
        "preliminary": pipeline.ctas.preliminary,
        "missing_vitals": list(pipeline.ctas.missing_vitals),
        "pipeline": pipeline.model_dump(),
    }


@router.get("/ui")
@router.get("/ui/")
async def serve_chatbot_ui():
    return FileResponse(_UI_FILE, headers=CHATBOT_UI_HEADERS)


@router.post("/realtime-session")
async def create_realtime_session():
    api_key = get_openai_api_key()
    if not _realtime_enabled():
        raise HTTPException(status_code=503, detail="Realtime voice is disabled for this deployment. Set ENABLE_OPENAI_REALTIME=true and provide OPENAI_API_KEY.")
    if not api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured")

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Realtime dependency missing: {exc}") from exc

    session_config = {
        "type": "realtime",
        "model": _realtime_model(),
        "instructions": REALTIME_SYSTEM_PROMPT,
        "audio": {
            "input": {"turn_detection": {"type": "server_vad"}},
            "output": {"voice": _realtime_voice()},
        },
        "tools": [COMPLETE_TRIAGE_TOOL],
        "tool_choice": "auto",
    }

    async with httpx.AsyncClient(timeout=20.0) as http:
        response = await http.post(
            "https://api.openai.com/v1/realtime/client_secrets",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"session": session_config},
        )

    if response.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"OpenAI realtime client secret failed: {response.text}")

    payload = response.json()
    client_secret_value = payload.get("value") or payload.get("client_secret", {}).get("value", "")
    if client_secret_value:
        payload["value"] = client_secret_value
        payload["client_secret"] = {
            "value": client_secret_value,
            "expires_at": payload.get("expires_at") or payload.get("client_secret", {}).get("expires_at"),
        }
    payload["session"] = payload.get("session") or session_config
    payload["transport"] = "webrtc"
    return payload


@router.post("/score")
async def score_triage(body: ChatbotTriageRequest):
    db = database.SessionLocal()
    try:
        clinical_data = _clinical_data_with_nurse_vitals(body.clinical_data, body.nurse_vitals)
        pipeline = run_triage_pipeline(
            db=db,
            patient_id=body.patient_id,
            scenario_name=body.scenario,
            clinical_data=clinical_data,
            raw_form_data={
                "presenting_complaint_Main_Concern": clinical_data.primary_complaint,
                "Pain_assessment_pain_scale": clinical_data.pain_score,
                "age": clinical_data.age,
                "medical_history": ", ".join(clinical_data.history),
            },
            source="chatbot",
        )
        return _legacy_result_from_pipeline(pipeline)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Scoring error: {exc}")
    finally:
        db.close()


@router.post("/message", response_model=MessageResponse)
async def chat_message(body: MessageRequest):
    nurse_vitals = _nurse_vitals_payload(body.nurse_vitals)

    try:
        reply, result = _agent.chat(body.message, body.history, nurse_vitals=nurse_vitals)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {exc}")

    updated_history = list(body.history)
    updated_history.append({"role": "user", "content": body.message})
    updated_history.append({"role": "assistant", "content": reply})

    if result and result.get("clinical_data"):
        db = database.SessionLocal()
        try:
            clinical_data = ClinicalData(**merge_nurse_vitals(result["clinical_data"], nurse_vitals))
            pipeline = run_triage_pipeline(
                db=db,
                patient_id=None,
                scenario_name="normal",
                clinical_data=clinical_data,
                raw_form_data={"presenting_complaint_Main_Concern": clinical_data.primary_complaint},
                source="chatbot",
            )
            result = _legacy_result_from_pipeline(pipeline, reason=result.get("reason"))
        finally:
            db.close()

    return MessageResponse(reply=reply, history=updated_history, result=result)


if MULTIPART_AVAILABLE:
    @router.post("/transcribe")
    async def transcribe_audio(audio: UploadFile = File(...)):
        openai_client = require_openai_client()
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
            with open(tmp_path, "rb") as audio_file:
                model_name = _transcription_model()
                try:
                    transcript = openai_client.audio.transcriptions.create(
                        model=model_name,
                        file=audio_file,
                        response_format="text",
                    )
                except Exception:
                    if model_name == "whisper-1":
                        raise
                    audio_file.seek(0)
                    transcript = openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text",
                    )
            return {"transcript": transcript.strip()}
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Transcription error: {exc}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
else:
    @router.post("/transcribe")
    async def transcribe_audio_unavailable():
        raise HTTPException(status_code=503, detail="Audio transcription requires python-multipart and is not enabled")


@router.post("/speak")
async def text_to_speech(body: dict):
    openai_client = require_openai_client()
    text_value = str(body.get("text", "")).strip()
    if not text_value:
        raise HTTPException(status_code=400, detail="No text provided.")
    try:
        response = openai_client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text_value,
            response_format="mp3",
        )
        return StreamingResponse(
            io.BytesIO(response.content),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=reply.mp3"},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"TTS error: {exc}")