# Gesell OBS Skills (Python-first)

This bundle provides reusable "skills" for OBS automation:

- `skills/obs_script_python` — scripts that run inside OBS (Tools -> Scripts)
- `skills/obs_websocket` — external control using OBS WebSocket (OBS 28+)

## Quick start: obs_websocket (Python)
1) Enable WebSocket server in OBS (Tools -> WebSocket Server Settings).
2) Set env vars:
   - OBS_WS_HOST=localhost
   - OBS_WS_PORT=4455
   - OBS_WS_PASSWORD=your_password
3) Install:
   - pip install obsws-python
4) Run an example:
   - python skills/obs_websocket/examples/go_live_macro.py

## Quick start: obs_script_python
1) In OBS: Tools -> Scripts -> +
2) Load a template or example from `skills/obs_script_python/`.
3) Configure properties in the script UI.

## Notes
- Names must match exactly as shown in OBS (scenes, sources, inputs).
- For secrets (WebSocket password), prefer environment variables.
## Added: obs_session_inventory_csv
- Exports system inventory + OBS inputs/scenes to CSV for audit/forensics.
- `obs_session_inventory_csv` now also writes `obs_recording_session_*.csv` (record/stream status + settings snapshot).

