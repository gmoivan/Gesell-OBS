/**
 * Gesell template: OBS WebSocket Node client (obs-websocket-js).
 *
 * Install:
 *   npm i obs-websocket-js
 *
 * Env vars:
 *   OBS_WS_HOST, OBS_WS_PORT, OBS_WS_PASSWORD
 */

import OBSWebSocket from "obs-websocket-js";

const host = process.env.OBS_WS_HOST ?? "localhost";
const port = process.env.OBS_WS_PORT ?? "4455";
const password = process.env.OBS_WS_PASSWORD ?? "";

const obs = new OBSWebSocket();

export async function connect() {
  await obs.connect(`ws://${host}:${port}`, password);
}

export async function setScene(sceneName) {
  await obs.call("SetCurrentProgramScene", { sceneName });
}

export async function setMute(inputName, inputMuted) {
  await obs.call("SetInputMute", { inputName, inputMuted });
}

export async function startStream() {
  await obs.call("StartStream");
}

export async function disconnect() {
  await obs.disconnect();
}
