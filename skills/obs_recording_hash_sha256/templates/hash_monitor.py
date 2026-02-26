import os
import time
import hashlib
from pathlib import Path

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
    previous_size = -1
    stable_count = 0

    while stable_count < stable_checks:
        current_size = path.stat().st_size
        if current_size == previous_size:
            stable_count += 1
        else:
            stable_count = 0
            previous_size = current_size
        time.sleep(check_interval)

def monitor_directory(
    recording_directory: str,
    poll_interval: float = 5.0,
    create_sidecar: bool = True,
    log_file: str | None = None,
):
    seen = set()
    directory = Path(recording_directory)

    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {recording_directory}")

    print(f"Monitoring: {directory.resolve()}")

    while True:
        for file in directory.iterdir():
            if not file.is_file():
                continue
            if file.suffix.lower() not in {".mp4", ".mkv", ".mov", ".flv"}:
                continue
            if file.name in seen:
                continue

            print(f"New recording detected: {file.name}")
            wait_until_stable(file)

            digest = sha256_file(file)
            print(f"SHA-256: {digest}")

            if create_sidecar:
                sidecar_path = file.with_suffix(file.suffix + ".sha256")
                sidecar_path.write_text(digest + "  " + file.name)

            if log_file:
                with open(log_file, "a", encoding="utf-8") as log:
                    log.write(f"{file.name},{digest}\n")

            seen.add(file.name)

        time.sleep(poll_interval)
