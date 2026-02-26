import csv
import hashlib
import json
import os
import platform
import socket
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil  # optional
except Exception:
    psutil = None

from obsws_python import ReqClient, EventClient


# ---------------------------
# Configuration
# ---------------------------

@dataclass
class ObsWsConfig:
    host: str = "localhost"
    port: int = 4455
    password: str = ""

    @staticmethod
    def from_env() -> "ObsWsConfig":
        host = os.getenv("OBS_WS_HOST", "localhost")
        port = int(os.getenv("OBS_WS_PORT", "4455"))
        password = os.getenv("OBS_WS_PASSWORD", "")
        return ObsWsConfig(host=host, port=port, password=password)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp_for_filename() -> str:
    # e.g. 20260226T223015Z
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ---------------------------
# Host inventory (best-effort, cross-platform)
# ---------------------------

def collect_system_facts() -> List[Tuple[str, str, str]]:
    """Return list of (category, key, value)."""
    facts: List[Tuple[str, str, str]] = []
    ts = utc_now_iso()

    def add(cat: str, key: str, val: Any):
        if val is None:
            return
        facts.append((cat, key, str(val)))

    add("time", "timestamp_utc", ts)
    add("host", "hostname", socket.gethostname())
    add("host", "fqdn", socket.getfqdn())
    add("os", "platform", platform.platform())
    add("os", "system", platform.system())
    add("os", "release", platform.release())
    add("os", "version", platform.version())
    add("os", "machine", platform.machine())
    add("os", "processor", platform.processor())
    add("python", "version", sys.version.replace("\n", " "))
    add("python", "executable", sys.executable)

    if psutil:
        try:
            vm = psutil.virtual_memory()
            add("memory", "total_bytes", vm.total)
            add("memory", "available_bytes", vm.available)
        except Exception:
            pass

        try:
            add("cpu", "logical_cores", psutil.cpu_count(logical=True))
            add("cpu", "physical_cores", psutil.cpu_count(logical=False))
        except Exception:
            pass

        try:
            for part in psutil.disk_partitions(all=False):
                add("disks", f"mount_{part.mountpoint}_fstype", part.fstype)
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    add("disks", f"mount_{part.mountpoint}_total_bytes", usage.total)
                    add("disks", f"mount_{part.mountpoint}_free_bytes", usage.free)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            addrs = psutil.net_if_addrs()
            for iface, items in addrs.items():
                for a in items:
                    addr = getattr(a, "address", None)
                    if addr:
                        add("network", f"{iface}_{a.family}", addr)
        except Exception:
            pass

    return facts


# ---------------------------
# OBS inventory via WebSocket
# ---------------------------

COMMON_DEVICE_KEYS = [
    "device_id",
    "device",
    "audio_device_id",
    "video_device_id",
    "input_device_id",
    "capture_device",
    "mic_device",
]

COMMON_FRIENDLY_NAME_KEYS = [
    "device_name",
    "device",
    "name",
    "capture_device_name",
    "audio_device_name",
    "video_device_name",
]


def _pluck_device_fields(settings: Dict[str, Any]) -> Tuple[str, str]:
    device_id = ""
    device_name = ""

    for k in COMMON_DEVICE_KEYS:
        if k in settings and settings[k]:
            device_id = str(settings[k])
            break

    for k in COMMON_FRIENDLY_NAME_KEYS:
        if k in settings and settings[k]:
            device_name = str(settings[k])
            break

    return device_id, device_name


def safe_call(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def collect_obs_app_metadata(client: ReqClient) -> Dict[str, Any]:
    ver = safe_call(lambda: client.get_version(), default={})
    out: Dict[str, Any] = {}
    if ver:
        for k in dir(ver):
            if k.startswith("_"):
                continue
            try:
                v = getattr(ver, k)
            except Exception:
                continue
            if isinstance(v, (str, int, float, bool)) or v is None:
                out[k] = v
    return out


def collect_obs_inputs(client: ReqClient) -> List[Dict[str, Any]]:
    ts = utc_now_iso()
    rows: List[Dict[str, Any]] = []

    inputs = safe_call(lambda: client.get_input_list().inputs, default=[]) or []
    for inp in inputs:
        name = inp.get("inputName")
        kind = inp.get("inputKind")
        is_audio = bool(inp.get("inputAudio", False))
        is_video = bool(inp.get("inputVideo", False))

        settings_obj = safe_call(lambda: client.get_input_settings(name).input_settings, default={}) or {}
        device_id, device_name = _pluck_device_fields(settings_obj)

        rows.append({
            "timestamp_utc": ts,
            "input_name": name,
            "input_kind": kind,
            "is_audio": is_audio,
            "is_video": is_video,
            "selected_device_id": device_id,
            "selected_device_name": device_name,
            "raw_settings_json": json.dumps(settings_obj, separators=(",", ":"), ensure_ascii=False),
        })

    return rows


def collect_obs_scenes(client: ReqClient) -> List[Dict[str, Any]]:
    ts = utc_now_iso()
    out: List[Dict[str, Any]] = []

    scenes = safe_call(lambda: client.get_scene_list().scenes, default=[]) or []
    for scene in scenes:
        scene_name = scene.get("sceneName")
        items = safe_call(lambda: client.get_scene_item_list(scene_name).scene_items, default=[]) or []
        for idx, it in enumerate(items):
            out.append({
                "timestamp_utc": ts,
                "scene_name": scene_name,
                "order_index": idx,
                "scene_item_id": it.get("sceneItemId"),
                "source_name": it.get("sourceName"),
                "enabled": it.get("sceneItemEnabled"),
            })

    return out


def collect_obs_recording_session(client: ReqClient) -> List[Dict[str, Any]]:
    ts = utc_now_iso()

    current_scene = safe_call(lambda: client.get_current_program_scene().current_program_scene_name, default=None)
    current_profile = safe_call(lambda: client.get_current_profile().current_profile_name, default=None)
    current_collection = safe_call(lambda: client.get_current_scene_collection().current_scene_collection_name, default=None)

    record_status = safe_call(lambda: client.get_record_status(), default=None)
    stream_status = safe_call(lambda: client.get_stream_status(), default=None)
    virtualcam_status = safe_call(lambda: client.get_virtual_cam_status(), default=None)

    video_settings = safe_call(lambda: client.get_video_settings(), default=None)
    audio_settings = safe_call(lambda: client.get_audio_settings(), default=None)
    record_dir = safe_call(lambda: client.get_record_directory().record_directory, default=None)

    stats = safe_call(lambda: client.get_stats(), default=None)
    ver = collect_obs_app_metadata(client)

    def obj_to_json(o) -> str:
        if o is None:
            return ""
        try:
            d = o.__dict__
            return json.dumps(d, separators=(",", ":"), ensure_ascii=False, default=str)
        except Exception:
            return json.dumps(str(o), ensure_ascii=False)

    row = {
        "timestamp_utc": ts,
        "current_program_scene": current_scene or "",
        "current_profile": current_profile or "",
        "current_scene_collection": current_collection or "",
        "record_directory": record_dir or "",
        "record_status_json": obj_to_json(record_status),
        "stream_status_json": obj_to_json(stream_status),
        "virtualcam_status_json": obj_to_json(virtualcam_status),
        "video_settings_json": obj_to_json(video_settings),
        "audio_settings_json": obj_to_json(audio_settings),
        "stats_json": obj_to_json(stats),
        "obs_version_json": json.dumps(ver, separators=(",", ":"), ensure_ascii=False),
    }
    return [row]


# ---------------------------
# Hashing (SHA-256) for recorded file
# ---------------------------

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def wait_until_stable(path: Path, check_interval: float = 1.0, stable_checks: int = 3):
    """Wait until file size stops changing to avoid hashing partial writes."""
    prev = -1
    stable = 0
    while stable < stable_checks:
        size = path.stat().st_size
        if size == prev:
            stable += 1
        else:
            stable = 0
            prev = size
        time.sleep(check_interval)


def write_sha256_sidecar(recording_path: str, sidecar_suffix: str = ".sha256") -> Optional[str]:
    p = Path(recording_path)
    if not p.exists() or not p.is_file():
        return None

    wait_until_stable(p)
    digest = sha256_file(p)

    sidecar = p.with_suffix(p.suffix + sidecar_suffix)
    sidecar.write_text(digest + "  " + p.name, encoding="utf-8")
    return str(sidecar)


# ---------------------------
# CSV Writers
# ---------------------------

def write_system_inventory_csv(path: Path, facts: List[Tuple[str, str, str]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp_utc", "category", "key", "value"])
        ts = utc_now_iso()
        for cat, key, val in facts:
            if cat == "time" and key == "timestamp_utc":
                ts = val
            writer.writerow([ts, cat, key, val])


def write_dict_rows_csv(path: Path, rows: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with path.open("w", newline="", encoding="utf-8") as f:
            f.write("timestamp_utc\n")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


# ---------------------------
# Public entrypoints
# ---------------------------

def generate_inventory_csv(
    output_dir: str,
    include_scenes: bool = True,
    include_recording_session: bool = True,
):
    out_dir = Path(output_dir)
    stamp = utc_stamp_for_filename()

    sys_csv = out_dir / f"system_inventory_{stamp}.csv"
    inputs_csv = out_dir / f"obs_inputs_inventory_{stamp}.csv"
    scenes_csv = out_dir / f"obs_scenes_inventory_{stamp}.csv"
    session_csv = out_dir / f"obs_recording_session_{stamp}.csv"

    facts = collect_system_facts()
    write_system_inventory_csv(sys_csv, facts)

    cfg = ObsWsConfig.from_env()
    client = ReqClient(host=cfg.host, port=cfg.port, password=cfg.password)

    inputs = collect_obs_inputs(client)
    write_dict_rows_csv(inputs_csv, inputs)

    if include_scenes:
        scenes = collect_obs_scenes(client)
        write_dict_rows_csv(scenes_csv, scenes)

    if include_recording_session:
        session = collect_obs_recording_session(client)
        write_dict_rows_csv(session_csv, session)

    return {
        "system_inventory_csv": str(sys_csv),
        "obs_inputs_inventory_csv": str(inputs_csv),
        "obs_scenes_inventory_csv": str(scenes_csv) if include_scenes else None,
        "obs_recording_session_csv": str(session_csv) if include_recording_session else None,
    }


def run_on_recording_stop(
    output_dir: str,
    include_scenes: bool = True,
    include_recording_session: bool = True,
    create_sha256_sidecar: bool = True,
    print_events: bool = False,
):
    """Daemon: listen for recording stop and then write CSV inventory + optional SHA-256 sidecar.

    This integrates "inventory capture" + "recording hash" into ONE skill module.

    It uses obsws-python's EventClient callback registration. Callback name must match
    the event in snake_case, prefixed with 'on_'.
    """
    cfg = ObsWsConfig.from_env()

    # Event client for callbacks; separate ReqClient used to call RPCs if needed.
    ev = EventClient(host=cfg.host, port=cfg.port, password=cfg.password)
    req = ReqClient(host=cfg.host, port=cfg.port, password=cfg.password)

    # Keep track of the last known output path from record events.
    state = {"last_output_path": ""}

    def _log(msg: str):
        if print_events:
            print(msg, flush=True)

    def on_record_state_changed(data):
        # Example fields observed in obsws-python:
        #   data.output_state, data.output_path
        output_state = getattr(data, "output_state", "")
        output_path = getattr(data, "output_path", "") or ""
        if output_path:
            state["last_output_path"] = output_path

        _log(f"[RecordStateChanged] state={output_state} path={output_path}")

        # Stop event: run capture + hash
        if output_state == "OBS_WEBSOCKET_OUTPUT_STOPPED":
            _log("[RecordStateChanged] Recording stopped. Capturing inventory...")
            files = generate_inventory_csv(
                output_dir=output_dir,
                include_scenes=include_scenes,
                include_recording_session=include_recording_session,
            )
            _log(f"[Inventory] {files}")

            if create_sha256_sidecar and state["last_output_path"]:
                sidecar = write_sha256_sidecar(state["last_output_path"])
                _log(f"[SHA256] sidecar={sidecar}")

    # Some OBS versions also emit RecordFileChanged with the new file path.
    def on_record_file_changed(data):
        # Protocol docs mention file name for saved recording / new file.
        # Field names vary; try common attributes.
        possible = [
            getattr(data, "new_output_path", ""),
            getattr(data, "output_path", ""),
            getattr(data, "recording_file_path", ""),
            getattr(data, "record_file_path", ""),
            getattr(data, "record_file", ""),
        ]
        p = next((x for x in possible if x), "")
        if p:
            state["last_output_path"] = p
        _log(f"[RecordFileChanged] path={p}")

    ev.callback.register([on_record_state_changed, on_record_file_changed])

    _log("Listening for OBS recording stop events. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        _log("Exiting.")
