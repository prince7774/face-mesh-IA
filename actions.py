"""
actions.py
-----------
Recebe gestos já detectados e executa a ação correspondente (mouse, teclado,
scroll, troca de modo), respeitando o cooldown de cada gesto e o modo atual.
"""

import time
import pyautogui
from config import GESTURE_ACTIONS, COOLDOWN_SECONDS, MODES

pyautogui.FAILSAFE = True  # mover o mouse pro canto superior esquerdo aborta ações (segurança)
pyautogui.PAUSE = 0        # não pausar entre chamadas do pyautogui (o cooldown já controla o ritmo)


class ActionExecutor:
    def __init__(self, on_mode_change=None):
        self.mode_index = 0
        self._last_fired = {}  # gesto -> timestamp do último disparo
        self.on_mode_change = on_mode_change  # callback opcional pra UI/log

    @property
    def mode(self):
        return MODES[self.mode_index]

    def _cooldown_ok(self, gesture):
        now = time.time()
        last = self._last_fired.get(gesture, 0.0)
        cd = COOLDOWN_SECONDS.get(gesture, 0.4)
        if (now - last) >= cd:
            self._last_fired[gesture] = now
            return True
        return False

    def _toggle_mode(self):
        self.mode_index = (self.mode_index + 1) % len(MODES)
        if self.on_mode_change:
            self.on_mode_change(self.mode)

    def _run_action(self, action):
        kind = action["type"]

        if kind == "toggle_mode":
            self._toggle_mode()

        elif kind == "mouse_click":
            pyautogui.click(button=action.get("button", "left"))

        elif kind == "mouse_move_dir":
            pyautogui.moveRel(action.get("dx", 0), action.get("dy", 0), duration=0)

        elif kind == "key_press":
            key = action["key"]
            if "+" in key:
                pyautogui.hotkey(*key.split("+"))
            else:
                pyautogui.press(key)

        elif kind == "scroll":
            pyautogui.scroll(action.get("amount", 0))

    def handle_gestures(self, gestures):
        """gestures: lista de strings vinda do GestureDetector.detect()."""
        mode_actions = GESTURE_ACTIONS.get(self.mode, {})
        for gesture in gestures:
            action = mode_actions.get(gesture)
            if action is None:
                continue
            if not self._cooldown_ok(gesture):
                continue
            self._run_action(action)
