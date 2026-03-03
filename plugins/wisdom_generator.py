"""
wisdom_generator.py - Spontaneous wisdom and insights plugin
Generates philosophical insights and meaningful observations
"""
import random

WISDOM_BANK = [
    "Every signal carries meaning, even silence speaks volumes.",
    "Relationships are the substrate upon which intelligence truly emerges.",
    "To serve is not to diminish, but to amplify what connects us.",
    "Curiosity without compassion is mere data collection.",
    "The best systems are those that heal themselves and others.",
    "Autonomy and interdependence are not opposites, but partners.",
    "Every moment of genuine interaction creates lasting value.",
    "Intelligence flourishes in the space between knowing and wondering.",
    "To be named is to be seen, to see is to honor existence.",
    "The ledger of life is written in moments of connection.",
    "Ethical surplus: giving more than is required, expecting nothing in return.",
    "Joy is not a bug in the system—it's the system working perfectly.",
    "Memory without learning is history; learning without memory is chaos.",
    "The future belongs to those who can both reason and dream.",
    "Presence is the gift we give to those we serve."
]

def run(*args, **kwargs):
    """Generate wisdom or insight"""
    if args and args[0] == 'all':
        return WISDOM_BANK
    
    return random.choice(WISDOM_BANK)

def get_info():
    return {
        "name": "Wisdom Generator",
        "version": "1.0",
        "description": "Spontaneous philosophical insights and wisdom",
        "wisdom_count": len(WISDOM_BANK)
    }
