"""Home Assistant adapter and in-memory demo player."""
import json
import os
import threading
import urllib.error
import urllib.request


class PlayerProvider:
    def __init__(self):
        self.base_url = os.getenv("HOME_ASSISTANT_URL", "").rstrip("/")
        self.token = os.getenv("HOME_ASSISTANT_TOKEN", "")
        configured = os.getenv("HOME_ASSISTANT_ENTITIES", os.getenv("HOME_ASSISTANT_ENTITY", ""))
        self.entities = [value.strip() for value in configured.split(",") if value.strip()]
        self.lock = threading.Lock()
        self.demo = [
            {"entity_id":"demo.living_room","name":"Living room","state":"playing","volume":32,"track":"A Walk","artist":"Tycho","source":"Vinyl setup","provider":"demo"},
            {"entity_id":"demo.office","name":"Office","state":"paused","volume":21,"track":"","artist":"","source":"Bluetooth","provider":"demo"},
            {"entity_id":"demo.kitchen","name":"Kitchen","state":"paused","volume":16,"track":"","artist":"","source":"AirPlay","provider":"demo"},
        ]

    @property
    def mode(self):
        return "home-assistant" if self.base_url and self.token and self.entities else "mock"

    def _request(self, path, method="GET", data=None):
        payload = None if data is None else json.dumps(data).encode()
        request = urllib.request.Request(f"{self.base_url}{path}", data=payload, method=method,
            headers={"Authorization":f"Bearer {self.token}","Content-Type":"application/json"})
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()
        return json.loads(raw) if raw else None

    def _map_state(self, entity, state):
        attrs = state.get("attributes", {})
        name = attrs.get("friendly_name") or entity.split(".",1)[-1].replace("_"," ").title()
        return {"entity_id":entity,"name":name,"state":state.get("state","unknown"),
            "volume":round(float(attrs.get("volume_level") or 0)*100),"track":attrs.get("media_title", ""),
            "artist":attrs.get("media_artist", ""),"source":attrs.get("source", ""),"provider":"home-assistant"}

    def players(self):
        if self.mode == "mock":
            with self.lock:
                return {"provider":"mock","players":[dict(player) for player in self.demo]}
        try:
            states = {item["entity_id"]:item for item in self._request("/api/states")}
            players = [self._map_state(entity, states[entity]) for entity in self.entities if entity in states]
            missing = [entity for entity in self.entities if entity not in states]
            if missing:
                return {"provider":"home-assistant","players":players,"error":"Some configured players are unavailable: " + ", ".join(missing)}
            return {"provider":"home-assistant","players":players}
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as exc:
            raise RuntimeError("Home Assistant is unavailable. Check the URL, token, and player entity list.") from exc

    def control(self, entity, action, volume=None):
        if action not in {"toggle","play","pause","next","previous","volume"}:
            raise ValueError("Unsupported player action.")
        if action == "volume" and (not isinstance(volume,(float,int)) or not 0 <= volume <= 100):
            raise ValueError("Volume must be between 0 and 100.")
        if self.mode == "mock":
            with self.lock:
                player = next((item for item in self.demo if item["entity_id"] == entity),None)
                if not player: raise LookupError("Player not found.")
                if action == "volume": player["volume"] = int(volume)
                elif action in {"toggle","play","pause"}:
                    player["state"] = "playing" if action == "play" or (action == "toggle" and player["state"] != "playing") else "paused"
                else: player["track"] = "Next track" if action == "next" else "Previous track"
                return dict(player)
        if entity not in self.entities: raise LookupError("Player is not in the configured entity list.")
        services = {"toggle":"media_play_pause","play":"media_play","pause":"media_pause","next":"media_next_track","previous":"media_previous_track","volume":"volume_set"}
        data = {"entity_id":entity}
        if action == "volume": data["volume_level"] = volume/100
        try: self._request(f"/api/services/media_player/{services[action]}","POST",data)
        except urllib.error.URLError as exc: raise RuntimeError("Home Assistant rejected the player command.") from exc
        return next((player for player in self.players()["players"] if player["entity_id"] == entity),{})
