import obspython as obs
import webbrowser

# -----------------------------
# Configuration
# -----------------------------
# Change this URL to the page you want to open.
TARGET_URL = "https://example.com"

# -----------------------------
# Button action handler
# -----------------------------
def on_button_clicked(props, prop):
    # Purpose: Open the configured URL when the OBS button is clicked.
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

# End section: button action handler


# -----------------------------
# OBS script metadata and UI
# -----------------------------
def script_description():
    # Purpose: Provide the script description shown in OBS Scripts UI.
    return "Adds a Sign in button that opens a browser page."

def script_properties():
    # Purpose: Build the OBS properties panel and register the Sign in button.
    props = obs.obs_properties_create()
    obs.obs_properties_add_button(props, "my_button", "Sign in", on_button_clicked)
    return props

# End section: OBS script metadata and UI


# -----------------------------
# Required OBS script hooks
# -----------------------------
def script_update(settings):
    # Purpose: React to property updates (unused in this minimal script).
    pass

def script_defaults(settings):
    # Purpose: Set default property values (none required for this script).
    pass

# End section: required OBS script hooks
