from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from types import SimpleNamespace
from typing import Any
import random
import math

from .config import *
from .audio import *
from .balistica import Retroceso, Bloom, direccion_en_cono
from .miras import crear_miras, _textura_anillo

app = Ursina(title="Cazador de Oleadas v2")
# Ursina exposes several runtime proxies that its type stubs model incompletely.
_held_keys: Any = held_keys
_ursina_time: Any = time
_application: Any = application
_app: Any = app
_entity_factory: Any = Entity
_text_factory: Any = Text
window.color = color.black
try:
    window.exit_button.visible = False
except Exception:
    pass


# ESTADO DEL JUEGO
# =====================================================================
def leer_record():
    try:
        return int(RECORD_FILE.read_text())
    except Exception:
        return 0


def guardar_record(valor):
    try:
        RECORD_FILE.write_text(str(valor))
    except Exception:
        pass


def nuevo_estado(record):
    return dict(
        estado="menu",
        salud=100,
        salud_max=100,
        stamina=100,
        puede_correr=True,
        puntos=0,
        creditos=0,
        record=record,
        oleada=0,
        cola=[],
        spawn_t=0,
        intermedio=0,
        arma=0,
        desbloqueadas=[True, True, True, False, False],
        niv=[dict(dano=0, carga=0, cad=0, rec=0) for _ in ARMAS],
        mag=[a["cargador"] for a in ARMAS],
        reserva=[a["reserva_ini"] for a in ARMAS],
        perks=dict(vida=0, vel=0, fuego=0, robo=0, dron=0),
        hab=dict(dash=0, onda=0, torreta=0, furia=0),
        cdh=dict(dash=0, onda=0, torreta=0, furia=0),
        dash_t=0,
        dash_dir=(0, 1),
        dash_fx_t=0,
        furia_t=0,
        tienda_arma=0,
        tienda_sel=0,
        tienda_tab=0,
        cd=0,
        recarga=0,
        retroceso=0,
        fogonazo=0,
        hit_t=0,
        hit_cab=False,
        combo=0,
        combo_t=0,
        muertes=0,
        dano_alpha=0,
        buff_t=0,
        aviso_t=0,
        t=0,
    )


S = SimpleNamespace()
vars(S).update(nuevo_estado(leer_record()))

retro = Retroceso()   # retroceso acumulado con recuperacion (balistica.py)
bloom = Bloom()       # dispersion creciente por rafaga
enemigos, proyectiles, recogibles, torretas, drones = [], [], [], [], []
ITEMS = []

# Limites de efectos para evitar picos de entidades durante las hordas.
MAX_PARTICULAS = 110
MAX_RAYOS = 28
MAX_ANILLOS = 10
EFECTOS_ACTIVOS = {"particula": [], "rayo": [], "anillo": []}
GRID_ENEMIGOS = {}
GRID_CELDA = 6.5
RADAR_INTERVALO = 0.05
HUD_INTERVALO = 0.05
TIENDA_CONTADOR = True   # la cuenta atras de la oleada sigue corriendo dentro de la tienda

# Culling visual: los modelos fuera del campo de vision o demasiado lejos
# no mantienen sus subentidades/renderers activos. La IA sigue funcionando.
DISTANCIA_RENDER = 58.0
MARGEN_VISION = 14.0
VISIBILIDAD_INTERVALO = 0.12
_radar_timer = 0.0
_hud_timer = 0.0


def esta_en_vista(pos, distancia_max=DISTANCIA_RENDER, margen=MARGEN_VISION):
    # Comprueba de forma barata si una posicion cae cerca del frustum de camara.
    if "camera" not in globals() or "jugador" not in globals():
        return True
    origen = camera.world_position
    delta = Vec3(pos.x - origen.x, pos.y - origen.y, pos.z - origen.z)
    distancia2 = delta.x * delta.x + delta.y * delta.y + delta.z * delta.z
    if distancia2 > distancia_max * distancia_max:
        return False
    if distancia2 < 0.0001:
        return True
    direccion = delta / math.sqrt(distancia2)
    frente = camera.forward
    dot = direccion.x * frente.x + direccion.y * frente.y + direccion.z * frente.z
    fov = float(getattr(camera, "fov", 90))
    limite = math.cos(math.radians(min(89, fov * 0.5 + margen)))
    return dot >= limite


def stat(i, k):
    a, n = ARMAS[i], S.niv[i]
    if k == "dano":
        return a["dano"] * (1 + 0.25 * n["dano"])
    if k == "cargador":
        return max(1, int(round(a["cargador"] * (1 + 0.25 * n["carga"]))))
    if k == "cadencia":
        return a["cadencia"] * (0.9 ** n["cad"])
    if k == "recarga":
        return a["recarga"] * (0.85 ** n["rec"])


def reserva_max(i):
    return int(ARMAS[i]["reserva_max"] * (1 + 0.25 * S.niv[i]["carga"]))


# =====================================================================
#  ESCENARIO
# =====================================================================
suelo = _entity_factory(
    model="plane",
    scale=ARENA * 2,
    texture="grass",
    texture_scale=(40, 40),
    collider="box",
)
Sky()

largo = ARENA * 2 + 2
for x, z, sx, sz in (
    (0, ARENA, largo, 1),
    (0, -ARENA, largo, 1),
    (ARENA, 0, 1, largo),
    (-ARENA, 0, 1, largo),
):
    _entity_factory(
        model="cube",
        position=(x, 3, z),
        scale=(sx, 6, sz),
        color=color.gray,
        texture="brick",
        texture_scale=(20, 2),
        collider="box",
    )

obstaculos = []  # (x, z, radio, altura), datos de colision independientes del render
obstaculos_meta = []
obstaculos_visibles = {}
_obstaculos_timer = 0.0
for _ in range(16):
    s = random.uniform(1.6, 3.6)
    h = random.uniform(3, 7)
    while True:
        x = random.uniform(-ARENA + 6, ARENA - 6)
        z = random.uniform(-ARENA + 6, ARENA - 6)
        if math.hypot(x, z) > 9:
            break
    col = color.hsv(random.uniform(180, 260), 0.25, random.uniform(0.45, 0.75))
    obstaculos.append((x, z, s * 0.62, h))
    obstaculos_meta.append((s, h, col))

# =====================================================================
#  JUGADOR Y ARMA
# =====================================================================
jugador = FirstPersonController(position=(0, 1, 0))
setattr(jugador, "speed", 5.5)
jugador.enabled = False
mouse.visible = True
mouse.locked = False
try:
    jugador.cursor.visible = False
    jugador.cursor.enabled = False
except Exception:
    pass
camera.fov = 90


def actualizar_obstaculos_visibles():
    """Crea solo obstaculos visibles/cercanos y libera los que quedan lejos."""
    for i, (x, z, _radio, _h) in enumerate(obstaculos):
        dx, dz = x - jugador.x, z - jugador.z
        cerca = dx * dx + dz * dz <= 14 * 14  # conserva colision alrededor del jugador
        visible = esta_en_vista(
            Vec3(x, obstaculos_meta[i][1] * 0.5, z), distancia_max=58
        )
        debe_existir = cerca or visible
        entidad = obstaculos_visibles.get(i)
        if debe_existir and entidad is None:
            escala, alto, col = obstaculos_meta[i]
            obstaculos_visibles[i] = _entity_factory(
                model="cube",
                position=(x, alto / 2, z),
                scale=(escala, alto, escala),
                texture="white_cube",
                color=col,
                collider="box",
            )
        elif not debe_existir and entidad is not None:
            destroy(entidad)
            del obstaculos_visibles[i]


arma_modelo = _entity_factory(
    parent=camera,
    model="cube",
    position=(0.4, -0.32, 0.9),
    scale=(0.1, 0.14, 0.5),
    color=color.dark_gray,
)
canon = _entity_factory(
    parent=arma_modelo,
    model="cube",
    position=(0, 0.25, 0.7),
    scale=(0.6, 0.4, 0.7),
    color=color.black,
)
fogonazo = _entity_factory(
    parent=camera,
    model="quad",
    position=(0.4, -0.2, 1.5),
    scale=0.35,
    color=color.yellow,
    enabled=False,
)

# =====================================================================
#  INTERFAZ
# =====================================================================
hud = _entity_factory(parent=camera.ui, enabled=False)
hud_info = _entity_factory(parent=hud)   # todo el HUD salvo retícula, miras y hitmarker
ui_menu = _entity_factory(parent=camera.ui)
ui_pausa = _entity_factory(parent=camera.ui, enabled=False)
ui_fin = _entity_factory(parent=camera.ui, enabled=False)
ui_tienda = _entity_factory(parent=camera.ui, enabled=False)
overlay_dano = _entity_factory(
    parent=camera.ui, model="quad", scale=(4, 2), color=Vec4(1, 0, 0, 0), z=2
)


def texto(txt, pos, esc=1.2, col=color.white, centro=False, padre=None, der=False):
    kw = dict(
        parent=padre if padre else hud_info,
        text=txt,
        position=pos,
        scale=esc,
        color=col,
        origin=(0, 0) if centro else ((0.5, 0) if der else (-0.5, 0)),
    )
    t = _text_factory(**kw)
    t._ult = txt
    return t


def poner(t, s):
    if t._ult != s:
        t.text = s
        t._ult = s


def fondo(padre, alfa=0.75, col=(0, 0, 0)):
    _entity_factory(
        parent=padre, model="quad", scale=(4, 2), color=Vec4(*col, alfa), z=1
    )


def panel_hud(pos, escala, alpha=0.80, z=0.65, padre=None):
    return _entity_factory(
        parent=padre if padre else hud_info,
        model="quad",
        position=(pos[0], pos[1], z),
        scale=escala,
        color=Vec4(0.045, 0.058, 0.078, alpha),
    )


def acento_hud(pos, escala, col=None, z=0.62, padre=None):
    return _entity_factory(
        parent=padre if padre else hud_info,
        model="quad",
        position=(pos[0], pos[1], z),
        scale=escala,
        color=col or color.rgb(225, 65, 75),
    )


def barra(pos, tam, col, z=0.55):
    bg = _entity_factory(
        parent=hud_info,
        model="quad",
        color=rgb255(36, 44, 58),
        scale=tam,
        position=(pos[0], pos[1], z),
    )
    return _entity_factory(
        parent=bg,
        model="quad",
        color=col,
        origin=(-0.5, 0),
        x=-0.5,
        z=-0.01,
        scale=(1.0, 1.0),
    )


# --- menu ---
fondo(ui_menu)
texto("CAZADOR DE OLEADAS", (0, 0.28), 3, color.orange, True, ui_menu)
texto(
    "Sobrevive a oleadas cada vez mas duras. Cada 5 oleadas llega un JEFE.\n"
    "Gana creditos con cada baja y gastalos en la TIENDA (tecla B entre oleadas).\n\n"
    "WASD moverte  ·  SHIFT correr  ·  ESPACIO saltar  ·  CLIC disparar  ·  CLIC DER apuntar\n"
    "R recargar  ·  1-5 o RUEDA cambiar arma  ·  ESC pausa\n\n"
    "HABILIDADES:  Q Dash   ·   E Onda de choque   ·   F Torreta automatica   ·   C Modo furia\n"
    "Compra DRONES de combate en la tienda para que te ayuden.\n\n"
    "Apunta a la cabeza para hacer el doble de dano.\n"
    "Recoge: verde = vida, dorado = municion, magenta = dano x2.",
    (0, -0.02),
    1.05,
    color.white,
    True,
    ui_menu,
)
texto("Pulsa ENTER para jugar", (0, -0.36), 2, color.yellow, True, ui_menu)
txt_menu_record = texto("", (0, -0.44), 1.1, color.light_gray, True, ui_menu)

# --- pausa ---
fondo(ui_pausa)
texto("PAUSA", (0, 0.1), 4, color.white, True, ui_pausa)
texto(
    "ESC / P: continuar      Q: salir",
    (0, -0.05),
    1.5,
    color.light_gray,
    True,
    ui_pausa,
)

# --- fin de partida ---
fondo(ui_fin)
texto("HAS MUERTO", (0, 0.22), 4, color.red, True, ui_fin)
txt_fin_stats = texto("", (0, 0), 1.7, color.white, True, ui_fin)
texto(
    "R / ENTER: jugar otra vez      ESC: salir",
    (0, -0.22),
    1.3,
    color.yellow,
    True,
    ui_fin,
)

# --- helpers de interfaz (coordenadas por bordes: valen para cualquier aspecto) ---
def rgb255(r, g, b, a=255):
    return Vec4(r / 255, g / 255, b / 255, a / 255)


TK = 1.0                       # multiplicador global del tamano de texto (HUD y tienda)
AR = window.aspect_ratio
MG = 0.033
L, R, T, B = -AR / 2 + MG, AR / 2 - MG, 0.5 - MG, -0.5 + MG
PANEL = rgb255(14, 18, 26, 150)          # translucido: se ve la escena detras
BORDE = rgb255(105, 120, 145, 210)       # borde claro de 2 px
GRIS = rgb255(150, 160, 176)
ORO = rgb255(255, 205, 100)
ROJO_H = rgb255(255, 64, 80)
VERDE = rgb255(60, 220, 130)
CIAN = rgb255(70, 200, 240)
NARANJA_H = rgb255(255, 165, 75)
TEX_ANILLO = _textura_anillo(256, 14)
TEX_ANILLO_FINO = _textura_anillo(256, 3)
CORTO = ("Pistola", "Rifle", "Escopeta", "Sniper", "Granadas")


def caja(padre, cx, cy, w, h, col, z=0.6):
    return _entity_factory(
        parent=padre, model="quad", position=(cx, cy, z), scale=(w, h), color=col
    )


class Borde:
    """Borde de 4 tiras. .color lo recolorea; .collider/.on_click van al panel."""

    def __init__(self, panel, tiras):
        object.__setattr__(self, "panel", panel)
        object.__setattr__(self, "tiras", tiras)
        object.__setattr__(self, "_col", None)

    @property
    def color(self):
        return self._col

    @color.setter
    def color(self, c):
        object.__setattr__(self, "_col", c)
        for t in self.tiras:
            t.color = c

    def __setattr__(self, k, v):
        if k in ("collider", "on_click"):
            setattr(self.panel, k, v)
        else:
            object.__setattr__(self, k, v)


def tarjeta(padre, cx, cy, w, h, col=None, borde=None, z=0.65, e=0.0026):
    """Panel (translucido por defecto) con borde real de grosor e."""
    panel = caja(padre, cx, cy, w, h, col or PANEL, z)
    c = borde or BORDE
    zb = z - 0.01
    tiras = [
        caja(padre, cx, cy + h / 2 - e / 2, w, e, c, zb),
        caja(padre, cx, cy - h / 2 + e / 2, w, e, c, zb),
        caja(padre, cx - w / 2 + e / 2, cy, e, h - 2 * e, c, zb),
        caja(padre, cx + w / 2 - e / 2, cy, e, h - 2 * e, c, zb),
    ]
    return Borde(panel, tiras)


def th(txt, x, y, esc, col=color.white, alin="l", padre=None):
    """Texto de interfaz. alin: l(izquierda) c(centro) r(derecha)."""
    return texto(txt, (x, y), esc * TK, col, alin == "c", padre or hud_info, der=(alin == "r"))


def ancho(s_, esc):
    """Ancho aproximado de un texto en unidades de camera.ui."""
    return len(s_) * 0.0135 * esc * TK


def fmt(n):
    return f"{int(n):,}".replace(",", " ")


# --- menu ya creado arriba; --- TIENDA ---
SL, SR = -AR / 2 + 0.05, AR / 2 - 0.05
TABS = ("Armas", "Perks", "Habilidades", "Suministros")
RANGOS = ((0, 5), (5, 10), (10, 14), (14, 16))   # indices de ITEMS por pestana
COL_FILA = rgb255(26, 33, 44)
COL_TAB = rgb255(32, 40, 54)

fondo(ui_tienda, 1.0, (13 / 255, 17 / 255, 25 / 255))
txt_tienda_sub = th("", SL, 0.446, 0.62, GRIS, padre=ui_tienda)
th("TIENDA", SL, 0.385, 3.0, color.white, padre=ui_tienda)
txt_tienda_cred = th("", SR - 0.29, 0.424, 1.7, ORO, "r", ui_tienda)
btn_iniciar = caja(ui_tienda, SR - 0.13, 0.424, 0.26, 0.058, ROJO_H, 0.5)
btn_iniciar.collider = "box"
btn_iniciar.on_click = lambda: iniciar_desde_tienda()
th("ENTER  Iniciar oleada", SR - 0.13, 0.424, 0.78, color.white, "c", ui_tienda)

tab_ents = []
_x = SL
for _k, (_nom, _w) in enumerate(zip(TABS, (0.105, 0.098, 0.155, 0.155))):
    _e = caja(ui_tienda, _x + _w / 2, 0.34, _w, 0.044, COL_TAB, 0.5)
    _e.collider = "box"
    _e.on_click = lambda k=_k: elegir_tab(k)
    _t = th(_nom, _x + _w / 2, 0.34, 0.8, color.white, "c", ui_tienda)
    tab_ents.append((_e, _t))
    _x += _w + 0.011

# fila de armas (solo pestana Armas)
strip = _entity_factory(parent=ui_tienda)
_N = len(ARMAS)
_CW = (SR - SL - 0.012 * (_N - 1)) / _N
cards = []
for _i in range(_N):
    _cx = SL + _CW / 2 + _i * (_CW + 0.012)
    _brd = tarjeta(strip, _cx, 0.245, _CW, 0.105, COL_FILA, BORDE, 0.55)
    _brd.collider = "box"
    _brd.on_click = lambda i=_i: elegir_arma_tienda(i)
    th(ARMAS[_i]["nombre"], _cx - _CW / 2 + 0.02, 0.267, 1.15, color.white, padre=strip)
    _ts = th("", _cx - _CW / 2 + 0.02, 0.222, 0.7, GRIS, padre=strip)
    cards.append((_brd, _ts))

# filas de mejoras (pool de 5)
filas = []
for _k in range(5):
    _f = _entity_factory(parent=ui_tienda)
    _f.brd = tarjeta(_f, 0, 0, SR - SL, 0.085, COL_FILA, BORDE, 0.55)
    _f.brd.collider = "box"
    _f.brd.on_click = lambda k=_k: click_fila(k)
    _f.t_nombre = th("", SL + 0.022, 0.02, 1.1, color.white, padre=_f)
    _f.t_desc = th("", SL + 0.022, -0.016, 0.62, GRIS, padre=_f)
    _f.t_prev = th("", SL + 0.62, 0.016, 0.7, color.white, padre=_f)
    _f.pips = [caja(_f, SL + 0.62 + j * 0.032 + 0.013, -0.02, 0.026, 0.007, BORDE, 0.5) for j in range(5)]
    _f.btn = caja(_f, SR - 0.14, 0, 0.26, 0.055, ORO, 0.5)
    _f.btn.collider = "box"
    _f.btn.on_click = lambda k=_k: comprar_fila(k)
    _f.t_btn = th("", SR - 0.14, 0, 0.85, color.black, "c", _f)
    filas.append(_f)

txt_tienda_msg = th("", 0, -0.40, 1.1, ORO, "c", ui_tienda)
th(
    "A/D arma   W/S elegir   1-4 o TAB pestana   ESPACIO o clic: comprar   ENTER: iniciar oleada   B/ESC: cerrar",
    0, -0.455, 0.62, GRIS, "c", ui_tienda,
)

# --- HUD EN PARTIDA (segun la referencia HUD_en_partida.png) ---
# 1. Tarjeta superior izquierda
CW_TL, CH_TL, PAD = 0.463, 0.17, 0.024
tarjeta(hud_info, L + CW_TL / 2, T - CH_TL / 2, CW_TL, CH_TL)
txt_oleada = th("", L + PAD, T - 0.042, 1.45, color.white)
txt_record = th("", L + CW_TL - PAD, T - 0.042, 0.6, GRIS, "r")
txt_enemigos = th("ENEMIGOS", L + PAD, T - 0.083, 0.6, GRIS)
txt_hint = th("", L + CW_TL - PAD, T - 0.083, 0.85, color.white, "r")
barra_enemigos = barra((L + CW_TL / 2, T - 0.106), (CW_TL - 2 * PAD, 0.008), ROJO_H)
txt_puntos = th("", L + PAD, T - 0.138, 0.95, color.white)
txt_cred = th("", L + CW_TL - PAD, T - 0.138, 1.05, ORO, "r")
# Combo independiente: solo aparece cuando la racha está activa.
box_combo = _entity_factory(parent=hud_info, enabled=False)
tarjeta(box_combo, 0, T - 0.122, 0.30, 0.044, PANEL, NARANJA_H)
caja(box_combo, -0.147, T - 0.122, 0.006, 0.044, NARANJA_H, 0.6)
txt_combo = th("", 0, T - 0.133, 0.82, NARANJA_H, "c", box_combo)
txt_buff = th("", L + PAD, T - CH_TL - 0.025, 0.65, color.magenta)

# 2. Cápsula de aviso (arriba al centro)
box_aviso = _entity_factory(parent=hud_info, enabled=False)
tarjeta(box_aviso, 0, T - 0.05, 0.42, 0.056)
caja(box_aviso, -0.21, T - 0.05, 0.006, 0.056, ORO, 0.6)
txt_aviso = th("", 0, T - 0.05, 0.95, color.white, "c", box_aviso)

hitmarker = texto("x", (0, 0), 2.2, color.white, True, hud)
hitmarker.enabled = False

# 3. Radar circular con norte y anillo de alcance
RAD = 0.105
RCX, RCY = R - RAD, T - RAD
_entity_factory(parent=hud_info, model="circle", scale=RAD * 2, position=(RCX, RCY, 0.60), color=PANEL)
_entity_factory(parent=hud_info, model="quad", texture=TEX_ANILLO_FINO, scale=RAD * 2 + 0.004,
                position=(RCX, RCY, 0.59), color=BORDE)
radar = _entity_factory(parent=hud_info, model="circle", scale=RAD * 1.6,
                        position=(RCX, RCY, 0.58), color=Vec4(0.02, 0.03, 0.045, 0.92))
for _esc in (0.33, 0.66, 1.0):          # anillos de distancia
    _entity_factory(parent=radar, model="quad", texture=TEX_ANILLO_FINO, scale=_esc,
                    color=Vec4(0.4, 0.5, 0.62, 0.5 if _esc < 1 else 0.3), z=-0.015)
for _w, _h in ((1.0, 0.006), (0.006, 1.0)):   # cruz de ejes
    _entity_factory(parent=radar, model="quad", scale=(_w, _h),
                    color=Vec4(0.4, 0.5, 0.62, 0.22), z=-0.012)
_entity_factory(parent=radar, model=Mesh(vertices=[(0, 0.07, 0), (-0.045, -0.04, 0), (0.045, -0.04, 0)],
                                         triangles=[(0, 1, 2)]),
                color=color.white, z=-0.02, double_sided=True)
# Punto central: referencia fija de la posición del jugador.
_entity_factory(parent=radar, model="circle", scale=0.018,
                color=ORO, position=(0, 0, -0.025))

# Brujula: 8 direcciones + marcas cada 15 grados, giran con el jugador (arriba = hacia donde miras)
_GRIS_OSC = rgb255(105, 114, 130)
radar_dirs = [
    (th(n_, RCX, RCY, esc_, col_, "c"), b_)
    for n_, b_, esc_, col_ in (
        ("N", 0, 0.7, ROJO_H), ("NE", 45, 0.4, _GRIS_OSC), ("E", 90, 0.6, GRIS),
        ("SE", 135, 0.4, _GRIS_OSC), ("S", 180, 0.6, GRIS), ("SO", 225, 0.4, _GRIS_OSC),
        ("O", 270, 0.6, GRIS), ("NO", 315, 0.4, _GRIS_OSC),
    )
]
radar_marcas = [
    (_entity_factory(parent=hud_info, model="circle",
                     scale=0.0042 if k_ % 3 == 0 else 0.0026,
                     color=rgb255(150, 165, 190, 230) if k_ % 3 == 0 else rgb255(105, 120, 145, 170),
                     position=(RCX, RCY, 0.57)), k_ * 15)
    for k_ in range(24)
]
_heading_ult = [None]


def actualizar_brujula(force=False):
    h = jugador.rotation_y
    if not force and _heading_ult[0] is not None and abs(h - _heading_ult[0]) < 0.15:
        return
    _heading_ult[0] = h
    for t_, b_ in radar_dirs:
        a_ = math.radians(b_ - h)
        r_ = 0.088 if len(t_.text) == 1 else 0.086
        t_.position = (RCX + math.sin(a_) * r_, RCY + math.cos(a_) * r_, 0)
    for e_, b_ in radar_marcas:
        a_ = math.radians(b_ - h)
        e_.position = (RCX + math.sin(a_) * 0.1, RCY + math.cos(a_) * 0.1, 0.57)

puntos_radar = []

# 4. Tarjeta de vida (abajo izquierda)
CW_BL, CH_BL = 0.472, 0.135
tarjeta(hud_info, L + CW_BL / 2, B + CH_BL / 2, CW_BL, CH_BL)
th("VIDA", L + PAD, B + 0.092, 0.6, GRIS)
X_VIDA_R = L + CW_BL - PAD
txt_vida_max = th("", X_VIDA_R, B + 0.097, 0.85, GRIS, "r")
txt_vida_n = th("", X_VIDA_R - 0.09, B + 0.097, 1.7, color.white, "r")
barra_vida = barra((L + CW_BL / 2, B + 0.063), (CW_BL - 2 * PAD, 0.017), VERDE)
barra_stamina = barra((L + CW_BL / 2, B + 0.041), (CW_BL - 2 * PAD, 0.005), CIAN)
# El color de vida comunica el estado sin depender únicamente del número.
th("RESISTENCIA", L + PAD, B + 0.022, 0.55, GRIS)

# 5. Habilidades: anillo con progreso + tecla debajo
def malla_arco(frac, seg=48, r_ext=0.5, r_int=0.44):
    n = max(0, min(seg, int(round(frac * seg))))
    if n == 0:
        return None
    verts, tris = [], []
    for i in range(n + 1):
        ang = math.pi / 2 - i * math.tau / seg      # arranca arriba, sentido horario
        c, s_ = math.cos(ang), math.sin(ang)
        verts += [(c * r_ext, s_ * r_ext, 0), (c * r_int, s_ * r_int, 0)]
    for i in range(n):
        a = 2 * i
        tris += [(a, a + 2, a + 1), (a + 1, a + 2, a + 3)]
    return Mesh(vertices=verts, triangles=tris, mode="triangle")


HAB_COL = dict(dash=CIAN, onda=CIAN, torreta=ORO, furia=ROJO_H)
HAB_NOM = dict(dash="DASH", onda="ONDA", torreta="TORR.", furia="FURIA")
CD_TOT = {k: 0.0 for k in HABS}
HR, HY = 0.045, -0.3875
# Base común para agrupar las cuatro habilidades y sus teclas.
tarjeta(hud_info, 0, -0.407, 0.49, 0.145, PANEL, BORDE, 0.67)
hab_ui = {}
for _xh, _k in zip((-0.1667, -0.0556, 0.0556, 0.1667), HABS):
    _entity_factory(parent=hud_info, model="circle", scale=HR * 2 - 0.012, position=(_xh, HY, 0.62), color=PANEL)
    _entity_factory(parent=hud_info, model="quad", texture=TEX_ANILLO, scale=HR * 2,
                    position=(_xh, HY, 0.61), color=BORDE)
    _arco = _entity_factory(parent=hud_info, model=malla_arco(1.0), scale=HR * 2,
                            position=(_xh, HY, 0.60), color=HAB_COL[_k], double_sided=True)
    _txt = th("", _xh, HY, 0.62, color.white, "c")
    caja(hud_info, _xh, -0.456, 0.026, 0.026, rgb255(226, 230, 238), 0.6)
    th(HABS[_k][0].upper(), _xh, -0.456, 0.6, color.black, "c")
    hab_ui[_k] = dict(arco=_arco, txt=_txt, n=48)

# 6. Armas (slots) + panel de municion (abajo derecha)
CW_BR, CH_BR = 0.471, 0.167
X_R = R - 0.027
tarjeta(hud_info, R - CW_BR / 2, B + CH_BR / 2, CW_BR, CH_BR)
slots_arma = {}
_NA = len(ARMAS)
_SW = (CW_BR - 0.008 * (_NA - 1)) / _NA
for _i in range(_NA):
    _sx = R - CW_BR + _SW / 2 + _i * (_SW + 0.008)
    _brd = tarjeta(hud_info, _sx, B + 0.21, _SW, 0.061, PANEL, BORDE, 0.65)
    caja(hud_info, _sx - _SW / 2 + 0.02, B + 0.222, 0.026, 0.026, rgb255(60, 70, 86), 0.6)
    _num = th(str(_i + 1), _sx - _SW / 2 + 0.02, B + 0.222, 0.6, color.white, "c")
    _nom = th(CORTO[_i] if _i < len(CORTO) else ARMAS[_i]["nombre"], _sx - _SW / 2 + 0.012, B + 0.196, 0.55, GRIS)
    slots_arma[_i] = dict(brd=_brd, nom=_nom, num=_num)

txt_arma_tipo = th("", X_R, B + 0.134, 0.62, GRIS, "r")
txt_mag = th("", X_R - 0.1, B + 0.082, 3.2, color.white, "r")
txt_mag_max = th("", X_R, B + 0.07, 1.3, GRIS, "r")
txt_reserva = th("", X_R - 0.2, B + 0.03, 0.8, GRIS, "r")
txt_baja = th("", X_R - 0.2, B + 0.03, 0.8, ROJO_H, "r")
X_BADGE = X_R - ancho("recargar", 0.8) - 0.018
X_BAJA_R = X_BADGE - 0.024
caja(hud_info, X_BADGE, B + 0.03, 0.024, 0.024, rgb255(226, 230, 238), 0.6)
th("R", X_BADGE, B + 0.03, 0.6, color.black, "c")
th("recargar", X_R, B + 0.03, 0.8, GRIS, "r")

# 7. Reticula dinamica (se abre con el bloom) y miras tacticas por arma
reticula = _entity_factory(parent=hud)
ticks = []
for _dx, _dy, _sx, _sy in ((-0.026, 0, 0.011, 0.003), (0.026, 0, 0.011, 0.003),
                           (0, 0.026, 0.003, 0.011), (0, -0.026, 0.003, 0.011)):
    _e = _entity_factory(parent=reticula, model="quad", color=color.white,
                         position=(_dx, _dy, 0.52), scale=(_sx, _sy))
    ticks.append((_e, _dx, _dy))
_entity_factory(parent=reticula, model="quad", color=ROJO_H, position=(0, 0, 0.52), scale=0.0035)
miras = crear_miras(hud)
_mira_act = None
_sens_base = Vec2(*jugador.mouse_sensitivity) if hasattr(jugador, "mouse_sensitivity") else None


def ocultar_mira():
    global _mira_act
    if _mira_act in miras:
        miras[_mira_act].enabled = False
    _mira_act = None
    reticula.enabled = True
    arma_modelo.enabled = True
    hud_info.enabled = True


def actualizar_mira(ads, a):
    """Muestra la mira tactica cuando el zoom ya esta al 60 %; si no, la reticula normal."""
    global _mira_act
    nombre = None
    if ads and (90 - camera.fov) >= 0.6 * (90 - a["fov_ads"]):
        nombre = a["mira"]
    if nombre != _mira_act:
        ocultar_mira()
        if nombre:
            miras[nombre].enabled = True
            _mira_act = nombre
            reticula.enabled = False
            arma_modelo.enabled = False
            hud_info.enabled = nombre != "mildot"
    if reticula.enabled:
        k = 1 + bloom.valor * 2.5
        for e, dx, dy in ticks:
            e.position = (dx * k, dy * k, 0.52)


# =====================================================================
#  UTILIDADES Y EFECTOS
# =====================================================================
def aviso(txt, dur=2.0, col=color.white):
    poner(txt_aviso, txt)
    txt_aviso.color = col
    S.aviso_t = dur
    box_aviso.enabled = dur > 0


def _crear_efecto(tipo, limite, entidad, duracion):
    activos = EFECTOS_ACTIVOS[tipo]
    if len(activos) >= limite:
        destroy(entidad)
        return False
    activos.append((entidad, S.t + duracion))
    return True


def limpiar_efectos():
    # Se ejecuta una vez por frame; impide que efectos olvidados se acumulen.
    for activos in EFECTOS_ACTIVOS.values():
        vivos = []
        for entidad, fin in activos:
            if S.t >= fin:
                destroy(entidad)
            else:
                vivos.append((entidad, fin))
        activos[:] = vivos


def particulas(pos, col, n=8, vel=2.0):
    # Los efectos puramente visuales no se crean fuera de la vista del jugador.
    if not esta_en_vista(pos, distancia_max=48):
        return
    disponibles = MAX_PARTICULAS - len(EFECTOS_ACTIVOS["particula"])
    for _ in range(min(n, max(0, disponibles))):
        p = _entity_factory(
            model="cube", color=col, scale=random.uniform(0.08, 0.2), position=pos
        )
        destino = (
            pos
            + Vec3(random.uniform(-1, 1), random.uniform(0, 1.5), random.uniform(-1, 1))
            * vel
            * 0.6
        )
        p.animate_position(destino, duration=0.5, curve=curve.out_quad)
        p.animate_scale(0, duration=0.5)
        _crear_efecto("particula", MAX_PARTICULAS, p, 0.56)


def rayo(a, b, col=color.yellow, grosor=0.04):
    if not (esta_en_vista(a, distancia_max=48) or esta_en_vista(b, distancia_max=48)):
        return
    if len(EFECTOS_ACTIVOS["rayo"]) >= MAX_RAYOS:
        return
    d = (b - a).length()
    if d < 0.05:
        return
    r = _entity_factory(
        model="cube", color=col, position=(a + b) / 2, scale=(grosor, grosor, d)
    )
    r.look_at(b)
    _crear_efecto("rayo", MAX_RAYOS, r, 0.07)


def anillo(pos, radio, col, dur=0.4):
    if not esta_en_vista(pos, distancia_max=48):
        return
    if len(EFECTOS_ACTIVOS["anillo"]) >= MAX_ANILLOS:
        return
    r = _entity_factory(
        model="circle",
        rotation_x=90,
        position=Vec3(pos.x, 0.15, pos.z),
        scale=1,
        color=col,
        double_sided=True,
    )
    r.animate_scale(radio * 2, duration=dur, curve=curve.out_quad)
    _crear_efecto("anillo", MAX_ANILLOS, r, dur + 0.02)


def construir_grid_enemigos():
    GRID_ENEMIGOS.clear()
    for enemigo in enemigos:
        if enemigo.muerto:
            continue
        celda = (int(enemigo.x // GRID_CELDA), int(enemigo.z // GRID_CELDA))
        GRID_ENEMIGOS.setdefault(celda, []).append(enemigo)


def vecinos_enemigos(enemigo):
    cx = int(enemigo.x // GRID_CELDA)
    cz = int(enemigo.z // GRID_CELDA)
    for ox in (-1, 0, 1):
        for oz in (-1, 0, 1):
            yield from GRID_ENEMIGOS.get((cx + ox, cz + oz), ())


def mult_combo():
    return min(1 + max(S.combo - 1, 0) * 0.1, 3)


def ganar(p):
    S.puntos += p
    S.creditos += p


def mas_cercano(pos, rango):
    mejor = None
    limite2 = rango * rango
    mejor_d2 = limite2
    for e in enemigos:
        if e.muerto:
            continue
        dx, dz = e.x - pos.x, e.z - pos.z
        d2 = dx * dx + dz * dz
        if d2 < mejor_d2:
            mejor, mejor_d2 = e, d2
    return mejor


def pos_spawn():
    for _ in range(40):
        ang = random.uniform(0, math.tau)
        r = random.uniform(ARENA * 0.55, ARENA - 4)
        x, z = math.cos(ang) * r, math.sin(ang) * r
        if math.hypot(x - jugador.x, z - jugador.z) < 18:
            continue
        if any(
            math.hypot(x - ox, z - oz) < orad + 1.5 for ox, oz, orad, _h in obstaculos
        ):
            continue
        return Vec3(x, 0, z)
    return Vec3(ARENA - 5, 0, ARENA - 5)


def herir(d):
    if S.estado != "jugando" or S.dash_t > 0:
        return
    S.salud -= d
    S.dano_alpha = min(0.6, S.dano_alpha + 0.35)
    S.combo = 0
    if S.salud <= 0:
        S.salud = 0
        terminar()


def agregar_municion(factor=1.0):
    for i, a in enumerate(ARMAS):
        S.reserva[i] = min(
            reserva_max(i), S.reserva[i] + int(a["cargador"] * 2 * factor)
        )


def botin(pos, garantizado=False):
    if garantizado or random.random() < 0.22:
        tipo = random.choices(["salud", "municion", "dano"], weights=[0.4, 0.45, 0.15])[
            0
        ]
        p = Vec3(pos.x + random.uniform(-1, 1), 0, pos.z + random.uniform(-1, 1))
        recogibles.append(Recogible(tipo, p))


def aplicar_fuego(en):
    if S.perks["fuego"] > 0:
        en.quema_t = 3
        en.quema_dps = 4 + 4 * S.perks["fuego"]


def golpear(en, dano, cabeza=False):
    """Dano del jugador: marcador de impacto + municion incendiaria."""
    S.hit_t = 0.12
    S.hit_cab = cabeza
    aplicar_fuego(en)
    en.recibir_dano(dano)


def danar_auto(en, dano):
    """Dano de torretas y drones."""
    aplicar_fuego(en)
    en.recibir_dano(dano)


def explosion(pos, radio, dano):
    anillo(pos, radio, Vec4(1, 0.5, 0, 0.6), 0.35)
    particulas(pos, color.orange, n=24, vel=4)
    for e in enemigos[:]:
        c = e.world_position + Vec3(0, e.alto / 2, 0)
        d = (c - pos).length()
        if d < radio + e.radio:
            golpear(e, dano * (1 - 0.5 * min(d / radio, 1)))


# =====================================================================
#  CLASES
# =====================================================================
class Enemigo(Entity):
    def __init__(self, tipo, pos):
        super().__init__(position=pos)
        d = TIPOS[tipo]
        esc = d["escala"]
        self.tipo = tipo
        self.alto = esc[1]
        self.radio = esc[0] * 0.5 + 0.2
        self.alcance = esc[0] / 2 + 1.1
        self.hp_max = self.hp = d["hp"] * (1 + 0.12 * (S.oleada - 1))
        self.vel = d["vel"] * random.uniform(0.9, 1.1)
        self.dano = d["dano"]
        self.ranged = d["ranged"]
        self.dispara = d["dispara"]
        self.color_base = d["color"]
        self.cd_ataque = 0
        self.cd_disparo = random.uniform(1, 2.5)
        self.flash = 0
        self.lado = random.choice([-1, 1])
        self.muerto = False
        self.quema_t = 0
        self.quema_dps = 0
        self.quema_fx = 0
        self.aturdido = 0

        self.cuerpo = _entity_factory(
            parent=self,
            model="cube",
            color=self.color_base,
            scale=esc,
            y=esc[1] / 2,
            collider="box",
        )
        self.cuerpo.enemigo = self
        for sx in (-0.22, 0.22):
            _entity_factory(
                parent=self.cuerpo,
                model="cube",
                color=color.white,
                scale=(0.18, 0.1, 0.1),
                position=(sx, 0.3, 0.5),
            )

        self.barra_bg = _entity_factory(
            parent=self,
            model="quad",
            color=color.black,
            scale=(max(1.2, esc[0]), 0.13),
            y=esc[1] + 0.5,
            billboard=True,
        )
        self.barra = _entity_factory(
            parent=self.barra_bg,
            model="quad",
            color=color.lime,
            origin=(-0.5, 0),
            x=-0.5,
            z=-0.01,
            scale=(1, 0.7),
        )
        self._vis_timer = random.uniform(0, VISIBILIDAD_INTERVALO)
        self._actualizar_visibilidad()

    def _actualizar_visibilidad(self):
        visible = esta_en_vista(self.world_position + Vec3(0, self.alto * 0.5, 0))
        if self.cuerpo.enabled != visible:
            self.cuerpo.enabled = visible
        if self.barra_bg.enabled != visible:
            self.barra_bg.enabled = visible

    def recibir_dano(self, d, flash=True):
        if self.muerto:
            return
        self.hp -= d
        ratio = clamp(self.hp / max(self.hp_max, 1), 0.0001, 1.0)
        self.barra.scale_x = ratio
        self.barra.color = color.red if ratio < 0.35 else color.lime
        if flash:
            self.cuerpo.color = color.white
            self.flash = 0.08
        if self.hp <= 0:
            self.morir()

    def morir(self):
        self.muerto = True
        d = TIPOS[self.tipo]
        particulas(
            self.world_position + Vec3(0, self.alto / 2, 0),
            self.color_base,
            n=18 if self.tipo == "jefe" else 8,
            vel=2.5,
        )
        S.combo += 1
        S.combo_t = 4
        pts = int(d["puntos"] * mult_combo())
        ganar(pts)
        if S.combo >= 3:
            aviso(f"¡Combo x{S.combo}! +{pts} puntos", 1.5, color.orange)
        S.muertes += 1
        if S.perks["robo"] > 0:
            S.salud = min(S.salud_max, S.salud + 2 * S.perks["robo"])
        if self.tipo == "jefe":
            for _ in range(3):
                botin(self.world_position, True)
        else:
            botin(self.world_position)
        if self in enemigos:
            enemigos.remove(self)
        destroy(self)

    def actualizar(self, dt):
        self._vis_timer -= dt
        if self._vis_timer <= 0:
            self._actualizar_visibilidad()
            self._vis_timer = VISIBILIDAD_INTERVALO

        if self.flash > 0:
            self.flash -= dt
            if self.flash <= 0:
                self.cuerpo.color = self.color_base

        # --- quemadura ---
        if self.quema_t > 0:
            self.quema_t -= dt
            self.recibir_dano(self.quema_dps * dt, flash=False)
            if self.muerto:
                return
            self.quema_fx -= dt
            if self.quema_fx <= 0:
                self.quema_fx = 0.25
                particulas(
                    self.world_position + Vec3(0, self.alto, 0),
                    color.orange,
                    n=1,
                    vel=0.7,
                )

        # --- aturdido (onda de choque) ---
        if self.aturdido > 0:
            self.aturdido -= dt
            return

        dx, dz = jugador.x - self.x, jugador.z - self.z
        dist = max(math.hypot(dx, dz), 0.001)
        dirx, dirz = dx / dist, dz / dist
        self.rotation_y = math.degrees(math.atan2(dx, dz))

        if self.ranged:
            if dist > 16:
                mx, mz = dirx, dirz
            elif dist < 9:
                mx, mz = -dirx, -dirz
            else:
                mx, mz = -dirz * self.lado, dirx * self.lado
        else:
            mx, mz = (dirx, dirz) if dist > self.alcance * 0.8 else (0, 0)

        for ox, oz, orad, _h in obstaculos:
            ddx, ddz = self.x - ox, self.z - oz
            dd = max(math.hypot(ddx, ddz), 0.001)
            if dd < orad + self.radio + 0.8:
                nx, nz = ddx / dd, ddz / dd
                hacia = mx * nx + mz * nz
                if hacia < 0:
                    tx, tz = -nz, nx
                    s = tx * mx + tz * mz
                    signo = self.lado if abs(s) < 0.15 else (1 if s > 0 else -1)
                    mx = mx - hacia * nx + tx * signo * abs(hacia)
                    mz = mz - hacia * nz + tz * signo * abs(hacia)

        self.x += mx * self.vel * dt
        self.z += mz * self.vel * dt

        for ox, oz, orad, _h in obstaculos:
            ddx, ddz = self.x - ox, self.z - oz
            dd = max(math.hypot(ddx, ddz), 0.001)
            lim = orad + self.radio
            if dd < lim:
                self.x = ox + ddx / dd * lim
                self.z = oz + ddz / dd * lim
        # Solo se comparan enemigos de celdas cercanas, no toda la horda.
        for o in vecinos_enemigos(self):
            if o is self or o.muerto:
                continue
            ddx, ddz = self.x - o.x, self.z - o.z
            d2 = ddx * ddx + ddz * ddz
            lim = self.radio + o.radio
            if 0.0001 < d2 < lim * lim:
                dd = math.sqrt(d2)
                empuje = (lim - dd) * 0.5
                self.x += ddx / dd * empuje
                self.z += ddz / dd * empuje
        self.x = clamp(self.x, -ARENA + 2, ARENA - 2)
        self.z = clamp(self.z, -ARENA + 2, ARENA - 2)

        self.cd_ataque -= dt
        if (
            not self.ranged
            and dist < self.alcance
            and jugador.y < self.alto - 0.3
            and self.cd_ataque <= 0
        ):
            self.cd_ataque = 1.0
            herir(self.dano)

        if self.dispara:
            self.cd_disparo -= dt
            if self.cd_disparo <= 0 and dist < 40:
                self.cd_disparo = (
                    2.2 if self.tipo == "jefe" else random.uniform(1.8, 2.8)
                )
                origen = self.world_position + Vec3(0, self.alto * 0.7, 0)
                objetivo = jugador.world_position + Vec3(0, 1.2, 0)
                base = (objetivo - origen).normalized()
                n = 3 if self.tipo == "jefe" else 1
                for k in range(n):
                    ang = (k - (n - 1) / 2) * 0.2
                    v = Vec3(
                        base.x * math.cos(ang) - base.z * math.sin(ang),
                        base.y,
                        base.x * math.sin(ang) + base.z * math.cos(ang),
                    )
                    proyectiles.append(
                        Proyectil(
                            origen, v.normalized(), 15 if self.tipo == "jefe" else 12
                        )
                    )


class Proyectil(Entity):
    def __init__(self, pos, direccion, dano):
        _entity_init: Any = super().__init__
        _entity_init(model="sphere", color=color.cyan, scale=0.45, position=pos)
        self.direccion = direccion
        self.dano = dano
        self.vida = 5


class Recogible(Entity):
    def __init__(self, tipo, pos):
        modelo, col = {
            "salud": ("sphere", color.lime),
            "municion": ("cube", color.gold),
            "dano": ("cube", color.magenta),
        }[tipo]
        _entity_init: Any = super().__init__
        _entity_init(model=modelo, color=col, scale=0.6, position=Vec3(pos.x, 1, pos.z))
        if tipo == "dano":
            self.rotation_x = 45
            self.rotation_z = 45
        self.tipo = tipo
        self.vida = 22
        self.fase = random.uniform(0, 6.28)


class Dron(Entity):
    """Dron de combate que orbita al jugador y dispara al enemigo mas cercano."""

    def __init__(self, idx):
        _entity_init: Any = super().__init__
        _entity_init(
            model="sphere", color=color.cyan, scale=0.4, position=jugador.world_position
        )
        _entity_factory(
            parent=self, model="cube", color=color.black, scale=(0.5, 0.5, 1.6), z=0.6
        )
        self.idx = idx
        self.ang = idx * 2.1
        self.cd = random.uniform(0, 0.8)

    def actualizar(self, dt):
        self.ang += dt * 1.6
        obj = jugador.world_position + Vec3(
            math.cos(self.ang) * 2.4,
            2.6 + math.sin(S.t * 2 + self.idx) * 0.2,
            math.sin(self.ang) * 2.4,
        )
        self.position += (obj - self.position) * min(1, 8 * dt)
        self.cd -= dt
        if self.cd <= 0 and enemigos:
            objetivo = mas_cercano(self.position, 25)
            if objetivo:
                self.cd = 0.8
                centro = objetivo.world_position + Vec3(0, objetivo.alto * 0.6, 0)
                self.look_at(centro)
                rayo(self.position, centro, color.cyan, 0.05)
                danar_auto(objetivo, 10)


class Torreta(Entity):
    """Torreta desplegable que dispara automaticamente durante un tiempo."""

    def __init__(self, pos, niv):
        super().__init__(position=Vec3(pos.x, 0, pos.z))
        _entity_factory(
            parent=self,
            model="cube",
            color=color.dark_gray,
            scale=(1.2, 0.5, 1.2),
            y=0.25,
        )
        self.cabeza = _entity_factory(
            parent=self, model="sphere", color=color.orange, scale=0.8, y=0.9
        )
        _entity_factory(
            parent=self.cabeza,
            model="cube",
            color=color.black,
            scale=(0.25, 0.25, 1.3),
            z=0.8,
        )
        self.dano = 14 * (1 + 0.35 * niv)
        self.cadencia = 0.5 * (0.88**niv)
        self.vida = self.vida_max = 25 + 5 * niv
        self.cd = 0.3
        self.sonido_activo = False
        self.sonido = cargar_audio(("torreta.wav", "turret.wav"), 0.30, loop=True)
        bg = _entity_factory(
            parent=self,
            model="quad",
            color=color.black,
            scale=(1.2, 0.12),
            y=2,
            billboard=True,
        )
        self.barra = _entity_factory(
            parent=bg,
            model="quad",
            color=color.orange,
            origin=(-0.5, 0),
            x=-0.5,
            z=-0.01,
            scale=(1, 0.7),
        )

    def quitar(self):
        detener_audio(self.sonido)
        self.sonido_activo = False
        if self in torretas:
            torretas.remove(self)
        destroy(self)

    def actualizar(self, dt):
        self.vida -= dt
        if self.vida <= 0:
            particulas(self.position + Vec3(0, 1, 0), color.orange, n=10)
            self.quitar()
            return
        self.barra.scale_x = clamp(self.vida / max(self.vida_max, 1), 0.0001, 1.0)
        self.cd -= dt
        objetivo = mas_cercano(self.position, 30)
        if objetivo:
            if not self.sonido_activo:
                reproducir_audio(self.sonido)
                self.sonido_activo = True
            self.cabeza.rotation_y = math.degrees(
                math.atan2(objetivo.x - self.x, objetivo.z - self.z)
            )
            if self.cd <= 0:
                self.cd = self.cadencia
                origen = self.cabeza.world_position + Vec3(0, 0.1, 0)
                centro = objetivo.world_position + Vec3(0, objetivo.alto * 0.6, 0)
                rayo(origen, centro, color.orange, 0.05)
                danar_auto(objetivo, self.dano)
        elif self.sonido_activo:
            detener_audio(self.sonido)
            self.sonido_activo = False


# =====================================================================
#  ARMAS
# =====================================================================
def aplicar_arma():
    a = ARMAS[S.arma]
    arma_modelo.color = a["color"]
    arma_modelo.scale = a["escala"]


def equipar(i):
    if i == S.arma or not S.desbloqueadas[i]:
        return
    S.arma = i
    S.recarga = 0
    aplicar_arma()
    reproducir_audio(SONIDO_CAMBIO)


def siguiente_arma(paso):
    i = S.arma
    for _ in range(len(ARMAS)):
        i = (i + paso) % len(ARMAS)
        if S.desbloqueadas[i]:
            equipar(i)
            return


def recargar():
    if (
        S.recarga > 0
        or S.mag[S.arma] >= stat(S.arma, "cargador")
        or S.reserva[S.arma] <= 0
    ):
        return
    S.recarga = stat(S.arma, "recarga")
    reproducir_audio(SONIDO_RECARGA)


def _v3(v):
    return (v.x, v.y, v.z)


def dispersion_actual(a, ads):
    """Cono base (hip/ADS) x movimiento x bloom de la rafaga."""
    base = a.get("dispersion_ads", a["dispersion"] * 0.4) if ads else a["dispersion"]
    en_mov = _held_keys["w"] or _held_keys["a"] or _held_keys["s"] or _held_keys["d"]
    if not getattr(jugador, "grounded", True):
        mov = 2.0
    elif en_mov and _held_keys["left shift"] and S.puede_correr:
        mov = 1.6
    elif en_mov:
        mov = 1.25
    else:
        mov = 1.0
    return base * mov * bloom.factor


def disparar():
    a = ARMAS[S.arma]
    furia = S.furia_t > 0
    if S.cd > 0 or S.recarga > 0:
        return
    if S.mag[S.arma] <= 0 and not furia:
        if S.reserva[S.arma] > 0:
            recargar()
        else:
            reproducir_audio(SONIDO_SIN_MUNICION)
            aviso("¡Sin municion!", 0.8, color.red)
        return

    if not furia:
        S.mag[S.arma] -= 1

    # El audio se reproduce despues de validar que el disparo es posible.
    reproducir_audio(SONIDOS_ARMAS[S.arma])

    S.cd = stat(S.arma, "cadencia") * (0.5 if furia else 1)
    S.retroceso = 1
    S.fogonazo = 0.05

    # La punteria se fija ANTES de aplicar el retroceso de este disparo.
    ads = bool(_held_keys["right mouse"])
    fwd, right, up = _v3(camera.forward), _v3(camera.right), _v3(camera.up)
    origen = camera.world_position
    disp = dispersion_actual(a, ads)

    # Retroceso vertical + horizontal acumulado (se recupera solo en update()).
    sube, giro = retro.disparar(a["kick_v"], a["kick_h"], a.get("tope", 0.0), a["recup"])
    piv = jugador.camera_pivot
    antes = piv.rotation_x
    piv.rotation_x = max(-85, antes - sube)
    retro.corregir(sube, antes - piv.rotation_x)
    jugador.rotation_y += giro
    bloom.disparo()

    muzzle = arma_modelo.world_position + Vec3(*fwd) * 0.8
    dano_base = stat(S.arma, "dano") * (2 if S.buff_t > 0 else 1)

    for _ in range(a["perdigones"]):
        v = Vec3(*direccion_en_cono(fwd, right, up, disp))
        ign = [jugador]
        fin = origen + v * 100
        impacto = False
        for _p in range(a["penetra"]):
            hit = raycast(origen, v, distance=120, ignore=ign, debug=False)
            if not hit.hit:
                break
            fin = hit.world_point
            impacto = True
            if a["explosion"] > 0:
                break
            en = getattr(hit.entity, "enemigo", None)
            if en:
                cabeza = hit.world_point.y > en.y + en.alto * 0.8
                ign.append(hit.entity)
                golpear(en, dano_base * (2 if cabeza else 1), cabeza)
            else:
                particulas(fin, color.light_gray, n=3, vel=1)
                break
        rayo(muzzle, fin, color.yellow, 0.03)
        if a["explosion"] > 0 and impacto:
            explosion(fin, a["explosion"], dano_base)

    if S.mag[S.arma] <= 0 and S.reserva[S.arma] > 0 and not furia:
        recargar()


# =====================================================================
#  HABILIDADES
# =====================================================================
def usar_dash():
    if S.cdh["dash"] > 0:
        return
    n = S.hab["dash"]
    fx, fz = jugador.forward.x, jugador.forward.z
    rx, rz = jugador.right.x, jugador.right.z
    mx = _held_keys["d"] - _held_keys["a"]
    mz = _held_keys["w"] - _held_keys["s"]
    if mx == 0 and mz == 0:
        mz = 1
    dx, dz = fx * mz + rx * mx, fz * mz + rz * mx
    l = max(math.hypot(dx, dz), 0.001)
    S.dash_dir = (dx / l, dz / l)
    S.dash_t = 0.2 + 0.02 * n
    S.cdh["dash"] = CD_BASE["dash"] * (0.85**n)


def usar_onda():
    if S.cdh["onda"] > 0:
        return
    n = S.hab["onda"]
    radio = 9 + n
    dano = 55 * (1 + 0.3 * n)
    S.cdh["onda"] = CD_BASE["onda"] * (0.85**n)
    c = jugador.world_position
    anillo(c, radio, Vec4(0.3, 0.8, 1, 0.6), 0.45)
    anillo(c, radio * 0.6, Vec4(1, 1, 1, 0.4), 0.3)
    for e in enemigos[:]:
        dx, dz = e.x - c.x, e.z - c.z
        d = max(math.hypot(dx, dz), 0.001)
        if d < radio + e.radio:
            e.aturdido = 1.5
            e.x = clamp(e.x + dx / d * 4, -ARENA + 2, ARENA - 2)
            e.z = clamp(e.z + dz / d * 4, -ARENA + 2, ARENA - 2)
            e.recibir_dano(dano)
    for p in proyectiles[:]:
        if math.hypot(p.x - c.x, p.z - c.z) < radio:
            proyectiles.remove(p)
            destroy(p)


def usar_torreta():
    if S.cdh["torreta"] > 0:
        return
    n = S.hab["torreta"]
    maximo = 1 + n // 2
    hit = raycast(
        camera.world_position,
        camera.forward,
        distance=18,
        ignore=[jugador],
        debug=False,
    )
    p = hit.world_point if hit.hit else camera.world_position + camera.forward * 6
    p = Vec3(clamp(p.x, -ARENA + 3, ARENA - 3), 0, clamp(p.z, -ARENA + 3, ARENA - 3))
    while len(torretas) >= maximo:
        torretas[0].quitar()
    torretas.append(Torreta(p, n))
    S.cdh["torreta"] = CD_BASE["torreta"] * (0.85**n)
    aviso("Torreta desplegada", 1, color.orange)


def usar_furia():
    if S.cdh["furia"] > 0 or S.furia_t > 0:
        return
    n = S.hab["furia"]
    S.furia_t = 8 + 2 * n
    S.cdh["furia"] = CD_BASE["furia"] * (0.85**n)
    aviso("¡MODO FURIA!", 1.5, color.orange)


def sincronizar_drones():
    n = S.perks["dron"]
    while len(drones) < n:
        drones.append(Dron(len(drones)))
    while len(drones) > n:
        destroy(drones.pop())


# =====================================================================
#  TIENDA
# =====================================================================
def comprar_arma(i):
    S.desbloqueadas[i] = True
    equipar(i)


def mejorar_arma(i, c):
    S.niv[i][c] += 1
    if c == "carga":
        S.mag[i] = stat(i, "cargador")


def mejorar_perk(k):
    S.perks[k] += 1
    if k == "vida":
        S.salud_max = 100 + 20 * S.perks["vida"]
        S.salud = min(S.salud_max, S.salud + 20)
    elif k == "dron":
        sincronizar_drones()


def mejorar_hab(k):
    S.hab[k] += 1


def curar_todo():
    S.salud = S.salud_max


def rellenar_municion():
    for i in range(len(ARMAS)):
        S.reserva[i] = reserva_max(i)
        S.mag[i] = stat(i, "cargador")


def item(nombre, nivel, maximo, coste, accion, desc, bloqueado=False, previa=""):
    return dict(
        previa=previa,
        nombre=nombre,
        nivel=nivel,
        maximo=maximo,
        coste=coste,
        accion=accion,
        desc=desc,
        bloqueado=bloqueado,
    )


def previa_mejora(i, c):
    """Texto 'actual -> siguiente nivel' para las mejoras de arma."""
    a, n = ARMAS[i], S.niv[i][c]
    if c == "dano":
        return f"DAÑO {a['dano'] * (1 + .25 * n):.0f} -> +25% {a['dano'] * (1 + .25 * (n + 1)):.0f}"
    if c == "carga":
        sig = max(1, int(round(a["cargador"] * (1 + .25 * (n + 1)))))
        return f"CARGADOR {stat(i, 'cargador')} -> +25% {sig}"
    if c == "cad":
        return f"CADENCIA {a['cadencia'] * .9 ** n:.2f} s -> {a['cadencia'] * .9 ** (n + 1):.2f} s"
    return f"RECARGA {a['recarga'] * .85 ** n:.1f} s -> {a['recarga'] * .85 ** (n + 1):.1f} s"


def construir_items():
    i = S.tienda_arma
    a = ARMAS[i]
    bloq = not S.desbloqueadas[i]
    items = []
    if bloq:
        items.append(
            item(
                f'Comprar {a["nombre"]}',
                0,
                1,
                a["precio"],
                lambda: comprar_arma(i),
                a["desc"],
            )
        )
    else:
        items.append(
            item(f'{a["nombre"]} (tecla {i + 1})', None, None, None, None, a["desc"])
        )
    for clave, nombre, base, desc in MEJORAS_ARMA:
        n = S.niv[i][clave]
        items.append(
            item(
                nombre,
                n,
                5,
                base * (n + 1),
                lambda c=clave: mejorar_arma(i, c),
                desc,
                bloq,
            )
        )

    perks = [
        ("vida", "Vida maxima", 150, 5, "+20 de vida maxima por nivel (y cura 20)."),
        ("vel", "Velocidad", 150, 4, "+8% de velocidad al andar y correr por nivel."),
        (
            "fuego",
            "Municion incendiaria",
            300,
            3,
            "Tus balas, torretas y drones queman al enemigo.",
        ),
        ("robo", "Robo de vida", 250, 3, "Recuperas 2 de vida por baja y por nivel."),
        ("dron", "Dron de combate", 350, 3, "Un dron mas que orbita y dispara solo."),
    ]
    for k, nombre, base, mx, desc in perks:
        n = S.perks[k]
        items.append(
            item(nombre, n, mx, base * (n + 1), lambda k=k: mejorar_perk(k), desc)
        )

    habs = [
        (
            "dash",
            "Dash (Q)",
            200,
            3,
            "Menos enfriamiento, mas distancia y mas tiempo invulnerable.",
        ),
        (
            "onda",
            "Onda de choque (E)",
            250,
            3,
            "Mas dano, mas radio y menos enfriamiento.",
        ),
        (
            "torreta",
            "Torreta (F)",
            300,
            4,
            "Mas dano, cadencia, duracion y +1 torreta cada 2 niveles.",
        ),
        ("furia", "Modo furia (C)", 300, 3, "Mas duracion y menos enfriamiento."),
    ]
    for k, nombre, base, mx, desc in habs:
        n = S.hab[k]
        items.append(
            item(nombre, n, mx, base * (n + 1), lambda k=k: mejorar_hab(k), desc)
        )

    items.append(
        item("Curacion completa", None, None, 100, curar_todo, "Restaura toda tu vida.")
    )
    items.append(
        item(
            "Municion completa",
            None,
            None,
            150,
            rellenar_municion,
            "Rellena cargadores y reservas de todas las armas.",
        )
    )
    items[0]["previa"] = f"DAÑO {stat(i, 'dano'):.0f} · CADENCIA {stat(i, 'cadencia'):.2f} s"
    for it_, (clave, *_r) in zip(items[1:5], MEJORAS_ARMA):
        it_["previa"] = previa_mejora(i, clave)
    return items


def estado_item(it):
    if it["accion"] is None:
        return "info"
    if it["maximo"] and it["nivel"] is not None and it["nivel"] >= it["maximo"]:
        return "max"
    if it["bloqueado"]:
        return "bloq"
    if S.creditos < it["coste"]:
        return "falta"
    return "ok"


def refrescar_tienda():
    ITEMS[:] = construir_items()
    poner(txt_tienda_cred, f"$ {fmt(S.creditos)}")
    poner(txt_tienda_sub, f"ENTRE OLEADAS · SIGUIENTE EN {int(max(S.intermedio, 0)) + 1} s")
    lo, hi = RANGOS[S.tienda_tab]
    S.tienda_sel = max(lo, min(hi - 1, S.tienda_sel))

    for k, (e, t) in enumerate(tab_ents):
        activo = k == S.tienda_tab
        e.color = ORO if activo else COL_TAB
        t.color = color.black if activo else color.white

    strip.enabled = S.tienda_tab == 0
    if S.tienda_tab == 0:
        for i, (brd, ts) in enumerate(cards):
            brd.color = ORO if i == S.tienda_arma else BORDE
            precio = ARMAS[i]["precio"]
            if S.desbloqueadas[i]:
                poner(ts, "EQUIPADA" if i == S.arma else "Disponible")
                ts.color = VERDE if i == S.arma else GRIS
            else:
                poner(ts, f"Bloqueada · ${precio}")
                ts.color = ORO if S.creditos >= precio else GRIS

    y0 = 0.13 if S.tienda_tab == 0 else 0.235
    for k, f in enumerate(filas):
        idx = lo + k
        if idx >= hi:
            f.enabled = False
            continue
        f.enabled = True
        f.y = y0 - k * 0.097
        it = ITEMS[idx]
        est = estado_item(it)
        f.brd.color = ORO if idx == S.tienda_sel else BORDE
        poner(f.t_nombre, it["nombre"])
        poner(f.t_desc, it["desc"])
        poner(f.t_prev, it["previa"])
        f.t_prev.color = VERDE if it["previa"].startswith(("DAÑO", "CARG", "CADE", "RECA")) and "->" in it["previa"] else GRIS
        # pips de nivel
        compra = it["nombre"].startswith("Comprar")
        mostrar = it["maximo"] and it["nivel"] is not None and not compra and est != "info"
        for j, p in enumerate(f.pips):
            p.enabled = bool(mostrar) and j < it["maximo"]
            if p.enabled:
                p.color = VERDE if j < it["nivel"] else BORDE
        # boton de compra
        f.btn.enabled = f.t_btn.enabled = est != "info"
        if est == "ok":
            c = it["coste"]
            txt = f"Comprar · ${c}" if compra else (f"Mejorar · ${c}" if it["nivel"] is not None else f"${c}")
            f.btn.color, f.t_btn.color = ORO, color.black
        elif est == "falta":
            txt = f"Faltan ${it['coste'] - S.creditos} · ${it['coste']}"
            f.btn.color, f.t_btn.color = COL_TAB, GRIS
        elif est == "max":
            txt = "NIVEL MÁXIMO"
            f.btn.color, f.t_btn.color = rgb255(30, 62, 46), VERDE
        else:
            txt = "Bloqueada"
            f.btn.color, f.t_btn.color = COL_TAB, GRIS
        poner(f.t_btn, txt)


def elegir_tab(k):
    S.tienda_tab = k % len(TABS)
    S.tienda_sel = RANGOS[S.tienda_tab][0]
    refrescar_tienda()


def elegir_arma_tienda(i):
    S.tienda_arma = i % len(ARMAS)
    if S.tienda_tab == 0:
        S.tienda_sel = 0
    refrescar_tienda()


def mover_sel(paso):
    lo, hi = RANGOS[S.tienda_tab]
    S.tienda_sel = lo + (S.tienda_sel - lo + paso) % (hi - lo)
    refrescar_tienda()


def click_fila(k):
    S.tienda_sel = RANGOS[S.tienda_tab][0] + k
    refrescar_tienda()


def comprar_fila(k):
    S.tienda_sel = RANGOS[S.tienda_tab][0] + k
    comprar_seleccion()


def iniciar_desde_tienda():
    cerrar_tienda()
    S.intermedio = 0.01


def actualizar_tienda(dt):
    """Cuenta atras viva dentro de la tienda (TIENDA_CONTADOR)."""
    if not TIENDA_CONTADOR:
        return
    S.intermedio -= dt
    if S.intermedio <= 0:
        iniciar_desde_tienda()
        return
    poner(txt_tienda_sub, f"ENTRE OLEADAS · SIGUIENTE EN {int(S.intermedio) + 1} s")


def msg_tienda(s):
    poner(txt_tienda_msg, s)


def comprar_seleccion():
    it = ITEMS[S.tienda_sel]
    if it["accion"] is None:
        msg_tienda("Nada que comprar aqui")
    elif it["bloqueado"]:
        msg_tienda("Primero compra esta arma")
    elif it["maximo"] and it["nivel"] >= it["maximo"]:
        msg_tienda("Ya esta al maximo")
    elif S.creditos < it["coste"]:
        msg_tienda("Creditos insuficientes")
    else:
        S.creditos -= it["coste"]
        it["accion"]()
        msg_tienda("¡Comprado!")
    refrescar_tienda()


def abrir_tienda():
    S.estado = "tienda"
    S.tienda_arma = S.arma
    S.tienda_tab = 0
    S.tienda_sel = 0
    ocultar_mira()
    jugador.enabled = False
    mouse.visible = True
    mouse.locked = False
    camera.fov = 90
    hud.enabled = False
    ui_tienda.enabled = True
    msg_tienda("")
    refrescar_tienda()


def cerrar_tienda():
    S.estado = "jugando"
    jugador.enabled = True
    mouse.locked = True
    hud.enabled = True
    ui_tienda.enabled = False
    aplicar_arma()


# =====================================================================
#  OLEADAS
# =====================================================================
def componer_oleada(n):
    total = min(4 + n * 3, 40)
    pesos = {"normal": 10, "rapido": 0, "tirador": 0, "tanque": 0}
    if n >= 2:
        pesos["rapido"] = 4
    if n >= 3:
        pesos["tirador"] = 3
    if n >= 4:
        pesos["tanque"] = 2
    lista = random.choices(list(pesos), weights=list(pesos.values()), k=total)
    if n % 5 == 0:
        lista.append("jefe")
    return lista


def iniciar_oleada():
    S.oleada += 1
    S.cola = componer_oleada(S.oleada)
    S.enemigos_oleada_total = len(S.cola)
    S.spawn_t = 1.5
    if S.oleada % 5 == 0:
        aviso(f"¡¡JEFE!!  Oleada {S.oleada}", 3, color.red)
    else:
        aviso(f"OLEADA {S.oleada}", 2.5, color.white)


def actualizar_oleadas(dt):
    if S.intermedio > 0:
        S.intermedio -= dt
        if S.intermedio <= 0:
            iniciar_oleada()
        return

    if S.cola:
        S.spawn_t -= dt
        # Mantiene una horda activa acotada: cada enemigo tiene varias
        # entidades visuales y actualiza IA/colisiones en cada frame.
        # El total de enemigos de la oleada sigue creciendo por separado.
        max_sim = min(12, 5 + S.oleada)
        if S.spawn_t <= 0 and len(enemigos) < max_sim:
            tipo = S.cola.pop(0)
            e = Enemigo(tipo, pos_spawn())
            enemigos.append(e)
            particulas(e.world_position + Vec3(0, 1, 0), e.color_base, n=6)
            S.spawn_t = max(0.45, 1.5 - 0.06 * S.oleada)
    elif not enemigos:
        bono = 100 * S.oleada
        ganar(bono)
        aviso(f"¡Oleada {S.oleada} superada!  +{bono}", 3, color.lime)
        S.intermedio = INTERMEDIO
        S.salud = min(S.salud_max, S.salud + 15)
        agregar_municion(0.5)
        for _ in range(2):
            botin(Vec3(random.uniform(-15, 15), 0, random.uniform(-15, 15)), True)


# =====================================================================
#  ESTADOS DEL JUEGO
# =====================================================================
def detener_audio_torretas():
    """Detiene el audio de todas las torretas antes de limpiar o cambiar de estado."""
    for torreta in torretas[:]:
        detener_audio(torreta.sonido)
        torreta.sonido_activo = False


def iniciar():
    global _radar_timer, _hud_timer
    detener_audio_torretas()
    _radar_timer = 0.0
    _hud_timer = 0.0
    for activos in EFECTOS_ACTIVOS.values():
        for entidad, _fin in activos:
            destroy(entidad)
        activos.clear()
    for lista in (enemigos, proyectiles, recogibles, torretas, drones):
        for e in lista:
            destroy(e)
        lista.clear()
    vars(S).update(nuevo_estado(S.record))
    retro.reiniciar()
    bloom.reiniciar()
    _heading_ult[0] = None
    ocultar_mira()
    aplicar_arma()
    camera.fov = 90
    jugador.position = Vec3(0, 1, 0)
    jugador.rotation_y = 0
    jugador.camera_pivot.rotation_x = 0
    jugador.enabled = True
    mouse.locked = True
    ui_menu.enabled = False
    ui_fin.enabled = False
    ui_pausa.enabled = False
    ui_tienda.enabled = False
    hud.enabled = True
    box_aviso.enabled = False
    poner(txt_aviso, "")
    S.estado = "jugando"
    iniciar_oleada()


def pausar():
    detener_audio_torretas()
    ocultar_mira()
    S.estado = "pausa"
    jugador.enabled = False
    mouse.visible = True
    mouse.locked = False
    camera.fov = 90
    ui_pausa.enabled = True


def reanudar():
    S.estado = "jugando"
    jugador.enabled = True
    mouse.locked = True
    ui_pausa.enabled = False


def terminar():
    detener_audio_torretas()
    ocultar_mira()
    S.estado = "fin"
    nuevo = S.puntos > S.record
    if nuevo:
        S.record = S.puntos
        guardar_record(S.record)
    jugador.enabled = False
    mouse.visible = True
    mouse.locked = False
    camera.fov = 90
    hud.enabled = False
    ui_fin.enabled = True
    poner(
        txt_fin_stats,
        f"Llegaste a la oleada {S.oleada}\n"
        f"Puntos: {S.puntos}     Bajas: {S.muertes}\n\n"
        + ("¡NUEVO RECORD!" if nuevo else f"Record: {S.record}"),
    )


def recoger(r):
    if r.tipo == "salud":
        S.salud = min(S.salud_max, S.salud + 35)
        aviso("+35 Vida", 1, color.lime)
    elif r.tipo == "municion":
        agregar_municion(1)
        aviso("+ Municion", 1, color.gold)
    else:
        S.buff_t = 12
        aviso("¡DANO DOBLE!", 1.5, color.magenta)
    particulas(r.position, r.color, n=8)
    recogibles.remove(r)
    destroy(r)


# =====================================================================
#  BUCLE PRINCIPAL
# =====================================================================
def actualizar_radar():
    th = math.radians(jugador.rotation_y)
    c, s = math.cos(th), math.sin(th)
    for i, e in enumerate(enemigos):
        if i >= len(puntos_radar):
            puntos_radar.append(
                _entity_factory(parent=radar, model="circle", scale=0.05, z=-0.01)
            )
        dx, dz = e.x - jugador.x, e.z - jugador.z
        rx = dx * c - dz * s
        ry = dx * s + dz * c
        l = math.hypot(rx, ry)
        k = 1 if l < RADAR_RANGE else RADAR_RANGE / l
        p = puntos_radar[i]
        p.position = (rx * k / RADAR_RANGE * 0.48, ry * k / RADAR_RANGE * 0.48, -0.01)
        p.color = TIPOS[e.tipo]["color"]
        p.enabled = True
    for p in puntos_radar[len(enemigos) :]:
        p.enabled = False


def actualizar_hud(dt):
    a = ARMAS[S.arma]
    poner(txt_oleada, f"OLEADA {S.oleada}")
    poner(txt_record, f"RÉCORD {fmt(max(S.record, S.puntos))}")
    poner(txt_puntos, f"Puntos {fmt(S.puntos)}")
    poner(txt_cred, f"$ {fmt(S.creditos)}")

    total_en = len(enemigos) + len(S.cola)
    if S.intermedio > 0:
        poner(txt_enemigos, "PREPARACIÓN")
        poner(txt_hint, f"{int(S.intermedio) + 1} s · B tienda")
        barra_enemigos.scale_x = 0.0001
    else:
        max_en = max(getattr(S, "enemigos_oleada_total", total_en), total_en, 1)
        poner(txt_enemigos, "ENEMIGOS")
        poner(txt_hint, f"{total_en} / {max_en}")
        barra_enemigos.scale_x = clamp(total_en / max_en, 0.0001, 1.0)

    combo_activo = S.combo > 1
    if box_combo.enabled != combo_activo:
        box_combo.enabled = combo_activo
    poner(txt_combo, f"COMBO  x{mult_combo():.1f}" if combo_activo else "")
    poner(txt_buff, f"DANO x2  {int(S.buff_t) + 1}s" if S.buff_t > 0 else "")
    txt_buff.color = color.magenta if S.buff_t > 0 else GRIS

    # --- vida ---
    salud_max = max(S.salud_max, 1)
    smax_txt = f"/ {S.salud_max}"
    poner(txt_vida_max, smax_txt)
    poner(txt_vida_n, f"{int(S.salud)}")
    txt_vida_n.x = X_VIDA_R - ancho(smax_txt, 0.85) - 0.012
    txt_vida_n.color = ROJO_H if S.salud < salud_max * 0.3 else color.white
    proporcion_vida = clamp(S.salud / salud_max, 0.0001, 1.0)
    barra_vida.scale_x = proporcion_vida
    barra_vida.color = ROJO_H if proporcion_vida <= 0.30 else (NARANJA_H if proporcion_vida <= 0.60 else VERDE)
    barra_stamina.scale_x = clamp(S.stamina / 100.0, 0.0001, 1.0)

    # --- municion ---
    cargador = stat(S.arma, "cargador")
    mag = S.mag[S.arma]
    furia = S.furia_t > 0
    max_txt = f"/ {cargador}"
    poner(txt_arma_tipo, f'{a["nombre"].upper()} · {"AUTO" if a["auto"] else "SEMI"}')
    poner(txt_mag, "INF" if furia else str(mag))
    poner(txt_mag_max, max_txt)
    txt_mag.x = X_R - ancho(max_txt, 1.3) - 0.01
    baja = (not furia) and mag <= max(1, cargador * 0.25)
    txt_mag.color = ROJO_H if baja else color.white
    if S.recarga > 0:
        msg_baja, col_baja = "RECARGANDO", NARANJA_H
    elif baja and S.reserva[S.arma] <= 0 and mag <= 0:
        msg_baja, col_baja = "SIN MUNICIÓN", ROJO_H
    elif baja:
        msg_baja, col_baja = "MUNICIÓN BAJA", ROJO_H
    else:
        msg_baja, col_baja = "", ROJO_H
    poner(txt_baja, (msg_baja + " ·") if msg_baja else "")
    txt_baja.color = col_baja
    txt_baja.x = X_BAJA_R
    poner(txt_reserva, f"Reserva {S.reserva[S.arma]} ·")
    txt_reserva.x = (X_BAJA_R - ancho(msg_baja + " ·", 0.8) - 0.012) if msg_baja else X_BAJA_R

    for idx, ui in slots_arma.items():
        activo = idx == S.arma
        libre = S.desbloqueadas[idx]
        ui["brd"].color = ORO if activo else BORDE
        poner(ui["nom"], (CORTO[idx] if idx < len(CORTO) else ARMAS[idx]["nombre"]) if libre else f'${ARMAS[idx]["precio"]}')
        ui["nom"].color = color.white if activo else (GRIS if libre else rgb255(90, 98, 112))

    # --- habilidades: anillo de progreso ---
    for k, (tecla, nombre) in HABS.items():
        ui = hab_ui[k]
        cd = S.cdh[k]
        CD_TOT[k] = max(CD_TOT[k], cd)
        if k == "furia" and S.furia_t > 0:
            frac = S.furia_t / (8 + 2 * S.hab["furia"])
            s_, tcol, col = f"{int(S.furia_t) + 1}", NARANJA_H, NARANJA_H
        elif cd > 0:
            frac = 1 - cd / max(CD_TOT[k], 0.01)
            s_, tcol, col = f"{int(cd) + 1}", GRIS, HAB_COL[k]
        else:
            frac, s_, tcol, col = 1.0, HAB_NOM[k], color.white, HAB_COL[k]
            CD_TOT[k] = 0.0
        n = int(round(frac * 48))
        if n != ui["n"]:
            m = malla_arco(frac)
            ui["n"] = n
            ui["arco"].enabled = m is not None
            if m is not None:
                ui["arco"].model = m
        ui["arco"].color = col
        poner(ui["txt"], s_)
        ui["txt"].color = tcol

    if S.aviso_t > 0:
        S.aviso_t = max(0, S.aviso_t - dt)
        box_aviso.enabled = S.aviso_t > 0
        if S.aviso_t == 0:
            poner(txt_aviso, "")
    else:
        box_aviso.enabled = False

    S.hit_t = max(0, S.hit_t - dt)
    visible = S.hit_t > 0
    if hitmarker.enabled != visible:
        hitmarker.enabled = visible
    if visible:
        hitmarker.color = color.red if S.hit_cab else color.white

    S.dano_alpha = max(0, S.dano_alpha - dt * 1.5)
    extra = 0.12 if S.salud < salud_max * 0.3 else 0
    overlay_dano.color = Vec4(1, 0, 0, clamp(S.dano_alpha + extra, 0, 1))

    S.fogonazo = max(0, S.fogonazo - dt)
    f = S.fogonazo > 0
    if fogonazo.enabled != f:
        fogonazo.enabled = f


def update():
    dt = min(float(getattr(_ursina_time, "dt", 0.0)), 0.05)
    if S.estado == "tienda":
        actualizar_tienda(dt)
        return
    if S.estado != "jugando":
        return
    S.t += dt

    global _obstaculos_timer
    _obstaculos_timer -= dt
    if _obstaculos_timer <= 0:
        actualizar_obstaculos_visibles()
        _obstaculos_timer = 0.20

    # --- correr / energia ---
    moviendo = _held_keys["w"] or _held_keys["a"] or _held_keys["s"] or _held_keys["d"]
    correr = _held_keys["left shift"] and moviendo and S.puede_correr
    if correr:
        S.stamina -= 28 * dt
        if S.stamina <= 0:
            S.stamina = 0
            S.puede_correr = False
    else:
        S.stamina = min(100, S.stamina + 18 * dt)
        if S.stamina > 25:
            S.puede_correr = True
    factor_vel = 1 + 0.08 * S.perks["vel"]
    setattr(jugador, "speed", (9 if correr else 5.5) * factor_vel)

    # --- temporizadores ---
    S.buff_t = max(0, S.buff_t - dt)
    S.furia_t = max(0, S.furia_t - dt)
    for k in S.cdh:
        S.cdh[k] = max(0, S.cdh[k] - dt)
    if S.combo_t > 0:
        S.combo_t -= dt
        if S.combo_t <= 0:
            S.combo = 0

    # --- dash ---
    if S.dash_t > 0:
        S.dash_t -= dt
        v = 30 * (1 + 0.15 * S.hab["dash"])
        nx = jugador.x + S.dash_dir[0] * v * dt
        nz = jugador.z + S.dash_dir[1] * v * dt
        libre = (
            abs(nx) < ARENA - 1.5
            and abs(nz) < ARENA - 1.5
            and not any(
                math.hypot(nx - ox, nz - oz) < orad + 0.7
                for ox, oz, orad, _h in obstaculos
            )
        )
        if libre:
            jugador.x, jugador.z = nx, nz
        S.dash_fx_t -= dt
        if S.dash_fx_t <= 0:
            particulas(jugador.world_position + Vec3(0, 1, 0), color.cyan, n=1, vel=0.5)
            S.dash_fx_t = 0.08

    # --- zoom al apuntar ---
    ads = bool(_held_keys["right mouse"])
    objetivo_fov = ARMAS[S.arma]["fov_ads"] if ads else 90
    camera.fov = lerp(camera.fov, objetivo_fov, min(1, 12 * dt))
    if _sens_base is not None:      # sensibilidad proporcional al zoom
        jugador.mouse_sensitivity = _sens_base * (camera.fov / 90) ** 0.9

    # --- arma ---
    S.cd = max(0, S.cd - dt)
    if S.recarga > 0:
        S.recarga -= dt
        if S.recarga <= 0:
            n = min(stat(S.arma, "cargador") - S.mag[S.arma], S.reserva[S.arma])
            S.mag[S.arma] += n
            S.reserva[S.arma] -= n
    if _held_keys["left mouse"] and ARMAS[S.arma]["auto"]:
        disparar()
    S.retroceso = max(0, S.retroceso - dt * 9)

    # --- recuperacion del retroceso y bloom: solo se devuelve lo acumulado ---
    rdx, rdy = retro.recuperar(dt)
    if rdx or rdy:
        piv = jugador.camera_pivot
        piv.rotation_x = max(-85, min(85, piv.rotation_x + rdx))
        jugador.rotation_y -= rdy
    bloom.actualizar(dt)
    actualizar_mira(ads, ARMAS[S.arma])
    actualizar_brujula()
    arma_modelo.z = 0.9 - 0.12 * S.retroceso
    objetivo_rot = 50 if S.recarga > 0 else 0
    arma_modelo.rotation_x = lerp(arma_modelo.rotation_x, objetivo_rot, min(1, 12 * dt))

    # --- oleadas y enemigos ---
    actualizar_oleadas(dt)
    construir_grid_enemigos()
    for e in enemigos[:]:
        if not e.muerto:
            e.actualizar(dt)
        if S.estado != "jugando":
            return

    # --- armas automaticas ---
    for d in drones:
        d.actualizar(dt)
    for t in torretas[:]:
        t.actualizar(dt)

    # --- proyectiles enemigos ---
    centro = jugador.world_position + Vec3(0, 1, 0)
    for p in proyectiles[:]:
        p.position += p.direccion * 14 * dt
        p.vida -= dt
        quitar = p.vida <= 0 or abs(p.x) > ARENA or abs(p.z) > ARENA or p.y < 0
        if not quitar and (p.position - centro).length() < 1.0:
            herir(p.dano)
            quitar = True
        if not quitar:
            for ox, oz, orad, h in obstaculos:
                if p.y < h and math.hypot(p.x - ox, p.z - oz) < orad - 0.2:
                    quitar = True
                    break
        if quitar:
            if p in proyectiles:
                proyectiles.remove(p)
            destroy(p)
        if S.estado != "jugando":
            return

    # --- objetos recogibles ---
    for r in recogibles[:]:
        r.rotation_y += 120 * dt
        r.y = 1 + math.sin(S.t * 3 + r.fase) * 0.2
        r.vida -= dt
        if r.vida < 5:
            r.visible = int(S.t * 8) % 2 == 0
        if r.vida <= 0:
            recogibles.remove(r)
            destroy(r)
        elif math.hypot(r.x - jugador.x, r.z - jugador.z) < 1.6 and jugador.y < 2.5:
            recoger(r)

    limpiar_efectos()

    global _radar_timer, _hud_timer
    _radar_timer -= dt
    _hud_timer -= dt
    if _hud_timer <= 0:
        actualizar_hud(HUD_INTERVALO)
        _hud_timer = HUD_INTERVALO
    if _radar_timer <= 0:
        actualizar_radar()
        _radar_timer = RADAR_INTERVALO


def input(key):
    if S.estado == "menu":
        if key == "enter":
            iniciar()
        elif key == "escape":
            _application.quit()

    elif S.estado == "jugando":
        if key in ("escape", "p"):
            pausar()
        elif key == "left mouse down":
            disparar()
        elif key == "r":
            recargar()
        elif key in ("1", "2", "3", "4", "5"):
            equipar(int(key) - 1)
        elif key == "scroll up":
            siguiente_arma(1)
        elif key == "scroll down":
            siguiente_arma(-1)
        elif key == "q":
            usar_dash()
        elif key == "e":
            usar_onda()
        elif key == "f":
            usar_torreta()
        elif key == "c":
            usar_furia()
        elif key == "b" and S.intermedio > 0:
            abrir_tienda()
        elif key == "enter" and S.intermedio > 0:
            S.intermedio = 0.01

    elif S.estado == "tienda":
        if key in ("w", "up arrow"):
            mover_sel(-1)
        elif key in ("s", "down arrow"):
            mover_sel(1)
        elif key in ("a", "left arrow"):
            elegir_arma_tienda(S.tienda_arma - 1)
        elif key in ("d", "right arrow"):
            elegir_arma_tienda(S.tienda_arma + 1)
        elif key in ("1", "2", "3", "4"):
            elegir_tab(int(key) - 1)
        elif key == "tab":
            elegir_tab(S.tienda_tab + 1)
        elif key == "space":
            comprar_seleccion()
        elif key == "enter":
            iniciar_desde_tienda()
        elif key in ("b", "escape"):
            cerrar_tienda()

    elif S.estado == "pausa":
        if key in ("escape", "p"):
            reanudar()
        elif key == "q":
            _application.quit()

    elif S.estado == "fin":
        if key in ("r", "enter"):
            iniciar()
        elif key == "escape":
            _application.quit()


poner(txt_menu_record, f"Record: {S.record}")
aplicar_arma()


def run():
    _app.run()