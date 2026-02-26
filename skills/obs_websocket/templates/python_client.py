"""
Gesell template: OBS WebSocket Python client (obsws-python).

Install:
  pip install obsws-python

Env vars (recommended):
  OBS_WS_HOST, OBS_WS_PORT, OBS_WS_PASSWORD
"""

import os
from dataclasses import dataclass

from obsws_python import ReqClient


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


class ObsController:
    def __init__(self, cfg: ObsWsConfig):
        self.cfg = cfg
        self.client = ReqClient(host=cfg.host, port=cfg.port, password=cfg.password)

    def set_scene(self, scene_name: str):
        self.client.set_current_program_scene(scene_name)

    def set_input_mute(self, input_name: str, mute: bool):
        self.client.set_input_mute(input_name, mute)

    def set_scene_item_enabled(self, scene_name: str, source_name: str, enabled: bool):
        item_id = self.client.get_scene_item_id(scene_name, source_name).scene_item_id
        self.client.set_scene_item_enabled(scene_name, item_id, enabled)

    def start_stream(self):
        self.client.start_stream()

    def stop_stream(self):
        self.client.stop_stream()

    def start_record(self):
        self.client.start_record()

    def stop_record(self):
        self.client.stop_record()
