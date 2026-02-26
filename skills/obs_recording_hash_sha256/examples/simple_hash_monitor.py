from skills.obs_recording_hash_sha256.templates.hash_monitor import monitor_directory

RECORDING_DIR = r"C:\Users\YourUser\Videos"

if __name__ == "__main__":
    monitor_directory(
        recording_directory=RECORDING_DIR,
        poll_interval=5.0,
        create_sidecar=True,
        log_file="recording_hash_log.csv",
    )
