"""
gesture_detector.py
--------------------
Recebe o resultado bruto do FaceLandmarker (blendshapes + landmarks) e
devolve uma lista de gestos detectados neste frame: ex. ["double_blink"],
["gaze_left"], [] (nenhum), etc.

Não conhece nada sobre mouse/teclado — só interpreta o rosto.
"""

import time
from config import THRESHOLDS

# Índices dos landmarks de íris e cantos dos olhos no FaceLandmarker
# (modelo com 478 pontos, íris incluída).
LEFT_EYE_CORNERS = (33, 133)      # canto externo, canto interno (olho esquerdo da pessoa)
RIGHT_EYE_CORNERS = (362, 263)    # canto interno, canto externo (olho direito da pessoa)
LEFT_EYE_TOP_BOTTOM = (159, 145)
RIGHT_EYE_TOP_BOTTOM = (386, 374)
LEFT_IRIS_CENTER = 468
RIGHT_IRIS_CENTER = 473


class GestureDetector:
    def __init__(self, thresholds=None):
        self.t = thresholds or THRESHOLDS

        # Estado interno para reconhecer piscar duplo
        self._eye_was_closed = False
        self._last_blink_time = 0.0
        self._pending_double_blink_start = None

        # Estado para "olhar sustentado" (evita disparo por passada rápida do olho)
        self._gaze_dir_since = {}  # direção -> timestamp de quando começou

    def _blendshape_score(self, blendshapes, name):
        for cat in blendshapes:
            if cat.category_name == name:
                return cat.score
        return 0.0

    def _gaze_position(self, landmarks, corners, iris_idx, top_bottom):
        """Retorna (h, v) normalizados 0..1 da posição da íris dentro do olho."""
        c0, c1 = corners
        p0 = landmarks[c0]
        p1 = landmarks[c1]
        iris = landmarks[iris_idx]
        top = landmarks[top_bottom[0]]
        bottom = landmarks[top_bottom[1]]

        eye_width = max(abs(p1.x - p0.x), 1e-6)
        eye_height = max(abs(bottom.y - top.y), 1e-6)

        h = (iris.x - min(p0.x, p1.x)) / eye_width
        v = (iris.y - min(top.y, bottom.y)) / eye_height
        return h, v

    def detect(self, face_landmarker_result):
        """
        face_landmarker_result: resultado do FaceLandmarker (tem
        .face_blendshapes e .face_landmarks, ambos listas — pegamos o rosto 0).
        Retorna: lista de strings com os gestos disparados neste frame.
        """
        now = time.time()
        fired = []

        if not face_landmarker_result.face_landmarks:
            return fired  # nenhum rosto detectado

        landmarks = face_landmarker_result.face_landmarks[0]
        blendshapes = (
            face_landmarker_result.face_blendshapes[0]
            if face_landmarker_result.face_blendshapes
            else []
        )

        # --- Piscar duplo ---------------------------------------------------
        blink_l = self._blendshape_score(blendshapes, "eyeBlinkLeft")
        blink_r = self._blendshape_score(blendshapes, "eyeBlinkRight")
        eyes_closed = (blink_l > self.t["blink_score"]) and (blink_r > self.t["blink_score"])

        if eyes_closed and not self._eye_was_closed:
            # borda de descida: olho acabou de fechar -> conta como um piscar
            gap = now - self._last_blink_time
            if gap >= self.t["blink_min_gap"]:
                if self._pending_double_blink_start is not None and \
                        (now - self._pending_double_blink_start) <= self.t["double_blink_window"]:
                    fired.append("double_blink")
                    self._pending_double_blink_start = None
                else:
                    self._pending_double_blink_start = now
                self._last_blink_time = now
        self._eye_was_closed = eyes_closed

        # Expira a janela de piscar duplo se passou tempo demais
        if self._pending_double_blink_start is not None and \
                (now - self._pending_double_blink_start) > self.t["double_blink_window"]:
            self._pending_double_blink_start = None

        # --- Levantar sobrancelha -------------------------------------------
        brow = self._blendshape_score(blendshapes, "browInnerUp")
        if brow > self.t["brow_raise_score"]:
            fired.append("brow_raise")

        # --- Boca aberta ------------------------------------------------------
        jaw = self._blendshape_score(blendshapes, "jawOpen")
        if jaw > self.t["mouth_open_score"]:
            fired.append("mouth_open")

        # --- Direção do olhar (média dos dois olhos) --------------------------
        h_l, v_l = self._gaze_position(landmarks, LEFT_EYE_CORNERS, LEFT_IRIS_CENTER, LEFT_EYE_TOP_BOTTOM)
        h_r, v_r = self._gaze_position(landmarks, RIGHT_EYE_CORNERS, RIGHT_IRIS_CENTER, RIGHT_EYE_TOP_BOTTOM)
        h = (h_l + h_r) / 2
        v = (v_l + v_r) / 2

        direction = None
        if h < self.t["gaze_h_left"]:
            direction = "gaze_left"
        elif h > self.t["gaze_h_right"]:
            direction = "gaze_right"
        elif v < self.t["gaze_v_up"]:
            direction = "gaze_up"
        elif v > self.t["gaze_v_down"]:
            direction = "gaze_down"

        if direction:
            start = self._gaze_dir_since.get(direction)
            if start is None:
                self._gaze_dir_since[direction] = now
            elif (now - start) >= self.t["gaze_hold_time"]:
                fired.append(direction)
            # não reseta aqui: deixamos disparar de novo a cada frame; o
            # cooldown por gesto em actions.py controla a repetição
        else:
            self._gaze_dir_since.clear()

        return fired, {"h": h, "v": v, "blink_l": blink_l, "blink_r": blink_r,
                        "brow": brow, "jaw": jaw}
