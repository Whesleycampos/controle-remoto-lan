from __future__ import annotations

import base64
import io
import json
import queue
import socket
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except ImportError as exc:
    raise SystemExit("Tkinter nao esta disponivel nesta instalacao do Python.") from exc

try:
    import pyperclip
    import requests
    from PIL import Image, ImageTk
except ImportError as exc:
    raise SystemExit("Dependencias do laptop ausentes. Rode instalar_laptop.bat.") from exc


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "laptop_config.json"
TRANSFER_DIR = Path.home() / "Downloads" / "ControleRemotoLAN"
DEFAULT_PORT = 8765
DEFAULT_PASSWORD = "controle"
DISCOVERY_PORT = 8766
CONTROL_PORT = 8767


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def normalize_host_and_port(host_text: str, port_text: str) -> tuple[str, int]:
    host_text = host_text.strip()
    port = int(port_text.strip() or DEFAULT_PORT)

    if "://" in host_text:
        parsed = urllib.parse.urlparse(host_text)
        if parsed.hostname:
            host_text = parsed.hostname
        if parsed.port:
            port = parsed.port
    elif host_text.count(":") == 1:
        host_part, port_part = host_text.rsplit(":", 1)
        if host_part and port_part.isdigit():
            host_text = host_part
            port = int(port_part)

    return host_text.strip("/"), port


class LoginApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Controle Remoto LAN - Laptop")
        self.root.geometry("460x300")
        self.root.minsize(420, 280)
        self.session = requests.Session()
        self.connecting = False
        self.connected = False
        self.auto_connect_after_discovery = True

        config = load_config()
        self.host_var = tk.StringVar(value=str(config.get("host", "")))
        self.port_var = tk.StringVar(value=str(config.get("port", DEFAULT_PORT)))
        self.password_var = tk.StringVar(value=str(config.get("password", DEFAULT_PASSWORD)))
        self.save_password_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Procurando Host na rede...")

        self.build_login()
        threading.Thread(target=self.discovery_worker, daemon=True).start()

    def build_login(self) -> None:
        frame = tk.Frame(self.root, padx=22, pady=20)
        frame.pack(fill="both", expand=True)

        title = tk.Label(frame, text="Controle Remoto LAN", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", pady=(0, 16))

        tk.Label(frame, text="IP do computador Host (automatico quando encontrado)").pack(anchor="w")
        tk.Entry(frame, textvariable=self.host_var).pack(fill="x", pady=(2, 10))

        tk.Label(frame, text="Porta").pack(anchor="w")
        tk.Entry(frame, textvariable=self.port_var).pack(fill="x", pady=(2, 10))

        tk.Label(frame, text="Senha do Host (padrao: controle)").pack(anchor="w")
        password_entry = tk.Entry(frame, textvariable=self.password_var, show="*")
        password_entry.pack(fill="x", pady=(2, 8))

        tk.Checkbutton(frame, text="Salvar senha neste laptop", variable=self.save_password_var).pack(anchor="w")

        row = tk.Frame(frame)
        row.pack(fill="x", pady=(14, 0))
        tk.Button(row, text="Conectar", command=self.connect).pack(side="left")
        tk.Button(row, text="Procurar Host", command=self.enable_discovery).pack(side="left", padx=(8, 0))
        tk.Label(row, textvariable=self.status_var, fg="#a33").pack(side="left", padx=(12, 0))

        password_entry.bind("<Return>", lambda _event: self.connect())

    def enable_discovery(self) -> None:
        self.auto_connect_after_discovery = True
        self.status_var.set("Procurando Host na rede...")

    def discovery_worker(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(2)
            try:
                sock.bind(("", DISCOVERY_PORT))
            except OSError as exc:
                self.root.after(0, lambda: self.status_var.set(f"Busca automatica indisponivel: {exc}"))
                return

            while not self.connected:
                try:
                    data, address = sock.recvfrom(4096)
                except socket.timeout:
                    continue
                except OSError:
                    return

                try:
                    payload = json.loads(data.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if payload.get("app") != "ControleRemotoLAN":
                    continue

                host = address[0]
                port = int(payload.get("port") or DEFAULT_PORT)
                hostname = str(payload.get("hostname") or host)

                def apply_discovery() -> None:
                    if self.connected:
                        return
                    self.host_var.set(host)
                    self.port_var.set(str(port))
                    self.status_var.set(f"Host encontrado: {hostname}. Conectando...")
                    if self.auto_connect_after_discovery and not self.connecting:
                        self.connect()

                self.root.after(0, apply_discovery)

    def connect(self) -> None:
        if self.connecting or self.connected:
            return
        password = self.password_var.get()
        try:
            host, port = normalize_host_and_port(self.host_var.get(), self.port_var.get())
        except ValueError:
            self.status_var.set("Porta invalida")
            return
        if not host:
            self.status_var.set("Informe o IP do Host")
            return
        if not password:
            self.status_var.set("Informe a senha")
            return

        self.status_var.set("Conectando...")
        self.connecting = True
        threading.Thread(target=self.connect_worker, args=(host, port, password), daemon=True).start()

    def connect_worker(self, host: str, port: int, password: str) -> None:
        base_url = f"http://{host}:{port}"
        try:
            response = self.session.post(f"{base_url}/login", json={"password": password}, timeout=8)
            if response.status_code == 403:
                raise RuntimeError("Senha incorreta")
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            def failed(error: Exception = exc) -> None:
                self.connecting = False
                self.status_var.set(str(error))

            self.root.after(0, failed)
            return

        config = {"host": host, "port": port}
        if self.save_password_var.get():
            config["password"] = password
        save_config(config)

        self.root.after(0, lambda: self.open_remote(base_url, data["token"], data["status"], password))

    def open_remote(self, base_url: str, token: str, status: dict[str, Any], password: str) -> None:
        self.connected = True
        self.connecting = False
        for child in self.root.winfo_children():
            child.destroy()
        RemoteWindow(self.root, self.session, base_url, token, status, password)

    def run(self) -> None:
        self.root.mainloop()


class RemoteWindow:
    def __init__(
        self,
        root: tk.Tk,
        session: requests.Session,
        base_url: str,
        token: str,
        status: dict[str, Any],
        password: str,
    ) -> None:
        self.root = root
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.password = password
        self.views = self.parse_views(status)
        self.current_view = self.choose_initial_view(status)
        self.remote_width = 1
        self.remote_height = 1
        self.apply_view_dimensions(self.current_view)
        self.stop_event = threading.Event()
        self.frame_queue: queue.Queue[Image.Image] = queue.Queue(maxsize=1)
        self.control_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=500)
        self.token_lock = threading.Lock()
        self.login_lock = threading.Lock()
        self.view_lock = threading.Lock()
        self.stream_generation = 0
        self.control_fast_connected = False
        self.latest_image: Image.Image | None = None
        self.tk_image: ImageTk.PhotoImage | None = None
        self.image_item: int | None = None
        self.overlay_item: int | None = None
        self.view_bar: tk.Frame | None = None
        self.view_buttons: dict[str, tk.Button] = {}
        self.transfer_bar: tk.Frame | None = None
        self.exit_button: tk.Button | None = None
        self.clipboard_enabled = True
        self.last_host_clipboard = ""
        self.last_local_clipboard = self.local_clipboard_text()
        self.display_box = (0, 0, 1, 1)
        self.last_move_sent = 0.0
        self.pressed_keys: set[str] = set()

        self.root.title("Controle Remoto LAN - conectado")
        self.root.configure(background="black")
        self.root.attributes("-fullscreen", True)
        self.root.focus_force()

        self.canvas = tk.Canvas(self.root, background="black", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.focus_set()

        self.create_view_buttons()
        self.create_transfer_buttons()

        self.exit_button = tk.Button(
            self.root,
            text="Sair",
            command=self.close,
            bg="#1f2937",
            fg="#f9fafb",
            activebackground="#374151",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
        )
        self.exit_button.place(relx=1.0, x=-14, y=14, anchor="ne")

        self.bind_events()
        self.show_overlay(f"Conectado a {self.base_url}   |   clique em Sair para encerrar")

        threading.Thread(target=self.stream_worker, daemon=True).start()
        threading.Thread(target=self.control_worker, daemon=True).start()
        threading.Thread(target=self.clipboard_worker, daemon=True).start()
        self.root.after(15, self.draw_loop)
        self.root.after(5000, self.hide_overlay)

    def bind_events(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Configure>", lambda _event: self.render_latest())

        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<ButtonPress-1>", lambda event: self.on_button(event, "down", "left"))
        self.canvas.bind("<ButtonRelease-1>", lambda event: self.on_button(event, "up", "left"))
        self.canvas.bind("<ButtonPress-2>", lambda event: self.on_button(event, "down", "middle"))
        self.canvas.bind("<ButtonRelease-2>", lambda event: self.on_button(event, "up", "middle"))
        self.canvas.bind("<ButtonPress-3>", lambda event: self.on_button(event, "down", "right"))
        self.canvas.bind("<ButtonRelease-3>", lambda event: self.on_button(event, "up", "right"))
        self.canvas.bind("<MouseWheel>", self.on_wheel)
        self.canvas.bind("<KeyPress>", self.on_key_down)
        self.canvas.bind("<KeyRelease>", self.on_key_up)
        self.canvas.bind("<FocusOut>", self.on_focus_out)

    def parse_views(self, status: dict[str, Any]) -> list[dict[str, Any]]:
        views = status.get("views")
        if isinstance(views, list) and views:
            parsed: list[dict[str, Any]] = []
            for item in views:
                if not isinstance(item, dict):
                    continue
                view_id = str(item.get("id", "")).strip()
                if not view_id:
                    continue
                try:
                    width = int(item.get("width", 1))
                    height = int(item.get("height", 1))
                except (TypeError, ValueError):
                    continue
                parsed.append(
                    {
                        "id": view_id,
                        "label": str(item.get("label") or ("Duas telas" if view_id == "all" else f"Tela {view_id}")),
                        "width": max(1, width),
                        "height": max(1, height),
                    }
                )
            if parsed:
                return parsed

        return [
            {
                "id": str(status.get("active_view") or "1"),
                "label": "Tela 1",
                "width": max(1, int(status.get("width", 1))),
                "height": max(1, int(status.get("height", 1))),
            }
        ]

    def choose_initial_view(self, status: dict[str, Any]) -> str:
        active = str(status.get("active_view") or "").strip()
        view_ids = {item["id"] for item in self.views}
        if active in view_ids:
            return active
        if "all" in view_ids:
            return "all"
        return self.views[0]["id"]

    def view_info(self, view_id: str) -> dict[str, Any]:
        for item in self.views:
            if item["id"] == view_id:
                return item
        return self.views[0]

    def apply_view_dimensions(self, view_id: str) -> None:
        view = self.view_info(view_id)
        self.remote_width = int(view["width"])
        self.remote_height = int(view["height"])

    def view_snapshot(self) -> tuple[str, int]:
        with self.view_lock:
            return self.current_view, self.stream_generation

    def active_view_id(self) -> str:
        with self.view_lock:
            return self.current_view

    def stream_changed(self, generation: int) -> bool:
        with self.view_lock:
            return self.stream_generation != generation

    def set_view(self, view_id: str) -> None:
        if view_id not in {item["id"] for item in self.views}:
            return
        with self.view_lock:
            if self.current_view == view_id:
                return
            self.current_view = view_id
            self.stream_generation += 1
        self.apply_view_dimensions(view_id)
        self.latest_image = None
        if self.image_item is not None:
            self.canvas.delete(self.image_item)
            self.image_item = None
        self.update_view_buttons()
        self.show_overlay(f"Visualizando {self.view_info(view_id)['label']}")
        self.canvas.focus_set()

    def create_view_buttons(self) -> None:
        self.view_bar = tk.Frame(self.root, bg="#111827")
        self.view_bar.place(x=14, y=14, anchor="nw")
        for view in self.views:
            view_id = view["id"]
            if view_id != "all" and view_id not in ("1", "2"):
                continue
            button = tk.Button(
                self.view_bar,
                text=str(view["label"]),
                command=lambda item=view_id: self.set_view(item),
                relief="flat",
                padx=12,
                pady=6,
                cursor="hand2",
            )
            button.pack(side="left", padx=(0, 6))
            self.view_buttons[view_id] = button
        self.update_view_buttons()

    def update_view_buttons(self) -> None:
        active = self.active_view_id()
        for view_id, button in self.view_buttons.items():
            if view_id == active:
                button.configure(bg="#2563eb", fg="#ffffff", activebackground="#1d4ed8", activeforeground="#ffffff")
            else:
                button.configure(bg="#374151", fg="#f9fafb", activebackground="#4b5563", activeforeground="#ffffff")

    def create_transfer_buttons(self) -> None:
        self.transfer_bar = tk.Frame(self.root, bg="#111827")
        self.transfer_bar.place(x=14, y=54, anchor="nw")
        tk.Button(
            self.transfer_bar,
            text="Enviar arquivo",
            command=self.choose_files_to_upload,
            bg="#374151",
            fg="#f9fafb",
            activebackground="#4b5563",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=(0, 6))
        tk.Button(
            self.transfer_bar,
            text="Baixar copiados",
            command=self.download_copied_files,
            bg="#374151",
            fg="#f9fafb",
            activebackground="#4b5563",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=6,
            cursor="hand2",
        ).pack(side="left", padx=(0, 6))

    def local_clipboard_text(self) -> str:
        try:
            value = pyperclip.paste()
        except Exception:
            return ""
        return value if isinstance(value, str) else ""

    def set_local_clipboard_text(self, text: str) -> None:
        try:
            pyperclip.copy(text)
        except Exception:
            pass

    def clipboard_worker(self) -> None:
        while not self.stop_event.is_set():
            if not self.clipboard_enabled:
                self.stop_event.wait(1)
                continue

            try:
                response = self.session.get(
                    f"{self.base_url}/clipboard",
                    headers=self.auth_headers(),
                    timeout=3,
                )
                if response.status_code in (401, 403):
                    self.relogin()
                elif response.ok:
                    host_text = str(response.json().get("text", ""))
                    if host_text and host_text != self.last_host_clipboard and host_text != self.local_clipboard_text():
                        self.set_local_clipboard_text(host_text)
                        self.last_host_clipboard = host_text
                        self.last_local_clipboard = host_text
                        self.schedule_ui(lambda: self.show_overlay("Texto copiado do Host para o laptop"))
                        self.schedule_ui_later(1600, self.hide_overlay)
            except Exception:
                pass

            local_text = self.local_clipboard_text()
            if local_text and local_text != self.last_local_clipboard and local_text != self.last_host_clipboard:
                try:
                    response = self.session.post(
                        f"{self.base_url}/clipboard",
                        headers=self.auth_headers(),
                        json={"text": local_text},
                        timeout=3,
                    )
                    if response.status_code in (401, 403):
                        self.relogin()
                    elif response.ok:
                        self.last_local_clipboard = local_text
                        self.last_host_clipboard = local_text
                except Exception:
                    pass

            self.stop_event.wait(1)

    def choose_files_to_upload(self) -> None:
        paths = filedialog.askopenfilenames(title="Enviar arquivo para o computador remoto")
        if not paths:
            self.canvas.focus_set()
            return
        self.canvas.focus_set()
        threading.Thread(target=self.upload_files_worker, args=(list(paths),), daemon=True).start()

    def upload_files_worker(self, paths: list[str]) -> None:
        for index, path_text in enumerate(paths, start=1):
            path = Path(path_text)
            if not path.is_file():
                continue
            self.schedule_ui(lambda name=path.name, index=index, total=len(paths): self.show_overlay(f"Enviando {index}/{total}: {name}"))
            try:
                start = self.session.post(
                    f"{self.base_url}/files/upload-start",
                    headers=self.auth_headers(),
                    json={"name": path.name, "size": path.stat().st_size},
                    timeout=10,
                )
                if start.status_code in (401, 403):
                    self.relogin()
                    start = self.session.post(
                        f"{self.base_url}/files/upload-start",
                        headers=self.auth_headers(),
                        json={"name": path.name, "size": path.stat().st_size},
                        timeout=10,
                    )
                start.raise_for_status()
                upload_id = start.json()["upload_id"]
                with path.open("rb") as file:
                    while not self.stop_event.is_set():
                        chunk = file.read(768 * 1024)
                        if not chunk:
                            break
                        payload = {
                            "upload_id": upload_id,
                            "data": base64.b64encode(chunk).decode("ascii"),
                        }
                        response = self.session.post(
                            f"{self.base_url}/files/upload-chunk",
                            headers=self.auth_headers(),
                            json=payload,
                            timeout=20,
                        )
                        response.raise_for_status()
                finish = self.session.post(
                    f"{self.base_url}/files/upload-finish",
                    headers=self.auth_headers(),
                    json={"upload_id": upload_id},
                    timeout=10,
                )
                finish.raise_for_status()
            except Exception as exc:
                self.schedule_ui(lambda exc=exc: self.show_overlay(f"Falha ao enviar arquivo: {exc}"))
                self.schedule_ui_later(3500, self.hide_overlay)
                return
        self.schedule_ui(lambda: self.show_overlay("Arquivo(s) enviados para Downloads\\ControleRemotoLAN no Host"))
        self.schedule_ui_later(3500, self.hide_overlay)

    def download_copied_files(self) -> None:
        self.canvas.focus_set()
        threading.Thread(target=self.download_copied_files_worker, daemon=True).start()

    def download_copied_files_worker(self) -> None:
        self.schedule_ui(lambda: self.show_overlay("Baixando arquivos copiados no Host..."))
        try:
            response = self.session.get(
                f"{self.base_url}/files/download-copied",
                headers=self.auth_headers(),
                stream=True,
                timeout=(10, 120),
            )
            if response.status_code in (401, 403):
                self.relogin()
                response = self.session.get(
                    f"{self.base_url}/files/download-copied",
                    headers=self.auth_headers(),
                    stream=True,
                    timeout=(10, 120),
                )
            response.raise_for_status()
            TRANSFER_DIR.mkdir(parents=True, exist_ok=True)
            name = self.filename_from_response(response) or f"arquivos-copiados-{time.strftime('%Y%m%d-%H%M%S')}.zip"
            path = TRANSFER_DIR / name
            with path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        file.write(chunk)
        except Exception as exc:
            self.schedule_ui(lambda exc=exc: self.show_overlay(f"Nao consegui baixar copiados: {exc}"))
            self.schedule_ui_later(4000, self.hide_overlay)
            return
        self.set_local_clipboard_text(str(path))
        self.schedule_ui(lambda: self.show_overlay(f"Baixado no laptop: {path.name}"))
        self.schedule_ui_later(4000, self.hide_overlay)

    def filename_from_response(self, response: requests.Response) -> str | None:
        disposition = response.headers.get("Content-Disposition", "")
        marker = "filename="
        if marker not in disposition:
            return None
        name = disposition.split(marker, 1)[1].strip().strip('"')
        return Path(name).name or None

    def show_overlay(self, text: str) -> None:
        self.hide_overlay()
        self.overlay_item = self.canvas.create_text(
            18,
            18,
            text=text,
            anchor="nw",
            fill="#e5e7eb",
            font=("Segoe UI", 12, "bold"),
        )

    def hide_overlay(self) -> None:
        if self.overlay_item is not None:
            self.canvas.delete(self.overlay_item)
            self.overlay_item = None

    def schedule_ui(self, callback: Any) -> None:
        if self.stop_event.is_set():
            return
        try:
            self.root.after(0, callback)
        except tk.TclError:
            pass

    def schedule_ui_later(self, milliseconds: int, callback: Any) -> None:
        if self.stop_event.is_set():
            return
        try:
            self.root.after(milliseconds, callback)
        except tk.TclError:
            pass

    def current_token(self) -> str:
        with self.token_lock:
            return self.token

    def auth_headers(self) -> dict[str, str]:
        return {"X-Remote-Token": self.current_token()}

    def control_socket_address(self) -> tuple[str, int]:
        parsed = urllib.parse.urlparse(self.base_url)
        host = parsed.hostname or self.base_url.replace("http://", "").split(":", 1)[0]
        return host, CONTROL_PORT

    def relogin(self) -> bool:
        with self.login_lock:
            if self.stop_event.is_set():
                return False
            try:
                response = self.session.post(
                    f"{self.base_url}/login",
                    json={"password": self.password},
                    timeout=8,
                )
                response.raise_for_status()
                data = response.json()
            except Exception as exc:
                self.schedule_ui(lambda: self.show_overlay(f"Reconectando automaticamente... {exc}"))
                return False

            with self.token_lock:
                self.token = data["token"]
            self.apply_view_dimensions(self.active_view_id())
            self.schedule_ui(lambda: self.show_overlay(f"Reconectado a {self.base_url}"))
            self.schedule_ui_later(2500, self.hide_overlay)
            return True

    def stream_worker(self) -> None:
        retry_seconds = 1.0
        while not self.stop_event.is_set():
            view_id, generation = self.view_snapshot()
            url = (
                f"{self.base_url}/stream?"
                f"token={urllib.parse.quote(self.current_token())}&"
                f"view={urllib.parse.quote(view_id)}"
            )
            try:
                with self.session.get(url, stream=True, timeout=(8, 20)) as response:
                    if response.status_code in (401, 403):
                        if not self.relogin():
                            self.stop_event.wait(retry_seconds)
                            retry_seconds = min(30.0, retry_seconds * 1.5)
                        continue
                    response.raise_for_status()
                    retry_seconds = 1.0
                    self.schedule_ui(
                        lambda view_id=view_id: self.show_overlay(
                            f"Conectado a {self.base_url} - {self.view_info(view_id)['label']}"
                        )
                    )
                    self.schedule_ui_later(2500, self.hide_overlay)
                    buffer = bytearray()
                    view_changed = False
                    for chunk in response.iter_content(chunk_size=8192):
                        if self.stop_event.is_set():
                            return
                        if self.stream_changed(generation):
                            view_changed = True
                            break
                        if not chunk:
                            continue
                        buffer.extend(chunk)
                        while True:
                            start = buffer.find(b"\xff\xd8")
                            end = buffer.find(b"\xff\xd9", start + 2)
                            if start < 0 or end < 0:
                                if len(buffer) > 2_000_000:
                                    del buffer[:-100_000]
                                break
                            jpg = bytes(buffer[start : end + 2])
                            del buffer[: end + 2]
                            try:
                                image = Image.open(io.BytesIO(jpg)).convert("RGB")
                                image.load()
                            except Exception:
                                continue
                            self.put_latest_frame(image)
                    if view_changed:
                        continue
            except Exception as exc:
                if not self.stop_event.is_set():
                    self.schedule_ui(lambda exc=exc: self.show_overlay(f"Reconectando automaticamente... {exc}"))

            if not self.stop_event.is_set():
                self.stop_event.wait(retry_seconds)
                retry_seconds = min(30.0, retry_seconds * 1.5)

    def put_latest_frame(self, image: Image.Image) -> None:
        try:
            self.frame_queue.put_nowait(image)
        except queue.Full:
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.frame_queue.put_nowait(image)
            except queue.Full:
                pass

    def control_worker(self) -> None:
        while not self.stop_event.is_set():
            if self.fast_control_loop():
                continue
            self.http_control_loop()

    def fast_control_loop(self) -> bool:
        host, port = self.control_socket_address()
        try:
            with socket.create_connection((host, port), timeout=4) as sock:
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                sock.settimeout(5)
                file = sock.makefile("rwb", buffering=0)
                hello = json.dumps({"token": self.current_token()}, separators=(",", ":")).encode("utf-8") + b"\n"
                file.write(hello)
                response = file.readline(4096)
                if not response:
                    return False
                try:
                    data = json.loads(response.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return False
                if not data.get("ok"):
                    if self.relogin():
                        return True
                    return False
                self.control_fast_connected = True
                self.schedule_ui(lambda: self.show_overlay("Mouse sincronizado em modo rapido"))
                self.schedule_ui_later(1600, self.hide_overlay)
                while not self.stop_event.is_set():
                    try:
                        payload = self.control_queue.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    if payload.get("type") == "move":
                        payload = self.latest_move_payload(payload)
                    line = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
                    file.write(line)
                return True
        except Exception:
            if self.control_fast_connected:
                self.control_fast_connected = False
                self.schedule_ui(lambda: self.show_overlay("Canal rapido caiu; usando fallback"))
                self.schedule_ui_later(2200, self.hide_overlay)
            return False

    def http_control_loop(self) -> None:
        url = f"{self.base_url}/control"
        fallback_until = time.time() + 3.0
        while not self.stop_event.is_set() and time.time() < fallback_until:
            try:
                payload = self.control_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if payload.get("type") == "move":
                payload = self.latest_move_payload(payload)
            for attempt in range(3):
                if self.stop_event.is_set():
                    return
                try:
                    response = self.session.post(url, json=payload, headers=self.auth_headers(), timeout=3)
                    if response.status_code in (401, 403):
                        self.relogin()
                        continue
                    break
                except Exception:
                    if attempt == 0:
                        self.relogin()
                    self.stop_event.wait(0.3)

    def latest_move_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        latest = payload
        with self.control_queue.mutex:
            while self.control_queue.queue and self.control_queue.queue[0].get("type") == "move":
                latest = self.control_queue.queue.popleft()
        return latest

    def enqueue_control(self, payload: dict[str, Any]) -> None:
        if self.stop_event.is_set():
            return
        if payload.get("type") == "move" and self.control_queue.qsize() > 8:
            self.drop_stale_moves()
        try:
            self.control_queue.put_nowait(payload)
        except queue.Full:
            if payload.get("type") == "move":
                return
            try:
                self.control_queue.put(payload, timeout=0.1)
            except queue.Full:
                pass

    def drop_stale_moves(self) -> None:
        with self.control_queue.mutex:
            latest_move: dict[str, Any] | None = None
            kept: list[dict[str, Any]] = []
            for item in self.control_queue.queue:
                if item.get("type") == "move":
                    latest_move = item
                else:
                    kept.append(item)
            self.control_queue.queue.clear()
            if latest_move is not None:
                self.control_queue.queue.append(latest_move)
            self.control_queue.queue.extend(kept[:50])

    def draw_loop(self) -> None:
        try:
            while True:
                self.latest_image = self.frame_queue.get_nowait()
        except queue.Empty:
            pass
        self.render_latest()
        if not self.stop_event.is_set():
            self.root.after(15, self.draw_loop)

    def render_latest(self) -> None:
        if self.latest_image is None:
            return
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        ratio = min(canvas_width / self.remote_width, canvas_height / self.remote_height)
        display_width = max(1, int(self.remote_width * ratio))
        display_height = max(1, int(self.remote_height * ratio))
        left = (canvas_width - display_width) // 2
        top = (canvas_height - display_height) // 2
        self.display_box = (left, top, display_width, display_height)

        resized = self.latest_image.resize((display_width, display_height), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        if self.image_item is None:
            self.image_item = self.canvas.create_image(left, top, image=self.tk_image, anchor="nw")
        else:
            self.canvas.coords(self.image_item, left, top)
            self.canvas.itemconfigure(self.image_item, image=self.tk_image)
        if self.overlay_item is not None:
            self.canvas.tag_raise(self.overlay_item)
        if self.view_bar is not None:
            self.view_bar.lift()
        if self.transfer_bar is not None:
            self.transfer_bar.lift()
        if self.exit_button is not None:
            self.exit_button.lift()

    def map_point(self, event: tk.Event) -> tuple[int, int] | None:
        left, top, width, height = self.display_box
        px = int(event.x) - left
        py = int(event.y) - top
        if px < 0 or py < 0 or px > width or py > height:
            return None
        x = round(px * self.remote_width / width)
        y = round(py * self.remote_height / height)
        return x, y

    def on_motion(self, event: tk.Event) -> str:
        now = time.monotonic()
        if now - self.last_move_sent < 0.016:
            return "break"
        self.last_move_sent = now
        point = self.map_point(event)
        if point:
            self.enqueue_control({"type": "move", "view": self.active_view_id(), "x": point[0], "y": point[1]})
        return "break"

    def on_button(self, event: tk.Event, action: str, button: str) -> str:
        point = self.map_point(event)
        if point:
            self.enqueue_control(
                {
                    "type": "button",
                    "view": self.active_view_id(),
                    "action": action,
                    "button": button,
                    "x": point[0],
                    "y": point[1],
                }
            )
        self.canvas.focus_set()
        return "break"

    def on_wheel(self, event: tk.Event) -> str:
        point = self.map_point(event)
        if point:
            self.enqueue_control(
                {
                    "type": "scroll",
                    "view": self.active_view_id(),
                    "delta_y": -int(event.delta),
                    "x": point[0],
                    "y": point[1],
                }
            )
        return "break"

    def on_key_down(self, event: tk.Event) -> str:
        key_id = event.keysym
        if key_id not in self.pressed_keys:
            self.pressed_keys.add(key_id)
            self.enqueue_control(
                {
                    "type": "key",
                    "action": "down",
                    "keysym": event.keysym,
                    "key": event.char or event.keysym,
                }
            )
        return "break"

    def on_key_up(self, event: tk.Event) -> str:
        key_id = event.keysym
        if key_id in self.pressed_keys:
            self.pressed_keys.remove(key_id)
        self.enqueue_control(
            {
                "type": "key",
                "action": "up",
                "keysym": event.keysym,
                "key": event.char or event.keysym,
            }
        )
        return "break"

    def on_focus_out(self, _event: tk.Event) -> None:
        for key in list(self.pressed_keys):
            self.enqueue_control({"type": "key", "action": "up", "keysym": key, "key": key})
        self.pressed_keys.clear()

    def close(self) -> None:
        self.stop_event.set()
        self.root.attributes("-fullscreen", False)
        self.root.destroy()


def main() -> None:
    app = LoginApp()
    try:
        app.run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
