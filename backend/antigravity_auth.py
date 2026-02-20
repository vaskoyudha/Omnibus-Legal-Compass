import os
import json
import base64
import hashlib
import time
import secrets
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import requests
import logging

logger = logging.getLogger(__name__)

ANTIGRAVITY_CLIENT_ID = "1071006060591-tmhssin2h21lcre235vtolojh4g403ep.apps.googleusercontent.com"
ANTIGRAVITY_CLIENT_SECRET = "REDACTED_SECRET"  # pragma: allowlist secret
ANTIGRAVITY_REDIRECT_URI = "http://localhost:51121/oauth-callback"

_auth_status = {"status": "idle", "message": "", "token": None}
_oauth_server = None

def generate_pkce_pair():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode('utf-8')
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('utf-8')).digest()).rstrip(b'=').decode('utf-8')
    return verifier, challenge

def build_auth_url(challenge):
    scopes = [
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
    params = {
        "client_id": ANTIGRAVITY_CLIENT_ID,
        "redirect_uri": ANTIGRAVITY_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
        "prompt": "consent",
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _auth_status
        parsed_path = urllib.parse.urlparse(self.path)
        if parsed_path.path == "/oauth-callback":
            query = urllib.parse.parse_qs(parsed_path.query)
            if "code" in query:
                code = query["code"][0]
                _auth_status["status"] = "code_received"
                _auth_status["code"] = code
                
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Success!</h1><p>You can close this window and return to Omnibus Legal Compass.</p><script>setTimeout(window.close, 2000);</script></body></html>")
            else:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"<html><body><h1>Error</h1><p>No authorization code received.</p></body></html>")
                _auth_status["status"] = "error"
                _auth_status["message"] = "No authorization code received."

    def log_message(self, format, *args):
        pass

def exchange_code_for_token(code, verifier):
    global _auth_status
    try:
        data = {
            "client_id": ANTIGRAVITY_CLIENT_ID,
            "client_secret": ANTIGRAVITY_CLIENT_SECRET,
            "code": code,
            "redirect_uri": ANTIGRAVITY_REDIRECT_URI,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
        r = requests.post("https://oauth2.googleapis.com/token", data=data, timeout=30)
        r.raise_for_status()
        resp_json = r.json()
        refresh_token = resp_json.get("refresh_token")
        
        if refresh_token:
            save_token_to_opencode_config(refresh_token)
            _auth_status["status"] = "success"
            _auth_status["token"] = refresh_token
        else:
            _auth_status["status"] = "error"
            _auth_status["message"] = "No refresh token returned by Google (you may need to revoke access and try again)."
            
    except Exception as e:
        logger.error(f"Failed to exchange code: {e}")
        _auth_status["status"] = "error"
        _auth_status["message"] = f"Failed to exchange code: {str(e)}"

def save_token_to_opencode_config(refresh_token):
    config_dir = os.path.expanduser("~/.config/opencode")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "antigravity-accounts.json")
    
    # Try getting user email (optional)
    email = "user@example.com"
    
    data = {"version": 4, "accounts": [], "activeIndex": 0, "activeIndexByFamily": {"claude": 0, "gemini": 0}}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                existing = json.load(f)
                if isinstance(existing, dict) and "accounts" in existing:
                    data = existing
        except Exception:
            pass
            
    # Add new account
    account = {
        "email": email,
        "refreshToken": refresh_token,
        "addedAt": int(time.time() * 1000),
        "lastUsed": int(time.time() * 1000),
        "enabled": True,
        "rateLimitResetTimes": {},
        "fingerprint": {
            "deviceId": str(uuid.uuid4()),
            "userAgent": "antigravity/1.18.3 darwin/arm64",
            "apiClient": "google-cloud-sdk vscode/1.86.0",
            "clientMetadata": {"ideType": "ANTIGRAVITY", "platform": "MACOS", "pluginType": "GEMINI"},
            "createdAt": int(time.time() * 1000)
        }
    }
    
    # Check if we should update an existing one instead
    updated = False
    for i, acc in enumerate(data["accounts"]):
        if acc.get("refreshToken") == refresh_token:
            data["accounts"][i]["lastUsed"] = int(time.time() * 1000)
            updated = True
            break
            
    if not updated:
        data["accounts"].append(account)
        
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
        
    # Also update environment
    os.environ["ANTIGRAVITY_REFRESH_TOKEN"] = refresh_token

def start_auth_server(verifier):
    global _oauth_server, _auth_status
    _auth_status = {"status": "waiting", "message": "Waiting for browser auth...", "code": None}
    
    if _oauth_server:
        try:
            _oauth_server.shutdown()
        except:
            pass
            
    server_address = ('', 51121)
    _oauth_server = HTTPServer(server_address, OAuthCallbackHandler)
    
    def serve():
        global _oauth_server, _auth_status
        server_instance = _oauth_server
        if not server_instance:
            return
        server_instance.timeout = 1
        start_time = time.time()
        
        while _auth_status["status"] == "waiting" and time.time() - start_time < 300: # 5 mins max
            server_instance.handle_request()
            
        server_instance.server_close()
        _oauth_server = None
        
        if _auth_status["status"] == "code_received":
            exchange_code_for_token(_auth_status["code"], verifier)
            
    thread = threading.Thread(target=serve)
    thread.daemon = True
    thread.start()

def get_auth_status():
    global _auth_status
    return _auth_status
