"""
app_server.py
--------------
Versão web local do painel do TecladoIA. Em vez de uma janela nativa via
pywebview (que dependia do WebView2 Runtime do Windows, indisponível
nesse PC), este servidor local abre o mesmo painel no seu navegador
padrão — mesma interface, sem depender de nenhum motor extra do sistema.

Uso:
    python app_server.py

Abre automaticamente http://127.0.0.1:8765 no navegador.
Pressione Ctrl+C no terminal para encerrar o servidor.
"""

import base64
import os
import threading
import time
import webbrowser

import cv2
import mediapipe as mp
from flask import Flask, jsonify, send_from_directory
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

import config
import status_bus
from actions import ActionExecutor
from gesture_detector import GestureDetector

GUI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui")
PORT = 8765

app = Flask(__name__, static_folder=None)


GESTURE_LABELS_PT = {
    "double_blink": "Piscar duplo",
    "brow_raise": "Sobrancelha",
    "mouth_open": "Boca aberta",
    "gaze_left": "Olhar esquerda",
    "gaze_right": "Olhar direita",
    "gaze_up": "Olhar cima",
    "gaze_down": "Olhar baixo",
}


def draw_face_landmarks(frame, face_landmarker_result):
    """Desenha um pontinho verde para cada ponto de referência detectado no rosto."""
    if not face_landmarker_result.face_landmarks:
        return
    h, w = frame.shape[:2]
    landmarks = face_landmarker_result.face_landmarks[0]
    for lm in landmarks:
        x, y = int(lm.x * w), int(lm.y * h)
        cv2.circle(frame, (x, y), 1, (150, 255, 0), -1)


class SharedState:
    def __init__(self):
        self.running = True
        self.detector = GestureDetector()
        self.executor = ActionExecutor()
        self.lock = threading.Lock()
        self.gesture_counts = {k: 0 for k in GESTURE_LABELS_PT}
        self.latest = {
            "frame": None,
            "mode": "mouse",
            "gestures": [],
            "metrics": {},
            "counts": dict(self.gesture_counts),
            "camera_error": None,
        }


state = SharedState()


@app.route("/")
def index():
    return send_from_directory(GUI_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(GUI_DIR, filename)


@app.route("/api/status")
def api_status():
    with state.lock:
        return jsonify(state.latest)


@app.route("/api/toggle_mode", methods=["POST"])
def api_toggle_mode():
    state.executor._toggle_mode()
    return jsonify({"mode": state.executor.mode})


@app.route("/api/quit", methods=["POST"])
def api_quit():
    state.running = False

    def _shutdown():
        time.sleep(0.3)
        os._exit(0)

    threading.Thread(target=_shutdown, daemon=True).start()
    return jsonify({"ok": True})


def build_landmarker():
    base_options = mp_python.BaseOptions(model_asset_path=config.MODEL_PATH)
    options = mp_vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=mp_vision.RunningMode.VIDEO,
        num_faces=1,
        output_face_blendshapes=True,
        output_facial_transformation_matrixes=False,
        min_face_detection_confidence=0.5,
        min_face_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return mp_vision.FaceLandmarker.create_from_options(options)


def camera_loop():
    try:
        landmarker = build_landmarker()
    except Exception as e:
        with state.lock:
            state.latest["camera_error"] = f"Erro ao carregar o modelo: {e}"
        return

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    if not cap.isOpened():
        with state.lock:
            state.latest["camera_error"] = (
                "Nao consegui abrir a camera. Verifique config.CAMERA_INDEX."
            )
        return

    start_time = time.time()

    while state.running:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.2)
            continue

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        timestamp_ms = int((time.time() - start_time) * 1000)
        result = landmarker.detect_for_video(mp_image, timestamp_ms)

        gestures_fired, metrics = state.detector.detect(result)
        state.executor.handle_gestures(gestures_fired)
        status_bus.write_status(state.executor.mode, gestures_fired)

        for g in gestures_fired:
            if g in state.gesture_counts:
                state.gesture_counts[g] += 1

        draw_face_landmarks(frame, result)

        ok2, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if ok2:
            with state.lock:
                state.latest = {
                    "frame": base64.b64encode(buf).decode("ascii"),
                    "mode": state.executor.mode,
                    "gestures": gestures_fired,
                    "metrics": metrics,
                    "counts": dict(state.gesture_counts),
                    "camera_error": None,
                }

        time.sleep(0.03)

    cap.release()
    landmarker.close()


if __name__ == "__main__":
    threading.Thread(target=camera_loop, daemon=True).start()
    threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}")).start()
    print(f"TecladoIA rodando em http://127.0.0.1:{PORT} — abrindo no navegador...")
    app.run(host="127.0.0.1", port=PORT, debug=False)