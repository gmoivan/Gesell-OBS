# Gesell Skill: obs_websocket

## Purpose
Control OBS Studio **from an external process** using OBS WebSocket (built into OBS v28+).

Use this skill when you need:
- remote control (same machine or over LAN/VPN)
- integration with bots, control panels, Stream Deck alternatives
- orchestrations that shouldn't run inside OBS

## Preconditions
- OBS running
- WebSocket server enabled in OBS:
  - Tools -> WebSocket Server Settings
  - Note host/port (commonly 4455) and password

## Libraries
### Python (recommended)
- `obsws-python` (request client for obs-websocket v5)

### Node.js (optional)
- `obs-websocket-js`

## Inputs (typical)
- `host` (default: localhost)
- `port` (default: 4455)
- `password` (store in env var; do not hardcode)
- action payload:
  - `scene_name`, `input_name`, `source_name`, `mute`, etc.

## Outputs
- API responses (success / error)
- your program logs/telemetry

## Failure modes & diagnostics
- Connection refused: OBS not running, wrong host/port, firewall
- Authentication failure: password mismatch
- Request errors: scene/source not found; name mismatch

## Provided assets
### Templates
- `templates/python_client.py` — minimal client wrapper (Python-first)
- `templates/node_client.js` — minimal Node wrapper

### Examples
- `examples/go_live_macro.py` — set scene -> unmute mic -> start stream
- `examples/brb_macro.py` — set BRB scene -> mute mic -> optionally hide camera source

## Suggested Gesell interface (for prompting)
- Env vars:
  - OBS_WS_HOST, OBS_WS_PORT, OBS_WS_PASSWORD
- Intent:
  - macro name, ordered steps, and any rollback behavior on failure
