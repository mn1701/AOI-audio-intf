"""A small local music remote with optional Home Assistant control."""
import os
import threading
import urllib.request

from flask import Flask, jsonify, request

app = Flask(__name__)
lock = threading.Lock()
mock = {"volume": 35, "playing": False, "track": "Demo player", "provider": "mock"}
HA_URL = os.getenv("HOME_ASSISTANT_URL", "").rstrip("/")
HA_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN", "")
ENTITY = os.getenv("HOME_ASSISTANT_ENTITY", "media_player.living_room")


def ha_call(domain, service, data):
    payload = urllib.request.Request(
        f"{HA_URL}/api/services/{domain}/{service}",
        data=__import__("json").dumps(data).encode(),
        headers={"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(payload, timeout=4) as response:
        return response.status < 300


@app.get("/")
def index():
    return """<!doctype html><meta name=viewport content='width=device-width'><title>Family Music Remote</title>
    <style>body{font:18px system-ui;max-width:600px;margin:3rem auto;padding:0 1rem;background:#171923;color:#f7f7fb}button{font:inherit;padding:.8rem 1rem;margin:.3rem;border:0;border-radius:.6rem;background:#d9b8ff}article{padding:1rem;background:#252938;border-radius:1rem}</style>
    <h1>Family Music Remote</h1><article><p id=s>Connecting…</p><button onclick="send('volume',-5)">Volume −</button><button onclick="send('volume',5)">Volume +</button><button onclick="send('toggle',0)">Play / pause</button><p id=e></p></article>
    <script>async function refresh(){let r=await fetch('/api/player'),p=await r.json();document.querySelector('#s').textContent=`${p.track} · ${p.volume}% · ${p.playing?'playing':'paused'} (${p.provider})`}
    async function send(action,amount){let r=await fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,amount})});let p=await r.json();document.querySelector('#e').textContent=p.error||'';refresh()} refresh();</script>"""


@app.get("/api/player")
def player_state():
    if HA_URL and HA_TOKEN:
        try:
            req = urllib.request.Request(f"{HA_URL}/api/states/{ENTITY}", headers={"Authorization": f"Bearer {HA_TOKEN}"})
            with urllib.request.urlopen(req, timeout=4) as response:
                import json
                state = json.load(response)
            attrs = state.get("attributes", {})
            return jsonify(track=attrs.get("media_title", ENTITY), volume=round((attrs.get("volume_level") or 0) * 100), playing=state.get("state") == "playing", provider="home-assistant")
        except Exception:
            return jsonify(error="Could not reach Home Assistant. Check its URL, token, and player entity."), 502
    with lock:
        return jsonify(mock)


@app.post("/api/control")
def control():
    body = request.get_json(silent=True) or {}
    action, amount = body.get("action"), body.get("amount", 0)
    if action not in {"volume", "toggle"} or (action == "volume" and (not isinstance(amount, int) or abs(amount) > 20)):
        return jsonify(error="Use volume with an integer step from -20 to 20, or toggle."), 400
    if HA_URL and HA_TOKEN:
        try:
            if action == "volume":
                state = player_state().get_json()
                level = max(0, min(100, state["volume"] + amount)) / 100
                ha_call("media_player", "volume_set", {"entity_id": ENTITY, "volume_level": level})
            else:
                ha_call("media_player", "media_play_pause", {"entity_id": ENTITY})
            return player_state()
        except Exception:
            return jsonify(error="Home Assistant rejected the command."), 502
    with lock:
        if action == "volume":
            mock["volume"] = max(0, min(100, mock["volume"] + amount))
        else:
            mock["playing"] = not mock["playing"]
        return jsonify(mock)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
