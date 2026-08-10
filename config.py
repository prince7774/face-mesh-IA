"""
config.py
----------
Ponto único de configuração do TecladoIA.

Se um gesto está disparando cedo demais (falso positivo) ou tarde demais
(não detecta), ajuste os valores em THRESHOLDS.
Se quiser mudar o que cada gesto faz, mexa em GESTURE_ACTIONS.
"""

# ---------------------------------------------------------------------------
# LIMIARES (0.0 a 1.0 para blendshapes; pixels/proporção para o resto)
# ---------------------------------------------------------------------------
THRESHOLDS = {
    # Blendshape "eyeBlinkLeft"/"eyeBlinkRight": quanto maior, mais fechado o olho.
    "blink_score": 0.5,
    # Janela de tempo (segundos) para considerar dois piscares como "piscar duplo".
    "double_blink_window": 0.6,
    # Tempo mínimo (segundos) que o olho precisa ficar aberto entre um piscar e outro,
    # pra não confundir um piscar longo com dois piscares.
    "blink_min_gap": 0.08,

    # Blendshape "browInnerUp": sobrancelha levantada.
    "brow_raise_score": 0.4,

    # Blendshape "jawOpen": boca aberta.
    "mouth_open_score": 0.35,

    # Direção do olhar: posição da íris dentro do "retângulo" do olho, normalizada de 0 a 1.
    # < gaze_h_left  -> olhando para a esquerda (da perspectiva de quem olha a câmera)
    # > gaze_h_right -> olhando para a direita
    "gaze_h_left": 0.38,
    "gaze_h_right": 0.62,
    "gaze_v_up": 0.38,
    "gaze_v_down": 0.62,

    # Tempo (segundos) que o olhar precisa se manter numa direção antes de disparar,
    # pra não acionar só porque a pessoa passou o olho de relance.
    "gaze_hold_time": 0.35,
}

# ---------------------------------------------------------------------------
# COOLDOWN — tempo mínimo (segundos) entre disparos do MESMO gesto,
# pra não sair clicando/scrollando sem parar enquanto o gesto continua ativo.
# ---------------------------------------------------------------------------
COOLDOWN_SECONDS = {
    "double_blink": 0.5,
    "brow_raise": 0.8,
    "mouth_open": 0.5,
    "gaze_left": 0.5,
    "gaze_right": 0.5,
    "gaze_up": 0.4,
    "gaze_down": 0.4,
}

# ---------------------------------------------------------------------------
# MODOS — o levantar de sobrancelha alterna entre modos.
# Cada modo reinterpreta os MESMOS gestos de forma diferente.
# ---------------------------------------------------------------------------
MODES = ["mouse", "navegacao"]

# ---------------------------------------------------------------------------
# AÇÕES por gesto, por modo.
# Tipos suportados (ver actions.py): "mouse_click", "mouse_move_dir", "key_press",
# "scroll", "toggle_mode"
# ---------------------------------------------------------------------------
GESTURE_ACTIONS = {
    "mouse": {
        "double_blink": {"type": "mouse_click", "button": "left"},
        "mouth_open": {"type": "mouse_click", "button": "right"},
        "gaze_left": {"type": "mouse_move_dir", "dx": -25, "dy": 0},
        "gaze_right": {"type": "mouse_move_dir", "dx": 25, "dy": 0},
        "gaze_up": {"type": "mouse_move_dir", "dx": 0, "dy": -25},
        "gaze_down": {"type": "mouse_move_dir", "dx": 0, "dy": 25},
        "brow_raise": {"type": "toggle_mode"},
    },
    "navegacao": {
        "double_blink": {"type": "key_press", "key": "enter"},
        "mouth_open": {"type": "key_press", "key": "alt+left"},   # voltar página
        "gaze_left": {"type": "key_press", "key": "shift+tab"},   # elemento anterior
        "gaze_right": {"type": "key_press", "key": "tab"},        # próximo elemento
        "gaze_up": {"type": "scroll", "amount": 180},
        "gaze_down": {"type": "scroll", "amount": -180},
        "brow_raise": {"type": "toggle_mode"},
    },
}

# Câmera
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# Caminho do modelo do Face Landmarker (baixe conforme o README.md)
MODEL_PATH = "face_landmarker.task"

# Mostrar overlay de debug (pontos do rosto, modo atual, valores de blendshape)
SHOW_DEBUG_OVERLAY = True
