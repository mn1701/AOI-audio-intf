# Audio Console

A React and TypeScript control panel for music players, backed by a Flask service. Control individual players, save multi-player scenes, and inspect durable command jobs and partial failures.

## Run

Requires Python 3.10 or newer and Node.js with npm.

```sh
cd server
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Run `npm install` and `npm run dev` from `client` in another terminal. The API listens on localhost port 8000. `npm run build` builds assets that Flask can serve.

Without device configuration the provider exposes three in-memory demonstration players. For Home Assistant, set `HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN`, and comma-separated `HOME_ASSISTANT_ENTITIES` to media player entity IDs. Tokens stay on the server. Use a trusted Home Assistant address and transport. `AUDIO_DATABASE` selects the SQLite file, defaulting to `server/data/audio.sqlite3`.

## Scenes and execution

A scene contains unique target players, volume values from 0 to 80, and optional playback states. Saving a scene uses its version to prevent overwriting a concurrent edit. Scene execution creates a persistent job and enters a bounded queue of 32 jobs. One worker executes jobs in submission order. Individual controls share its device lock.

Submit an `Idempotency-Key` header when executing a scene or group volume command. Reusing a key with the same payload returns the existing job; reusing it with a different payload fails. Each player result records completed steps, its prior snapshot, and any error. Physical devices can fail independently, so a scene may complete partially. Commands are not automatically retried or rolled back. Interrupted jobs are marked on service restart and require manual review.

## Structure and API

`server/audio/provider.py` adapts Home Assistant and demo players. `storage.py` stores versioned scenes and jobs. `services/executor.py` validates and serializes scene commands. `routes.py` exposes scenes, group volume, and job status under `/api`. The existing player routes provide discovery and single-device controls. `client/src/features/Scenes.tsx` contains scene editing and live job status.

Run one application process per database and device group. SQLite persists job records; the execution queue and demo player state live in process memory. The API assumes trusted local access and has no user authentication.
