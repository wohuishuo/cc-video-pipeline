import http.client
from pathlib import Path
import sys
import threading


APP = Path(__file__).resolve().parents[2] / "apps" / "youtube-oauth-bootstrap"
sys.path.insert(0, str(APP))

from youtube_oauth.callback import LoopbackReceiver
from youtube_oauth.flow import OAuthAttempt


def test_loopback_receiver_rejects_wrong_state_then_accepts_exact_callback():
    receiver = LoopbackReceiver()
    attempt = OAuthAttempt("https://accounts.google.com/auth", "expected-state", "verifier", f"http://127.0.0.1:{receiver.port}/oauth/callback")
    result = {}
    worker = threading.Thread(target=lambda: result.setdefault("code", receiver.receive(attempt, 3)), daemon=True)
    worker.start()
    connection = http.client.HTTPConnection("127.0.0.1", receiver.port, timeout=2)

    connection.request("GET", "/oauth/callback?state=wrong&code=stolen")
    assert connection.getresponse().status == 400
    connection.request("GET", "/oauth/callback?state=expected-state&code=accepted")
    assert connection.getresponse().status == 200
    worker.join(timeout=3); receiver.close(); connection.close()

    assert result == {"code": "accepted"}
