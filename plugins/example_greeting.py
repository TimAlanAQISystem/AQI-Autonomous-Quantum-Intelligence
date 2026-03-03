"""
example_greeting.py - Example plugin for Agent X
Demonstrates the plugin system
"""

def run(*args, **kwargs):
    """Main plugin entry point"""
    if args:
        name = args[0]
        return f"Hello, {name}! Greetings from Agent X plugin system."
    return "Hello! This is Agent X's greeting plugin."

def get_info():
    """Plugin metadata"""
    return {
        "name": "Greeting Plugin",
        "version": "1.0",
        "description": "Provides personalized greetings"
    }
