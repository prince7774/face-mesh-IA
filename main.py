"""
main.py
--------
TecladoIA — controle de interface por expressões faciais.

Uso:
    python main.py

Pressione 'q' na janela de vídeo para sair.
Levante as sobrancelhas para alternar entre os modos "mouse" e "navegacao".

Requer o modelo face_landmarker.task na mesma pasta (ver README.md).
"""

import sys
import time

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

import config
from gesture_detector import GestureDetector
from actions import ActionExecutor


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


def draw_debug_overlay(frame, mode, gestures_fired, metrics):
    h, w = frame.shape[:2]
    lines = [
        f"Modo: {mode}",
        f"Gestos: {', '.join(gestures_fired) if gestures_fired else '-'}",
        f"olhar h={metrics['h']:.2f} v={metrics['v']:.2f}",
        f"piscar E={metrics['blink_l']:.2f} D={metrics['blink_r']:.2f}",
        f"sobrancelha={metrics['brow']:.2f} boca={metrics['jaw']:.2f}",
    ]
    for i, line in enumerate(lines):
        cv2.putText(frame, line, (10, 25 + i * 22), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 0), 2, cv2.LINE_AA)


def main():
    try:
        landmarker = build_landmarker()
    except Exception as e:
        print(f"Erro ao carregar o modelo '{config.MODEL_PATH}': {e}")
        print("Verifique se o arquivo face_landmarker.task está na pasta do projeto (veja README.md).")
        sys.exit(1)

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    if not cap.isOpened():
        print("Não consegui abrir a câmera. Verifique config.CAMERA_INDEX.")
        sys.exit(1)

    detector = GestureDetector()

    def on_mode_change(new_mode):
        print(f"[modo alterado] -> {new_mode}")

    executor = ActionExecutor(on_mode_change=on_mode_change)

    start_time = time.time()
    print("TecladoIA rodando. Pressione 'q' na janela de vídeo para sair.")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Falha ao ler frame da câmera.")
                break

            frame = cv2.flip(frame, 1)  # espelha, fica mais natural pro usuário
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            timestamp_ms = int((time.time() - start_time) * 1000)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            gestures_fired, metrics = detector.detect(result)
            executor.handle_gestures(gestures_fired)

            if config.SHOW_DEBUG_OVERLAY:
                draw_debug_overlay(frame, executor.mode, gestures_fired, metrics)
                cv2.imshow("TecladoIA - debug", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        landmarker.close()


if __name__ == "__main__":
    main()