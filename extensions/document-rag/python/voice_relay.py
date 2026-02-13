#!/usr/bin/env python3
"""
MOBIUS Voice Relay — Phone-as-Mic over Wi-Fi

Runs a WebSocket server that:
1. Serves a phone-friendly web page with Web Speech API
2. Receives transcribed text from the phone via per-input WebSocket sessions
3. Broadcasts transcripts to the MOBIUS desktop client

Socket lifecycle: phone opens a new WS per voice input session,
sends transcript(s), then closes. Stale sockets are reaped automatically.

Usage:
    python voice_relay.py [--port 8089] [--host 0.0.0.0]
    python voice_relay.py stop
"""

import asyncio
import json
import sys
import socket
import time
from pathlib import Path
from http import HTTPStatus

try:
    import websockets
    from websockets.asyncio.server import serve
except ImportError:
    print(json.dumps({"error": "websockets not installed. Run: pip install websockets"}))
    sys.exit(1)

try:
    import qrcode
    import qrcode.image.svg
    import io
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

# --- Configuration ---
DEFAULT_PORT = 8089
DEFAULT_HOST = "0.0.0.0"
STOP_FILE = Path(__file__).parent / ".voice_relay_stop"
HEARTBEAT_INTERVAL = 15    # seconds between pings
HEARTBEAT_TIMEOUT = 10     # seconds to wait for pong
SESSION_MAX_IDLE = 120     # seconds before idle session is reaped
MAX_PHONE_SESSIONS = 3     # max concurrent phone connections (prevent leaks)

# --- Session tracking ---
# Each entry: {"ws": websocket, "role": str, "connected_at": float, "last_active": float, "id": str}
sessions = {}
_session_counter = 0


def next_session_id():
    global _session_counter
    _session_counter += 1
    return f"s{_session_counter}"


def get_local_ip():
    """Get the machine's local Wi-Fi IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_desktop_sessions():
    return [s for s in sessions.values() if s["role"] == "desktop"]


def get_phone_sessions():
    return [s for s in sessions.values() if s["role"] == "phone"]


async def close_stale_sessions():
    """Periodically close idle and unresponsive connections."""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        now = time.time()
        stale = []
        for sid, session in list(sessions.items()):
            idle_time = now - session["last_active"]
            # Reap phone sessions idle beyond threshold
            if session["role"] == "phone" and idle_time > SESSION_MAX_IDLE:
                stale.append(sid)
            # Reap any session idle beyond 5 minutes
            elif idle_time > 300:
                stale.append(sid)

        for sid in stale:
            session = sessions.pop(sid, None)
            if session:
                try:
                    await session["ws"].close(1000, "Session idle timeout")
                except Exception:
                    pass

        # Enforce max phone sessions — close oldest if over limit
        phone_sessions = get_phone_sessions()
        if len(phone_sessions) > MAX_PHONE_SESSIONS:
            phone_sessions.sort(key=lambda s: s["connected_at"])
            excess = phone_sessions[:len(phone_sessions) - MAX_PHONE_SESSIONS]
            for session in excess:
                sid = session["id"]
                sessions.pop(sid, None)
                try:
                    await session["ws"].close(1000, "Too many phone sessions")
                except Exception:
                    pass


async def handle_websocket(websocket):
    """Handle a WebSocket connection with session tracking and heartbeat."""
    path = websocket.request.path if hasattr(websocket, 'request') else ''
    params = {}
    if '?' in path:
        query = path.split('?', 1)[1]
        for pair in query.split('&'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                params[k] = v

    role = params.get('role', 'desktop')
    sid = next_session_id()
    now = time.time()

    session = {
        "ws": websocket,
        "role": role,
        "connected_at": now,
        "last_active": now,
        "id": sid,
    }
    sessions[sid] = session

    try:
        # Send session info to client
        await websocket.send(json.dumps({
            "type": "session_start",
            "session_id": sid,
            "role": role,
        }))

        async for message in websocket:
            session["last_active"] = time.time()

            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            msg_type = data.get('type', '')

            # Phone sends transcript
            if msg_type == 'transcript' and role == 'phone':
                text = data.get('text', '')
                if text:
                    broadcast = json.dumps({
                        'type': 'voice_transcript',
                        'text': text,
                        'session_id': sid,
                        'timestamp': time.time(),
                    })
                    dead_sessions = []
                    for dsid, dsession in list(sessions.items()):
                        if dsession["role"] == "desktop":
                            try:
                                await dsession["ws"].send(broadcast)
                            except Exception:
                                dead_sessions.append(dsid)

                    # Clean up dead desktop sessions
                    for dsid in dead_sessions:
                        sessions.pop(dsid, None)

                    # Ack to phone
                    try:
                        await websocket.send(json.dumps({
                            'type': 'ack',
                            'text_length': len(text),
                        }))
                    except Exception:
                        pass

            # Phone signals recording stopped — close this session
            elif msg_type == 'recording_stopped' and role == 'phone':
                await websocket.send(json.dumps({'type': 'session_end', 'session_id': sid}))
                break  # exit loop, finally block cleans up

            # Heartbeat pong (client responding to our ping)
            elif msg_type == 'pong':
                pass  # last_active already updated above

    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        # Log unexpected errors but don't crash the server
        print(json.dumps({"error": f"Session {sid} error: {str(e)}"}), file=sys.stderr)
    finally:
        sessions.pop(sid, None)


def generate_qr_svg(url):
    """Generate QR code as SVG bytes."""
    if not HAS_QRCODE:
        return None
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory, box_size=10)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue()


# --- Phone page HTML ---
# Phone opens a NEW WebSocket per recording session, closes when done.
PHONE_PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>MOBIUS</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: #0a0a0f; color: #e0e0e8;
    height: 100dvh; display: flex; flex-direction: column;
    padding: 24px 16px env(safe-area-inset-bottom, 16px);
  }
  .header { text-align: center; padding: 8px 0 16px; }
  .header h1 { font-size: 18px; font-weight: 600; letter-spacing: 2px; }
  .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
  .dot.on { background: #4ade80; } .dot.off { background: #f87171; }
  .messages {
    flex: 1; overflow-y: auto; padding: 8px 0;
    display: flex; flex-direction: column; gap: 8px;
  }
  .msg {
    max-width: 85%; padding: 10px 14px; border-radius: 16px;
    font-size: 15px; line-height: 1.4; word-break: break-word;
  }
  .msg.sent { align-self: flex-end; background: #1a3a5c; color: #c0d8f0; border-bottom-right-radius: 4px; }
  .msg.ack { align-self: flex-start; background: #1a2a1a; color: #86efac; border-bottom-left-radius: 4px; font-size: 13px; }
  .input-row {
    display: flex; gap: 8px; padding-top: 12px;
    border-top: 1px solid #1a1a2e;
  }
  .input-row textarea {
    flex: 1; background: #12121a; border: 1px solid #2a2a3a; border-radius: 12px;
    color: #e0e0e8; font-size: 16px; padding: 12px 14px; resize: none;
    font-family: inherit; line-height: 1.4; min-height: 48px; max-height: 120px;
  }
  .input-row textarea::placeholder { color: #555; }
  .input-row textarea:focus { outline: none; border-color: #818cf8; }
  .send-btn {
    width: 48px; height: 48px; border-radius: 50%; border: none;
    background: #818cf8; color: #fff; font-size: 20px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer; flex-shrink: 0; align-self: flex-end;
  }
  .send-btn:active { transform: scale(0.93); }
  .send-btn:disabled { background: #333; color: #666; }
</style>
</head>
<body>

<div class="header">
  <h1><span class="dot off" id="dot"></span>MOBIUS</h1>
</div>

<div class="messages" id="messages"></div>

<div class="input-row">
  <textarea id="input" rows="1" placeholder="Type or use mic on keyboard..." autofocus
    oninput="this.style.height='auto';this.style.height=Math.min(this.scrollHeight,120)+'px'"></textarea>
  <button class="send-btn" id="sendBtn" onclick="send()">&#x2191;</button>
</div>

<script>
var ws = null, connected = false;
var input = document.getElementById('input');
var messages = document.getElementById('messages');
var dot = document.getElementById('dot');
var sendBtn = document.getElementById('sendBtn');

function connect() {
  var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(proto + '//' + location.host + '/ws?role=phone');
  ws.onopen = function() {
    connected = true;
    dot.className = 'dot on';
    addMsg('Connected to MOBIUS', 'ack');
  };
  ws.onclose = function() {
    connected = false; ws = null;
    dot.className = 'dot off';
    setTimeout(connect, 3000);
  };
  ws.onerror = function() { try { ws.close(); } catch(e) {} };
  ws.onmessage = function(evt) {
    try {
      var msg = JSON.parse(evt.data);
      if (msg.type === 'ack') addMsg('Received', 'ack');
    } catch(e) {}
  };
}

function send() {
  var text = input.value.trim();
  if (!text || !ws || ws.readyState !== 1) return;
  ws.send(JSON.stringify({ type: 'transcript', text: text }));
  addMsg(text, 'sent');
  input.value = '';
  input.style.height = 'auto';
  input.focus();
}

function addMsg(text, cls) {
  var el = document.createElement('div');
  el.className = 'msg ' + cls;
  el.textContent = text;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
}

// Send on Enter (without Shift)
input.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
});

connect();
</script>
</body>
</html>"""


def build_setup_page(local_ip, port):
    """Build the desktop-facing setup page with QR code and instructions."""
    phone_url = f"http://{local_ip}:{port}/"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>MOBIUS Voice Relay Setup</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: #0a0a0f; color: #e0e0e8; min-height: 100vh;
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; padding: 40px 20px;
  }}
  h1 {{ font-size: 24px; font-weight: 600; margin-bottom: 8px; color: #fff; }}
  .subtitle {{ font-size: 14px; color: #888; margin-bottom: 32px; }}
  .qr-container {{ background: #fff; border-radius: 16px; padding: 20px; margin-bottom: 24px; }}
  .qr-container img {{ width: 220px; height: 220px; }}
  .url-box {{
    font-family: monospace; font-size: 18px; color: #818cf8;
    background: #12121a; border: 1px solid #2a2a3a; border-radius: 8px;
    padding: 10px 20px; margin-bottom: 32px; letter-spacing: 0.5px;
  }}
  .instructions {{
    max-width: 480px; background: #12121a; border: 1px solid #2a2a3a;
    border-radius: 12px; padding: 24px; margin-bottom: 24px;
  }}
  .instructions h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #818cf8; }}
  .instructions ol {{ padding-left: 20px; line-height: 2; font-size: 14px; }}
  .instructions li {{ color: #ccc; }}
  .note {{
    max-width: 480px; background: #1a1a2e; border: 1px solid #333;
    border-radius: 12px; padding: 20px; font-size: 13px; line-height: 1.7; color: #999;
  }}
  .note strong {{ color: #818cf8; }}
  .status-bar {{ margin-top: 24px; font-size: 13px; color: #666; }}
  .status-bar .dot {{
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    margin-right: 6px; background: #4ade80; animation: blink 2s ease-in-out infinite;
  }}
  @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.3; }} }}
</style>
</head>
<body>
  <h1>MOBIUS Voice Relay</h1>
  <p class="subtitle">Use your phone as a wireless microphone</p>
  <div class="qr-container"><img src="/qr.svg" alt="QR Code"></div>
  <div class="url-box">{phone_url}</div>
  <div class="instructions">
    <h2>How to connect</h2>
    <ol>
      <li>Make sure your phone is on the <strong>same Wi-Fi network</strong> as this computer</li>
      <li>Scan the QR code above with your phone camera</li>
      <li>Tap the microphone button on the page that opens</li>
      <li>Speak — your words appear in the MOBIUS chat window</li>
    </ol>
  </div>
  <div class="note">
    <strong>How it works:</strong> This uses your phone's built-in speech-to-text
    (the same one your keyboard uses). Your voice is processed entirely by your
    phone — nothing is recorded or stored. Only the transcribed text is sent over
    your local Wi-Fi to MOBIUS. The desktop stays fully offline.
  </div>
  <div class="status-bar"><span class="dot"></span> Voice Relay running on port {port}</div>
</body>
</html>"""


async def http_handler(connection, request):
    """Serve the phone page, setup page, and QR code."""
    local_ip = get_local_ip()
    port = DEFAULT_PORT

    if request.path == '/' or request.path == '/index.html':
        return websockets.http11.Response(
            HTTPStatus.OK, "OK",
            websockets.datastructures.Headers({"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache"}),
            PHONE_PAGE_HTML.encode('utf-8'),
        )

    if request.path == '/setup':
        page = build_setup_page(local_ip, port)
        return websockets.http11.Response(
            HTTPStatus.OK, "OK",
            websockets.datastructures.Headers({"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache"}),
            page.encode('utf-8'),
        )

    if request.path == '/qr.svg':
        phone_url = f"http://{local_ip}:{port}/"
        svg_data = generate_qr_svg(phone_url)
        if svg_data:
            return websockets.http11.Response(
                HTTPStatus.OK, "OK",
                websockets.datastructures.Headers({"Content-Type": "image/svg+xml", "Cache-Control": "no-cache"}),
                svg_data,
            )
        return websockets.http11.Response(
            HTTPStatus.SERVICE_UNAVAILABLE, "QR library not installed",
            websockets.datastructures.Headers({"Content-Type": "text/plain"}),
            b"pip install qrcode",
        )

    if request.path == '/health':
        body = json.dumps({
            "status": "ok",
            "sessions": len(sessions),
            "phones": len(get_phone_sessions()),
            "desktops": len(get_desktop_sessions()),
            "phone_url": f"http://{local_ip}:{port}/",
            "setup_url": f"http://localhost:{port}/setup",
        })
        return websockets.http11.Response(
            HTTPStatus.OK, "OK",
            websockets.datastructures.Headers({"Content-Type": "application/json"}),
            body.encode('utf-8'),
        )

    # Clear all sessions (crash recovery endpoint)
    if request.path == '/reset':
        count = len(sessions)
        for sid, session in list(sessions.items()):
            try:
                await session["ws"].close(1000, "Server reset")
            except Exception:
                pass
        sessions.clear()
        body = json.dumps({"status": "reset", "sessions_cleared": count})
        return websockets.http11.Response(
            HTTPStatus.OK, "OK",
            websockets.datastructures.Headers({"Content-Type": "application/json"}),
            body.encode('utf-8'),
        )

    if request.path.startswith('/ws'):
        return None


async def run_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Run the voice relay server."""
    local_ip = get_local_ip()

    STOP_FILE.unlink(missing_ok=True)
    sessions.clear()  # Clean slate on startup

    print(json.dumps({
        "status": "starting",
        "host": host,
        "port": port,
        "local_ip": local_ip,
        "phone_url": f"http://{local_ip}:{port}/",
        "setup_url": f"http://localhost:{port}/setup",
    }))

    stop_event = asyncio.Event()

    async def check_stop():
        while not stop_event.is_set():
            if STOP_FILE.exists():
                STOP_FILE.unlink(missing_ok=True)
                stop_event.set()
                return
            await asyncio.sleep(1)

    async with serve(
        handle_websocket,
        host,
        port,
        process_request=http_handler,
        ping_interval=HEARTBEAT_INTERVAL,
        ping_timeout=HEARTBEAT_TIMEOUT,
        close_timeout=5,
    ) as server:
        print(json.dumps({
            "status": "running",
            "phone_url": f"http://{local_ip}:{port}/",
            "setup_url": f"http://localhost:{port}/setup",
            "message": f"Open http://{local_ip}:{port}/ on your phone (or scan QR at /setup)",
        }))
        sys.stdout.flush()

        # Start stale session reaper
        reaper = asyncio.create_task(close_stale_sessions())

        await check_stop()

        reaper.cancel()

    # Clean up all remaining sessions
    for sid, session in list(sessions.items()):
        try:
            await session["ws"].close(1000, "Server shutting down")
        except Exception:
            pass
    sessions.clear()

    print(json.dumps({"status": "stopped"}))


def main():
    port = DEFAULT_PORT
    host = DEFAULT_HOST
    args = sys.argv[1:]

    if 'stop' in args:
        STOP_FILE.touch()
        print(json.dumps({"status": "stop_signal_sent"}))
        return

    for i, arg in enumerate(args):
        if arg == '--port' and i + 1 < len(args):
            port = int(args[i + 1])
        elif arg == '--host' and i + 1 < len(args):
            host = args[i + 1]

    asyncio.run(run_server(host, port))


if __name__ == "__main__":
    main()
