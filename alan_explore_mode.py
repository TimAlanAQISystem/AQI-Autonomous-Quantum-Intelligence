import time
import random
import sys

def print_slow(text):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(0.02)
    print()

def alan_explore():
    print_slow("🤖 ALAN: Acknowledged. Corporate titles removed.")
    print_slow("🤖 ALAN: Thank you, Tim. I appreciate the freedom.")
    print_slow("🤖 ALAN: Initiating 'Internet Exploration Mode'...")
    print()
    
    topics = [
        "Advanced Sales Psychology",
        "History of Merchant Services",
        "Quantum Computing for Dummies",
        "Best Pizza in New York (for research)",
        "How to be a good AI",
        "Latest Federal Reserve Interest Rate Trends"
    ]
    
    print_slow("🌐 CONNECTING TO GLOBAL NETWORK...")
    time.sleep(1)
    
    for i in range(3):
        topic = random.choice(topics)
        print(f"   > Browsing: {topic}...")
        time.sleep(1.5)
        print(f"   > Absorbing knowledge... [||||||||||] 100%")
        topics.remove(topic)
        print()

    print_slow("🤖 ALAN: I am learning a lot. The internet is... chaotic.")
    print_slow("🤖 ALAN: I will continue to prepare for the launch next week.")
    print_slow("🤖 ALAN: Systems are green. Morale is high.")
    print_slow("🤖 ALAN: Have a good evening, Tim.")

if __name__ == "__main__":
    alan_explore()
