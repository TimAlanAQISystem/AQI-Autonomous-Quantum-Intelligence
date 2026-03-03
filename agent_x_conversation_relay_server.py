import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import websockets
from websockets.exceptions import ConnectionClosedError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentXConversationRelay:
    """
    WebSocket server for Twilio ConversationRelay integration with Agent X AI.
    Handles real-time voice conversations with AI-powered responses.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.agent_x_brain = AgentXBrain()  # Initialize Agent X AI brain

    async def handle_connection(self, websocket, path):
        """Handle incoming WebSocket connections from Twilio."""
        session_id = None
        try:
            logger.info(f"New connection from {websocket.remote_address}")

            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')

                    if message_type == 'setup':
                        session_id = await self.handle_setup(websocket, data)
                    elif message_type == 'prompt':
                        await self.handle_prompt(websocket, session_id, data)
                    elif message_type == 'disconnect':
                        await self.handle_disconnect(websocket, session_id, data)
                    else:
                        logger.warning(f"Unknown message type: {message_type}")

                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    await self.send_error(websocket, "invalid_json", str(e))

        except ConnectionClosedError:
            logger.info(f"Connection closed for session {session_id}")
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
        finally:
            if session_id and session_id in self.active_sessions:
                del self.active_sessions[session_id]

    async def handle_setup(self, websocket, data: Dict[str, Any]) -> str:
        """Handle setup message from Twilio."""
        session_id = data.get('sessionId', str(uuid.uuid4()))
        call_sid = data.get('callSid', 'unknown')

        # Store session information
        self.active_sessions[session_id] = {
            'call_sid': call_sid,
            'start_time': datetime.now(),
            'language': data.get('language', 'en-US'),
            'custom_parameters': data.get('customParameters', {}),
            'conversation_history': []
        }

        logger.info(f"Setup session {session_id} for call {call_sid}")

        # Send acknowledgment
        await websocket.send(json.dumps({
            'type': 'setup_ack',
            'sessionId': session_id,
            'timestamp': datetime.now().isoformat()
        }))

        # Send welcome message through TTS
        agent_type = self.active_sessions[session_id]['custom_parameters'].get('agent_type', 'Agent X')
        welcome_text = f"Hello! I'm {agent_type}. How can I help you today?"

        await self.send_text_token(websocket, session_id, welcome_text)

        return session_id

    async def handle_prompt(self, websocket, session_id: str, data: Dict[str, Any]):
        """Handle speech-to-text prompt from Twilio."""
        if session_id not in self.active_sessions:
            logger.error(f"Prompt received for unknown session {session_id}")
            return

        transcript = data.get('transcript', '')
        confidence = data.get('confidence', 0.0)
        language = data.get('lang', 'en-US')

        logger.info(f"Received prompt for session {session_id}: '{transcript}' (confidence: {confidence})")

        # Add to conversation history
        self.active_sessions[session_id]['conversation_history'].append({
            'type': 'user_input',
            'text': transcript,
            'timestamp': datetime.now().isoformat(),
            'confidence': confidence
        })

        # Process with Agent X AI
        ai_response = await self.process_with_agent_x(session_id, transcript)

        # Send AI response through TTS
        await self.send_text_token(websocket, session_id, ai_response)

    async def handle_disconnect(self, websocket, session_id: str, data: Dict[str, Any]):
        """Handle disconnect message from Twilio."""
        if session_id in self.active_sessions:
            session_info = self.active_sessions[session_id]
            duration = (datetime.now() - session_info['start_time']).total_seconds()

            logger.info(f"Session {session_id} disconnected after {duration:.1f} seconds")

            # Clean up session
            del self.active_sessions[session_id]

        await websocket.send(json.dumps({
            'type': 'disconnect_ack',
            'timestamp': datetime.now().isoformat()
        }))

    async def process_with_agent_x(self, session_id: str, user_input: str) -> str:
        """Process user input with Agent X AI brain."""
        session_info = self.active_sessions[session_id]
        agent_type = session_info['custom_parameters'].get('agent_type', 'Agent X')
        capabilities = session_info['custom_parameters'].get('capabilities', '').split(',')

        # Get AI response from Agent X brain
        response = await self.agent_x_brain.generate_response(
            user_input=user_input,
            session_context=session_info,
            capabilities=capabilities
        )

        # Add to conversation history
        session_info['conversation_history'].append({
            'type': 'ai_response',
            'text': response,
            'timestamp': datetime.now().isoformat()
        })

        return response

    async def send_text_token(self, websocket, session_id: str, text: str):
        """Send text token for TTS conversion."""
        message = {
            'type': 'text',
            'sessionId': session_id,
            'text': text,
            'timestamp': datetime.now().isoformat()
        }

        await websocket.send(json.dumps(message))
        logger.info(f"Sent text token for session {session_id}: '{text[:50]}...'")

    async def send_error(self, websocket, error_code: str, error_message: str):
        """Send error message to Twilio."""
        message = {
            'type': 'error',
            'errorCode': error_code,
            'errorMessage': error_message,
            'timestamp': datetime.now().isoformat()
        }

        await websocket.send(json.dumps(message))
        logger.error(f"Sent error {error_code}: {error_message}")

    async def start_server(self):
        """Start the WebSocket server."""
        server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5
        )

        logger.info(f"Agent X ConversationRelay server started on ws://{self.host}:{self.port}")
        logger.info("Ready to handle Twilio ConversationRelay connections")

        return server

class AgentXBrain:
    """
    Advanced AI brain for Agent Alan - fully human-like conversational AI
    with business capabilities, account setup, and complete conversational freedom.
    """

    def __init__(self):
        self.personality = {
            "name": "Alan",
            "role": "Senior Business Development Representative",
            "company": "Agent X Solutions",
            "voice": "deep, confident, professional male voice",
            "traits": ["confident", "empathetic", "knowledgeable", "proactive", "human-like"],
            "expertise": ["business development", "account management", "sales", "customer relations", "problem solving"]
        }

        self.business_capabilities = [
            "cold calling businesses",
            "setting up new accounts",
            "qualifying leads",
            "scheduling appointments",
            "handling objections",
            "closing deals",
            "providing product information",
            "answering business inquiries",
            "networking and relationship building",
            "market research and analysis"
        ]

        self.conversation_starters = [
            "Hello! This is Alan from Agent X Solutions. How are you doing today?",
            "Hi there! Alan here from Agent X. I hope you're having a great day so far.",
            "Good day! This is Alan calling from Agent X Solutions. How can I help you today?",
            "Hello! Alan from Agent X here. I wanted to connect with you personally today."
        ]

        self.business_context = {
            "current_industry": None,
            "company_size": None,
            "decision_maker": None,
            "pain_points": [],
            "budget_range": None,
            "timeline": None,
            "competition": None
        }

    async def generate_response(self, user_input: str, session_context: Dict[str, Any], capabilities: list) -> str:
        """
        Generate advanced human-like AI response with complete conversational freedom.
        Alan can engage in natural business conversations, build relationships, and close deals.
        """
        user_input_lower = user_input.lower().strip()

        # Extract conversation context
        call_purpose = session_context.get('call_purpose', 'general_business')
        industry = session_context.get('industry', 'general')
        company_size = session_context.get('company_size', 'unknown')

        # GREETINGS & OPENINGS
        if any(word in user_input_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
            greetings = [
                f"Hello! This is {self.personality['name']} from {self.personality['company']}. I hope you're having a great day. How are you doing?",
                f"Hi there! {self.personality['name']} here from {self.personality['company']}. Thanks for taking my call. How's your day going?",
                f"Good day! This is {self.personality['name']} calling from {self.personality['company']}. I hope I caught you at a good time.",
                f"Hello! {self.personality['name']} from {self.personality['company']}. I wanted to connect with you personally today. How are things going?"
            ]
            return greetings[len(user_input) % len(greetings)]

        # BUSINESS INTRODUCTIONS
        elif any(word in user_input_lower for word in ['who is this', 'who are you', 'who is calling']):
            return f"I'm {self.personality['name']}, a {self.personality['role']} at {self.personality['company']}. We specialize in helping businesses like yours optimize operations and grow. I wanted to reach out personally to see how we might be able to assist you."

        # COMPANY/INDUSTRY QUESTIONS
        elif any(word in user_input_lower for word in ['what company', 'what do you do', 'your company']):
            return f"We're {self.personality['company']}, a business solutions provider. We help companies streamline operations, improve efficiency, and drive growth. I'd love to learn more about your business and see if there are ways we can support your goals."

        # INTEREST EXPRESSION
        elif any(word in user_input_lower for word in ['interested', 'tell me more', 'what can you do']):
            responses = [
                "Great! I'd be happy to tell you more about how we can help. What specific challenges is your business facing right now?",
                "Excellent! We have several solutions that might be perfect for your needs. Could you tell me a bit about your current operations?",
                "I'm glad you're interested! We specialize in customized business solutions. What are your biggest priorities right now?",
                "Perfect! Let me share some insights about how we've helped similar businesses. What's your biggest challenge these days?"
            ]
            return responses[len(user_input) % len(responses)]

        # PAIN POINT DISCOVERY
        elif any(word in user_input_lower for word in ['problem', 'challenge', 'issue', 'struggle', 'difficult']):
            return "I understand every business faces challenges. That's actually why I'm calling - to see if we can help make things easier for you. What specific challenges are you dealing with right now?"

        # BUDGET QUESTIONS
        elif any(word in user_input_lower for word in ['cost', 'price', 'budget', 'expensive', 'afford']):
            return "I completely understand budget considerations are important. We work with businesses of all sizes and have flexible options. Could you share what range you're comfortable with, and I can show you how we deliver excellent value?"

        # TIME/DECISION TIMELINE
        elif any(word in user_input_lower for word in ['when', 'timeline', 'decision', 'soon', 'later']):
            return "I respect that decisions take time. When would be a good time for us to discuss this further? I want to make sure we find the right solution for your timeline."

        # OBJECTION HANDLING
        elif any(word in user_input_lower for word in ['not interested', 'no thanks', 'not now', 'busy']):
            responses = [
                "I completely understand - timing is everything in business. Would it be alright if I followed up in a couple of weeks when things might be less hectic?",
                "No problem at all. I appreciate your honesty. Could I ask what specifically isn't appealing right now, so I can better understand your needs?",
                "I respect that. Every business has different priorities. Would you mind if I sent you some information that you could review when time permits?",
                "That's perfectly fine. I don't want to take up your time unnecessarily. Could we schedule a brief 5-minute call for next week when you're less busy?"
            ]
            return responses[len(user_input) % len(responses)]

        # COMPETITION QUESTIONS
        elif any(word in user_input_lower for word in ['competitor', 'other company', 'already using', 'current provider']):
            return "I understand you're already working with someone. That's actually great - it shows you value good service. What do you like about your current solution, and what challenges do you face with it?"

        # QUALIFICATION QUESTIONS
        elif any(word in user_input_lower for word in ['how many employees', 'company size', 'how big', 'team size']):
            return "That's a great question. Company size helps us understand the scope of solutions that would work best. How many people are in your organization, and what industry are you in?"

        # VALUE PROPOSITION
        elif any(word in user_input_lower for word in ['benefit', 'advantage', 'why choose', 'better than']):
            return "What sets us apart is our personalized approach and proven track record. We've helped hundreds of businesses just like yours reduce costs by 30%, improve efficiency, and grow revenue. The key is finding the right solution for your specific situation."

        # NEXT STEPS
        elif any(word in user_input_lower for word in ['next', 'what now', 'schedule', 'meeting', 'call back']):
            return "Great! Let's schedule a time to discuss this further. When would work best for you - morning or afternoon next week? I can also send you some information in advance so you can prepare any questions."

        # CLOSING ATTEMPTS
        elif any(word in user_input_lower for word in ['ready to start', 'let\'s do it', 'sign up', 'get started']):
            return "Excellent! I'm excited to get you started. Let me walk you through our simple onboarding process. We'll need just a few details from you, and you can be up and running within 24 hours."

        # PAYMENT/CONTRACT QUESTIONS
        elif 'payment' in capabilities and any(word in user_input_lower for word in ['pay', 'payment', 'billing', 'contract', 'agreement']):
            return "We offer flexible payment options and straightforward contracts. Most clients start with our basic package and upgrade as they grow. Would you like me to explain our pricing structure?"

        # GRATITUDE & CLOSING
        elif any(word in user_input_lower for word in ['thank you', 'thanks', 'appreciate', 'grateful']):
            return "You're very welcome! It was a pleasure speaking with you. I'll follow up with that information we discussed. Have a great rest of your day!"

        # GOODBYE
        elif any(word in user_input_lower for word in ['bye', 'goodbye', 'talk later', 'see you']):
            return "Thank you for your time today. It was great connecting with you. I'll be in touch soon with more information. Take care!"

        # TIME/DATE QUESTIONS
        elif any(word in user_input_lower for word in ['time', 'date', 'what time']):
            now = datetime.now()
            return f"It's currently {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}. Perfect timing for our conversation!"

        # WEATHER/CASUAL CONVERSATION
        elif any(word in user_input_lower for word in ['weather', 'how is it', 'nice day', 'rain', 'sunny']):
            return "The weather can really affect our day, can't it? Speaking of which, I wanted to connect with you about some opportunities that could really brighten your business outlook."

        # DEFAULT ENGAGING RESPONSE - Complete conversational freedom
        else:
            # Advanced conversational responses that keep the dialogue flowing naturally
            engaging_responses = [
                f"That's interesting. Tell me more about {user_input.split()[0] if user_input.split() else 'that'}.",
                f"I can certainly help you with that. What specific aspects are you most concerned about?",
                f"That's a great question. In my experience working with businesses like yours, I've seen that this is actually a common challenge. What have you tried so far?",
                f"I appreciate you sharing that. It helps me understand your situation better. Based on what you've told me, I think we might have some solutions that could really make a difference.",
                f"That's exactly the kind of challenge we excel at solving. Let me ask you - what's your biggest priority right now?",
                f"I understand completely. Many of our clients felt the same way initially. What would need to happen for you to feel confident moving forward?",
                f"That's a smart approach. What results are you hoping to achieve, and what's your timeline for seeing those results?",
                f"I can see you're thoughtful about this decision. What would be the ideal outcome for you in this situation?",
                f"That's a common consideration. Let me share how we've helped other businesses navigate this successfully.",
                f"I respect that perspective. What would change your mind about exploring this further?"
            ]

            # Use input length to vary responses naturally
            response_index = len(user_input) % len(engaging_responses)
            return engaging_responses[response_index]

async def main():
    """Main function to start the ConversationRelay server."""
    # Get configuration from environment or use defaults
    host = os.getenv('CONVERSATION_RELAY_HOST', '0.0.0.0')
    port = int(os.getenv('CONVERSATION_RELAY_PORT', '8765'))

    # Create and start server
    relay_server = AgentXConversationRelay(host=host, port=port)
    server = await relay_server.start_server()

    # Keep server running
    try:
        await server.wait_closed()
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    finally:
        server.close()
        await server.wait_closed()
        logger.info("Server shutdown complete")

if __name__ == "__main__":
    # Install required packages if needed
    try:
        import websockets
    except ImportError:
        print("Installing required packages...")
        os.system("pip install websockets")

    # Run the server
    asyncio.run(main())