import obspython as obs
import webbrowser

# Change this URL to the page you want to open.
TARGET_URL = "https://example.com"

def on_button_clicked(props, prop):
    if not TARGET_URL:
        obs.script_messagebox(
            "Please set TARGET_URL in the script file.",
            "OBS Python Script",
            obs.OBS_MESSAGEBOX_OK,
            obs.OBS_MESSAGEBOX_INFORMATION
        )
        return True

    webbrowser.open(TARGET_URL)
    obs.script_log(obs.LOG_INFO, f"Opened URL: {TARGET_URL}")
    return True

def script_description():
    return "Adds a Sign in button that opens a browser page."

def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_button(props, "my_button", "Sign in", on_button_clicked)
    return props

def script_update(settings):
    pass

def script_defaults(settings):
    pass
