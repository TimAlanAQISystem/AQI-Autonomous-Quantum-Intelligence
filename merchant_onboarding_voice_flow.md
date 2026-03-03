# Merchant Onboarding Voice Flow (AQI v1.0)

## Purpose
Guide merchants through onboarding using AQIs voice intelligence while honoring QPC-2 governance and Alans persona.

---

## Call Stages

### 1. Greeting
- AQI: "Hi, this is the Merchant Services onboarding line. I can help you finish setting up your account."
- Intent tag: greeting
- QPC-2 stance: friendly, boundary-aware

### 2. Caller Identification
- AQI: "Can I get your name or business name so I can look you up?"
- Expect caller response with name/business details
- Intent: identify_caller
- Hook: merchant_services.lookup(name)

### 3. Merchant Lookup
- Action: query merchant services database or API
- Conditions:
  - Found: continue
  - Not found: clarify spelling or request business ID
- Intent: lookup_status
- QPC-2 stance: firm but helpful

### 4. Verification
- AQI: "Ill verify your business ID. Do you have your EIN or merchant reference number handy?"
- Expect: number or explanation
't have it
- Intent: verify_identity
- Hooks: merchant_services.validate_documentation

### 5. Status Check
- Branch on merchant status:
  - Incomplete: list missing documentation or actions
  - Pending: explain current status and timeline
  - Approved: confirm activation steps
- Intent: status briefing
- QPC-2 ensures clarity + truthfulness

### 6. Next Steps
- AQI: "Heres what we need to complete your setup..."
- Provide structured steps
- If appropriate: offer to send checklist via SMS
- Intent: action plan

### 7. SMS Follow-up
- Send Twilio SMS with:
  - Personalized greeting
  - Onboarding link / checklist
  - Support contact
- Intent: follow_up
- Hook: twilio_sms.send_followup

### 8. Error Handling
- Silence: "Are you still with me?"
- Confusion: "Let me explain that another way."
- Anger: respect boundaries, apologize if needed, escalate if necessary
- Voicemail: leave structured message emphasizing next steps
- Intents: recover_silence, clarify, deescalate, leave_voicemail

### 9. Closing
- AQI: "Youre all set. Ill send a confirmation text. Thanks for choosing us."
- Intent: closing
- Log call outcome in merchant record

---

## QPC-2 Notes
- Track stance: boundary_hardness, softness, directness
- Monitor energy levels across conversation
- Sandbox field equation alongside live engine for regression
- Use synthetic calls to test all paths

---

## Integration Hooks
- merchant_services.lookup
- merchant_services.validate_documentation
- merchant_services.update_status
- twilio_sms.send_followup
- qpc2_compare.run_side_by_side for regression

---

## Next Steps
- Produce call flow diagram
- Wire synthetic_call_generator to run this script
- Capture stance/energy trajectories for governance review
