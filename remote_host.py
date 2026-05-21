from __future__ import annotations

import argparse
import getpass
import hashlib
import hmac
import html
import io
import ipaddress
import json
import secrets
import socket
import sys
import threading
import time
import urllib.parse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "host_config.json"
PASSWORD_NOTE_PATH = APP_DIR / "SENHA_GERADA_HOST.txt"
EASY_PASSWORD = "controle"
DISCOVERY_PORT = 8766

DEFAULT_CONFIG: dict[str, Any] = {
    "bind_host": "0.0.0.0",
    "port": 8765,
    "fps": 12,
    "jpeg_quality": 90,
    "scale": 1.0,
    "monitor_index": 1,
    "session_hours": 87600,
    "allow_private_network_only": True,
    "discovery_enabled": True,
}

PIL_Image = None
mss_module = None
pyautogui_module = None


def make_password_hash(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 250_000)
    return salt.hex(), digest.hex()


def verify_password(password: str, config: dict[str, Any]) -> bool:
    salt = str(config.get("password_salt", ""))
    expected = str(config.get("password_hash", ""))
    if not salt or not expected:
        return False
    _, actual = make_password_hash(password, salt)
    return hmac.compare_digest(actual, expected)


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        password = create_or_reset_config(reset=True)
        print()
        print("Senha inicial criada para este Host:")
        print(password)
        print(f"Tambem salvei em: {PASSWORD_NOTE_PATH}")
        print()

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        config = json.load(file)

    merged = dict(DEFAULT_CONFIG)
    merged.update(config)
    try:
        if float(merged.get("session_hours", 0)) < float(DEFAULT_CONFIG["session_hours"]):
            merged["session_hours"] = DEFAULT_CONFIG["session_hours"]
    except (TypeError, ValueError):
        merged["session_hours"] = DEFAULT_CONFIG["session_hours"]
    try:
        if int(merged.get("jpeg_quality", 0)) < int(DEFAULT_CONFIG["jpeg_quality"]):
            merged["jpeg_quality"] = DEFAULT_CONFIG["jpeg_quality"]
    except (TypeError, ValueError):
        merged["jpeg_quality"] = DEFAULT_CONFIG["jpeg_quality"]
    try:
        if float(merged.get("scale", 0)) < float(DEFAULT_CONFIG["scale"]):
            merged["scale"] = DEFAULT_CONFIG["scale"]
    except (TypeError, ValueError):
        merged["scale"] = DEFAULT_CONFIG["scale"]
    return merged


def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def create_or_reset_config(reset: bool = False, password: str | None = None) -> str:
    if CONFIG_PATH.exists() and not reset:
        print(f"Configuracao ja existe: {CONFIG_PATH}")
        print("Use --reset-password para trocar a senha.")
        return ""

    generated_password = password or EASY_PASSWORD
    salt, digest = make_password_hash(generated_password)

    config = dict(DEFAULT_CONFIG)
    config["password_salt"] = salt
    config["password_hash"] = digest
    save_config(config)

    note = (
        "Controle Remoto LAN - Host\n"
        "==========================\n\n"
        f"Senha: {generated_password}\n\n"
        "O app do laptop ja vem preenchido com a senha padrao 'controle'.\n"
        "Para trocar a senha, execute resetar_senha_host.bat no computador controlado.\n"
    )
    PASSWORD_NOTE_PATH.write_text(note, encoding="utf-8")
    return generated_password


def prompt_new_password() -> str:
    while True:
        first = getpass.getpass("Nova senha do Host: ").strip()
        second = getpass.getpass("Repita a nova senha: ").strip()
        if not first:
            print("A senha nao pode ficar vazia.")
            continue
        if first != second:
            print("As senhas nao conferem.")
            continue
        return first


def set_easy_password() -> str:
    return create_or_reset_config(reset=True, password=EASY_PASSWORD)


def apply_high_quality_config() -> None:
    config = load_config()
    config["jpeg_quality"] = DEFAULT_CONFIG["jpeg_quality"]
    config["scale"] = DEFAULT_CONFIG["scale"]
    config["fps"] = DEFAULT_CONFIG["fps"]
    save_config(config)


def load_runtime_dependencies() -> None:
    global PIL_Image, mss_module, pyautogui_module

    try:
        from PIL import Image
        import mss
        import pyautogui
    except ImportError as exc:
        print("Dependencias do Host nao instaladas.")
        print("Rode instalar_host.bat neste computador e tente novamente.")
        print(f"Detalhe: {exc}")
        raise SystemExit(1) from exc

    PIL_Image = Image
    mss_module = mss
    pyautogui_module = pyautogui
    pyautogui.PAUSE = 0
    pyautogui.FAILSAFE = False


def is_private_client(ip_text: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback or ip.is_link_local


def local_ip_addresses() -> list[str]:
    ips: set[str] = set()
    try:
        for item in socket.gethostbyname_ex(socket.gethostname())[2]:
            if item and not item.startswith("127."):
                ips.add(item)
    except OSError:
        pass

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                ips.add(ip)
    except OSError:
        pass

    return sorted(ips)


def start_discovery_beacon(config: dict[str, Any]) -> None:
    if not config.get("discovery_enabled", True):
        return

    port = int(config.get("port", 8765))

    def worker() -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            while True:
                payload = {
                    "app": "ControleRemotoLAN",
                    "hostname": socket.gethostname(),
                    "port": port,
                    "urls": [f"http://{ip}:{port}" for ip in local_ip_addresses()],
                    "easy_password": True,
                }
                try:
                    sock.sendto(json.dumps(payload).encode("utf-8"), ("255.255.255.255", DISCOVERY_PORT))
                except OSError:
                    pass
                time.sleep(2)

    threading.Thread(target=worker, daemon=True).start()


def clamp(value: float, low: int, high: int) -> int:
    return max(low, min(high, int(round(value))))


SPECIAL_CODE_MAP = {
    "Backspace": "backspace",
    "Tab": "tab",
    "Enter": "enter",
    "NumpadEnter": "enter",
    "Escape": "esc",
    "Space": "space",
    "PageUp": "pageup",
    "PageDown": "pagedown",
    "End": "end",
    "Home": "home",
    "ArrowLeft": "left",
    "ArrowUp": "up",
    "ArrowRight": "right",
    "ArrowDown": "down",
    "Insert": "insert",
    "Delete": "delete",
    "ControlLeft": "ctrl",
    "ControlRight": "ctrl",
    "ShiftLeft": "shift",
    "ShiftRight": "shift",
    "AltLeft": "alt",
    "AltRight": "alt",
    "MetaLeft": "win",
    "MetaRight": "win",
    "CapsLock": "capslock",
    "PrintScreen": "printscreen",
    "ScrollLock": "scrolllock",
    "Pause": "pause",
    "NumLock": "numlock",
}

PUNCTUATION_CODE_MAP = {
    "Minus": "-",
    "Equal": "=",
    "BracketLeft": "[",
    "BracketRight": "]",
    "Backslash": "\\",
    "Semicolon": ";",
    "Quote": "'",
    "Backquote": "`",
    "Comma": ",",
    "Period": ".",
    "Slash": "/",
    "NumpadAdd": "+",
    "NumpadSubtract": "-",
    "NumpadMultiply": "*",
    "NumpadDivide": "/",
    "NumpadDecimal": ".",
}

KEY_NAME_MAP = {
    "Return": "enter",
    "Enter": "enter",
    "Escape": "esc",
    "Esc": "esc",
    "BackSpace": "backspace",
    "Backspace": "backspace",
    "Tab": "tab",
    "space": "space",
    "Space": "space",
    "Prior": "pageup",
    "Page_Up": "pageup",
    "Next": "pagedown",
    "Page_Down": "pagedown",
    "Home": "home",
    "End": "end",
    "Insert": "insert",
    "Delete": "delete",
    "Left": "left",
    "Right": "right",
    "Up": "up",
    "Down": "down",
    "Shift_L": "shift",
    "Shift_R": "shift",
    "Control_L": "ctrl",
    "Control_R": "ctrl",
    "Alt_L": "alt",
    "Alt_R": "alt",
    "Win_L": "win",
    "Win_R": "win",
    "Super_L": "win",
    "Super_R": "win",
    "Caps_Lock": "capslock",
}


def normalize_key(payload: dict[str, Any]) -> str | None:
    code = str(payload.get("code") or "")
    key = str(payload.get("key") or "")
    keysym = str(payload.get("keysym") or "")

    if keysym:
        if keysym in KEY_NAME_MAP:
            return KEY_NAME_MAP[keysym]
        if keysym.startswith("F") and keysym[1:].isdigit():
            return keysym.lower()
        if len(keysym) == 1:
            return keysym.lower()

    if code:
        if code in SPECIAL_CODE_MAP:
            return SPECIAL_CODE_MAP[code]
        if code in PUNCTUATION_CODE_MAP:
            return PUNCTUATION_CODE_MAP[code]
        if code.startswith("Key") and len(code) == 4:
            return code[-1].lower()
        if code.startswith("Digit") and len(code) == 6:
            return code[-1]
        if code.startswith("Numpad") and code[6:].isdigit():
            return code[6:]
        if code.startswith("F") and code[1:].isdigit():
            return code.lower()

    if key:
        if key in KEY_NAME_MAP:
            return KEY_NAME_MAP[key]
        if key in ("Control", "Ctrl"):
            return "ctrl"
        if key == "Alt":
            return "alt"
        if key == "Shift":
            return "shift"
        if key in ("Meta", "OS"):
            return "win"
        if len(key) == 1:
            return key.lower()

    return None


CLIENT_HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Controle Remoto LAN</title>
  <style>
    :root { color-scheme: dark; font-family: Arial, sans-serif; }
    * { box-sizing: border-box; }
    html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; background: #050505; }
    #screen { width: 100vw; height: 100vh; object-fit: contain; display: block; user-select: none; -webkit-user-drag: none; cursor: crosshair; }
    #login { position: fixed; inset: 0; display: grid; place-items: center; background: #101114; color: #f5f5f5; }
    #login form { width: min(420px, calc(100vw - 32px)); background: #1b1d23; border: 1px solid #323743; padding: 22px; border-radius: 8px; box-shadow: 0 20px 80px #0008; }
    h1 { margin: 0 0 14px; font-size: 22px; }
    label { display: block; font-size: 13px; margin-bottom: 8px; color: #cdd2dc; }
    input { width: 100%; height: 42px; border-radius: 6px; border: 1px solid #454b58; background: #0f1117; color: #fff; padding: 0 12px; font-size: 16px; }
    button { height: 42px; border: 0; border-radius: 6px; background: #2f7df6; color: #fff; padding: 0 16px; font-weight: 700; cursor: pointer; }
    .row { display: flex; gap: 10px; margin-top: 14px; }
    #message { min-height: 20px; color: #ffb5b5; font-size: 13px; margin-top: 10px; }
    #toolbar { position: fixed; left: 12px; top: 12px; display: none; gap: 8px; align-items: center; padding: 8px; background: #111827dd; border: 1px solid #374151; border-radius: 8px; color: #e5e7eb; opacity: .18; transition: opacity .2s ease; }
    #toolbar:hover { opacity: 1; }
    #toolbar button { height: 34px; background: #374151; }
    #toolbar button.active { background: #2563eb; }
    #toolbar button:disabled { opacity: .35; cursor: default; }
    #toolbar span { font-size: 12px; white-space: nowrap; }
  </style>
</head>
<body>
  <img id="screen" alt="" draggable="false" />
  <div id="toolbar">
    <button class="view-btn" data-view="all" type="button">Duas telas</button>
    <button class="view-btn" data-view="1" type="button">Tela 1</button>
    <button class="view-btn" data-view="2" type="button">Tela 2</button>
    <button id="fullscreen" type="button">Tela cheia</button>
    <button id="disconnect" type="button">Sair</button>
    <span id="status"></span>
  </div>
  <div id="login">
    <form id="loginForm">
      <h1>Controle Remoto LAN</h1>
      <label for="password">Senha do Host</label>
      <input id="password" type="password" autocomplete="current-password" autofocus />
      <div class="row"><button type="submit">Conectar</button></div>
      <div id="message"></div>
    </form>
  </div>
  <script>
    const screen = document.getElementById('screen');
    const login = document.getElementById('login');
    const form = document.getElementById('loginForm');
    const password = document.getElementById('password');
    const message = document.getElementById('message');
    const toolbar = document.getElementById('toolbar');
    const statusEl = document.getElementById('status');
    let token = null;
    let remote = { width: 1, height: 1 };
    let views = [];
    let activeView = '1';
    let lastMove = 0;
    const pressed = new Set();

    function api(path, options = {}) {
      options.headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {});
      if (token) options.headers['X-Remote-Token'] = token;
      return fetch(path, options);
    }

    function displayBox() {
      const rect = screen.getBoundingClientRect();
      const imageRatio = remote.width / remote.height;
      const boxRatio = rect.width / rect.height;
      let width, height, left, top;
      if (boxRatio > imageRatio) {
        height = rect.height;
        width = height * imageRatio;
        left = rect.left + (rect.width - width) / 2;
        top = rect.top;
      } else {
        width = rect.width;
        height = width / imageRatio;
        left = rect.left;
        top = rect.top + (rect.height - height) / 2;
      }
      return { left, top, width, height };
    }

    function pointFromEvent(event) {
      const box = displayBox();
      const px = event.clientX - box.left;
      const py = event.clientY - box.top;
      if (px < 0 || py < 0 || px > box.width || py > box.height) return null;
      return {
        x: Math.round(px * remote.width / box.width),
        y: Math.round(py * remote.height / box.height)
      };
    }

    function sendControl(payload) {
      if (!token) return;
      payload.view = activeView;
      api('/control', { method: 'POST', body: JSON.stringify(payload) }).catch(() => {});
    }

    function viewById(viewId) {
      return views.find((item) => item.id === viewId);
    }

    function updateViewButtons() {
      const ids = new Set(views.map((item) => item.id));
      document.querySelectorAll('.view-btn').forEach((button) => {
        const viewId = button.dataset.view;
        button.disabled = !ids.has(viewId);
        button.classList.toggle('active', viewId === activeView);
      });
    }

    function applyStatus(status) {
      views = Array.isArray(status.views) && status.views.length
        ? status.views
        : [{ id: status.active_view || '1', label: 'Tela 1', width: status.width, height: status.height }];
      activeView = status.active_view || (viewById('all') ? 'all' : views[0].id);
      const view = viewById(activeView) || views[0];
      activeView = view.id;
      remote = { width: view.width, height: view.height };
      statusEl.textContent = `${view.label || activeView} - ${remote.width} x ${remote.height}`;
      updateViewButtons();
    }

    function setView(viewId) {
      const view = viewById(viewId);
      if (!view || viewId === activeView) return;
      activeView = viewId;
      remote = { width: view.width, height: view.height };
      statusEl.textContent = `${view.label || activeView} - ${remote.width} x ${remote.height}`;
      updateViewButtons();
      screen.src = `/stream?token=${encodeURIComponent(token)}&view=${encodeURIComponent(activeView)}&t=${Date.now()}`;
      screen.focus();
    }

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      message.textContent = '';
      try {
        const response = await fetch('/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ password: password.value })
        });
        if (!response.ok) throw new Error('Senha incorreta ou Host indisponivel.');
        const data = await response.json();
        token = data.token;
        applyStatus(data.status);
        screen.src = `/stream?token=${encodeURIComponent(token)}&view=${encodeURIComponent(activeView)}&t=${Date.now()}`;
        login.style.display = 'none';
        toolbar.style.display = 'flex';
        screen.focus();
        document.documentElement.requestFullscreen?.().catch(() => {});
      } catch (error) {
        message.textContent = error.message || String(error);
      }
    });

    screen.addEventListener('pointermove', (event) => {
      const now = performance.now();
      if (now - lastMove < 16) return;
      lastMove = now;
      const point = pointFromEvent(event);
      if (point) sendControl({ type: 'move', x: point.x, y: point.y });
    });

    screen.addEventListener('pointerdown', (event) => {
      const point = pointFromEvent(event);
      if (!point) return;
      screen.setPointerCapture?.(event.pointerId);
      sendControl({ type: 'button', action: 'down', button: event.button, x: point.x, y: point.y });
      event.preventDefault();
    });

    screen.addEventListener('pointerup', (event) => {
      const point = pointFromEvent(event);
      if (!point) return;
      sendControl({ type: 'button', action: 'up', button: event.button, x: point.x, y: point.y });
      event.preventDefault();
    });

    screen.addEventListener('wheel', (event) => {
      const point = pointFromEvent(event);
      if (point) sendControl({ type: 'scroll', delta_y: event.deltaY, x: point.x, y: point.y });
      event.preventDefault();
    }, { passive: false });

    window.addEventListener('keydown', (event) => {
      if (!token) return;
      if (!pressed.has(event.code)) {
        pressed.add(event.code);
        sendControl({ type: 'key', action: 'down', code: event.code, key: event.key });
      }
      event.preventDefault();
    }, true);

    window.addEventListener('keyup', (event) => {
      if (!token) return;
      pressed.delete(event.code);
      sendControl({ type: 'key', action: 'up', code: event.code, key: event.key });
      event.preventDefault();
    }, true);

    window.addEventListener('blur', () => {
      for (const code of pressed) sendControl({ type: 'key', action: 'up', code });
      pressed.clear();
    });

    document.addEventListener('contextmenu', (event) => event.preventDefault());
    document.querySelectorAll('.view-btn').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
    document.getElementById('fullscreen').addEventListener('click', () => document.documentElement.requestFullscreen?.());
    document.getElementById('disconnect').addEventListener('click', () => location.reload());
  </script>
</body>
</html>
"""


class RemoteState:
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.sessions: dict[str, float] = {}
        self.failed_logins: dict[str, list[float]] = {}
        self.lock = threading.Lock()
        self._monitors_cache: tuple[float, list[dict[str, int]]] | None = None

    def create_session(self) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + float(self.config.get("session_hours", 87600)) * 3600
        with self.lock:
            self.sessions[token] = expires_at
        return token

    def valid_session(self, token: str | None) -> bool:
        if not token:
            return False
        now = time.time()
        with self.lock:
            expires_at = self.sessions.get(token)
            if not expires_at:
                return False
            if expires_at < now:
                self.sessions.pop(token, None)
                return False
            self.sessions[token] = now + float(self.config.get("session_hours", 87600)) * 3600
            return True

    def too_many_failures(self, ip: str) -> bool:
        now = time.time()
        with self.lock:
            failures = [item for item in self.failed_logins.get(ip, []) if now - item < 600]
            self.failed_logins[ip] = failures
            return len(failures) >= 20

    def record_failure(self, ip: str) -> None:
        with self.lock:
            self.failed_logins.setdefault(ip, []).append(time.time())

    def clear_failures(self, ip: str) -> None:
        with self.lock:
            self.failed_logins.pop(ip, None)

    def monitors(self) -> list[dict[str, int]]:
        now = time.time()
        with self.lock:
            if self._monitors_cache and now - self._monitors_cache[0] < 2:
                return [dict(item) for item in self._monitors_cache[1]]

        assert mss_module is not None
        with mss_module.mss() as sct:
            monitors = [
                {
                    "left": int(item["left"]),
                    "top": int(item["top"]),
                    "width": int(item["width"]),
                    "height": int(item["height"]),
                }
                for item in sct.monitors
            ]

        with self.lock:
            self._monitors_cache = (now, monitors)
        return [dict(item) for item in monitors]

    def physical_monitor_count(self) -> int:
        return max(0, len(self.monitors()) - 1)

    def normalize_view_id(self, view_value: Any = None) -> str:
        count = self.physical_monitor_count()
        text = str(view_value or "").strip().lower()
        if text in ("all", "0", "duas", "duas-telas", "todas", "todos"):
            return "all" if count >= 2 else "1"
        if text.isdigit():
            index = int(text)
            if 1 <= index <= count:
                return str(index)

        try:
            configured = int(self.config.get("monitor_index", 1))
        except (TypeError, ValueError):
            configured = 1
        if count >= 2:
            return "all"
        if 1 <= configured <= count:
            return str(configured)
        return "1"

    def monitor(self, view_value: Any = None) -> dict[str, Any]:
        monitors = self.monitors()
        view_id = self.normalize_view_id(view_value)
        index = 0 if view_id == "all" else int(view_id)
        if index >= len(monitors):
            index = 1 if len(monitors) > 1 else 0
            view_id = str(index)
        monitor = dict(monitors[index])
        monitor["id"] = view_id
        monitor["index"] = index
        monitor["label"] = "Duas telas" if view_id == "all" else f"Tela {view_id}"
        return monitor

    def available_views(self) -> list[dict[str, Any]]:
        monitors = self.monitors()
        count = max(0, len(monitors) - 1)
        views: list[dict[str, Any]] = []
        if count >= 2:
            all_monitor = dict(monitors[0])
            all_monitor.update({"id": "all", "index": 0, "label": "Duas telas"})
            views.append(all_monitor)
        for index in range(1, count + 1):
            item = dict(monitors[index])
            item.update({"id": str(index), "index": index, "label": f"Tela {index}"})
            views.append(item)
        return views

    def public_status(self, view_value: Any = None) -> dict[str, Any]:
        monitor = self.monitor(view_value)
        return {
            "width": monitor["width"],
            "height": monitor["height"],
            "active_view": monitor["id"],
            "views": self.available_views(),
            "fps": int(self.config.get("fps", 12)),
            "quality": int(self.config.get("jpeg_quality", DEFAULT_CONFIG["jpeg_quality"])),
            "scale": float(self.config.get("scale", DEFAULT_CONFIG["scale"])),
            "hostname": socket.gethostname(),
        }

    def screen_point(self, x_value: Any, y_value: Any, view_value: Any = None) -> tuple[int, int]:
        monitor = self.monitor(view_value)
        x = clamp(float(x_value), 0, monitor["width"] - 1)
        y = clamp(float(y_value), 0, monitor["height"] - 1)
        return monitor["left"] + x, monitor["top"] + y


class RemoteRequestHandler(BaseHTTPRequestHandler):
    server_version = "ControleRemotoLAN/1.0"
    state: RemoteState

    def log_message(self, format_string: str, *args: Any) -> None:
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {self.client_address[0]} - {format_string % args}")

    def client_allowed(self) -> bool:
        if not self.state.config.get("allow_private_network_only", True):
            return True
        return is_private_client(self.client_address[0])

    def token_from_request(self) -> str | None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        if "token" in query and query["token"]:
            return query["token"][0]
        return self.headers.get("X-Remote-Token")

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status: int, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        if length <= 0 or length > 1024 * 1024:
            return None
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def require_session(self) -> bool:
        if self.state.valid_session(self.token_from_request()):
            return True
        self.send_json(HTTPStatus.UNAUTHORIZED, {"error": "sessao invalida"})
        return False

    def do_GET(self) -> None:
        if not self.client_allowed():
            self.send_json(HTTPStatus.FORBIDDEN, {"error": "somente rede local"})
            return

        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_text(HTTPStatus.OK, CLIENT_HTML, "text/html; charset=utf-8")
            return
        if parsed.path == "/health":
            self.send_json(HTTPStatus.OK, {"ok": True, "app": "Controle Remoto LAN"})
            return
        if parsed.path == "/status":
            if not self.require_session():
                return
            query = urllib.parse.parse_qs(parsed.query)
            view = (query.get("view") or query.get("monitor") or [None])[0]
            self.send_json(HTTPStatus.OK, self.state.public_status(view))
            return
        if parsed.path == "/stream":
            if not self.require_session():
                return
            self.handle_stream()
            return

        self.send_json(HTTPStatus.NOT_FOUND, {"error": "nao encontrado"})

    def do_POST(self) -> None:
        if not self.client_allowed():
            self.send_json(HTTPStatus.FORBIDDEN, {"error": "somente rede local"})
            return

        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/login":
            self.handle_login()
            return
        if parsed.path == "/control":
            if not self.require_session():
                return
            self.handle_control()
            return

        self.send_json(HTTPStatus.NOT_FOUND, {"error": "nao encontrado"})

    def handle_login(self) -> None:
        ip = self.client_address[0]
        if self.state.too_many_failures(ip):
            self.send_json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "muitas tentativas"})
            return

        payload = self.read_json()
        if not payload or not verify_password(str(payload.get("password", "")), self.state.config):
            self.state.record_failure(ip)
            self.send_json(HTTPStatus.FORBIDDEN, {"error": "senha incorreta"})
            return

        self.state.clear_failures(ip)
        token = self.state.create_session()
        self.send_json(HTTPStatus.OK, {"token": token, "status": self.state.public_status()})

    def handle_control(self) -> None:
        payload = self.read_json()
        if not payload:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "json invalido"})
            return

        try:
            apply_control_event(self.state, payload)
        except Exception as exc:  # Keep the Host alive if one input event fails.
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return

        self.send_json(HTTPStatus.OK, {"ok": True})

    def handle_stream(self) -> None:
        assert PIL_Image is not None
        assert mss_module is not None

        fps = max(1, min(30, int(self.state.config.get("fps", 12))))
        quality = max(25, min(95, int(self.state.config.get("jpeg_quality", DEFAULT_CONFIG["jpeg_quality"]))))
        scale = max(0.2, min(1.0, float(self.state.config.get("scale", DEFAULT_CONFIG["scale"]))))
        delay = 1.0 / fps
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        view = (query.get("view") or query.get("monitor") or [None])[0]
        monitor = self.state.monitor(view)
        capture_region = {
            "left": monitor["left"],
            "top": monitor["top"],
            "width": monitor["width"],
            "height": monitor["height"],
        }

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()

        try:
            with mss_module.mss() as sct:
                while True:
                    started = time.perf_counter()
                    screenshot = sct.grab(capture_region)
                    image = PIL_Image.frombytes("RGB", screenshot.size, screenshot.rgb)
                    if scale < 0.999:
                        width = max(1, int(image.width * scale))
                        height = max(1, int(image.height * scale))
                        image = image.resize((width, height), resample=PIL_Image.Resampling.BILINEAR)

                    output = io.BytesIO()
                    image.save(output, format="JPEG", quality=quality, optimize=False, subsampling=0)
                    frame = output.getvalue()
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
                    self.wfile.flush()

                    elapsed = time.perf_counter() - started
                    if elapsed < delay:
                        time.sleep(delay - elapsed)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return


def apply_control_event(state: RemoteState, payload: dict[str, Any]) -> None:
    assert pyautogui_module is not None
    event_type = str(payload.get("type") or "")
    view = payload.get("view", payload.get("monitor"))

    if event_type == "move":
        x, y = state.screen_point(payload.get("x", 0), payload.get("y", 0), view)
        pyautogui_module.moveTo(x, y, duration=0)
        return

    if event_type == "button":
        x, y = state.screen_point(payload.get("x", 0), payload.get("y", 0), view)
        button = normalize_button(payload.get("button", "left"))
        action = str(payload.get("action") or "")
        if action == "down":
            pyautogui_module.mouseDown(x=x, y=y, button=button)
        elif action == "up":
            pyautogui_module.mouseUp(x=x, y=y, button=button)
        else:
            raise ValueError("acao de mouse invalida")
        return

    if event_type == "scroll":
        x, y = state.screen_point(payload.get("x", 0), payload.get("y", 0), view)
        delta_y = float(payload.get("delta_y", payload.get("deltaY", 0)))
        if delta_y == 0:
            return
        clicks = int(round(-delta_y / 120))
        if clicks == 0:
            clicks = -1 if delta_y > 0 else 1
        pyautogui_module.scroll(clicks, x=x, y=y)
        return

    if event_type == "key":
        key = normalize_key(payload)
        if not key:
            return
        action = str(payload.get("action") or "")
        if action == "down":
            pyautogui_module.keyDown(key)
        elif action == "up":
            pyautogui_module.keyUp(key)
        else:
            raise ValueError("acao de teclado invalida")
        return

    raise ValueError("tipo de evento invalido")


def normalize_button(button: Any) -> str:
    if button in (0, "0", "left", "esquerdo"):
        return "left"
    if button in (1, "1", "middle", "meio"):
        return "middle"
    if button in (2, "2", "right", "direito"):
        return "right"
    return "left"


def serve() -> None:
    config = load_config()
    load_runtime_dependencies()
    start_discovery_beacon(config)

    state = RemoteState(config)
    RemoteRequestHandler.state = state
    bind_host = str(config.get("bind_host", "0.0.0.0"))
    port = int(config.get("port", 8765))

    server = ThreadingHTTPServer((bind_host, port), RemoteRequestHandler)
    urls = [f"http://{ip}:{port}" for ip in local_ip_addresses()]
    safe_urls = "\n".join(f"  {html.escape(url)}" for url in urls) or "  Nao consegui detectar o IP local."

    print("Controle Remoto LAN - Host")
    print("===========================")
    print(f"Computador: {socket.gethostname()}")
    print("Enderecos para usar no laptop:")
    print(safe_urls)
    print(f"Senha padrao: {EASY_PASSWORD}")
    print("O laptop tenta encontrar este Host automaticamente na rede.")
    print()
    print("Deixe esta janela aberta enquanto estiver controlando.")
    print("Se o Windows Firewall perguntar, permita acesso em redes privadas.")
    print("Pressione Ctrl+C nesta janela para parar o Host.")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nHost encerrado.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Host do Controle Remoto LAN")
    parser.add_argument("--init", action="store_true", help="cria a configuracao inicial se ela nao existir")
    parser.add_argument("--easy-access", action="store_true", help="define a senha padrao facil")
    parser.add_argument("--high-quality", action="store_true", help="aplica imagem em qualidade alta")
    parser.add_argument("--reset-password", action="store_true", help="troca a senha do Host")
    args = parser.parse_args()

    if args.high_quality:
        apply_high_quality_config()
        print("Qualidade alta aplicada: escala 100%, JPEG 90.")
        return

    if args.easy_access:
        password = set_easy_password()
        print("Acesso facil ativado.")
        print(f"Senha padrao: {password}")
        return

    if args.init:
        password = create_or_reset_config(reset=False)
        if password:
            print("Configuracao inicial criada.")
            print(f"Senha: {password}")
            print(f"Arquivo com a senha: {PASSWORD_NOTE_PATH}")
        return

    if args.reset_password:
        password = prompt_new_password()
        create_or_reset_config(reset=True, password=password)
        print("Senha atualizada.")
        return

    serve()


if __name__ == "__main__":
    main()
