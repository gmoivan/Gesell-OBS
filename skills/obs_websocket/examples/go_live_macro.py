"""
Example macro: Go Live
- Set scene
- Unmute mic input
- Start streaming

Requires:
  pip install obsws-python

Configure via env vars:
  OBS_WS_HOST, OBS_WS_PORT, OBS_WS_PASSWORD
Optional:
  GO_LIVE_SCENE (default: "Starting Soon")
  GO_LIVE_MIC_INPUT (default: "Mic/Aux")
"""

import os
from skills.obs_websocket.templates.python_client import ObsWsConfig, ObsController

def main():
    cfg = ObsWsConfig.from_env()
    ctl = ObsController(cfg)

    scene = os.getenv("GO_LIVE_SCENE", "Starting Soon")
    mic = os.getenv("GO_LIVE_MIC_INPUT", "Mic/Aux")

    ctl.set_scene(scene)
    ctl.set_input_mute(mic, False)
    ctl.start_stream()
    print("Go Live macro executed.")

if __name__ == "__main__":
    main()
