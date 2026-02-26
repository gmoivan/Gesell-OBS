"""
Toggle a source's visibility within the current scene on a timer.

Notes:
- Visibility is scene-item specific. This script searches the current program scene for a
  scene item that corresponds to the named source.
"""

import obspython as obs

SOURCE_NAME = ""
INTERVAL_MS = 2000
ENABLED = False

_state = False

def script_description():
    return "Gesell: Toggle a source's visibility in the current scene (timer)"

def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_bool(props, "enabled", "Enabled")
    obs.obs_properties_add_int(props, "interval_ms", "Interval (ms)", 200, 60000, 200)
    obs.obs_properties_add_text(props, "source_name", "Source name", obs.OBS_TEXT_DEFAULT)
    return props

def script_update(settings):
    global SOURCE_NAME, INTERVAL_MS, ENABLED
    ENABLED = obs.obs_data_get_bool(settings, "enabled")
    INTERVAL_MS = obs.obs_data_get_int(settings, "interval_ms")
    SOURCE_NAME = obs.obs_data_get_string(settings, "source_name")

    obs.timer_remove(_tick)
    if ENABLED:
        obs.timer_add(_tick, int(INTERVAL_MS))

def script_load(settings):
    obs.script_log(obs.LOG_INFO, "Loaded Gesell toggle source visibility script")
    script_update(settings)

def script_unload():
    obs.timer_remove(_tick)

def _tick():
    global _state
    if not ENABLED or not SOURCE_NAME:
        return

    scene_src = obs.obs_frontend_get_current_scene()
    if not scene_src:
        return

    try:
        scene = obs.obs_scene_from_source(scene_src)
        if not scene:
            return

        item = obs.obs_scene_find_source(scene, SOURCE_NAME)
        if not item:
            obs.script_log(obs.LOG_WARNING, f"Source not found in current scene: {SOURCE_NAME}")
            return

        _state = not _state
        obs.obs_sceneitem_set_visible(item, _state)

    finally:
        obs.obs_source_release(scene_src)
