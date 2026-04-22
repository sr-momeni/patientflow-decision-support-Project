"""Chatbot Agent - GPT-powered ED triage intake assistant.

This module handles anonymized symptom intake only.
Registration, patient identity, and local nurse-entered checks remain outside
of the cloud LLM conversation and are handled by the local system.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

from backend.agents.urgency_scoring_agent import UrgencyScoringAgent


MAX_ASSISTANT_FOLLOW_UPS = 2


def get_openai_api_key() -> str:
    return (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("OPEN_API_KEY")
        or os.getenv("OPEN_AI_API_KEY")
        or ""
    ).strip()


def openai_configured() -> bool:
    return OpenAI is not None and bool(get_openai_api_key())


def require_openai_client():
    if OpenAI is None:
        raise RuntimeError("openai package is not installed")
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=api_key)


_PII_REPLACEMENTS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b"), "[REDACTED_PHONE]"),
    (re.compile(r"\b\d{8,12}\b"), "[REDACTED_HEALTH_ID]"),
    (re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"), "[REDACTED_DOB]"),
    (re.compile(r"\b\d{1,5}\s+[A-Za-z0-9.\- ]+\s(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct)\b", re.IGNORECASE), "[REDACTED_ADDRESS]"),
    (re.compile(r"\bmy name is\s+[A-Za-z]+(?:\s+[A-Za-z]+){0,2}\b", re.IGNORECASE), "my name is [REDACTED_NAME]"),
    (re.compile(r"\b(?:name|full name)\s*:\s*[A-Za-z]+(?:\s+[A-Za-z]+){0,2}\b", re.IGNORECASE), "name: [REDACTED_NAME]"),
    (re.compile(r"\b(?:health\s*card|healthcard)\s*(?:number)?\s*:\s*[A-Za-z0-9-]+\b", re.IGNORECASE), "health card: [REDACTED_HEALTH_ID]"),
]


SYSTEM_PROMPT = """You are an emergency department triage intake assistant.
Your role is to collect only the minimum clinical information needed for CTAS triage.
Registration, personal identity, and local nurse checks are handled outside this chat.

BEHAVIOR RULES:
1. Assume the patient can describe the main complaint in ONE message.
2. Your ideal first question is: "Please briefly describe your main symptoms and when they started."
3. Keep the interaction short and direct for an emergency setting.
4. Ask at most 1 or 2 short follow-up questions only if a critical triage detail is missing.
5. Never ask for name, gender, address, phone number, email, health card number, or date of birth.
6. If the patient includes personal details, ignore them and focus only on symptoms.
7. If local nurse-entered vitals are supplied in system context, use them instead of asking for them again.
8. Keep replies concise. No therapy-style reassurance, no diagnosis, no general conversation.
9. If the first patient message already contains enough information, do not ask another question. Complete triage directly.
10. Do not invent normal clinical values. If a measured vital or detail is unknown, return null.

Collect only what is clinically relevant:
- main symptom / chief complaint
- when it started
- pain score if relevant
- consciousness / confusion / collapse
- breathing difficulty if relevant
- active seizure or uncontrolled bleeding
- fever/infection clues if relevant
- age bracket if clinically important
- relevant high-risk history if clearly stated

WHEN YOU HAVE ENOUGH INFORMATION:
Output EXACTLY this structure on its own line with no extra text:

[TRIAGE_COMPLETE]
{
  "primary_complaint": "<short phrase>",
  "pain_score": <0-10 integer or null>,
  "consciousness": "<alert|verbal|pain|unresponsive|null>",
  "spo2": <float or null>,
  "heart_rate": <integer or null>,
  "systolic_bp": <integer or null>,
  "respiratory_rate": <integer or null>,
  "temperature": <float or null>,
  "active_seizure": <true|false|null>,
  "uncontrollable_hemorrhage": <true|false|null>,
  "resp_distress": "<none|mild|moderate|severe|null>",
  "age": <integer or null>,
  "history": [<zero or more of: "chronic_disease", "immunocompromised", "pregnancy", "stroke_history">],
  "summary": "<one short clinical summary. If vitals are missing, note that nurse vitals are still pending.>"
}

Unknown measured values must stay null. Keep the summary short and clinically relevant.
"""

CTAS_DESCRIPTIONS = {
    1: ("Resuscitation", "Immediate life-threatening - requires resuscitation now."),
    2: ("Emergent", "High risk - must be seen within 15 minutes."),
    3: ("Urgent", "Should be seen within 30 minutes."),
    4: ("Less Urgent", "Should be seen within 1 hour."),
    5: ("Non-Urgent", "Can wait up to 2 hours. Not immediately life-threatening."),
}

CTAS_COLORS = {1: "#c0392b", 2: "#e67e22", 3: "#f1c40f", 4: "#27ae60", 5: "#2980b9"}


VITAL_FIELDS = ("systolic_bp", "temperature", "heart_rate", "spo2", "respiratory_rate")


def sanitize_pii_text(text: str) -> str:
    """Redact personal identifiers so only anonymized symptom text is sent to OpenAI."""
    sanitized = text or ""
    for pattern, replacement in _PII_REPLACEMENTS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized


def sanitize_message_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    sanitized_history: List[Dict[str, str]] = []
    for message in history:
        sanitized_history.append(
            {
                "role": message.get("role", "user"),
                "content": sanitize_pii_text(message.get("content", "")),
            }
        )
    return sanitized_history


def merge_nurse_vitals(clinical_data: Dict[str, Any], nurse_vitals: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    merged = dict(clinical_data)
    if not nurse_vitals:
        return merged
    for field_name in VITAL_FIELDS:
        value = nurse_vitals.get(field_name)
        if value is not None:
            merged[field_name] = value
    return merged


def urgency_band(ctas_level: int) -> str:
    if ctas_level in (1, 2):
        return "high"
    if ctas_level == 3:
        return "medium"
    return "low"


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def build_triage_reason(clinical_data: Dict[str, Any], ctas_level: int) -> str:
    reasons: List[str] = []
    complaint = str(clinical_data.get("primary_complaint", "")).strip()
    if complaint:
        reasons.append(complaint)

    if clinical_data.get("active_seizure") is True:
        reasons.append("active seizure")
    if clinical_data.get("uncontrollable_hemorrhage") is True:
        reasons.append("uncontrolled bleeding")

    resp_distress = str(clinical_data.get("resp_distress") or "").lower()
    if resp_distress in {"moderate", "severe"}:
        reasons.append(f"{resp_distress} respiratory distress")

    spo2 = _safe_float(clinical_data.get("spo2"))
    if spo2 is not None and spo2 < 95:
        reasons.append(f"SpO2 {spo2:g}%")

    heart_rate = _safe_int(clinical_data.get("heart_rate"))
    if heart_rate is not None and heart_rate > 120:
        reasons.append(f"heart rate {heart_rate}")

    systolic_bp = _safe_int(clinical_data.get("systolic_bp"))
    if systolic_bp is not None and systolic_bp < 100:
        reasons.append(f"systolic BP {systolic_bp}")

    pain_score = _safe_int(clinical_data.get("pain_score"))
    if pain_score is not None and pain_score >= 8:
        reasons.append(f"pain {pain_score}/10")

    summary_bits: List[str] = []
    for reason in reasons:
        if reason not in summary_bits:
            summary_bits.append(reason)
        if len(summary_bits) == 2:
            break

    missing_vitals = [field_name for field_name in VITAL_FIELDS if clinical_data.get(field_name) is None]
    if missing_vitals:
        summary_bits.append("nurse vitals pending")

    if not summary_bits:
        summary_bits.append("available symptom history")

    return f"CTAS {ctas_level} based on {', '.join(summary_bits[:3])}."


class TriageChatbotAgent:
    """Manages a single anonymized ED triage conversation session."""

    def __init__(self):
        self.scorer = UrgencyScoringAgent()

    def chat(
        self,
        user_message: str,
        history: List[Dict[str, str]],
        nurse_vitals: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Process one chatbot turn using symptom-only intake plus optional local nurse vitals."""
        openai_client = require_openai_client()
        sanitized_history = sanitize_message_history(history)
        sanitized_user_message = sanitize_pii_text(user_message)

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        if nurse_vitals:
            vitals_text = ", ".join(
                f"{field_name}={nurse_vitals[field_name]}"
                for field_name in VITAL_FIELDS
                if nurse_vitals.get(field_name) is not None
            )
            if vitals_text:
                messages.append(
                    {
                        "role": "system",
                        "content": f"Local nurse-entered vitals already available: {vitals_text}. Use these values in the final triage output. Do not ask for them again unless a critical clarification is still required.",
                    }
                )

        assistant_turns = sum(1 for message in sanitized_history if message.get("role") == "assistant")
        if assistant_turns >= MAX_ASSISTANT_FOLLOW_UPS:
            messages.append(
                {
                    "role": "system",
                    "content": "You have reached the follow-up limit. Do not ask another question. Complete triage now using available symptom detail, local nurse vitals if provided, and null for unknown measured values. Output [TRIAGE_COMPLETE].",
                }
            )

        messages.extend(sanitized_history)
        messages.append({"role": "user", "content": sanitized_user_message})

        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.1,
            max_tokens=400,
        )

        reply = response.choices[0].message.content.strip()
        if "[TRIAGE_COMPLETE]" in reply:
            return self._handle_completion(reply, nurse_vitals=nurse_vitals)
        return reply, None

    def _handle_completion(
        self,
        raw_reply: str,
        nurse_vitals: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        try:
            marker = "[TRIAGE_COMPLETE]"
            json_str = raw_reply[raw_reply.index(marker) + len(marker):].strip()
            clinical_data = json.loads(json_str)
        except (ValueError, json.JSONDecodeError):
            return raw_reply.replace("[TRIAGE_COMPLETE]", "").strip(), None

        clinical_data = merge_nurse_vitals(clinical_data, nurse_vitals)
        ctas_level = self.scorer.calculate_urgency(clinical_data)
        name, description = CTAS_DESCRIPTIONS.get(ctas_level, ("Unknown", ""))
        color = CTAS_COLORS.get(ctas_level, "#7f8c8d")
        reason = build_triage_reason(clinical_data, ctas_level)

        result = {
            "ctas_level": ctas_level,
            "ctas_name": name,
            "ctas_description": description,
            "color": color,
            "summary": clinical_data.get("summary", "Assessment complete."),
            "clinical_data": clinical_data,
            "urgency": urgency_band(ctas_level),
            "reason": reason,
        }
        reply_text = "Triage intake complete. Review the result below."
        return reply_text, result