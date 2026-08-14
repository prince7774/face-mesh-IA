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
import status_bus
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


GESTURE_LABELS_PT = {
    "double_blink": "piscar duplo",
    "brow_raise": "sobrancelha levantada",
    "mouth_open": "boca aberta",
    "gaze_left": "olhar esquerda",
    "gaze_right": "olhar direita",
    "gaze_up": "olhar cima",
    "gaze_down": "olhar baixo",
}

COUNTER_LABELS_PT = {
    "double_blink": "Piscadas",
    "brow_raise": "Sobrancelha",
    "mouth_open": "Boca",
    "gaze_left": "Olhar Esq",
    "gaze_right": "Olhar Dir",
    "gaze_up": "Olhar Cima",
    "gaze_down": "Olhar Baixo",
}


def draw_gesture_counters(frame, counts):
    """Desenha uma barra horizontal na parte de baixo com a contagem de cada gesto."""
    h, w = frame.shape[:2]
    items = [(COUNTER_LABELS_PT[k], counts.get(k, 0)) for k in COUNTER_LABELS_PT]

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.42
    thickness = 1
    bar_h = 32
    y0 = h - bar_h
    pad_x = 8

    # calcula a largura de cada coluna pelo texto real, evitando sobreposição
    texts = [f"{label}: {count}" for label, count in items]
    col_widths = []
    for t in texts:
        (tw, th), _ = cv2.getTextSize(t, font, font_scale, thickness)
        col_widths.append(tw + pad_x * 2)

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, y0), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.line(frame, (0, y0), (w, y0), (80, 80, 80), 1)

    x = 0
    for i, t in enumerate(texts):
        cv2.putText(frame, t, (x + pad_x, y0 + 21), font, font_scale,
                    (0, 255, 150), thickness, cv2.LINE_AA)
        x += col_widths[i]
        if i < len(texts) - 1 and x < w:
            cv2.line(frame, (x, y0), (x, h), (60, 60, 60), 1)


def draw_face_landmarks(frame, face_landmarker_result):
    """Desenha um pontinho para cada ponto de referência detectado no rosto."""
    if not face_landmarker_result.face_landmarks:
        return
    h, w = frame.shape[:2]
    landmarks = face_landmarker_result.face_landmarks[0]
    for lm in landmarks:
        x, y = int(lm.x * w), int(lm.y * h)
        cv2.circle(frame, (x, y), 1, (0, 255, 150), -1)


def draw_debug_overlay(frame, mode, gestures_fired, metrics):
    """Desenha um painel tipo tabela no canto superior esquerdo com os valores."""
    gestures_pt = [GESTURE_LABELS_PT.get(g, g) for g in gestures_fired]
    mode_pt = "navegação" if mode == "navegacao" else mode

    rows = [
        ("Modo", mode_pt),
        ("Gesto", ", ".join(gestures_pt) if gestures_pt else "-"),
        ("Olhar h", f"{metrics['h']:.2f}"),
        ("Olhar v", f"{metrics['v']:.2f}"),
        ("Piscar E", f"{metrics['blink_l']:.2f}"),
        ("Piscar D", f"{metrics['blink_r']:.2f}"),
        ("Sobrancelha", f"{metrics['brow']:.2f}"),
        ("Boca", f"{metrics['jaw']:.2f}"),
    ]

    label_col_w = 130
    value_col_w = 90
    row_h = 26
    pad = 10
    box_w = label_col_w + value_col_w + pad * 2
    box_h = row_h * len(rows) + pad * 2

    h, w = frame.shape[:2]
    x0 = w - box_w - 12  # encostado na direita
    y0 = 12

    # fundo semi-transparente
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0, y0), (x0 + box_w, y0 + box_h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
    cv2.rectangle(frame, (x0, y0), (x0 + box_w, y0 + box_h), (80, 80, 80), 1)

    for i, (label, value) in enumerate(rows):
        y = y0 + pad + i * row_h + 18
        cv2.putText(frame, label, (x0 + pad, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (180, 180, 180), 1, cv2.LINE_AA)
        cv2.putText(frame, value, (x0 + pad + label_col_w, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (0, 255, 150), 1, cv2.LINE_AA)
        if i < len(rows) - 1:
            cv2.line(frame, (x0, y0 + pad + (i + 1) * row_h),
                      (x0 + box_w, y0 + pad + (i + 1) * row_h), (60, 60, 60), 1)


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

    gesture_counts = {k: 0 for k in COUNTER_LABELS_PT}

    if config.SHOW_DEBUG_OVERLAY:
        cv2.namedWindow("TecladoIA - debug", cv2.WINDOW_NORMAL)
        # ~1/3 de uma tela comum (assume algo perto de 1920x1080; ajuste
        # os números abaixo se sua tela for muito diferente disso)
        cv2.resizeWindow("TecladoIA - debug", 640, 480)

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
            status_bus.write_status(executor.mode, gestures_fired)

            for g in gestures_fired:
                if g in gesture_counts:
                    gesture_counts[g] += 1

            if config.SHOW_DEBUG_OVERLAY:
                draw_face_landmarks(frame, result)
                draw_debug_overlay(frame, executor.mode, gestures_fired, metrics)
                draw_gesture_counters(frame, gesture_counts)
                cv2.imshow("TecladoIA - debug", frame)
                cv2.resizeWindow("TecladoIA - debug", config.FRAME_WIDTH, config.FRAME_HEIGHT)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        landmarker.close()


if __name__ == "__main__":
    main()