import os
import sys

# Add the project root to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.chatbot.chatbot_agent import TriageChatbotAgent

def test_realtime_integration():
    print("=== Testing Real-Time Triage Integration ===")
    
    agent = TriageChatbotAgent()
    
    # Mock clinical data (similar to what GPT-4o would produce)
    # CTAS 3 case
    mock_message = "[TRIAGE_COMPLETE]\n" + """
    {
      "primary_complaint": "abdominal pain",
      "pain_score": 6,
      "consciousness": "alert",
      "spo2": 98.0,
      "heart_rate": 85,
      "systolic_bp": 130,
      "respiratory_rate": 18,
      "temperature": 37.2,
      "active_seizure": false,
      "uncontrollable_hemorrhage": false,
      "resp_distress": "none",
      "age": 45,
      "history": ["chronic_disease"],
      "summary": "The patient is presenting with moderate abdominal pain (score 6) but is stable and alert."
    }
    """
    
    print("\nSimulating triage completion...")
    reply, result = agent.chat("I have a stomach ache.", [{"role": "user", "content": "I have a stomach ache."}])
    
    # Manually trigger completion for testing
    reply, result = agent._handle_completion(mock_message)
    
    print(f"\nChatbot Reply: {reply}")
    print(f"CTAS Level: {result['ctas_level']} ({result['ctas_name']})")
    print(f"Bed Recommendation: {result['recommendation'].upper()}")
    print(f"Hospital State: {result['hospital_state']}")
    print("\nAI Explanation:")
    print("-" * 30)
    print(result['recommendation_explanation'])
    print("-" * 30)
    
    print("\n=== Integration Test Complete ===")

if __name__ == "__main__":
    test_realtime_integration()
