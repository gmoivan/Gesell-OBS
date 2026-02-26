import obspython as obs

def script_description():
    return "Gesell: OBS Python skill template (basic)"

def script_load(settings):
    obs.script_log(obs.LOG_INFO, "Loaded Gesell basic OBS Python template")

def script_unload():
    obs.script_log(obs.LOG_INFO, "Unloaded Gesell basic OBS Python template")
