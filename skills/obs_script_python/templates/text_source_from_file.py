"""
Updates a Text (GDI+) or Text (FreeType 2) source from a local file on a timer.

Usage:
- Create a text source in OBS (name it exactly).
- Put text in a file on disk.
- Load this script in Tools -> Scripts.
"""

import os
import obspython as obs

SOURCE_NAME = ""
FILE_PATH = ""
INTERVAL_MS = 1000
ENABLED = True

def script_description():
    return "Gesell: Update a text source from a file (timer)"

def script_properties():
    props = obs.obs_properties_create()

    obs.obs_properties_add_bool(props, "enabled", "Enabled")
    obs.obs_properties_add_int(props, "interval_ms", "Interval (ms)", 200, 60000, 200)
    obs.obs_properties_add_text(props, "source_name", "Text source name", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_path(
        props,
        "file_path",
        "Text file path",
        obs.OBS_PATH_FILE,
        "Text Files (*.txt);;All Files (*.*)",
        None,
    )
    return props

def script_update(settings):
    global SOURCE_NAME, FILE_PATH, INTERVAL_MS, ENABLED

    ENABLED = obs.obs_data_get_bool(settings, "enabled")
    INTERVAL_MS = obs.obs_data_get_int(settings, "interval_ms")
    SOURCE_NAME = obs.obs_data_get_string(settings, "source_name")
    FILE_PATH = obs.obs_data_get_string(settings, "file_path")

    obs.timer_remove(_tick)
    if ENABLED:
        obs.timer_add(_tick, int(INTERVAL_MS))

def script_load(settings):
    obs.script_log(obs.LOG_INFO, "Loaded Gesell text-from-file script")
    script_update(settings)

def script_unload():
    obs.timer_remove(_tick)

def _set_text_on_source(source_name: str, text_value: str) -> bool:
    src = obs.obs_get_source_by_name(source_name)
    if not src:
        return False

    try:
        settings = obs.obs_source_get_settings(src)
        try:
            obs.obs_data_set_string(settings, "text", text_value)
            obs.obs_source_update(src, settings)
        finally:
            obs.obs_data_release(settings)
        return True
    finally:
        obs.obs_source_release(src)

def _tick():
    if not ENABLED:
        return
    if not SOURCE_NAME or not FILE_PATH:
        return

    if not os.path.exists(FILE_PATH):
        obs.script_log(obs.LOG_WARNING, f"File not found: {FILE_PATH}")
        return

    try:
        with open(FILE_PATH, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception as e:
        obs.script_log(obs.LOG_WARNING, f"Failed reading file: {e}")
        return

    ok = _set_text_on_source(SOURCE_NAME, text)
    if not ok:
        obs.script_log(obs.LOG_WARNING, f"Source not found: {SOURCE_NAME}")
