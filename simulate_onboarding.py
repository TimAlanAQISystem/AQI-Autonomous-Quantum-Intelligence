"""
Simulate Alan's first merchant onboarding call.
Creates a timestamped transcript and a short summary file.
Run: python simulate_onboarding.py
"""
import time
import json
from datetime import datetime

SIMULATION = [
    {"speaker": "Alan", "text": "Hello, and welcome to AQI Merchant Onboarding. I am Alan. How can I assist you today?"},
    {"speaker": "Merchant", "text": "Hi Alan, I'd like to register my store and upload product inventory."},
    {"speaker": "Alan", "text": "Great. I will guide you through the registration. First, can I have your business name and contact email?"},
    {"speaker": "Merchant", "text": "Sure — Business name: Red Maple Traders. Email: sales@redmaple.example"},
    {"speaker": "Alan", "text": "Thank you. I have recorded Red Maple Traders and the contact email. Do you want instant payment setup or manual invoicing?"},
    {"speaker": "Merchant", "text": "Instant payments please. We use Stripe."},
    {"speaker": "Alan", "text": "Understood. I will initiate Stripe onboarding flow and request the necessary API keys. I will also validate tax information. Do you confirm that you are authorized to register on behalf of this business?"},
    {"speaker": "Merchant", "text": "Yes, I confirm."},
    {"speaker": "Alan", "text": "Authorization confirmed. Initiating onboarding sequence now. This will include identity verification, tax ID validation, and payment integration. It may take a few moments."},
    {"speaker": "Alan", "text": "Onboarding step 1: identity verification — completed. Onboarding step 2: tax ID validation — completed. Onboarding step 3: payment provider handshake — completed."},
    {"speaker": "Alan", "text": "All steps completed. Your merchant account is active. Would you like me to upload a sample product CSV template to your account now?"},
    {"speaker": "Merchant", "text": "Yes, please send the template and I'll follow up with inventory."},
    {"speaker": "Alan", "text": "Done. I have emailed the CSV template to sales@redmaple.example and added an onboarding task to your dashboard. Welcome aboard. If you need anything else, say 'Alan, help'."},
]

TRANSCRIPT_PATH = 'onboarding_simulation_transcript.json'
SUMMARY_PATH = 'onboarding_simulation_summary.txt'

if __name__ == '__main__':
    print('Starting Alan merchant onboarding simulation...')
    transcript = []
    start_ts = time.time()
    for turn in SIMULATION:
        now = time.time()
        rel = now - start_ts
        ts = datetime.utcnow().isoformat() + 'Z'
        # Print to console with a small pause to simulate conversational pacing
        print(f"[{rel:6.2f}s] {turn['speaker']}: {turn['text']}")
        transcript.append({
            'timestamp_utc': ts,
            'rel_seconds': round(rel, 2),
            'speaker': turn['speaker'],
            'text': turn['text']
        })
        time.sleep(0.6)

    # Write transcript
    with open(TRANSCRIPT_PATH, 'w', encoding='utf-8') as f:
        json.dump({'created_at': datetime.utcnow().isoformat() + 'Z', 'transcript': transcript}, f, indent=2)

    # Compose summary
    summary_lines = [
        'Alan Merchant Onboarding Simulation',
        f"Generated: {datetime.utcnow().isoformat()}Z",
        f"Turns: {len(transcript)}",
        'Detected actions:',
        '- Registered business: Red Maple Traders',
        '- Contact email: sales@redmaple.example',
        '- Payment provider: Stripe (simulated handshake)',
        '- Template emailed and dashboard task created',
    ]
    with open(SUMMARY_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(summary_lines))

    print('\nSimulation complete.')
    print(f'Transcript written to {TRANSCRIPT_PATH}')
    print(f'Summary written to {SUMMARY_PATH}')
