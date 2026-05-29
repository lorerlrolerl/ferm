"""
Simple webhook server for auto-deploy from GitHub.
Runs on the NAS, listens for GitHub push events on port 9000.

Setup:
  uv run python webhook.py &
  # or run as a separate docker service (see docker-compose.yml)

GitHub webhook:
  Payload URL: http://100.120.120.18:9000/deploy
  Content type: application/json
  Secret: same as WEBHOOK_SECRET in .env
  Events: Just the push event
"""
import hashlib
import hmac
import json
import logging
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").encode()
DEPLOY_DIR     = os.getenv("DEPLOY_DIR", "/volume1/docker/fermlog")
DEPLOY_BRANCH  = os.getenv("DEPLOY_BRANCH", "main")


def verify_signature(payload: bytes, sig_header: str) -> bool:
    if not WEBHOOK_SECRET:
        log.warning("No WEBHOOK_SECRET set — skipping signature check")
        return True
    expected = "sha256=" + hmac.new(WEBHOOK_SECRET, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig_header or "")


def run_deploy():
    log.info("Starting deploy...")
    commands = [
        ["git", "-C", DEPLOY_DIR, "pull", "origin", DEPLOY_BRANCH],
        ["docker", "compose", "-p", "fermlog", "up", "-d", "--build"],
        ["docker", "image", "prune", "-f"],
    ]
    for cmd in commands:
        log.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=DEPLOY_DIR)
        if result.stdout: log.info(result.stdout)
        if result.stderr: log.info(result.stderr)
        if result.returncode != 0:
            log.error(f"Command failed: {' '.join(cmd)}")
            return False
    log.info("Deploy complete.")
    return True


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/deploy":
            self.send_response(404); self.end_headers(); return

        length  = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(length)
        sig     = self.headers.get("X-Hub-Signature-256", "")

        if not verify_signature(payload, sig):
            log.warning("Invalid signature — rejected")
            self.send_response(403); self.end_headers(); return

        try:
            data   = json.loads(payload)
            branch = data.get("ref", "").replace("refs/heads/", "")
        except Exception:
            branch = ""

        if branch != DEPLOY_BRANCH:
            log.info(f"Push to '{branch}' — ignoring (watching '{DEPLOY_BRANCH}')")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ignored")
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"deploying")

        # Run deploy in background so webhook returns immediately
        import threading
        threading.Thread(target=run_deploy, daemon=True).start()

    def log_message(self, format, *args):
        log.info("%s - %s", self.address_string(), format % args)


if __name__ == "__main__":
    port = int(os.getenv("WEBHOOK_PORT", 9000))
    log.info(f"Webhook server listening on port {port}")
    HTTPServer(("0.0.0.0", port), WebhookHandler).serve_forever()