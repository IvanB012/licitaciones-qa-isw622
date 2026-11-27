"""Fixtures E2E: la app REAL con uvicorn en un puerto libre, BD SQLite temporal sembrada y tipo de cambio sin red.

- `ENV=test` hace que la app use el proveedor de cambio que siempre falla (nunca toca la red).
- Cada prueba arranca su propio servidor y su propia BD (con el seed), así no dependen unas de otras.
- Chromium en modo headless (el predeterminado de pytest-playwright). Si falta: `python -m playwright install chromium`.
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from seeds.seed import SEED_USERS

ROOT = Path(__file__).resolve().parents[2]
EVIDENCIAS = ROOT / "04_Evidencias" / "e2e"
ADMIN = (SEED_USERS[0][0], SEED_USERS[0][1])  # admin / contraseña de prueba del README


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Servidor:
    """Proceso uvicorn con la app real sobre una BD de archivo; se puede detener y volver a levantar con la misma BD."""

    def __init__(self, tmp_path: Path):
        self.port = _free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.env = {
            **os.environ,
            "DATABASE_URL": f"sqlite:///{(tmp_path / 'e2e.db').as_posix()}",
            "SECRET_KEY": "clave-e2e",
            "ENV": "test",
        }
        self.env.pop("EXCHANGE_RATE_URL", None)
        self.log = tmp_path / "uvicorn.log"
        self.proc: subprocess.Popen | None = None

    def sembrar(self) -> None:
        subprocess.run([sys.executable, "-m", "seeds.seed", "--reset"], cwd=ROOT, env=self.env, check=True, capture_output=True)

    def iniciar(self) -> None:
        cmd = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(self.port), "--log-level", "warning"]
        with open(self.log, "ab") as out:
            self.proc = subprocess.Popen(cmd, cwd=ROOT, env=self.env, stdout=out, stderr=out)
        limite = time.time() + 30
        while time.time() < limite:
            if self.proc.poll() is not None:
                raise RuntimeError(f"uvicorn terminó antes de tiempo:\n{self.log.read_text(errors='replace')}")
            try:
                if httpx.get(f"{self.url}/api/health", timeout=1).status_code == 200:
                    return
            except httpx.HTTPError:
                time.sleep(0.2)
        raise RuntimeError("uvicorn no respondió a tiempo")

    def detener(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc = None

    def reiniciar(self) -> None:
        """Detiene el servidor y lo vuelve a levantar con la MISMA BD (sin volver a sembrar)."""
        self.detener()
        self.iniciar()


@pytest.fixture
def servidor(tmp_path):
    srv = Servidor(tmp_path)
    srv.sembrar()
    srv.iniciar()
    yield srv
    srv.detener()


@pytest.fixture
def iniciar_sesion(page, servidor):
    """Entra a la UI como admin (credenciales del README) y espera el panel."""

    def _login():
        page.goto(f"{servidor.url}/login")
        page.get_by_test_id("login-username-input").fill(ADMIN[0])
        page.get_by_test_id("login-password-input").fill(ADMIN[1])
        page.get_by_test_id("login-submit").click()
        page.get_by_test_id("nav-user").wait_for()

    return _login


@pytest.fixture
def captura(page):
    """Guarda una captura en 04_Evidencias/e2e/ con nombre `<EV>_<CP>_<paso>.png`."""
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)

    def _tomar(ev: str, cp: str, paso: str):
        page.screenshot(path=str(EVIDENCIAS / f"{ev}_{cp}_{paso}.png"), full_page=True)

    return _tomar
