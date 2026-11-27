"""Ejecuta CP-015 y CP-016 contra la app local en marcha y escribe la evidencia en 04_Evidencias/.

Uso:  python run_seguridad.py <repo> <base_url>
Los veredictos se calculan a partir de las respuestas reales. No se imprimen contraseñas ni cookies.
"""
import contextlib
import datetime
import platform
import re
import subprocess
import sys
from pathlib import Path

import httpx
from markupsafe import escape

REPO = Path(sys.argv[1])
BASE = sys.argv[2]
sys.path.insert(0, str(REPO))
from seeds.seed import SEED_USERS  # noqa: E402  (usuarios SINTÉTICOS del seed; no se reproducen en la evidencia)

OUT = REPO / "04_Evidencias"
OPERADOR = next((u, p) for u, p, r in SEED_USERS if u == "operador")
NOMBRES = ["<script>alert(1)</script>", "Acme & Co", "Nombre; DROP TABLE", "Acme \U0001F600"]
PROHIBIDO_TRAZA = ["Traceback", ".py", 'File "', "sqlalchemy", "sqlite", "C:\\", "/Users/", "site-packages"]
PROHIBIDO_SECRETO = ["Admin#2026", "Operador#2026", "SECRET_KEY", "argon2", "cambiar-esta-clave"]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def cabecera(ev, titulo, cps, reqs, objetivo, esperado, contra_app=True):
    contexto = (
        [
            f"Aplicación      : {BASE} (BD temporal con el seed de referencia, datos sintéticos)",
            "Usuario         : operador (credenciales de prueba del README; no se reproducen aquí)",
        ]
        if contra_app
        else ["Aplicación      : no se usa la app en marcha; pytest crea su propia BD temporal limpia por cada prueba (datos sintéticos)"]
    )
    return [
        f"{ev} - {titulo}",
        "=" * 78,
        f"Casos de prueba : {cps}",
        f"Requisitos      : {reqs}",
        f"Fecha/hora      : {datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')}",
        f"Commit probado  : {git('rev-parse', 'HEAD')[:7]} ({git('log', '-1', '--format=%s')})",
        f"Build de QA     : qa-build-1 -> {git('rev-list', '-n', '1', 'qa-build-1')[:7]}  (los commits posteriores solo tocan docs/tests)",
        f"Entorno         : Python {platform.python_version()} / {platform.system()} {platform.release()}",
        *contexto,
        "",
        f"OBJETIVO: {objetivo}",
        f"RESULTADO ESPERADO (de las reglas, no del código): {esperado}",
        "",
    ]


class Evidencia:
    def __init__(self, nombre, cabecera_lineas):
        self.nombre, self.lineas, self.checks = nombre, list(cabecera_lineas), []

    def log(self, texto=""):
        self.lineas.append(texto)

    def peticion(self, etiqueta, r, cuerpo_max=300):
        self.log(f"> {etiqueta}")
        ctype = r.headers.get("content-type", "")
        self.log(f"< HTTP {r.status_code}   content-type: {ctype.split(';')[0]}")
        cuerpo = r.text
        if "json" in ctype:
            self.log("< cuerpo: " + (cuerpo if len(cuerpo) <= cuerpo_max else cuerpo[:cuerpo_max] + "..."))
        else:
            self.log(f"< cuerpo: HTML de {len(cuerpo)} caracteres")

    def check(self, descripcion, ok):
        self.checks.append((descripcion, bool(ok)))
        self.log(f"   [{'OK ' if ok else 'FALLA'}] {descripcion}")

    def cerrar(self):
        todo = all(ok for _, ok in self.checks)
        self.log("")
        self.log("VERIFICACIONES")
        for d, ok in self.checks:
            self.log(f"  {'OK   ' if ok else 'FALLA'}  {d}")
        self.log("")
        self.log(f"RESULTADO OBTENIDO: {'PASA' if todo else 'FALLA'}  ({sum(ok for _, ok in self.checks)}/{len(self.checks)} verificaciones)")
        (OUT / self.nombre).write_text("\n".join(self.lineas) + "\n", encoding="utf-8")
        return todo


def sin_fugas(texto):
    lista = PROHIBIDO_TRAZA + PROHIBIDO_SECRETO
    return [t for t in lista if t in texto]


@contextlib.contextmanager
def api_cliente():
    with httpx.Client(base_url=BASE, timeout=10) as c:
        r = c.post("/api/auth/login", json={"username": OPERADOR[0], "password": OPERADOR[1]})
        assert r.status_code == 200, "no se pudo iniciar sesión (¿BD sin seed?)"
        yield c


@contextlib.contextmanager
def ui_cliente():
    with httpx.Client(base_url=BASE, timeout=10, follow_redirects=False) as c:
        r = c.post("/login", data={"username": OPERADOR[0], "password": OPERADOR[1]})
        assert r.status_code == 303, "no se pudo iniciar sesión en la UI"
        yield c


resultados = {}

# ---------------------------------------------------------------- EV-101: CP-015 por API
ev = Evidencia(
    "EV-101_CP-015_API_nombres_no_permitidos.txt",
    cabecera(
        "EV-101", "Seguridad: nombres de proveedor no permitidos por la API", "CP-015", "REQ-012",
        "Intentar crear proveedores con <script>, & , ; y emoji directamente contra POST /api/providers.",
        "422 validacion_nombre para cada nombre y no se guarda nada; un nombre válido de control sí se acepta.",
    ),
)
with api_cliente() as c:
    antes = c.get("/api/providers").json()
    ev.log(f"Proveedores antes de la prueba: {len(antes)}")
    ev.log("")
    for nombre in NOMBRES:
        r = c.post("/api/providers", json={"name": nombre})
        ev.peticion(f"POST /api/providers  name={nombre!r}", r)
        cuerpo = r.json() if "json" in r.headers.get("content-type", "") else {}
        ev.check(f"{nombre!r} -> 422 validacion_nombre", r.status_code == 422 and cuerpo.get("error") == "validacion_nombre")
        ev.log("")
    despues = c.get("/api/providers").json()
    ev.log(f"Proveedores después de los 4 intentos: {len(despues)}")
    ev.check("no se guardó ningún proveedor (misma cantidad antes y después)", len(despues) == len(antes))
    ev.check("ningún nombre enviado aparece en el listado", not any(p["name"] in NOMBRES for p in despues))
    ev.log("")
    control = "Servicios del Pacífico (Prueba), S.A."
    r = c.post("/api/providers", json={"name": control})
    ev.peticion(f"POST /api/providers  name={control!r}   (control positivo)", r)
    ev.check("el nombre válido de control se acepta con 201 (el validador no rechaza todo)", r.status_code == 201)
resultados["EV-101"] = ev.cerrar()

# ---------------------------------------------------------------- EV-102: CP-015 por la UI
ev = Evidencia(
    "EV-102_CP-015_UI_escape_y_rechazo.txt",
    cabecera(
        "EV-102", "Seguridad: formulario de la UI rechaza y escapa los nombres no permitidos", "CP-015", "REQ-012",
        "Enviar los 4 nombres por el formulario /providers/new y revisar el HTML devuelto; además, un título de licitación con <script>.",
        "422 con mensaje de error visible; el valor se muestra escapado (sin <script> crudo) y no se guarda; el título con <script> se muestra como texto.",
    ),
)
with ui_cliente() as u:
    for nombre in NOMBRES:
        r = u.post("/providers/new", data={"name": nombre, "contact_email": ""})
        ev.peticion(f"POST /providers/new  name={nombre!r}", r)
        html = r.text
        ev.check(f"{nombre!r} -> 422 con data-testid=\"error-message\"", r.status_code == 422 and 'data-testid="error-message"' in html)
        ev.check(f"{nombre!r} -> el valor reenviado queda escapado ({escape(nombre)!s})", str(escape(nombre)) in html)
        if "<" in nombre:
            ev.check("no aparece el HTML crudo en la respuesta (no se ejecutaría)", nombre not in html)
        ev.log("")
    listado = u.get("/providers").text
    ev.log("> GET /providers")
    ev.check("el listado no contiene ninguno de los 4 nombres", not any(str(escape(n)) in listado or n in listado for n in NOMBRES))

with api_cliente() as c:
    cierre = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    titulo = "<script>alert(1)</script>"
    r = c.post("/api/tenders", json={"code": "LIC-SEG-XSS", "title": titulo, "budget": "1000000.00", "closes_at": cierre})
    ev.log("")
    ev.peticion("POST /api/tenders  title='<script>alert(1)</script>'", r)
    ev.check("la licitación con título <script> se guarda como texto (201)", r.status_code == 201)
    tid = r.json().get("id")
with ui_cliente() as u:
    for ruta in ("/tenders", f"/tenders/{tid}"):
        html = u.get(ruta).text
        ev.log(f"> GET {ruta}")
        ev.check(f"{ruta}: no contiene <script>alert(1)</script> crudo", titulo not in html)
        ev.check(f"{ruta}: contiene la versión escapada {escape(titulo)!s}", str(escape(titulo)) in html)
resultados["EV-102"] = ev.cerrar()

# ---------------------------------------------------------------- EV-103: CP-016
ev = Evidencia(
    "EV-103_CP-016_errores_sin_trazas.txt",
    cabecera(
        "EV-103", "Seguridad: errores controlados sin trazas, rutas ni credenciales", "CP-016", "REQ-012",
        "Provocar errores reales (404, 401, 400, 405, 422) y leer el cuerpo completo de cada respuesta.",
        "Formato {\"error\",\"detalle\"} con el HTTP correcto y ninguna respuesta contiene trazas, nombres .py, rutas ni credenciales.",
    ),
)
ev.log("Textos buscados en cada respuesta (trazas y rutas): " + ", ".join(repr(t) for t in PROHIBIDO_TRAZA))
ev.log("Además se busca: las contraseñas de los usuarios de prueba, SECRET_KEY, su valor de ejemplo y los hashes argon2 (valores no reproducidos aquí).")
ev.log("")
casos = []  # (etiqueta, cliente, método, ruta, kwargs, status esperado, código esperado)
with api_cliente() as c, httpx.Client(base_url=BASE, timeout=10) as anon, ui_cliente() as u:
    casos = [
        ("GET /api/no-existe", c, "get", "/api/no-existe", {}, 404, "no_encontrado"),
        ("GET /api/providers/99999", c, "get", "/api/providers/99999", {}, 404, "no_encontrado"),
        ("GET /api/tenders/99999", c, "get", "/api/tenders/99999", {}, 404, "no_encontrado"),
        ("GET /api/providers  (sin sesión)", anon, "get", "/api/providers", {}, 401, "no_autenticado"),
        ("GET /api/auth/login  (método no permitido)", anon, "get", "/api/auth/login", {}, 405, "metodo_no_permitido"),
        ("POST /api/providers  (JSON malformado)", c, "post", "/api/providers", {"content": "{no es json", "headers": {"content-type": "application/json"}}, 400, "solicitud_invalida"),
        ("POST /api/providers  (cuerpo sin 'name')", c, "post", "/api/providers", {"json": {}}, 422, "validacion"),
        ("POST /api/auth/login  (credenciales falsas)", anon, "post", "/api/auth/login", {"json": {"username": "admin", "password": "intento-incorrecto-123"}}, 401, "credenciales_invalidas"),
    ]
    for etiqueta, cli, metodo, ruta, kw, status, codigo in casos:
        r = getattr(cli, metodo)(ruta, **kw)
        ev.peticion(etiqueta, r, cuerpo_max=400)
        j = r.json() if "json" in r.headers.get("content-type", "") else {}
        ev.check(f"{etiqueta} -> {status} {codigo}", r.status_code == status and j.get("error") == codigo)
        ev.check(f"{etiqueta} -> formato {{error, detalle}} únicamente", set(j) == {"error", "detalle"})
        fugas = sin_fugas(r.text)
        ev.check(f"{etiqueta} -> sin trazas ni credenciales {fugas if fugas else ''}".strip(), not fugas)
        ev.log("")
    for ruta in ("/tenders/99999", "/offers/99999/edit", "/users/99999/edit"):
        r = u.get(ruta)
        ev.log(f"> GET {ruta}   (UI)")
        ev.log(f"< HTTP {r.status_code}")
        ev.check(f"UI {ruta} -> página de error controlada (404 o 403), no un 500", r.status_code in (404, 403))
        fugas = sin_fugas(r.text)
        ev.check(f"UI {ruta} -> sin trazas ni credenciales {fugas if fugas else ''}".strip(), not fugas)
        ev.log("")
ev.log("NOTA: provocar un error 500 real exige alterar el código de la aplicación. Ese caso (ruta de prueba que lanza una excepción con un texto")
ev.log("'secreto') se ejecuta en EV-104 con pytest, que es la forma prevista en el diseño del caso CP-016.")
resultados["EV-103"] = ev.cerrar()

# ---------------------------------------------------------------- EV-104: pytest CP-015/016
NODOS = [
    "tests/unit/test_provider_rules.py::test_nombre_con_caracteres_no_permitidos_se_rechaza",
    "tests/api/test_providers_api.py::test_nombre_invalido_422",
    "tests/api/test_providers_ui.py::test_alta_con_error_se_muestra_en_error_message",
    "tests/api/test_providers_ui.py::test_valores_renderizados_quedan_escapados",
    "tests/api/test_providers_ui.py::test_nombre_guardado_se_escapa_en_listado_y_edicion",
    "tests/api/test_errors_format.py::test_500_api_formato_generico_sin_traza",
    "tests/api/test_errors_format.py::test_500_ui_pagina_generica_sin_traza",
    "tests/api/test_errors_format.py::test_404_api",
    "tests/api/test_providers_api.py::test_error_no_expone_trazas_ni_rutas",
    "tests/api/test_offers_ui.py::test_oferta_inexistente_404_en_ui",
]
ev = Evidencia(
    "EV-104_CP-015_CP-016_pytest.txt",
    cabecera(
        "EV-104", "Seguridad: pruebas automatizadas de CP-015 y CP-016 (incluye el error 500 forzado)", "CP-015, CP-016", "REQ-012",
        "Ejecutar las pruebas pytest asociadas a CP-015 y CP-016.",
        "Todas pasan (incluido el 500 forzado, que devuelve un mensaje genérico sin traza ni 'secretos').",
        contra_app=False,
    ),
)
comando = [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider", "--no-header", "-W", "ignore", *NODOS]
ev.log("Comando: python -m pytest -v " + " ".join(NODOS))
ev.log("")
p = subprocess.run(comando, cwd=REPO, capture_output=True, text=True, encoding="utf-8")
salida = [ln for ln in (p.stdout + p.stderr).splitlines() if ln.strip()]
ev.lineas.extend(salida)
ev.log("")
resumen = next((ln for ln in reversed(salida) if " passed" in ln or " failed" in ln), "")
pasan = re.search(r"(\d+) passed", resumen)
fallan = re.search(r"(\d+) failed", resumen)
ev.check(f"pytest terminó con código {p.returncode} (0 = todas pasan)", p.returncode == 0)
ev.check(
    f"resumen real de pytest: {resumen.strip('= ')!r} (sin pruebas fallidas)",
    bool(pasan) and int(pasan.group(1)) >= len(NODOS) and not fallan,
)
resultados["EV-104"] = ev.cerrar()

print("RESUMEN:", {k: ("PASA" if v else "FALLA") for k, v in resultados.items()})
sys.exit(0 if all(resultados.values()) else 1)
