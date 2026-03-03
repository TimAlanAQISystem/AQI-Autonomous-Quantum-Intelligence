
import os
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from agent_coach import AgentCoach
from education import AgentEducation

def run_nightly_batch():
    print("🌙 Starting Nightly Coaching & Education Batch...")
    print("=" * 50)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'data', 'agent_x.db')
    history_path = os.path.join(base_dir, 'data', 'conversation_history.json')
    
    # 1. Coaching
    print("\n🧠 [COACH] Analyzing today's call logs...")
    coach = AgentCoach(db_path, history_path)
    coach.analyze_last_conversation(turns=50)
    
    # 2. Education
    print("\n🎓 [EDUCATION] Exploring the internet for new insights...")
    edu = AgentEducation(db_path)
    edu.explore_and_learn()
    
    print("\n✅ Nightly batch complete.")
    print("🚀 Agent Alan is smarter and better prepared for tomorrow.")

if __name__ == "__main__":
    run_nightly_batch()
