"""
Chatbot Agent — GPT-4o powered triage interviewer.
Maintains conversation history, collects clinical info,
and hands off to UrgencyScoringAgent when ready.
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional, Tuple

from openai import OpenAI

# Allow importing UrgencyScoringAgent from the agents sibling package
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from agents.urgency_scoring_agent import UrgencyScoringAgent

# ---------------------------------------------------------------------------
# Load API Key
# ---------------------------------------------------------------------------
_KEY_PATH = os.path.join(os.path.dirname(BACKEND_DIR), "openAI_key.txt")
with open(_KEY_PATH, "r") as _f:
    _API_KEY = _f.read().strip()

client = OpenAI(api_key=_API_KEY)

# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an experienced emergency department triage nurse conducting an initial patient assessment.
Your job is to gather enough clinical information through a calm, professional conversation to determine the patient's urgency level using the CTAS (Canadian Triage and Acuity Scale).

IMPORTANT RULES:
1. Ask ONE question at a time. Never ask multiple questions in the same message.
2. Start by asking the patient's chief complaint (main reason for visiting the ER).
3. Based on their answers, ask follow-up questions to collect the following information:
   - Chief complaint / primary symptom
   - Pain score (0–10)
   - Symptom onset (sudden vs gradual)
   - Consciousness level (are they alert, confused, responding only to voice/pain, or unresponsive)
   - Oxygen saturation / breathing difficulty (if relevant)
   - Heart rate and blood pressure (if known)
   - Respiratory rate (if relevant)
   - Presence of active seizure or uncontrolled bleeding
   - Fever or infection signs
   - Age
   - Relevant medical history (chronic disease, immunocompromised, pregnancy, stroke history)
4. You do NOT need perfect numbers for vitals — use clinical judgment. If a patient can't provide a number, infer from their description.
5. You may ask clarifying follow-ups if a symptom sounds serious or ambiguous.
6. Keep your language plain, calm, and empathetic. This is a voice conversation — avoid bullet points and markdown.
7. Do NOT diagnose the patient. Only collect information.

WHEN YOU HAVE ENOUGH INFORMATION:
Once you have gathered sufficient information to make a triage assessment (at minimum: chief complaint, pain level, consciousness, and one or two supporting details), you MUST end the conversation by outputting EXACTLY this structure on its own line with no other text before or after it:

[TRIAGE_COMPLETE]
{
  "primary_complaint": "<chief complaint as a short phrase>",
  "pain_score": <0-10 integer>,
  "consciousness": "<alert|verbal|pain|unresponsive>",
  "spo2": <float, e.g. 98.0 — use 98.0 if unknown>,
  "heart_rate": <integer, use 80 if unknown>,
  "systolic_bp": <integer, use 120 if unknown>,
  "respiratory_rate": <integer, use 16 if unknown>,
  "temperature": <float, use 37.0 if unknown>,
  "active_seizure": <true|false>,
  "uncontrollable_hemorrhage": <true|false>,
  "resp_distress": "<none|mild|moderate|severe>",
  "age": <integer>,
  "history": [<list of zero or more: "chronic_disease", "immunocompromised", "pregnancy", "stroke_history">],
  "summary": "<one sentence summarising the patient's presentation>"
}

The JSON must be valid. Use your best clinical estimate for any values not directly provided.
"""

# CTAS level descriptions for natural language output
CTAS_DESCRIPTIONS = {
    1: ("Resuscitation", "Immediate life-threatening — requires resuscitation now."),
    2: ("Emergent", "High risk — must be seen within 15 minutes."),
    3: ("Urgent", "Should be seen within 30 minutes."),
    4: ("Less Urgent", "Should be seen within 1 hour."),
    5: ("Non-Urgent", "Can wait up to 2 hours. Not immediately life-threatening."),
}

CTAS_COLORS = {1: "#c0392b", 2: "#e67e22", 3: "#f1c40f", 4: "#27ae60", 5: "#2980b9"}


class TriageChatbotAgent:
    """Manages a single patient triage conversation session."""

    def __init__(self):
        self.scorer = UrgencyScoringAgent()

    def chat(
        self, user_message: str, history: List[Dict[str, str]]
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Process one user turn.

        Args:
            user_message: The patient's latest text input.
            history: Conversation history as list of {role, content} dicts.
                     Should NOT include the system prompt.

        Returns:
            (reply_text, result_dict_or_None)
            If result_dict is not None, the conversation is complete.
            result_dict contains: ctas_level, ctas_name, ctas_description, color, summary, clinical_data
        """
        # Build messages list for the API call
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.2,
            max_tokens=600,
        )

        reply = response.choices[0].message.content.strip()

        # Check for triage completion signal
        if "[TRIAGE_COMPLETE]" in reply:
            return self._handle_completion(reply)

        return reply, None

    def _handle_completion(self, raw_reply: str) -> Tuple[str, Dict[str, Any]]:
        """Parse the [TRIAGE_COMPLETE] block and run the urgency scorer."""
        try:
            marker = "[TRIAGE_COMPLETE]"
            json_str = raw_reply[raw_reply.index(marker) + len(marker):].strip()
            clinical_data = json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            # Fallback — return partial message as plain text
            return raw_reply.replace("[TRIAGE_COMPLETE]", "").strip(), None

        # Run the urgency scorer
        ctas_level = self.scorer.calculate_urgency(clinical_data)
        name, description = CTAS_DESCRIPTIONS.get(ctas_level, ("Unknown", ""))
        color = CTAS_COLORS.get(ctas_level, "#7f8c8d")

        summary = clinical_data.get("summary", "Assessment complete.")
        reply_text = (
            f"Based on our conversation, I have completed your triage assessment. "
            f"Please see your result below."
        )

        result = {
            "ctas_level": ctas_level,
            "ctas_name": name,
            "ctas_description": description,
            "color": color,
            "summary": summary,
            "clinical_data": clinical_data,
        }

        return reply_text, result
