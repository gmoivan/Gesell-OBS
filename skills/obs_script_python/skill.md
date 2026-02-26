# Gesell Skill: obs_script_python

## Purpose
Automate OBS Studio **from inside OBS** using the built-in Python scripting runtime (`obspython`).

Use this skill when you want automations that:
- must run in-process with OBS (timers, scene/source/filter control, UI properties)
- benefit from Python for configuration parsing, file I/O, or light integrations

Prefer this skill over Lua when you control the OBS environment and Python scripting is available.

## Preconditions
- OBS must have **Python scripting enabled** (depends on platform/build).
- The script is loaded via: **Tools -> Scripts -> +**

## Core API
- `import obspython as obs`

Common capability areas:
- Scenes / sources / filters (enable/disable, visibility, settings)
- Frontend events (stream/record start/stop, scene change callbacks)
- Timers (`obs.timer_add`, `obs.timer_remove`)
- Script UI properties (`script_properties`, `script_update`)

## Inputs (typical parameters)
These are typically exposed through script properties:
- `scene_name` (string; exact match)
- `source_name` (string; exact match)
- `filter_name` (string; exact match)
- `interval_ms` (int)
- `enabled` (bool)
- file paths (string; local path on the OBS host)

## Outputs
- OBS state changes (scene switch, mute/unmute, visibility, filter enable)
- Logs in: **Tools -> Scripts -> Script Log**

## Patterns (recommended)
- Keep timer callbacks short and non-blocking.
- Validate that referenced scenes/sources exist; log actionable errors.
- Release OBS objects you acquire (`obs.source_release`, `obs.scene_release`, etc.).

## Failure modes & diagnostics
- **No Python option in Tools -> Scripts**: your OBS build likely lacks Python scripting support.
- **No effect / name mismatch**: verify exact scene/source/filter names (case/spacing).
- **Crashes / freezes**: avoid long blocking calls in timers/callbacks; offload heavy work.

## Provided assets
### Templates
- `templates/basic.py` — minimal scaffold
- `templates/text_source_from_file.py` — update text source from a file on a timer
- `templates/toggle_source_visibility.py` — toggle a source on/off

### Examples
- `examples/rotate_scenes_timer.py` — rotate through a list of scenes every N seconds
- `examples/mic_mute_on_scene.py` — mute/unmute a mic source when switching scenes

## Suggested Gesell interface (for prompting)
When you ask Gesell to implement something using this skill, describe:
- trigger (timer, scene change, stream start, hotkey)
- target (scene/source/filter)
- desired state transitions
- rate limits / timing constraints
- names of OBS objects exactly as in OBS UI
