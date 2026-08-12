const MODE_COLORS = {
  mouse: "#4C8DFF",
  navegacao: "#B378FF",
};
const MODE_LETTERS = {
  mouse: "M",
  navegacao: "N",
};
const GESTURE_LABELS = {
  double_blink: "Piscar duplo",
  brow_raise: "Sobrancelha levantada",
  mouth_open: "Boca aberta",
  gaze_left: "Olhar à esquerda",
  gaze_right: "Olhar à direita",
  gaze_up: "Olhar para cima",
  gaze_down: "Olhar para baixo",
};

const videoEl = document.getElementById("video");
const placeholderEl = document.getElementById("video-placeholder");
const modeCircle = document.getElementById("mode-circle");
const modeLetter = document.getElementById("mode-letter");
const modeName = document.getElementById("mode-name");
const pulseRing = document.getElementById("pulse-ring");
const gestureName = document.getElementById("gesture-name");
const gazeDot = document.getElementById("gaze-dot");

let gestureFadeTimeout = null;

window.updateStatus = function (payload) {
  if (payload.frame) {
    videoEl.src = "data:image/jpeg;base64," + payload.frame;
    videoEl.classList.add("has-frame");
    placeholderEl.style.display = "none";
  }

  const color = MODE_COLORS[payload.mode] || "#8792A8";
  modeCircle.style.background = color;
  modeLetter.textContent = MODE_LETTERS[payload.mode] || "?";
  modeName.textContent = payload.mode === "navegacao" ? "navegação" : payload.mode;

  const m = payload.metrics || {};
  setMeter("meter-blink-l", m.blink_l);
  setMeter("meter-blink-r", m.blink_r);
  setMeter("meter-brow", m.brow);
  setMeter("meter-jaw", m.jaw);

  if (typeof m.h === "number" && typeof m.v === "number") {
    gazeDot.style.left = clamp01(m.h) * 100 + "%";
    gazeDot.style.top = clamp01(m.v) * 100 + "%";
  }

  if (payload.gestures && payload.gestures.length > 0) {
    const label = GESTURE_LABELS[payload.gestures[0]] || payload.gestures[0];
    gestureName.textContent = label;
    firePulse();

    clearTimeout(gestureFadeTimeout);
    gestureFadeTimeout = setTimeout(() => {
      gestureName.textContent = "—";
    }, 1500);
  }
};

function setMeter(id, value) {
  const el = document.getElementById(id);
  if (el && typeof value === "number") {
    el.style.width = clamp01(value) * 100 + "%";
  }
}

function clamp01(v) {
  return Math.max(0, Math.min(1, v));
}

function firePulse() {
  pulseRing.classList.remove("pulsing");
  void pulseRing.offsetWidth;
  pulseRing.classList.add("pulsing");
}

async function poll() {
  try {
    const res = await fetch("/api/status");
    const payload = await res.json();

    if (payload.camera_error) {
      document.querySelector(".video-placeholder p").textContent = payload.camera_error;
    } else {
      window.updateStatus(payload);
    }
  } catch (e) {
    // servidor pode ainda não ter iniciado; tenta de novo no próximo ciclo
  }
  setTimeout(poll, 100);
}
poll();

document.getElementById("btn-toggle-mode").addEventListener("click", () => {
  fetch("/api/toggle_mode", { method: "POST" });
});

document.getElementById("btn-quit").addEventListener("click", () => {
  fetch("/api/quit", { method: "POST" });
});