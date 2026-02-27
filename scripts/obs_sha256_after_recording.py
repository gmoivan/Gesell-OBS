import obspython as obs
import os
import time
import hashlib
import shutil
import threading
import re

# -----------------------------
# Constants and regex patterns
# -----------------------------
MAX_RETRIES = 5
RETRY_DELAY = 1.5
READ_CHUNK_SIZE = 1024 * 1024

TIMESTAMP_RE = re.compile(r"^(?:\d{8}_\d{6}|\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})$")

# End section: constants and regex patterns


# -----------------------------
# OBS script description
# -----------------------------
def script_description():
    # Purpose: Describe this script in the OBS Scripts panel.
    return "After recording stops, move the file into a new folder and create a SHA-256 sidecar file."

# End section: OBS script description


# -----------------------------
# Logging helpers
# -----------------------------
def log_info(msg):
    # Purpose: Write informational messages to OBS script logs.
    obs.script_log(obs.LOG_INFO, msg)


def log_error(msg):
    # Purpose: Write error messages to OBS script logs.
    obs.script_log(obs.LOG_ERROR, msg)

# End section: logging helpers


# -----------------------------
# Naming and timestamp helpers
# -----------------------------
def is_timestamp(name):
    # Purpose: Check whether a folder name already follows the timestamp format.
    return bool(TIMESTAMP_RE.match(name))


def current_timestamp():
    # Purpose: Generate a timestamp string for unique folder names.
    return time.strftime("%Y%m%d_%H%M%S")

# End section: naming and timestamp helpers


# -----------------------------
# Directory and file movement
# -----------------------------
def ensure_unique_folder(parent_dir, base_name):
    # Purpose: Compute a non-conflicting destination folder for the recording.
    candidate = base_name
    target = os.path.join(parent_dir, candidate)

    if os.path.exists(target):
        if not is_timestamp(base_name):
            candidate = f"{base_name}_{current_timestamp()}"
        else:
            candidate = f"{base_name}_1"
        target = os.path.join(parent_dir, candidate)

    if os.path.exists(target):
        suffix = 2
        while True:
            candidate_try = f"{candidate}_{suffix}"
            target_try = os.path.join(parent_dir, candidate_try)
            if not os.path.exists(target_try):
                candidate = candidate_try
                target = target_try
                break
            suffix += 1

    return target


def move_with_retries(src, dst):
    # Purpose: Move the recording file with retry logic for transient lock issues.
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if not os.path.isfile(src):
                raise FileNotFoundError(src)
            shutil.move(src, dst)
            return True
        except Exception as e:
            last_err = e
            log_info(f"Move attempt {attempt}/{MAX_RETRIES} failed: {e}")
            time.sleep(RETRY_DELAY)
    log_error(f"Failed to move recording after {MAX_RETRIES} attempts: {last_err}")
    return False

# End section: directory and file movement


# -----------------------------
# Hashing and sidecar output
# -----------------------------
def sha256_file(path):
    # Purpose: Compute SHA-256 hash digest for a file using chunked reads.
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(READ_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def write_hash_file(recording_path, digest):
    # Purpose: Write the SHA-256 sidecar file next to the recording.
    hash_path = recording_path + ".sha256"
    filename = os.path.basename(recording_path)
    with open(hash_path, "w", encoding="utf-8") as f:
        f.write(f"{digest}  {filename}\n")
    return hash_path

# End section: hashing and sidecar output


# -----------------------------
# Main recording processing flow
# -----------------------------
def process_recording(path):
    # Purpose: Move, hash, and write sidecar for a completed recording.
    if not path:
        log_error("No recording path returned by OBS.")
        return

    if not os.path.isfile(path):
        log_error(f"Recording file not found: {path}")
        return

    parent_dir = os.path.dirname(path)
    filename = os.path.basename(path)
    base_name, _ext = os.path.splitext(filename)

    target_dir = ensure_unique_folder(parent_dir, base_name)

    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception as e:
        log_error(f"Failed to create target folder '{target_dir}': {e}")
        return

    dest_path = os.path.join(target_dir, filename)

    log_info(f"Moving recording to: {dest_path}")
    if not move_with_retries(path, dest_path):
        return

    try:
        log_info(f"Hashing recording: {dest_path}")
        digest = sha256_file(dest_path)
        hash_path = write_hash_file(dest_path, digest)
        log_info(f"SHA-256 written: {hash_path}")
    except Exception as e:
        log_error(f"Failed to hash recording: {e}")

# End section: main recording processing flow


# -----------------------------
# OBS frontend event callback
# -----------------------------
def on_event(event):
    # Purpose: Start background processing when OBS recording stops.
    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        path = obs.obs_frontend_get_last_recording()
        t = threading.Thread(target=process_recording, args=(path,), daemon=True)
        t.start()

# End section: OBS frontend event callback


# -----------------------------
# OBS lifecycle hooks
# -----------------------------
def script_load(settings):
    # Purpose: Register OBS frontend callback when the script loads.
    obs.obs_frontend_add_event_callback(on_event)
    log_info("SHA-256 recording script loaded.")


def script_unload():
    # Purpose: Log script unload event for operational visibility.
    log_info("SHA-256 recording script unloaded.")

# End section: OBS lifecycle hooks
