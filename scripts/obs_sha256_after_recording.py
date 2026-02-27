import obspython as obs
import os
import time
import hashlib
import shutil
import threading
import re

MAX_RETRIES = 5
RETRY_DELAY = 1.5
READ_CHUNK_SIZE = 1024 * 1024

TIMESTAMP_RE = re.compile(r"^(?:\d{8}_\d{6}|\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})$")


def script_description():
    return "After recording stops, move the file into a new folder and create a SHA-256 sidecar file."


def log_info(msg):
    obs.script_log(obs.LOG_INFO, msg)


def log_error(msg):
    obs.script_log(obs.LOG_ERROR, msg)


def is_timestamp(name):
    return bool(TIMESTAMP_RE.match(name))


def current_timestamp():
    return time.strftime("%Y%m%d_%H%M%S")


def ensure_unique_folder(parent_dir, base_name):
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


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(READ_CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def write_hash_file(recording_path, digest):
    hash_path = recording_path + ".sha256"
    filename = os.path.basename(recording_path)
    with open(hash_path, "w", encoding="utf-8") as f:
        f.write(f"{digest}  {filename}\n")
    return hash_path


def process_recording(path):
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


def on_event(event):
    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        path = obs.obs_frontend_get_last_recording()
        t = threading.Thread(target=process_recording, args=(path,), daemon=True)
        t.start()


def script_load(settings):
    obs.obs_frontend_add_event_callback(on_event)
    log_info("SHA-256 recording script loaded.")


def script_unload():
    log_info("SHA-256 recording script unloaded.")
