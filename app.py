"""
app.py
-------
Versão com interface gráfica do TecladoIA (substitui a janela de debug
do OpenCV por um painel HTML/CSS/JS, exibido numa janela nativa via
pywebview).

Uso:
    python app.py
"""

import base64
import json
import os
import sys
import threading
import time

import cv2
import mediapipe as mp
import webview
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

import config
import status_bus
from actions import ActionExecutor
from gesture_detector import GestureDetector

GUI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui")
INDEX_HTML = os.path.join(GUI_DIR, "index.html")


class AppState:
    def __init__(self):
        self.running = True
        self.detector = GestureDetector()
        self.executor = ActionExecutor()
        self.window = None


class Api:
    def __init__(self, state):
        self.state = state

    def toggle_mode(self):
        self.state.executor._toggle_mode()
        return self.state.executor.mode

    def quit(self):
        self.state.running = False
        return True


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


def camera_loop(state):
    try:
        landmarker = build_landmarker()
    except Exception as e:
        _push_error(state, f"Erro ao carregar o modelo: {e}")
        return

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    if not cap.isOpened():
        _push_error(state, "Nao consegui abrir a camera. Verifique config.CAMERA_INDEX.")
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

        ok2, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if ok2 and state.window:
            payload = {
                "frame": base64.b64encode(buf).decode("ascii"),
                "mode": state.executor.mode,
                "gestures": gestures_fired,
                "metrics": metrics,
            }
            _push_to_ui(state, payload)

        time.sleep(0.01)

    cap.release()
    landmarker.close()


def _push_to_ui(state, payload):
    try:
        state.window.evaluate_js(f"window.updateStatus({json.dumps(payload)})")
    except Exception:
        pass


def _push_error(state, message):
    print(message)
    if state.window:
        try:
            safe = json.dumps(message)
            state.window.evaluate_js(
                f'document.querySelector(".video-placeholder p").textContent = {safe}'
            )
        except Exception:
            pass


def main():
    state = AppState()
    api = Api(state)

    window = webview.create_window(
        "TecladoIA",
        INDEX_HTML,
        js_api=api,
        width=1040,
        height=680,
        min_size=(820, 560),
        background_color="#0F1420",
    )
    state.window = window

    def on_loaded():
        threading.Thread(target=camera_loop, args=(state,), daemon=True).start()

    window.events.loaded += on_loaded

    webview.start(gui="edgechromium", debug=False)
    state.running = False


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        print("=== ERRO AO INICIAR A INTERFACE ===")
        traceback.print_exc()
        input("Pressione Enter para fechar...")