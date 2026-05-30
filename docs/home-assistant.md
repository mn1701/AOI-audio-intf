# Home Assistant connection

Create a long-lived token in the Home Assistant profile page, then keep it in the shell environment rather than checking it into a file:

```sh
export HOME_ASSISTANT_URL="http://homeassistant.local:8123"
export HOME_ASSISTANT_TOKEN="your-token"
export HOME_ASSISTANT_ENTITIES="media_player.living_room,media_player.office"
python server/app.py
```

The provider reads current media-player states and sends playback or volume services to the selected entity. A speaker that does not expose track or source attributes still appears, with those fields left empty.
