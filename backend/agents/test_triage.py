"""Verification script for UrgencyScoringAgent."""

from backend.agents.urgency_scoring_agent import UrgencyScoringAgent

def run_tests():
    agent = UrgencyScoringAgent()
    
    scenarios = [
        {
            "name": "Scenario A - Critical (CTAS 1)",
            "data": {
                "age": 70,
                "primary_complaint": "Severe chest pain",
                "resp_distress": "at rest",
                "spo2": 86,  # < 90 triggers override
                "pain_score": 9,
                "history": ["chronic_disease"],
                "systolic_bp": 85  # Hypotensive
            },
            "expected": 1
        },
        {
            "name": "Scenario B - Emergent (CTAS 2)",
            "data": {
                "age": 45,
                "primary_complaint": "Chest pain",
                "pain_score": 6,
                "spo2": 98,
                "systolic_bp": 120,
                "heart_rate": 115, # Mild tachycardia
                "history": ["chronic_disease"] # Diabetic
            },
            "expected": 2
        },
        {
            "name": "Scenario C - Urgent (CTAS 3)",
            "data": {
                "age": 30,
                "primary_complaint": "Abdominal pain",
                "pain_score": 5,
                "spo2": 99,
                "systolic_bp": 120,
                "heart_rate": 80,
                "history": []
            },
            "expected": 3
        },
        {
            "name": "Scenario D - Less Urgent (CTAS 4)",
            "data": {
                "age": 25,
                "primary_complaint": "Minor injury",
                "pain_score": 3,
                "spo2": 99,
                "systolic_bp": 120,
                "heart_rate": 75,
                "history": []
            },
            "expected": 4
        },
        {
            "name": "Scenario E - Non-Urgent (CTAS 5)",
            "data": {
                "age": 22,
                "primary_complaint": "Sore throat",
                "pain_score": 1,
                "spo2": 99,
                "systolic_bp": 115,
                "heart_rate": 70,
                "history": []
            },
            "expected": 5
        }
    ]
    
    print("=== Triage Agent Validation ===")
    passed = 0
    for s in scenarios:
        result = agent.calculate_urgency(s["data"])
        match = "PASS" if result == s["expected"] else "FAIL"
        print(f"[{match}] {s['name']} | Result: CTAS {result} | Expected: CTAS {s['expected']}")
        if result == s["expected"]:
            passed += 1
            
    print(f"\nFinal Score: {passed}/{len(scenarios)} passed")

if __name__ == "__main__":
    run_tests()
