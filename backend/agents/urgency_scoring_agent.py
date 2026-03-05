"""Urgency Scoring Agent based on CTAS guidelines."""

from typing import Dict, Any, List

class UrgencyScoringAgent:
    """Classifies patient urgency into CTAS levels 1-5."""
    
    def __init__(self):
        # Thresholds for CTAS Mapping
        self.MAPPING = [
            (9, 1),  # >= 9 -> CTAS 1
            (7, 2),  # 7-8  -> CTAS 2
            (4, 3),  # 4-6  -> CTAS 3
            (2, 4),  # 2-3  -> CTAS 4
            (0, 5)   # 0-1  -> CTAS 5
        ]

    def calculate_urgency(self, data: Dict[str, Any]) -> int:
        """
        Calculates CTAS level based on provided patient data.
        
        Data schema:
        - gcs: int (3-15)
        - spo2: float (0-100)
        - active_seizure: bool
        - uncontrollable_hemorrhage: bool
        - heart_rate: int
        - systolic_bp: int
        - respiratory_rate: int
        - temperature: float
        - consciousness: str ('alert', 'verbal', 'pain', 'unresponsive')
        - primary_complaint: str
        - pain_score: int (0-10)
        - age: int
        - history: List[str] (e.g., ['chronic_disease', 'stroke', 'pregnancy'])
        """
        
        # Step 1: Red-Flag Override (CTAS 1)
        if self._is_ctas1_override(data):
            return 1
            
        # Step 2: Weighted Clinical Scoring
        vitals_score = self._score_vitals(data)
        complaint_score = self._score_complaint(data)
        risk_score = self._score_risks(data)
        age_adj = self._age_adjustment(data)
        
        total_score = vitals_score + complaint_score + risk_score + age_adj
        
        # Step 3: Mapping
        for threshold, level in self.MAPPING:
            if total_score >= threshold:
                return level
        
        return 5

    def _is_ctas1_override(self, data: Dict[str, Any]) -> bool:
        """Check for immediate life-threatening conditions."""
        if data.get('consciousness') == 'unresponsive':
            return True
        if data.get('spo2', 100) < 90:
            return True
        if data.get('active_seizure'):
            return True
        if data.get('uncontrollable_hemorrhage'):
            return True
        if data.get('resp_distress') == 'severe':
            return True
        return False

    def _score_vitals(self, data: Dict[str, Any]) -> int:
        """Scores vital instability."""
        points = 0
        
        hr = data.get('heart_rate', 70)
        sbp = data.get('systolic_bp', 120)
        rr = data.get('respiratory_rate', 16)
        spo2 = data.get('spo2', 98)
        cons = data.get('consciousness', 'alert')

        # Refined thresholds per user's scoring rules
        # Severe (+5), Moderate (+3), Mild (+1)
        
        # Spo2 Hypoxia
        if spo2 < 90: points += 5
        elif spo2 < 92: points += 3
        elif spo2 < 95: points += 1
        
        # Consciousness
        if cons in ['unresponsive', 'pain']: points += 5
        elif cons == 'verbal': points += 3
        
        # Systolic BP
        if sbp < 80: points += 5
        elif sbp < 90: points += 3
        elif sbp < 100: points += 1
        
        # Respiratory Rate
        if rr > 35: points += 5
        elif rr > 30: points += 3
        elif rr > 24: points += 1
        
        # Heart Rate
        if hr > 130: points += 5
        elif hr > 120: points += 3
        elif hr > 100: points += 1
            
        return points

    def _score_complaint(self, data: Dict[str, Any]) -> int:
        """Scores symptom severity and pain."""
        complaint = data.get('primary_complaint', '').lower()
        score = 0
        
        if 'chest pain' in complaint or 'stroke' in complaint:
            score = 4
        elif 'abdominal pain' in complaint:
            score = 3
        elif 'injury' in complaint or 'trauma' in complaint:
            score = 2
        else:
            score = 1
            
        # Pain adjustment
        pain = data.get('pain_score', 0)
        if pain >= 8:
            score += 2
        elif pain >= 5:
            score += 1
            
        return score

    def _score_risks(self, data: Dict[str, Any]) -> int:
        """Scores risk modifiers."""
        score = 0
        history = data.get('history', [])
        
        if 'chronic_disease' in history:
            score += 1
        if 'immunocompromised' in history:
            score += 1
        if 'pregnancy' in history:
            score += 2
        if 'stroke_history' in history:
            score += 1
            
        return score

    def _age_adjustment(self, data: Dict[str, Any]) -> int:
        """Adjusts score for age vulnerabilities."""
        age = data.get('age', 30)
        if age > 65 or age < 18:
            return 1
        return 0
