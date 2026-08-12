"""
status_bus.py
---------------
Canal simples de comunicação entre main.py/app.py (que sabem o estado
real do sistema) e overlay.py (a bolinha flutuante, que só precisa
exibir esse estado). Usa um arquivo JSON como "caixa de correio".
"""

import json
import os
import time

STATUS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status.json")

_last_gesture = None
_last_gesture_time = 0.0


def write_status(mode, gestures_fired):
    global _last_gesture, _last_gesture_time

    if gestures_fired:
        _last_gesture = gestures_fired[0]
        _last_gesture_time = time.time()

    data = {
        "mode": mode,
        "last_gesture": _last_gesture,
        "gesture_time": _last_gesture_time,
        "updated": time.time(),
    }

    tmp_path = STATUS_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp_path, STATUS_PATH)
    except OSError:
        pass


def read_status():
    try:
        with open(STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None