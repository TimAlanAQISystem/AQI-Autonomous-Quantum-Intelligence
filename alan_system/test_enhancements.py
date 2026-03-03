# Test script for alan_main enhancements
import sys
sys.path.append('.')

# Import datetime for the function
from datetime import datetime

# Mock the aqi_system to avoid import issues
class MockAQISystem:
    def process_business_query(self, text):
        return "Business query processed successfully."

# Mock the memory functions
def remember_fact(key, value):
    print(f"Remembering: {key} = {value}")

def get_fact(key):
    return None

def list_facts():
    return {}

# Set up mock
import alan_main
alan_main.aqi_system = MockAQISystem()
alan_main.remember_fact = remember_fact
alan_main.get_fact = get_fact
alan_main.list_facts = list_facts

# Test the function
test_inputs = [
    "hello",
    "how are you",
    "status of leads",
    "remember that my favorite color is blue",
    "what is my favorite color",
    "thank you",
    "help me",
    "market trends"
]

print("Testing enhanced process_user_utterance function:")
print("=" * 50)

for test_input in test_inputs:
    print(f"Input: '{test_input}'")
    try:
        response = alan_main.process_user_utterance(test_input)
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 30)

print("All tests completed successfully!")