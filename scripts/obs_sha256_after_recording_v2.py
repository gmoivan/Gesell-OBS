import obspython as obs
import os
import time
import hashlib
import shutil
import threading
import re
import csv
import platform
from datetime import datetime, timezone

MAX_RETRIES = 5
RETRY_DELAY = 1.5
READ_CHUNK_SIZE = 1024 * 1024

TIMESTAMP_RE = re.compile(r"^(?:\d{8}_\d{6}|\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})$")

CSV_FIELDS = [
    "recording_path",
    "recording_filename",
    "recording_folder",
    "recording_size_bytes",
    "recording_mtime_local",
    "recording_mtime_utc",
    "recording_stop_time_local",
    "recording_stop_time_utc",
    "recording_hash_sha256",
    "recording_hash_file",
    "system_platform",
    "system_os",
    "system_os_release",
    "system_os_version",
    "system_machine",
    "system_processor",
    "python_version",
    "obs_version_string",
    "obs_version_int",
    "scene_name",
    "scene_snapshot_time_local",
    "scene_snapshot_time_utc",
    "source_name",
    "source_id",
    "source_unversioned_id",
    "source_type",
    "source_active",
    "source_showing",
    "sceneitem_visible",
    "sceneitem_locked",
    "sceneitem_id",
]


def script_description():
    return (
        "After recording stops, move the file into a new folder, create a SHA-256 sidecar "
        "file, and write a CSV metadata report."
    )


def log_info(msg):
    obs.script_log(obs.LOG_INFO, msg)


def log_error(msg):
    obs.script_log(obs.LOG_ERROR, msg)


def is_timestamp(name):
    return bool(TIMESTAMP_RE.match(name))


def current_timestamp():
    return time.strftime("%Y%m%d_%H%M%S")


def format_ts(ts, tz):
    if ts is None:
        return ""
    return datetime.fromtimestamp(ts, tz).isoformat(timespec="seconds")


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


def source_type_to_str(source_type):
    mapping = [
        ("OBS_SOURCE_TYPE_INPUT", "input"),
        ("OBS_SOURCE_TYPE_FILTER", "filter"),
        ("OBS_SOURCE_TYPE_TRANSITION", "transition"),
        ("OBS_SOURCE_TYPE_SCENE", "scene"),
    ]
    for const_name, label in mapping:
        const_val = getattr(obs, const_name, None)
        if const_val is not None and source_type == const_val:
            return label
    return str(source_type)


def snapshot_system_info():
    info = {
        "system_platform": platform.platform(),
        "system_os": platform.system(),
        "system_os_release": platform.release(),
        "system_os_version": platform.version(),
        "system_machine": platform.machine(),
        "system_processor": platform.processor(),
        "python_version": platform.python_version(),
        "obs_version_string": "",
        "obs_version_int": "",
    }
    try:
        info["obs_version_string"] = obs.obs_get_version_string()
    except Exception:
        pass
    try:
        info["obs_version_int"] = str(obs.obs_get_version())
    except Exception:
        pass
    return info


def snapshot_scene_sources(snapshot_ts):
    info = {
        "scene_name": "",
        "scene_snapshot_time_local": format_ts(snapshot_ts, None),
        "scene_snapshot_time_utc": format_ts(snapshot_ts, timezone.utc),
        "sources": [],
    }

    scene_source = obs.obs_frontend_get_current_scene()
    if not scene_source:
        return info

    try:
        info["scene_name"] = obs.obs_source_get_name(scene_source)
        scene = obs.obs_scene_from_source(scene_source)
        if scene:
            items = obs.obs_scene_enum_items(scene)
            if items:
                for item in items:
                    source = obs.obs_sceneitem_get_source(item)
                    src_type = obs.obs_source_get_type(source)
                    info["sources"].append(
                        {
                            "source_name": obs.obs_source_get_name(source),
                            "source_id": obs.obs_source_get_id(source),
                            "source_unversioned_id": obs.obs_source_get_unversioned_id(source),
                            "source_type": source_type_to_str(src_type),
                            "source_active": str(bool(obs.obs_source_active(source))),
                            "source_showing": str(bool(obs.obs_source_showing(source))),
                            "sceneitem_visible": str(bool(obs.obs_sceneitem_visible(item))),
                            "sceneitem_locked": str(bool(obs.obs_sceneitem_locked(item))),
                            "sceneitem_id": str(obs.obs_sceneitem_get_id(item)),
                        }
                    )
                obs.sceneitem_list_release(items)
    finally:
        obs.obs_source_release(scene_source)

    return info


def write_metadata_csv(csv_path, recording_info, system_info, scene_info):
    rows = []
    scene_name = scene_info.get("scene_name", "")
    scene_local = scene_info.get("scene_snapshot_time_local", "")
    scene_utc = scene_info.get("scene_snapshot_time_utc", "")

    sources = scene_info.get("sources") or []
    if sources:
        for src in sources:
            row = {}
            row.update(recording_info)
            row.update(system_info)
            row["scene_name"] = scene_name
            row["scene_snapshot_time_local"] = scene_local
            row["scene_snapshot_time_utc"] = scene_utc
            row.update(src)
            rows.append(row)
    else:
        row = {}
        row.update(recording_info)
        row.update(system_info)
        row["scene_name"] = scene_name
        row["scene_snapshot_time_local"] = scene_local
        row["scene_snapshot_time_utc"] = scene_utc
        rows.append(row)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def process_recording(path, stop_ts, system_info, scene_info):
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
        return

    try:
        stat = os.stat(dest_path)
        recording_info = {
            "recording_path": dest_path,
            "recording_filename": filename,
            "recording_folder": target_dir,
            "recording_size_bytes": str(stat.st_size),
            "recording_mtime_local": format_ts(stat.st_mtime, None),
            "recording_mtime_utc": format_ts(stat.st_mtime, timezone.utc),
            "recording_stop_time_local": format_ts(stop_ts, None),
            "recording_stop_time_utc": format_ts(stop_ts, timezone.utc),
            "recording_hash_sha256": digest,
            "recording_hash_file": hash_path,
        }

        csv_path = dest_path + ".metadata.csv"
        write_metadata_csv(csv_path, recording_info, system_info, scene_info)
        log_info(f"Metadata CSV written: {csv_path}")
    except Exception as e:
        log_error(f"Failed to write metadata CSV: {e}")


def on_event(event):
    if event == obs.OBS_FRONTEND_EVENT_RECORDING_STOPPED:
        stop_ts = time.time()
        path = obs.obs_frontend_get_last_recording()
        system_info = snapshot_system_info()
        scene_info = snapshot_scene_sources(stop_ts)
        t = threading.Thread(
            target=process_recording,
            args=(path, stop_ts, system_info, scene_info),
            daemon=True,
        )
        t.start()


def script_load(settings):
    obs.obs_frontend_add_event_callback(on_event)
    log_info("SHA-256 + metadata CSV recording script loaded.")


def script_unload():
    log_info("SHA-256 + metadata CSV recording script unloaded.")
