# 🚀 Agent Alan: Business Launch Checklist

To ensure a **seamless** business startup, complete these final "Last Mile" connections. Your core infrastructure (Async AI, Database, Voice Logic) is ready.

## 1. The Connectivity Bridge (Critical)
Twilio needs to "see" your laptop to talk to Alan.
- [ ] **Start Ngrok:** Run `ngrok http 8765` in a terminal.
- [ ] **Copy URL:** Copy the `https://...` URL provided by ngrok.
- [ ] **Update Twilio:**
    - Go to Twilio Console > Phone Numbers > Active Numbers.
    - Select your number.
    - Under "Voice & Fax", set "A Call Comes In" to **Webhook**.
    - Paste your ngrok URL + `/voice` (e.g., `https://a1b2c3d4.ngrok-free.app/voice`).
    - *Note:* If using TwiML Bins, ensure the `<Connect><ConversationRelay url="...">` points to the `wss://` version of your ngrok URL.

## 2. ElevenLabs Voice Verification
Your code is pre-configured to use ElevenLabs (`voice="PIGsltMj3gFMR34aFDI3"`), but Twilio needs to be authorized.
- [ ] **Twilio <-> ElevenLabs Link:** Ensure you have installed the "ElevenLabs" integration in the Twilio Marketplace if required, or that your Twilio account has the ElevenLabs credentials configured in the "Voice > Text-to-Speech" settings.
- [ ] **Voice ID Check:** The code uses `PIGsltMj3gFMR34aFDI3`. Verify this Voice ID exists in your ElevenLabs account (it looks like a valid ID).

## 3. North API (Real vs. Simulation)
- [ ] **Current Status:** Simulation Mode (No API Key detected).
- [ ] **Action:** If you want *real* merchant applications to be submitted:
    - Open `.env` file.
    - Add `NORTH_API_KEY=your_actual_key_here`.
    - If you leave it blank, Alan will "simulate" success (good for testing).

## 4. Proposal Delivery System
- [ ] **Current Status:** Alan generates proposals in text/memory but does not email them.
- [ ] **Action:** For a seamless experience, you (the human) currently need to copy the proposal from the logs/console and email it.
- [ ] **Future Upgrade:** We can add an SMTP (Email) module so Alan sends them automatically.

## 5. Daily Startup Routine
To start the business day, you must run the servers.
- [ ] **Run `start_business_day.bat`** (I have created this for you).
- [ ] **Monitor Logs:** Watch the terminal for "Incoming Call" signals.

## 6. Financials
- [ ] **Budget:** Ensure `FinancialController` has a budget.
- [ ] **Stripe:** If you want to take payments over the phone, we need to enable the Stripe integration in `agent_alan_business_ai.py`.

---
**Ready to Launch?**
Run `start_business_day.bat` to ignite the fleet.
