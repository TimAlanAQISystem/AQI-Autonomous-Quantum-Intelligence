"""
Alternative Calling System - No Twilio Required

This module provides multiple calling alternatives:
1. WebRTC Browser Calling - Real-time voice calls through browser
2. Local Audio Simulation - TTS playback for testing
3. Mock Calling System - Simulated calls for development
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from typing import Dict, List, Optional, Any
import os
import sys

logger = logging.getLogger(__name__)

class AlternativeCallSystem:
    """Alternative calling system that doesn't require Twilio"""

    def __init__(self):
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        self.call_history: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def create_webrtc_call(self, to_number: str, script: str, agent) -> Dict[str, Any]:
        """Create a WebRTC-based call session"""
        call_id = str(uuid.uuid4())

        call_data = {
            'call_id': call_id,
            'to': to_number,
            'script': script,
            'status': 'pending',
            'mode': 'webrtc',
            'created_at': time.time(),
            'webrtc_offer': None,
            'webrtc_answer': None,
            'agent_responses': [],
            'conversation': []
        }

        with self._lock:
            self.active_calls[call_id] = call_data

        # Generate WebRTC session description
        session_description = self._generate_webrtc_session(call_id, script)

        call_data.update({
            'status': 'ready',
            'webrtc_session': session_description,
            'instructions': self._get_webrtc_instructions(to_number)
        })

        return {
            'status': 'success',
            'call_id': call_id,
            'mode': 'webrtc',
            'session_description': session_description,
            'instructions': call_data['instructions']
        }

    def create_local_simulation(self, to_number: str, script: str, agent) -> Dict[str, Any]:
        """Create a local audio simulation call"""
        call_id = str(uuid.uuid4())

        call_data = {
            'call_id': call_id,
            'to': to_number,
            'script': script,
            'status': 'simulating',
            'mode': 'local_simulation',
            'created_at': time.time(),
            'simulation_steps': []
        }

        with self._lock:
            self.active_calls[call_id] = call_data

        # Start local simulation in background
        threading.Thread(
            target=self._run_local_simulation,
            args=(call_id, script, agent),
            daemon=True
        ).start()

        return {
            'status': 'success',
            'call_id': call_id,
            'mode': 'local_simulation',
            'message': 'Local simulation started. Check logs for audio playback.'
        }

    def create_mock_call(self, to_number: str, script: str, agent) -> Dict[str, Any]:
        """Create a completely mocked call for testing"""
        call_id = str(uuid.uuid4())

        # Generate mock conversation
        mock_conversation = self._generate_mock_conversation(script, agent, 'mock')

        call_data = {
            'call_id': call_id,
            'to': to_number,
            'script': script,
            'status': 'completed',
            'mode': 'mock',
            'created_at': time.time(),
            'conversation': mock_conversation,
            'duration': len(mock_conversation) * 3,  # 3 seconds per exchange
            'outcome': 'successful_mock_call'
        }

        with self._lock:
            self.active_calls[call_id] = call_data
            self.call_history.append(call_data)

        return {
            'status': 'success',
            'call_id': call_id,
            'mode': 'mock',
            'conversation': mock_conversation,
            'message': 'Mock call completed successfully'
        }

    def get_call_status(self, call_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific call"""
        with self._lock:
            return self.active_calls.get(call_id)

    def list_active_calls(self) -> List[Dict[str, Any]]:
        """List all active calls"""
        with self._lock:
            return list(self.active_calls.values())

    def _generate_webrtc_session(self, call_id: str, script: str) -> Dict[str, Any]:
        """Generate WebRTC session description"""
        return {
            'type': 'offer',
            'sdp': f'v=0\r\no=- {int(time.time())} 1 IN IP4 127.0.0.1\r\ns=AgentX Call {call_id}\r\nt=0 0\r\n',
            'call_id': call_id,
            'script': script,
            'webrtc_config': {
                'iceServers': [
                    {'urls': 'stun:stun.l.google.com:19302'},
                    {'urls': 'stun:stun1.l.google.com:19302'}
                ]
            }
        }

    def _get_webrtc_instructions(self, to_number: str) -> str:
        """Get instructions for WebRTC calling"""
        return f"""
        To complete this call to {to_number}:

        1. Open a WebRTC-compatible browser (Chrome, Firefox, Safari, Edge)
        2. Navigate to: http://localhost:8777/webrtc-call/{self.active_calls[list(self.active_calls.keys())[-1]]['call_id']}
        3. Allow microphone/camera permissions when prompted
        4. Click "Start Call" to initiate the voice connection
        5. The AI agent will respond to your voice in real-time

        Note: This creates a direct browser-to-browser connection for testing purposes.
        """

    def _run_local_simulation(self, call_id: str, script: str, agent):
        """Run local audio simulation"""
        try:
            # Import TTS capabilities
            try:
                import pyttsx3
                tts_engine = pyttsx3.init()
                tts_available = True
            except ImportError:
                tts_available = False
                logger.warning("pyttsx3 not available for local simulation")

            # Simulate call flow
            steps = [
                f"Calling {self.active_calls[call_id]['to']}...",
                "Phone ringing...",
                "Call connected",
                f"Speaking: {script}"
            ]

            for step in steps:
                logger.info(f"Call {call_id}: {step}")
                if tts_available:
                    tts_engine.say(step)
                    tts_engine.runAndWait()
                time.sleep(2)

            # Simulate conversation
            if agent:
                try:
                    # Simulate user response
                    simulated_user_response = "Hello, I'm interested in your services. Can you tell me more?"
                    logger.info(f"Call {call_id}: Simulated user response: {simulated_user_response}")

                    # Get agent response
                    agent_reply = agent.reason(simulated_user_response)
                    logger.info(f"Call {call_id}: Agent response: {agent_reply}")

                    if tts_available:
                        tts_engine.say(f"Agent says: {agent_reply}")
                        tts_engine.runAndWait()

                except Exception as e:
                    logger.error(f"Agent interaction failed: {e}")

            # Complete call
            with self._lock:
                self.active_calls[call_id]['status'] = 'completed'
                self.active_calls[call_id]['simulation_steps'] = steps
                self.call_history.append(self.active_calls[call_id])

            logger.info(f"Call {call_id}: Local simulation completed")

        except Exception as e:
            logger.error(f"Local simulation failed for call {call_id}: {e}")
            with self._lock:
                self.active_calls[call_id]['status'] = 'failed'
                self.active_calls[call_id]['error'] = str(e)

    def _generate_mock_conversation(self, script: str, agent, mode: str = 'mock') -> List[Dict[str, Any]]:
        """Generate a mock conversation for testing"""
        conversation = []

        # Initial agent greeting
        conversation.append({
            'speaker': 'agent',
            'message': script,
            'timestamp': time.time()
        })

        # Mock user responses and agent replies
        mock_user_responses = [
            "Hi, I'm interested. Can you tell me more about your services?",
            "What are the pricing options?",
            "How do I get started?",
            "Thank you for the information. I'll think about it."
        ]

        for user_msg in mock_user_responses:
            conversation.append({
                'speaker': 'user',
                'message': user_msg,
                'timestamp': time.time()
            })

            if agent:
                try:
                    # For mock calls, use static responses to avoid async issues
                    if mode == 'mock':
                        agent_reply = "Hello! This is Agent X's greeting plugin."
                    else:
                        agent_reply = agent.reason(user_msg)
                    conversation.append({
                        'speaker': 'agent',
                        'message': agent_reply,
                        'timestamp': time.time()
                    })
                except Exception as e:
                    conversation.append({
                        'speaker': 'agent',
                        'message': f"Sorry, I encountered an error: {e}",
                        'timestamp': time.time()
                    })

        return conversation


# Global instance
alt_call_system = AlternativeCallSystem()


def create_alternative_call(to_number: str, script: str, agent, mode: str = 'mock') -> Dict[str, Any]:
    """
    Create a call using alternative methods (no Twilio required)

    Args:
        to_number: Phone number or identifier
        script: Call script/text
        agent: Agent instance for AI responses
        mode: 'webrtc', 'local_simulation', or 'mock'

    Returns:
        Call result dictionary
    """
    if mode == 'webrtc':
        return alt_call_system.create_webrtc_call(to_number, script, agent)
    elif mode == 'local_simulation':
        return alt_call_system.create_local_simulation(to_number, script, agent)
    elif mode == 'mock':
        return alt_call_system.create_mock_call(to_number, script, agent)
    else:
        return {
            'status': 'error',
            'message': f'Unknown mode: {mode}. Use webrtc, local_simulation, or mock'
        }


def get_call_status(call_id: str) -> Optional[Dict[str, Any]]:
    """Get status of a call"""
    return alt_call_system.get_call_status(call_id)


def list_active_calls() -> List[Dict[str, Any]]:
    """List all active calls"""
    return alt_call_system.list_active_calls()


if __name__ == '__main__':
    # Test the system
    print("Testing Alternative Call System...")

    # Mock agent for testing
    class MockAgent:
        def reason(self, message):
            return f"I understand you said: '{message}'. How can I help you further?"

    mock_agent = MockAgent()

    # Test mock call
    result = create_alternative_call('+14062102346', 'Hello from Agent X!', mock_agent, 'mock')
    print(f"Mock call result: {result}")

    # Test local simulation
    result = create_alternative_call('+14062102346', 'Hello from Agent X!', mock_agent, 'local_simulation')
    print(f"Local simulation result: {result}")

    # List active calls
    time.sleep(1)  # Wait for simulation to start
    active = list_active_calls()
    print(f"Active calls: {len(active)}")