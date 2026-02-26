"""
Example macro: BRB
- Set BRB scene
- Mute mic
- Optionally disable a camera source in the BRB scene

Requires:
  pip install obsws-python

Env vars:
  OBS_WS_HOST, OBS_WS_PORT, OBS_WS_PASSWORD
Optional:
  BRB_SCENE (default: "BRB")
  BRB_MIC_INPUT (default: "Mic/Aux")
  BRB_CAMERA_SOURCE (optional)
"""

import os
from skills.obs_websocket.templates.python_client import ObsWsConfig, ObsController

def main():
    cfg = ObsWsConfig.from_env()
    ctl = ObsController(cfg)

    scene = os.getenv("BRB_SCENE", "BRB")
    mic = os.getenv("BRB_MIC_INPUT", "Mic/Aux")
    cam = os.getenv("BRB_CAMERA_SOURCE", "")

    ctl.set_scene(scene)
    ctl.set_input_mute(mic, True)

    if cam:
        ctl.set_scene_item_enabled(scene, cam, False)

    print("BRB macro executed.")

if __name__ == "__main__":
    main()
