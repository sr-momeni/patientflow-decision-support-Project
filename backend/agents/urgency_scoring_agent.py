"""Urgency Scoring Agent based on CTAS guidelines."""

from typing import Any, Dict, List, Optional


class UrgencyScoringAgent:
    """Classifies patient urgency into CTAS levels 1-5 without inventing missing vitals."""

    def __init__(self):
        self.MAPPING = [
            (9, 1),
            (7, 2),
            (4, 3),
            (2, 4),
            (0, 5),
        ]

    def calculate_urgency(self, data: Dict[str, Any]) -> int:
        """Calculate CTAS level from provided clinical data."""
        if self._is_ctas1_override(data):
            return 1

        vitals_score = self._score_vitals(data)
        complaint_score = self._score_complaint(data)
        risk_score = self._score_risks(data)
        age_adj = self._age_adjustment(data)

        total_score = vitals_score + complaint_score + risk_score + age_adj
        for threshold, level in self.MAPPING:
            if total_score >= threshold:
                return level
        return 5

    def _to_int(self, value: Any) -> Optional[int]:
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        text = str(value).strip()
        if not text:
            return None
        try:
            return int(float(text))
        except (TypeError, ValueError):
            return None

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            return float(text)
        except (TypeError, ValueError):
            return None

    def _to_bool(self, value: Any) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if not text:
            return None
        if text in {"true", "1", "yes", "y"}:
            return True
        if text in {"false", "0", "no", "n"}:
            return False
        return None

    def _is_ctas1_override(self, data: Dict[str, Any]) -> bool:
        consciousness = str(data.get("consciousness") or "").strip().lower()
        spo2 = self._to_float(data.get("spo2"))
        active_seizure = self._to_bool(data.get("active_seizure"))
        hemorrhage = self._to_bool(data.get("uncontrollable_hemorrhage"))
        resp_distress = str(data.get("resp_distress") or "").strip().lower()

        if consciousness == "unresponsive":
            return True
        if spo2 is not None and spo2 < 90:
            return True
        if active_seizure is True:
            return True
        if hemorrhage is True:
            return True
        if resp_distress == "severe":
            return True
        return False

    def _score_vitals(self, data: Dict[str, Any]) -> int:
        points = 0

        hr = self._to_int(data.get("heart_rate"))
        sbp = self._to_int(data.get("systolic_bp"))
        rr = self._to_int(data.get("respiratory_rate"))
        spo2 = self._to_float(data.get("spo2"))
        cons = str(data.get("consciousness") or "").strip().lower()

        if spo2 is not None:
            if spo2 < 90:
                points += 5
            elif spo2 < 92:
                points += 3
            elif spo2 < 95:
                points += 1

        if cons in ["unresponsive", "pain"]:
            points += 5
        elif cons == "verbal":
            points += 3

        if sbp is not None:
            if sbp < 80:
                points += 5
            elif sbp < 90:
                points += 3
            elif sbp < 100:
                points += 1

        if rr is not None:
            if rr > 35:
                points += 5
            elif rr > 30:
                points += 3
            elif rr > 24:
                points += 1

        if hr is not None:
            if hr > 130:
                points += 5
            elif hr > 120:
                points += 3
            elif hr > 100:
                points += 1

        return points

    def _score_complaint(self, data: Dict[str, Any]) -> int:
        complaint = str(data.get("primary_complaint") or "").lower()
        score = 0

        if "chest pain" in complaint or "stroke" in complaint:
            score = 4
        elif "abdominal pain" in complaint:
            score = 3
        elif any(token in complaint for token in ("injury", "trauma", "fracture")):
            score = 2
        elif complaint:
            score = 1

        pain = self._to_int(data.get("pain_score"))
        if pain is not None:
            if pain >= 8:
                score += 2
            elif pain >= 5:
                score += 1

        return score

    def _score_risks(self, data: Dict[str, Any]) -> int:
        score = 0
        history = data.get("history", []) or []
        if not isinstance(history, list):
            history = [history]
        history_values = {str(item).strip().lower() for item in history if str(item).strip()}

        if "chronic_disease" in history_values:
            score += 1
        if "immunocompromised" in history_values:
            score += 1
        if "pregnancy" in history_values:
            score += 2
        if "stroke_history" in history_values:
            score += 1

        return score

    def _age_adjustment(self, data: Dict[str, Any]) -> int:
        age = self._to_int(data.get("age"))
        if age is None:
            return 0
        if age > 65 or age < 18:
            return 1
        return 0
