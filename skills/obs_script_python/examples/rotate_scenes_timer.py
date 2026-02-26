"""
Rotate through a set of scenes on a fixed timer.

- Provide a comma-separated list of scene names in the script UI.
- Interval controls how often the scene changes.
"""

import obspython as obs

SCENES_CSV = ""
INTERVAL_MS = 15000
ENABLED = False

_scene_names = []
_index = 0

def script_description():
    return "Example: Rotate scenes every N seconds (Gesell)"

def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_bool(props, "enabled", "Enabled")
    obs.obs_properties_add_int(props, "interval_ms", "Interval (ms)", 1000, 600000, 500)
    obs.obs_properties_add_text(props, "scenes_csv", "Scenes (comma-separated)", obs.OBS_TEXT_DEFAULT)
    return props

def script_update(settings):
    global SCENES_CSV, INTERVAL_MS, ENABLED, _scene_names, _index

    ENABLED = obs.obs_data_get_bool(settings, "enabled")
    INTERVAL_MS = obs.obs_data_get_int(settings, "interval_ms")
    SCENES_CSV = obs.obs_data_get_string(settings, "scenes_csv") or ""

    _scene_names = [s.strip() for s in SCENES_CSV.split(",") if s.strip()]
    _index = 0

    obs.timer_remove(_tick)
    if ENABLED and _scene_names:
        obs.timer_add(_tick, int(INTERVAL_MS))

def script_load(settings):
    obs.script_log(obs.LOG_INFO, "Loaded scene rotator example")
    script_update(settings)

def script_unload():
    obs.timer_remove(_tick)

def _tick():
    global _index
    if not ENABLED or not _scene_names:
        return

    name = _scene_names[_index % len(_scene_names)]
    _index += 1

    src = obs.obs_get_source_by_name(name)
    if not src:
        obs.script_log(obs.LOG_WARNING, f"Scene not found: {name}")
        return

    try:
        obs.obs_frontend_set_current_scene(src)
    finally:
        obs.obs_source_release(src)
