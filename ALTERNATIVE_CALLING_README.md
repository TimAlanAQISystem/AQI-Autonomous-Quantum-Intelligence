# Agent X Alternative Calling System

Since Twilio voice calling is currently disabled on your account, Agent X now supports multiple alternative calling methods that don't require external telecom services.

## Available Calling Modes

### 1. **Mock Calling** (Default)
- **Purpose**: Instant testing and development
- **How it works**: Simulates complete conversations with AI responses
- **Use case**: Testing AI responses, development, demos
- **No external dependencies**

### 2. **Local Audio Simulation**
- **Purpose**: Audio playback testing
- **How it works**: Uses local TTS to simulate call audio
- **Use case**: Testing TTS integration, audio workflows
- **Requires**: pyttsx3 or system TTS

### 3. **WebRTC Browser Calling**
- **Purpose**: Real-time voice interaction through browser
- **How it works**: Direct browser-to-system audio connection
- **Use case**: Live testing, demonstrations, voice interfaces
- **Requires**: Modern web browser with microphone access

### 4. **Twilio Calling** (When Available)
- **Purpose**: Production voice calling
- **How it works**: Traditional telecom API integration
- **Use case**: Real phone calls to actual numbers
- **Requires**: Twilio account with voice calling enabled

### 5. **SMS Messaging**
- **Purpose**: Text message communication and notifications
- **How it works**: Direct SMS sending via Twilio API
- **Use case**: Lead follow-up, appointment reminders, status updates
- **Requires**: Twilio account with SMS enabled (currently working)

## Quick Start

### 1. Start Agent X Server
```bash
python run_agent_service_full.py
```

### 2. Test Alternative Calling
```bash
python test_alternative_calling.py
```

### 3. Make Calls Using Different Modes

#### Using PowerShell Script
```powershell
# Mock call (default)
.\tools\fire_call.ps1 -Live -Mode mock

# Local simulation
.\tools\fire_call.ps1 -Live -Mode local_simulation

# WebRTC call
.\tools\fire_call.ps1 -Live -Mode webrtc
```

#### Using HTTP API
```bash
# Mock call
curl -X POST http://127.0.0.1:8777/call \
  -H "Content-Type: application/json" \
  -d '{"live": true, "to": "+14062102346", "call_mode": "mock"}'

# WebRTC call
curl -X POST http://127.0.0.1:8777/call \
  -H "Content-Type: application/json" \
  -d '{"live": true, "to": "+14062102346", "call_mode": "webrtc"}'
```

### 4. Test SMS Functionality
```bash
python test_sms.py
```

### 5. Send SMS Messages

#### Using HTTP API
```bash
# Send SMS message
curl -X POST http://127.0.0.1:8777/sms \
  -H "Content-Type: application/json" \
  -d '{"to": "+14062102346", "text": "Hello from Agent X!"}'

# Send test SMS (convenience endpoint)
curl -X POST http://127.0.0.1:8777/sms/test \
  -H "Content-Type: application/json" \
  -d '{"to": "+14062102346"}'
```

## Mode Details

### Mock Calling
```json
{
  "ok": true,
  "mode": "mock",
  "result": {
    "status": "success",
    "call_id": "uuid-here",
    "conversation": [
      {"speaker": "agent", "message": "Hello from Agent X!", "timestamp": 1234567890},
      {"speaker": "user", "message": "Hi, I'm interested...", "timestamp": 1234567891},
      {"speaker": "agent", "message": "Great! How can I help?", "timestamp": 1234567892}
    ]
  }
}
```

### WebRTC Calling
1. Make API call with `call_mode: "webrtc"`
2. Get response with WebRTC session URL
3. Open URL in browser: `http://127.0.0.1:8777/webrtc-call/{call_id}`
4. Allow microphone permissions
5. Click "Start Call" for real-time voice interaction

### Local Simulation
- Plays audio through system speakers
- Simulates call flow with TTS
- Logs conversation in server logs
- Useful for testing audio integration

## API Reference

### POST /call
Make a call using any supported mode.

**Parameters:**
- `live` (boolean): True for live calling modes
- `to` (string): Target identifier/phone number
- `text` (string): Call script/message
- `call_mode` (string): "mock", "local_simulation", "webrtc", or "twilio"

**Response:**
```json
{
  "ok": true,
  "mode": "mock|local_simulation|webrtc|twilio",
  "result": { /* mode-specific result */ }
}
```

### POST /sms
Send an SMS message using Twilio.

**Parameters:**
- `to` (string, required): Recipient phone number
- `text` (string, required): SMS message content
- `twilio_account_sid` (string, optional): Override account SID
- `twilio_auth_token` (string, optional): Override auth token
- `twilio_phone_number` (string, optional): Override sender number

**Response:**
```json
{
  "ok": true,
  "message_sid": "SMxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "status": "queued|sent|delivered|failed",
  "to": "+1234567890",
  "from": "+18883277213"
}
```

### POST /sms/test
Send a test SMS message (convenience endpoint).

**Parameters:**
- `to` (string, required): Test recipient phone number
- `text` (string, optional): Custom test message (uses default if not provided)
- `twilio_account_sid` (string, optional): Override account SID
- `twilio_auth_token` (string, optional): Override auth token
- `twilio_phone_number` (string, optional): Override sender number

**Response:** Same as `/sms` endpoint

### GET /webrtc-call/{call_id}
Serve WebRTC call interface for browser-based calling.

### GET /status
Check if Agent X server is running and initialized.

## Development & Testing

### Running Tests
```bash
# Run all alternative calling tests
python test_alternative_calling.py

# Run SMS functionality tests
python test_sms.py

# Test specific SMS functionality
python -c "
import requests
response = requests.post('http://127.0.0.1:8777/sms/test', 
                        json={'to': '+14062102346'})
print('SMS Test Result:', response.json())
"
```

### Adding New Calling Modes
1. Add handler in `alternative_calling.py`
2. Add API handler in `control_api.py`
3. Update `CallRequest` model if needed
4. Test with `test_alternative_calling.py`

## Architecture

```
Agent X Server (FastAPI)
├── control_api.py          # Main API endpoints (calls + SMS)
├── alternative_calling.py  # Alternative calling logic
├── call_harness.py         # Twilio integration (when available)
├── test_alternative_calling.py  # Calling mode tests
├── test_sms.py             # SMS functionality tests
└── test_twilio.py          # Twilio validation tests
```

## Benefits of Alternative Calling

1. **No External Dependencies**: Works without Twilio or telecom services
2. **Instant Testing**: Mock mode provides immediate results
3. **Audio Validation**: Local simulation tests TTS/audio systems
4. **Real-time Interaction**: WebRTC enables live voice testing
5. **Text Communication**: SMS provides reliable messaging capabilities
6. **Development Flexibility**: Multiple modes for different use cases
7. **Cost Effective**: No per-call charges during development

## Future Integration

When Twilio voice calling becomes available:
- Switch `call_mode` back to "twilio"
- All existing functionality will work
- Alternative modes remain available for testing

## Troubleshooting

### Server Not Running
```
Error: Cannot connect to Agent X server
Solution: python run_agent_service_full.py
```

### TTS Not Working
```
Error: pyttsx3 not available
Solution: pip install pyttsx3
```

### WebRTC Not Connecting
```
Error: Browser permissions denied
Solution: Allow microphone access in browser
```

### SMS Not Working
```
Error: Twilio credentials invalid
Solution: Check TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER environment variables
```

### SMS Delivery Issues
```
Error: Message not delivered
Solution: Verify recipient number format (+country_code), check Twilio account status
```

### Mock Calls Not Working
```
Error: Agent not initialized
Solution: Ensure Agent X server is fully started
```

---

**Note**: This alternative calling system allows you to continue developing and testing Agent X's AI capabilities while waiting for Twilio voice calling to be enabled. All modes integrate with the same AI agent backend, ensuring consistent behavior across different calling methods.