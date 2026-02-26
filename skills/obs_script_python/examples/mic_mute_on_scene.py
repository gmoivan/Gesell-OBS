"""
Mute/unmute a mic source when switching scenes.

Configure:
- mic_source_name: the audio input capture source name (e.g., "Mic/Aux" if it is an input)
- mute_on_scenes: comma-separated scene names where the mic should be muted
"""

import obspython as obs

MIC_SOURCE = ""
MUTE_ON_SCENES = ""

_mute_set = set()

def script_description():
    return "Example: Mute mic when switching to certain scenes (Gesell)"

def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_text(props, "mic_source", "Mic input/source name", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_text(props, "mute_on_scenes", "Mute on scenes (CSV)", obs.OBS_TEXT_DEFAULT)
    return props

def script_update(settings):
    global MIC_SOURCE, MUTE_ON_SCENES, _mute_set
    MIC_SOURCE = obs.obs_data_get_string(settings, "mic_source")
    MUTE_ON_SCENES = obs.obs_data_get_string(settings, "mute_on_scenes") or ""
    _mute_set = {s.strip() for s in MUTE_ON_SCENES.split(",") if s.strip()}

def script_load(settings):
    obs.script_log(obs.LOG_INFO, "Loaded mic mute on scene example")
    script_update(settings)
    obs.obs_frontend_add_event_callback(_on_event)

def script_unload():
    obs.obs_frontend_remove_event_callback(_on_event)

def _set_mute(source_or_input_name: str, mute: bool):
    src = obs.obs_get_source_by_name(source_or_input_name)
    if not src:
        obs.script_log(obs.LOG_WARNING, f"Mic source/input not found: {source_or_input_name}")
        return
    try:
        obs.obs_source_set_muted(src, mute)
    finally:
        obs.obs_source_release(src)

def _current_scene_name():
    scene_src = obs.obs_frontend_get_current_scene()
    if not scene_src:
        return None
    try:
        return obs.obs_source_get_name(scene_src)
    finally:
        obs.obs_source_release(scene_src)

def _on_event(event):
    if event != obs.OBS_FRONTEND_EVENT_SCENE_CHANGED:
        return
    if not MIC_SOURCE:
        return
    scene = _current_scene_name()
    if not scene:
        return
    _set_mute(MIC_SOURCE, scene in _mute_set)
