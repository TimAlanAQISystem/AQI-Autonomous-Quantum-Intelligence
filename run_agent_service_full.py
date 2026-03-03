"""Run Agent X (Alan) with audio/VAD, health endpoint, and control API.

This runner starts:
 - AQIAgentX (name: Alan)
 - Health server (127.0.0.1:8765)
 - AudioManager in lightweight test mode to avoid startup overloads
 - Control API (FastAPI) launched as a subprocess via uvicorn on 0.0.0.0:8777

Designed to be launched under the project's venv Python.
"""

import os
import sys
import threading
import time
import traceback
import socket

# Force UTF-8 console encoding to avoid Unicode errors on Windows consoles.
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(ROOT, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
DEBUG_LOG = os.path.join(LOG_DIR, 'control_service.debug.log')

def dlog(msg: str):
    """Emit a timestamped debug line to stdout and debug log."""
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(DEBUG_LOG, 'a', encoding='utf-8') as f:
            f.write(line + '\n')
    except Exception:
        pass

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, 'src'))

from aqi_agent_x import AQIAgentX
try:
    from agent_alan_business_ai import AgentAlanBusinessAI
except ImportError as e:
    print(f"Failed to import AgentAlanBusinessAI: {e}")
    traceback.print_exc()
    AgentAlanBusinessAI = None

# Health server
try:
    from src.health import start_health_server
except Exception:
    from health import start_health_server

# Control API (FastAPI app)
try:
    import control_api
    dlog('control_api imported successfully')
except Exception as e:
    dlog(f'control_api import failed: {e}')
    traceback.print_exc()
    control_api = None

# Simple direct agent API as fallback
import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs

class DirectAgentHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, agent, *args, **kwargs):
        self.agent = agent
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        if self.path == '/reason':
            try:
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
                message = data.get('message', '')
                
                # Call agent directly
                response = self.agent.reason(message)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True, 'response': response}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': False, 'error': str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == '/status':
            try:
                status = self.agent.get_status()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True, 'agent': status}).encode())
            except Exception as e:
                self.send_response(503)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': False, 'error': 'Agent not initialized'}).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_direct_agent_api(agent, host='0.0.0.0', port=8777):
    """Start a simple direct agent API server."""
    try:
        with socketserver.TCPServer((host, port), DirectAgentHandler) as httpd:
            print(f"Direct Agent API server started on {host}:{port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Failed to start direct agent API: {e}")

# Optional audio manager handle and uvicorn subprocess handle
audio = None
_uvicorn_proc = None


def start_control_api(agent, host='0.0.0.0', port=8777):
    """Start the control API using direct agent API since FastAPI has issues."""
    dlog('Using direct agent API (FastAPI has compatibility issues)')
    
    # Create handler class with agent
    class AgentHandler(DirectAgentHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(agent, *args, **kwargs)
    
    # Start direct agent API in main thread
    try:
        with socketserver.TCPServer((host, port), AgentHandler) as httpd:
            dlog(f'Direct Agent API server started on {host}:{port}')
            httpd.serve_forever()
    except Exception as e:
        dlog(f'Failed to start direct agent API: {e}')


def try_start_audio(agent):
    """Attempt to import and start the AudioManager in lightweight/test mode.

    This reduces VAD/model load during stabilization.
    """
    global audio
    try:
        import audio_manager as am
        # Start AudioManager in test_mode to avoid heavy VAD/model processing during startup.
        # test_mode=True disables VAD/model paths and uses lightweight processing to prevent
        # input/VAD queue overloads. forward_raw=False avoids forwarding every chunk to
        # higher layers which reduces queue pressure. This change is reversible.
        audio = am.AudioManager(test_mode=True, debug=False, forward_raw=False)

        # Wire callbacks for speech start/end
        def _on_start():
            try:
                agent.log_event('speech_start')
            except Exception:
                pass

        def _on_end():
            try:
                agent.log_event('speech_end')
            except Exception:
                pass

        audio.on_speech_start_callback = _on_start
        audio.on_speech_end_callback = _on_end

        # Start input (will attempt to open default device)
        try:
            audio.start_input()
            dlog('Audio input started (test mode)')
        except Exception as e:
            dlog(f'Audio input failed to start: {e}')
            traceback.print_exc()
            audio = None
    except Exception as e:
        dlog(f'AudioManager not available or failed to import: {e}')
        audio = None
    return audio


def main():
    dlog('BOOT: Initializing Alan (full service)')
    if AgentAlanBusinessAI:
        dlog("BOOT: Launching Agent Alan Business AI (The Boss)")
        agent = AgentAlanBusinessAI()
    else:
        dlog("BOOT: AgentAlanBusinessAI not found, falling back to standard AQIAgentX")
        agent = AQIAgentX(name='Alan')
    
    dlog('BOOT: Activating agent')
    agent.activate()
    dlog('BOOT: Agent activated')

    # Start health server on localhost
    try:
        start_health_server(agent, port=int(agent.config.get('health_port', 8765)))
        dlog('Health server listening on 127.0.0.1:8765')
    except Exception as e:
        dlog(f'Health server failed: {e}')

    # Start audio manager in lightweight/test mode to stabilize
    try:
        try_start_audio(agent)
    except Exception as e:
        dlog(f'Error starting audio: {e}')

    # Start control API in-process so it can access the agent object directly
    try:
        if control_api is None:
            dlog('control_api module missing; control endpoint unavailable')
        else:
            control_api.agent = agent

            host = str(agent.config.get('control_host', '0.0.0.0'))
            port = int(agent.config.get('control_port', 8777))
            dlog(f'CONTROL: Preparing to bind control API on {host}:{port}')

            # Preflight port check to surface conflicts early
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_sock.bind((host, port))
                test_sock.close()
                dlog('CONTROL: Port preflight bind succeeded (port free)')
            except Exception as e:
                dlog(f'CONTROL: Port preflight failed: {e}')
                raise

            # Heartbeat runs in a daemon thread while uvicorn runs in this process
            def _heartbeat():
                try:
                    while True:
                        agent.log_event('heartbeat')
                        time.sleep(60)
                except Exception:
                    pass

            hb = threading.Thread(target=_heartbeat, daemon=True)
            hb.start()

            # Launch uvicorn in a background thread and watchdog the bind
            import uvicorn

            def _run_uvicorn():
                try:
                    dlog('CONTROL: Starting uvicorn...')
                    uvicorn.run(control_api.app, host=host, port=port, log_level='info')
                except Exception as exc:
                    dlog(f'CONTROL: uvicorn failed: {exc}')
                    traceback.print_exc()

            uv_thread = threading.Thread(target=_run_uvicorn, daemon=True)
            uv_thread.start()

            # Wait for the control port to become reachable or timeout
            start_wait = time.monotonic()
            ready = False
            while time.monotonic() - start_wait < 20:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    target_host = '127.0.0.1' if host == '0.0.0.0' else host
                    if sock.connect_ex((target_host, port)) == 0:
                        ready = True
                        break
                finally:
                    sock.close()
                time.sleep(1)

            if ready:
                dlog('CONTROL: Control API is listening')
            else:
                dlog('CONTROL: Control API failed to start within 20s; exiting')
                os._exit(1)

            # Main loop to keep process alive if uvicorn is running in background
            while True:
                time.sleep(60)
    except Exception as e:
        dlog(f'Failed to start control API in-process: {e}')
        traceback.print_exc()

    # If control API was not started above, run a heartbeat loop here
    try:
        while True:
            agent.log_event('heartbeat')
            time.sleep(60)
    except KeyboardInterrupt:
        dlog('Shutdown requested')
    except Exception as e:
        dlog(f'Service loop error: {e}')
        traceback.print_exc()
    finally:
        try:
            if audio:
                audio.shutdown()
        except Exception:
            pass


if __name__ == '__main__':
    main()
