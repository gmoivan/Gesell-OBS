# Gesell Skill: obs_session_inventory_csv

## Purpose
Create CSV exports that capture:
1) **Pertinent system inventory** (host hardware/OS/devices)
2) **OBS session source inventory** (inputs/sources and device identifiers as available)

Intended for:
- forensic and compliance documentation
- reproducibility / audit trails
- chain-of-custody support artifacts

## Execution Model (recommended)
External Python script that connects to OBS via **OBS WebSocket** (OBS 28+) and writes:
- `system_inventory.csv` (key/value facts about the host system)
- `obs_inputs_inventory.csv` (one row per OBS input/source with relevant settings)
- `obs_scenes_inventory.csv` (optional; mapping of scenes to scene items)

## Inputs
- `output_dir` (path)
- OBS WebSocket connection:
  - `OBS_WS_HOST` (default: localhost)
  - `OBS_WS_PORT` (default: 4455)
  - `OBS_WS_PASSWORD` (required if configured)
- optional `include_scenes` (bool)

## Outputs

### obs_recording_session.csv (added)
Single-row snapshot capturing recording/stream status, current scene/profile/collection, record directory, and key audio/video settings (best-effort via WebSocket).

### system_inventory.csv
Normalized key/value records:
- timestamp_utc
- category (os, cpu, memory, disks, network, python, obs, etc.)
- key
- value

### obs_inputs_inventory.csv
Per-input records:
- timestamp_utc
- input_name
- input_kind
- is_audio
- is_video (best-effort)
- enabled (if available via scene mapping)
- selected_device_id (best-effort from input settings)
- selected_device_name (best-effort)
- raw_settings_json (minified JSON for audit trace)

### obs_scenes_inventory.csv (optional)
- timestamp_utc
- scene_name
- scene_item_id
- source_name
- enabled
- visible
- order_index

## Notes / Limits
- Device identifiers are **platform and input-kind specific** (e.g., WASAPI/DirectShow on Windows, CoreAudio/AVFoundation on macOS).
- The script extracts common settings keys when present (e.g., `device_id`, `device`, `audio_device_id`), but some inputs may not expose stable IDs.
- For deeper host hardware enumeration, optional dependency: `psutil` (used if installed).

## Provided Assets
- `templates/generate_inventory_csv.py` (Python-first, no required deps beyond obsws-python)
- `examples/run_inventory_capture.py` (invocation example)

## Recommended Gesell Invocation
Specify:
- output directory
- whether to include scene-item mapping
- any required fields for your compliance profile (e.g., GPU model, audio device serials)

## Added: Recording-stop automation (integrated)
This skill now includes a daemon entrypoint `run_on_recording_stop(...)` that listens for OBS recording stop events and automatically:
- writes the inventory CSVs, and
- optionally creates a SHA-256 sidecar file for the recorded output.

