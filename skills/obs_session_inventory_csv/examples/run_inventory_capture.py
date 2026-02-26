import os
from skills.obs_session_inventory_csv.templates.generate_inventory_csv import (
    generate_inventory_csv,
    run_on_recording_stop,
)

if __name__ == "__main__":
    mode = os.getenv("INVENTORY_MODE", "once").lower().strip()
    out_dir = os.getenv("INVENTORY_OUT_DIR", ".")
    include_scenes = os.getenv("INCLUDE_SCENES", "1") != "0"
    include_recording_session = os.getenv("INCLUDE_RECORDING_SESSION", "1") != "0"

    if mode == "daemon":
        run_on_recording_stop(
            output_dir=out_dir,
            include_scenes=include_scenes,
            include_recording_session=include_recording_session,
            create_sha256_sidecar=os.getenv("CREATE_SHA256_SIDECAR", "1") != "0",
            print_events=os.getenv("PRINT_EVENTS", "1") != "0",
        )
    else:
        out = generate_inventory_csv(
            output_dir=out_dir,
            include_scenes=include_scenes,
            include_recording_session=include_recording_session,
        )
        print("Wrote:")
        for k, v in out.items():
            print(f"  {k}: {v}")
