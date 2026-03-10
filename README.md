# Family Music Remote

A local web remote for a shared listening setup. It has a mock player for trying the interface and an optional Home Assistant provider for controlling a media player you own.

## Run it

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8000`. By default, commands use the mock player. To connect Home Assistant, set `HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN`, and `HOME_ASSISTANT_ENTITY` before starting the app. Keep the token private. The app binds to localhost and has no user authentication, so do not expose it to a network without adding access controls.
