# OBS 31+ compatibility note: uses OBS 31+ frontend/event and property APIs only.

import obspython as obs
import os
import csv
import time
import threading
import hashlib
import datetime

# -----------------------------
# Runtime settings and shared state
# -----------------------------
_SETTINGS = {
    "hash_output_dir": "",
    "csv_path": "",
    "csv_delimiter": ",",
    "retry_count": 5,
    "retry_delay_ms": 400,
}

_seen_paths = set()
_seen_lock = threading.Lock()
_io_lock = threading.Lock()
_loaded_csv_path = ""
_TAG = "[recording-hash]"

# End section: runtime settings and shared state


# -----------------------------
# Logging helper
# -----------------------------
def _log(level, msg):
    # Purpose: Prefix and route script log messages through OBS logging.
    obs.script_log(level, f"{_TAG} {msg}")

# End section: logging helper


# -----------------------------
# OBS script metadata and UI
# -----------------------------
def script_description():
    # Purpose: Describe this script in the OBS Scripts panel.
    return "Generate SHA-256 sidecar files and CSV logs for completed OBS recordings."


def script_defaults(settings):
    # Purpose: Define default values for user-configurable script properties.
    obs.obs_data_set_default_string(settings, "hash_output_dir", "")
    obs.obs_data_set_default_string(settings, "csv_path", "")
    obs.obs_data_set_default_string(settings, "csv_delimiter", ",")
    obs.obs_data_set_default_int(settings, "retry_count", 5)
    obs.obs_data_set_default_int(settings, "retry_delay_ms", 400)


def script_properties():
    # Purpose: Build the OBS properties UI for output, CSV, and retry options.
    props = obs.obs_properties_create()
    obs.obs_properties_add_path(
        props,
        "hash_output_dir",
        "Hash output folder (optional)",
        obs.OBS_PATH_DIRECTORY,
        "",
        None,
    )
    obs.obs_properties_add_path(
        props,
        "csv_path",
        "CSV file path",
        obs.OBS_PATH_FILE,
        "CSV (*.csv)",
        None,
    )
    p = obs.obs_properties_add_list(
        props,
        "csv_delimiter",
        "CSV delimiter",
        obs.OBS_COMBO_TYPE_LIST,
        obs.OBS_COMBO_FORMAT_STRING,
    )
    obs.obs_property_list_add_string(p, "Comma (,)", ",")
    obs.obs_property_list_add_string(p, "Semicolon (;)", ";")
    obs.obs_properties_add_int(props, "retry_count", "Retry count", 1, 50, 1)
    obs.obs_properties_add_int(props, "retry_delay_ms", "Retry delay (ms)", 0, 5000, 50)
    return props


def script_update(settings):
    # Purpose: Validate and apply settings from the OBS properties UI.
    hash_output_dir = _clean_path(obs.obs_data_get_string(settings, "hash_output_dir"))
    csv_path = _clean_path(obs.obs_data_get_string(settings, "csv_path"))
    delimiter = obs.obs_data_get_string(settings, "csv_delimiter")
    retry_count = int(obs.obs_data_get_int(settings, "retry_count"))
    retry_delay_ms = int(obs.obs_data_get_int(settings, "retry_delay_ms"))

    if delimiter not in (",", ";"):
        _log(obs.LOG_WARNING, "CSV delimiter invalid; defaulting to comma.")
        delimiter = ","

    if retry_count < 1:
        _log(obs.LOG_WARNING, "Retry count invalid; defaulting to 5.")
        retry_count = 5

    if retry_delay_ms < 0:
        _log(obs.LOG_WARNING, "Retry delay invalid; defaulting to 400 ms.")
        retry_delay_ms = 400

    _SETTINGS["hash_output_dir"] = hash_output_dir
    _SETTINGS["csv_path"] = csv_path
    _SETTINGS["csv_delimiter"] = delimiter
    _SETTINGS["retry_count"] = retry_count
    _SETTINGS["retry_delay_ms"] = retry_delay_ms

    if csv_path:
        _reload_seen_paths_from(csv_path)

# End section: OBS script metadata and UI


# -----------------------------
# OBS lifecycle registration
# -----------------------------
def script_load(settings):
    # Purpose: Register frontend callback when the script is loaded.
    obs.obs_frontend_add_event_callback(_on_frontend_event)
    _log(obs.LOG_INFO, "Loaded and listening for recording stop events.")


def script_unload():
    # Purpose: Unregister frontend callback when the script is unloaded.
    obs.obs_frontend_remove_event_callback(_on_frontend_event)
    _log(obs.LOG_INFO, "Unloaded.")

# End section: OBS lifecycle registration


# -----------------------------
# Event handling and async kickoff
# -----------------------------
def _on_frontend_event(event):
    # Purpose: React to recording-stopped events and launch background processing.
    if event != obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        return

    end_time_iso = _now_iso()
    duration_seconds = _get_recording_duration_seconds()
    recording_path = _resolve_last_recording_path()

    if not recording_path:
        _log(obs.LOG_ERROR, "Recording stopped but file path could not be resolved.")
        return

    t = threading.Thread(
        target=_process_recording,
        args=(recording_path, end_time_iso, duration_seconds),
        daemon=True,
    )
    t.start()

# End section: event handling and async kickoff


# -----------------------------
# Main recording processing pipeline
# -----------------------------
def _process_recording(path, end_time_iso, duration_seconds):
    # Purpose: Wait, hash, write sidecar, and append CSV for one recording.
    abs_path = _to_abs_path(path)
    if not abs_path:
        _log(obs.LOG_ERROR, "Resolved recording path is empty.")
        return

    norm_path = os.path.normcase(abs_path)
    with _seen_lock:
        if norm_path in _seen_paths:
            _log(obs.LOG_INFO, f"Skipping duplicate entry for {abs_path}")
            return

    ok, size_bytes = _wait_for_stable_file(
        abs_path, _SETTINGS["retry_count"], _SETTINGS["retry_delay_ms"]
    )
    if not ok:
        _log(obs.LOG_ERROR, f"File not ready after retries: {abs_path}")
        return

    sha256_hex = _hash_file_with_retries(
        abs_path, _SETTINGS["retry_count"], _SETTINGS["retry_delay_ms"]
    )
    if not sha256_hex:
        _log(obs.LOG_ERROR, f"Failed to hash file after retries: {abs_path}")
        return

    output_dir = _resolve_hash_output_dir(abs_path)
    if not output_dir:
        _log(obs.LOG_ERROR, "Hash output directory could not be resolved.")
        return

    if not _write_sidecar(output_dir, abs_path, sha256_hex):
        _log(obs.LOG_WARNING, f"Failed to write sidecar for {abs_path}")

    _append_csv_row(
        end_time_iso=end_time_iso,
        file_path=abs_path,
        file_name=os.path.basename(abs_path),
        file_size_bytes=size_bytes,
        duration_seconds=duration_seconds,
        sha256=sha256_hex,
    )

# End section: main recording processing pipeline


# -----------------------------
# Recording-path resolution helpers
# -----------------------------
def _resolve_last_recording_path():
    # Purpose: Resolve the best available file path for the just-finished recording.
    path = ""
    try:
        path = obs.obs_frontend_get_last_recording()
    except Exception:
        path = ""

    if path:
        return path

    output = None
    try:
        output = obs.obs_frontend_get_recording_output()
    except Exception:
        output = None

    if not output:
        return ""

    try:
        settings = obs.obs_output_get_settings(output)
        dir_or_path = ""
        ext_hint = ""
        if settings:
            dir_or_path = _first_string(
                settings, ["path", "directory", "rec_path", "recording_path"]
            )
            ext_hint = _first_string(
                settings, ["format", "rec_format", "file_format", "container", "extension"]
            )
            obs.obs_data_release(settings)
    finally:
        obs.obs_output_release(output)

    if not dir_or_path:
        return ""

    if os.path.isfile(dir_or_path):
        return dir_or_path

    if os.path.isdir(dir_or_path):
        candidate = _find_latest_file(dir_or_path, ext_hint)
        if candidate:
            return candidate

    return dir_or_path


def _first_string(obs_data, keys):
    # Purpose: Return the first non-empty OBS setting string from candidate keys.
    for k in keys:
        try:
            val = obs.obs_data_get_string(obs_data, k)
        except Exception:
            val = ""
        if val:
            return val
    return ""


def _find_latest_file(directory, ext_hint):
    # Purpose: Select the most recently modified file in a directory, optionally by extension.
    try:
        files = []
        ext = (ext_hint or "").lstrip(".").lower()
        for name in os.listdir(directory):
            path = os.path.join(directory, name)
            if not os.path.isfile(path):
                continue
            if ext and not name.lower().endswith("." + ext):
                continue
            files.append(path)
        if not files:
            return ""
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return files[0]
    except Exception:
        return ""

# End section: recording-path resolution helpers


# -----------------------------
# File readiness and hashing helpers
# -----------------------------
def _wait_for_stable_file(path, retries, delay_ms):
    # Purpose: Wait until file size stabilizes so hashing starts after writes complete.
    delay = max(0, delay_ms) / 1000.0
    last_err = None
    for _ in range(retries):
        if not os.path.exists(path):
            time.sleep(delay)
            continue
        try:
            size1 = os.path.getsize(path)
            time.sleep(delay)
            size2 = os.path.getsize(path)
            if size1 == size2 and size2 > 0:
                return True, size2
        except OSError as e:
            last_err = e
        time.sleep(delay)
    if last_err:
        _log(obs.LOG_WARNING, f"File stability check error: {last_err}")
    return False, 0


def _hash_file_with_retries(path, retries, delay_ms):
    # Purpose: Hash a file with retry behavior to tolerate transient access errors.
    delay = max(0, delay_ms) / 1000.0
    for attempt in range(retries):
        try:
            return _hash_file(path)
        except OSError as e:
            _log(obs.LOG_WARNING, f"Hash attempt {attempt + 1} failed: {e}")
            time.sleep(delay)
        except Exception as e:
            _log(obs.LOG_ERROR, f"Unexpected hash error: {e}")
            time.sleep(delay)
    return ""


def _hash_file(path):
    # Purpose: Compute SHA-256 digest for a file using chunked reads.
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

# End section: file readiness and hashing helpers


# -----------------------------
# Sidecar and CSV output writers
# -----------------------------
def _write_sidecar(output_dir, recording_path, sha256_hex):
    # Purpose: Persist hash output as a sidecar .sha256 file.
    try:
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.basename(recording_path)
        sidecar_path = os.path.join(output_dir, base_name + ".sha256")
        with open(sidecar_path, "w", encoding="utf-8") as f:
            f.write(f"{sha256_hex}  {base_name}\n")
        _log(obs.LOG_INFO, f"Sidecar written: {sidecar_path}")
        return True
    except Exception as e:
        _log(obs.LOG_ERROR, f"Sidecar write failed: {e}")
        return False


def _append_csv_row(
    end_time_iso,
    file_path,
    file_name,
    file_size_bytes,
    duration_seconds,
    sha256,
):
    # Purpose: Append deduplicated recording hash metadata to CSV.
    csv_path = _resolve_csv_path(file_path)
    if not csv_path:
        _log(obs.LOG_ERROR, "CSV path could not be resolved.")
        return False

    _ensure_seen_paths(csv_path)

    row = [
        end_time_iso,
        file_path,
        file_name,
        str(file_size_bytes),
        "" if duration_seconds is None else str(duration_seconds),
        sha256,
    ]

    norm_path = os.path.normcase(file_path)

    with _io_lock:
        with _seen_lock:
            if norm_path in _seen_paths:
                _log(obs.LOG_INFO, f"CSV dedupe: {file_path}")
                return False
            _seen_paths.add(norm_path)

        try:
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
            is_new = not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0
            with open(csv_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f, delimiter=_SETTINGS["csv_delimiter"])
                if is_new:
                    writer.writerow(
                        [
                            "end_time_iso",
                            "file_path",
                            "file_name",
                            "file_size_bytes",
                            "duration_seconds",
                            "sha256",
                        ]
                    )
                writer.writerow(row)
            _log(obs.LOG_INFO, f"CSV row written: {csv_path}")
            return True
        except Exception as e:
            _log(obs.LOG_ERROR, f"CSV write failed: {e}")
            with _seen_lock:
                _seen_paths.discard(norm_path)
            return False

# End section: sidecar and CSV output writers


# -----------------------------
# Output path and dedupe preload helpers
# -----------------------------
def _resolve_hash_output_dir(recording_path):
    # Purpose: Resolve where sidecar files should be written.
    configured = _SETTINGS["hash_output_dir"]
    if configured:
        if os.path.isdir(configured):
            return configured
        try:
            os.makedirs(configured, exist_ok=True)
            return configured
        except Exception as e:
            _log(obs.LOG_WARNING, f"Configured hash output dir unusable: {e}")
    rec_dir = os.path.dirname(recording_path)
    if rec_dir and os.path.isdir(rec_dir):
        return rec_dir
    return ""


def _resolve_csv_path(recording_path):
    # Purpose: Resolve CSV destination path from settings or recording directory.
    if _SETTINGS["csv_path"]:
        return _SETTINGS["csv_path"]
    rec_dir = os.path.dirname(recording_path)
    if not rec_dir:
        return ""
    return os.path.join(rec_dir, "recording_hashes.csv")


def _reload_seen_paths_from(csv_path):
    # Purpose: Preload already-recorded file paths from CSV for deduplication.
    global _loaded_csv_path
    with _seen_lock:
        _seen_paths.clear()
        _loaded_csv_path = csv_path

    if not csv_path or not os.path.exists(csv_path):
        return

    delimiter = _SETTINGS["csv_delimiter"]
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            first = True
            file_path_idx = 1
            for row in reader:
                if first:
                    first = False
                    if row and row[0] == "end_time_iso":
                        try:
                            file_path_idx = row.index("file_path")
                        except ValueError:
                            file_path_idx = 1
                        continue
                if len(row) > file_path_idx:
                    p = row[file_path_idx].strip()
                    if p:
                        norm = os.path.normcase(_to_abs_path(p))
                        with _seen_lock:
                            _seen_paths.add(norm)
    except Exception as e:
        _log(obs.LOG_WARNING, f"CSV preload failed: {e}")


def _ensure_seen_paths(csv_path):
    # Purpose: Ensure deduplication cache matches the currently targeted CSV.
    if not csv_path:
        return
    if _loaded_csv_path == csv_path:
        return
    _reload_seen_paths_from(csv_path)

# End section: output path and dedupe preload helpers


# -----------------------------
# Time and path normalization helpers
# -----------------------------
def _get_recording_duration_seconds():
    # Purpose: Read current recording duration from OBS, if available.
    try:
        val = obs.obs_frontend_get_recording_time()
        if val and val > 0:
            return int(val)
    except Exception:
        pass
    return None


def _now_iso():
    # Purpose: Return current local timestamp in ISO-8601 format.
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(
        timespec="seconds"
    )


def _clean_path(path):
    # Purpose: Normalize a user-provided path string into an absolute path.
    if not path:
        return ""
    p = path.strip().strip('"')
    p = os.path.expanduser(p)
    try:
        return os.path.abspath(p)
    except Exception:
        return p


def _to_abs_path(path):
    # Purpose: Convert a path to absolute form without raising on failure.
    if not path:
        return ""
    try:
        return os.path.abspath(path)
    except Exception:
        return path

# End section: time and path normalization helpers


# Quick setup/use:
# - Add this script in OBS (Tools -> Scripts), configure CSV path and optional hash output folder.
# - Start and stop a recording; a .sha256 sidecar and CSV row are created on stop.
