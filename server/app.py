"""Audio Console local API and static client server."""
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from audio.provider import PlayerProvider
from audio.storage import Store
from audio.routes import routes
from audio.services.executor import SceneExecutor

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "client" / "dist"


def create_app(provider=None):
    app = Flask(__name__)
    players = provider or PlayerProvider()
    store = Store()
    executor = SceneExecutor(players,store)
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024
    app.register_blueprint(routes(store,executor))
    app.extensions["scene_executor"] = executor

    @app.get("/api/health")
    def health():
        return jsonify(status="ok",provider=players.mode)

    @app.get("/api/players")
    def list_players():
        try: return jsonify(players.players())
        except RuntimeError as exc: return jsonify(error=str(exc),players=[]),502

    @app.post("/api/control")
    def control():
        body = request.get_json(silent=True) or {}
        try:
            with executor.device_lock:
                return jsonify(players.control(str(body.get("entity_id","")),body.get("action"),body.get("volume")))
        except ValueError as exc: return jsonify(error=str(exc)),400
        except LookupError as exc: return jsonify(error=str(exc)),404
        except RuntimeError as exc: return jsonify(error=str(exc)),502

    @app.get("/")
    def index():
        if DIST.exists(): return send_from_directory(DIST,"index.html")
        return jsonify(service="Audio Console API",client="Run npm install and npm run dev in client/")

    @app.get("/<path:path>")
    def asset(path): return send_from_directory(DIST,path)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1",port=8000)
