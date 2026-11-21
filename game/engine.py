from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from types import SimpleNamespace
from typing import Any
import random
import math

from .config import *
from .audio import *

app = Ursina(title='Cazador de Oleadas v2')
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
        estado='menu', salud=100, salud_max=100, stamina=100, puede_correr=True,
        puntos=0, creditos=0, record=record, oleada=0, cola=[], spawn_t=0, intermedio=0,
        arma=0, desbloqueadas=[True, True, True, False, False],
        niv=[dict(dano=0, carga=0, cad=0, rec=0) for _ in ARMAS],
        mag=[a['cargador'] for a in ARMAS], reserva=[a['reserva_ini'] for a in ARMAS],
        perks=dict(vida=0, vel=0, fuego=0, robo=0, dron=0),
        hab=dict(dash=0, onda=0, torreta=0, furia=0),
        cdh=dict(dash=0, onda=0, torreta=0, furia=0),
        dash_t=0, dash_dir=(0, 1), dash_fx_t=0, furia_t=0,
        tienda_arma=0, tienda_sel=0,
        cd=0, recarga=0, retroceso=0, fogonazo=0, hit_t=0, hit_cab=False,
        combo=0, combo_t=0, muertes=0, dano_alpha=0, buff_t=0, aviso_t=0, t=0,
    )


S = SimpleNamespace()
vars(S).update(nuevo_estado(leer_record()))

enemigos, proyectiles, recogibles, torretas, drones = [], [], [], [], []
ITEMS = []

# Limites de efectos para evitar picos de entidades durante las hordas.
MAX_PARTICULAS = 110
MAX_RAYOS = 28
MAX_ANILLOS = 10
EFECTOS_ACTIVOS = {'particula': [], 'rayo': [], 'anillo': []}
GRID_ENEMIGOS = {}
GRID_CELDA = 6.5
RADAR_INTERVALO = 0.10
HUD_INTERVALO = 0.10

# Culling visual: los modelos fuera del campo de vision o demasiado lejos
# no mantienen sus subentidades/renderers activos. La IA sigue funcionando.
DISTANCIA_RENDER = 58.0
MARGEN_VISION = 14.0
VISIBILIDAD_INTERVALO = 0.12
_radar_timer = 0.0
_hud_timer = 0.0


def esta_en_vista(pos, distancia_max=DISTANCIA_RENDER, margen=MARGEN_VISION):
    # Comprueba de forma barata si una posicion cae cerca del frustum de camara.
    if 'camera' not in globals() or 'jugador' not in globals():
        return True
    origen = camera.world_position
    delta = Vec3(pos.x - origen.x, pos.y - origen.y, pos.z - origen.z)
    distancia2 = delta.x * delta.x + delta.y * delta.y + delta.z * delta.z
    if distancia2 > distancia_max * distancia_max:
        return False
    if distancia2 < .0001:
        return True
    direccion = delta / math.sqrt(distancia2)
    frente = camera.forward
    dot = direccion.x * frente.x + direccion.y * frente.y + direccion.z * frente.z
    fov = float(getattr(camera, 'fov', 90))
    limite = math.cos(math.radians(min(89, fov * .5 + margen)))
    return dot >= limite


def stat(i, k):
    a, n = ARMAS[i], S.niv[i]
    if k == 'dano':
        return a['dano'] * (1 + .25 * n['dano'])
    if k == 'cargador':
        return max(1, int(round(a['cargador'] * (1 + .25 * n['carga']))))
    if k == 'cadencia':
        return a['cadencia'] * (.9 ** n['cad'])
    if k == 'recarga':
        return a['recarga'] * (.85 ** n['rec'])


def reserva_max(i):
    return int(ARMAS[i]['reserva_max'] * (1 + .25 * S.niv[i]['carga']))


# =====================================================================
#  ESCENARIO
# =====================================================================
suelo = _entity_factory(model='plane', scale=ARENA * 2, texture='grass', texture_scale=(40, 40), collider='box')
Sky()

largo = ARENA * 2 + 2
for x, z, sx, sz in ((0, ARENA, largo, 1), (0, -ARENA, largo, 1),
                     (ARENA, 0, 1, largo), (-ARENA, 0, 1, largo)):
    _entity_factory(model='cube', position=(x, 3, z), scale=(sx, 6, sz), color=color.gray,
           texture='brick', texture_scale=(20, 2), collider='box')

obstaculos = []   # (x, z, radio, altura), datos de colision independientes del render
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
    col = color.hsv(random.uniform(180, 260), .25, random.uniform(.45, .75))
    obstaculos.append((x, z, s * .62, h))
    obstaculos_meta.append((s, h, col))

# =====================================================================
#  JUGADOR Y ARMA
# =====================================================================
jugador = FirstPersonController(position=(0, 1, 0))
setattr(jugador, 'speed', 5.5)
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
        visible = esta_en_vista(Vec3(x, obstaculos_meta[i][1] * .5, z), distancia_max=58)
        debe_existir = cerca or visible
        entidad = obstaculos_visibles.get(i)
        if debe_existir and entidad is None:
            escala, alto, col = obstaculos_meta[i]
            obstaculos_visibles[i] = _entity_factory(
                model='cube', position=(x, alto / 2, z), scale=(escala, alto, escala),
                texture='white_cube', color=col, collider='box')
        elif not debe_existir and entidad is not None:
            destroy(entidad)
            del obstaculos_visibles[i]


arma_modelo = _entity_factory(parent=camera, model='cube', position=(.4, -.32, .9),
                     scale=(.1, .14, .5), color=color.dark_gray)
canon = _entity_factory(parent=arma_modelo, model='cube', position=(0, .25, .7), scale=(.6, .4, .7), color=color.black)
fogonazo = _entity_factory(parent=camera, model='quad', position=(.4, -.2, 1.5), scale=.35,
                  color=color.yellow, enabled=False)

# =====================================================================
#  INTERFAZ
# =====================================================================
hud = _entity_factory(parent=camera.ui, enabled=False)
ui_menu = _entity_factory(parent=camera.ui)
ui_pausa = _entity_factory(parent=camera.ui, enabled=False)
ui_fin = _entity_factory(parent=camera.ui, enabled=False)
ui_tienda = _entity_factory(parent=camera.ui, enabled=False)
overlay_dano = _entity_factory(parent=camera.ui, model='quad', scale=(4, 2), color=Vec4(1, 0, 0, 0), z=2)


def texto(txt, pos, esc=1.2, col=color.white, centro=False, padre=None):
    kw = dict(parent=padre if padre else hud, text=txt, position=pos, scale=esc, color=col)
    if centro:
        kw['origin'] = (0, 0)
    t = _text_factory(**kw)
    t._ult = txt
    return t


def poner(t, s):
    if t._ult != s:
        t.text = s
        t._ult = s


def fondo(padre):
    _entity_factory(parent=padre, model='quad', scale=(4, 2), color=Vec4(0, 0, 0, .75), z=1)


# --- menu ---
fondo(ui_menu)
texto('CAZADOR DE OLEADAS', (0, .28), 3, color.orange, True, ui_menu)
texto('Sobrevive a oleadas cada vez mas duras. Cada 5 oleadas llega un JEFE.\n'
      'Gana creditos con cada baja y gastalos en la TIENDA (tecla B entre oleadas).\n\n'
      'WASD moverte  ·  SHIFT correr  ·  ESPACIO saltar  ·  CLIC disparar  ·  CLIC DER apuntar\n'
      'R recargar  ·  1-5 o RUEDA cambiar arma  ·  ESC pausa\n\n'
      'HABILIDADES:  Q Dash   ·   E Onda de choque   ·   F Torreta automatica   ·   C Modo furia\n'
      'Compra DRONES de combate en la tienda para que te ayuden.\n\n'
      'Apunta a la cabeza para hacer el doble de dano.\n'
      'Recoge: verde = vida, dorado = municion, magenta = dano x2.',
      (0, -.02), 1.05, color.white, True, ui_menu)
texto('Pulsa ENTER para jugar', (0, -.36), 2, color.yellow, True, ui_menu)
txt_menu_record = texto('', (0, -.44), 1.1, color.light_gray, True, ui_menu)

# --- pausa ---
fondo(ui_pausa)
texto('PAUSA', (0, .1), 4, color.white, True, ui_pausa)
texto('ESC / P: continuar      Q: salir', (0, -.05), 1.5, color.light_gray, True, ui_pausa)

# --- fin de partida ---
fondo(ui_fin)
texto('HAS MUERTO', (0, .22), 4, color.red, True, ui_fin)
txt_fin_stats = texto('', (0, 0), 1.7, color.white, True, ui_fin)
texto('R / ENTER: jugar otra vez      ESC: salir', (0, -.22), 1.3, color.yellow, True, ui_fin)

# --- tienda ---
fondo(ui_tienda)
txt_tienda_cred = texto('', (0, .46), 1.8, color.gold, True, ui_tienda)
txt_hdr_arma = texto('', (-.86, .38), 1.1, color.orange, False, ui_tienda)
texto('MEJORAS PASIVAS', (-.86, .11), 1.1, color.orange, False, ui_tienda)
texto('HABILIDADES', (.08, .38), 1.1, color.orange, False, ui_tienda)
texto('SUMINISTROS', (.08, .15), 1.1, color.orange, False, ui_tienda)
txt_tienda_desc = texto('', (-.86, -.22), 1.1, color.white, False, ui_tienda)
txt_tienda_msg = texto('', (0, -.34), 1.4, color.yellow, True, ui_tienda)
texto('W/S o flechas: elegir   ENTER/ESPACIO: comprar   A/D: cambiar de arma   B/ESC: cerrar',
      (0, -.44), 1.0, color.light_gray, True, ui_tienda)
POS_FILAS = ([(-.86, .33 - .04 * k) for k in range(5)] + [(-.86, .06 - .04 * k) for k in range(5)]
             + [(.08, .33 - .04 * k) for k in range(4)] + [(.08, .10), (.08, .06)])
filas = [texto('', p, .95, color.white, False, ui_tienda) for p in POS_FILAS]

# --- HUD ---
txt_puntos = texto('', (-.86, .47), 1.4, color.yellow)
txt_record = texto('', (-.86, .43), 1.0, color.light_gray)
txt_cred = texto('', (-.86, .39), 1.3, color.gold)
txt_combo = texto('', (-.86, .35), 1.3, color.orange)
txt_buff = texto('', (-.86, .31), 1.1, color.magenta)
txt_furia = texto('', (-.86, .27), 1.3, color.orange)
txt_oleada = texto('', (0, .46), 2, color.white, True)
txt_enemigos = texto('', (0, .41), 1.1, color.light_gray, True)
txt_hint = texto('', (0, .34), 1.2, color.yellow, True)
txt_aviso = texto('', (0, .2), 2.4, color.white, True)
txt_vida = texto('', (-.86, -.395), 1.0, color.white)
txt_arma = texto('', (.58, -.36), 1.6, color.white)
hitmarker = texto('x', (0, 0), 2.5, color.white, True)
hitmarker.enabled = False

txt_hab = {}
for xh, k in zip((-.27, -.09, .09, .27), HABS):
    txt_hab[k] = texto('', (xh, -.43), 1.0, color.white, True)


def barra(pos, tam, col):
    bg = _entity_factory(parent=hud, model='quad', color=color.dark_gray, scale=tam, position=pos)
    return _entity_factory(parent=bg, model='quad', color=col, origin_x=-.5, x=-.5, z=-.01)


barra_vida = barra((-.63, -.44), (.46, .035), color.red)
barra_stamina = barra((-.63, -.48), (.46, .015), color.azure)

for dx, dy, sx, sy in ((-.014, 0, .012, .003), (.014, 0, .012, .003),
                       (0, .014, .003, .012), (0, -.014, .003, .012)):
    _entity_factory(parent=hud, model='quad', color=color.white, position=(dx, dy), scale=(sx, sy))

_entity_factory(parent=hud, model='circle', scale=.3, position=(.72, .26), color=color.dark_gray, z=.01)
radar = _entity_factory(parent=hud, model='circle', scale=.28, position=(.72, .26), color=Vec4(0, 0, 0, .65))
_entity_factory(parent=radar, model='circle', scale=.07, color=color.white, z=-.01)
puntos_radar = []


# =====================================================================
#  UTILIDADES Y EFECTOS
# =====================================================================
def aviso(txt, dur=2.0, col=color.white):
    poner(txt_aviso, txt)
    txt_aviso.color = col
    S.aviso_t = dur


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
    disponibles = MAX_PARTICULAS - len(EFECTOS_ACTIVOS['particula'])
    for _ in range(min(n, max(0, disponibles))):
        p = _entity_factory(model='cube', color=col, scale=random.uniform(.08, .2), position=pos)
        destino = pos + Vec3(random.uniform(-1, 1), random.uniform(0, 1.5),
                             random.uniform(-1, 1)) * vel * .6
        p.animate_position(destino, duration=.5, curve=curve.out_quad)
        p.animate_scale(0, duration=.5)
        _crear_efecto('particula', MAX_PARTICULAS, p, .56)


def rayo(a, b, col=color.yellow, grosor=.04):
    if not (esta_en_vista(a, distancia_max=48) or esta_en_vista(b, distancia_max=48)):
        return
    if len(EFECTOS_ACTIVOS['rayo']) >= MAX_RAYOS:
        return
    d = (b - a).length()
    if d < .05:
        return
    r = _entity_factory(model='cube', color=col, position=(a + b) / 2, scale=(grosor, grosor, d))
    r.look_at(b)
    _crear_efecto('rayo', MAX_RAYOS, r, .07)


def anillo(pos, radio, col, dur=.4):
    if not esta_en_vista(pos, distancia_max=48):
        return
    if len(EFECTOS_ACTIVOS['anillo']) >= MAX_ANILLOS:
        return
    r = _entity_factory(model='circle', rotation_x=90, position=Vec3(pos.x, .15, pos.z), scale=1,
               color=col, double_sided=True)
    r.animate_scale(radio * 2, duration=dur, curve=curve.out_quad)
    _crear_efecto('anillo', MAX_ANILLOS, r, dur + .02)


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
    return min(1 + max(S.combo - 1, 0) * .1, 3)


def ganar(p):
    S.puntos += p
    S.creditos += p


def mas_cercano(pos, rango):
    mejor = None
    limite2 = rango * rango
    mejor_d2 = limite2
    for e in enemigos:
        dx, dz = e.x - pos.x, e.z - pos.z
        d2 = dx * dx + dz * dz
        if d2 < mejor_d2:
            mejor, mejor_d2 = e, d2
    return mejor


def pos_spawn():
    for _ in range(40):
        ang = random.uniform(0, math.tau)
        r = random.uniform(ARENA * .55, ARENA - 4)
        x, z = math.cos(ang) * r, math.sin(ang) * r
        if math.hypot(x - jugador.x, z - jugador.z) < 18:
            continue
        if any(math.hypot(x - ox, z - oz) < orad + 1.5 for ox, oz, orad, _h in obstaculos):
            continue
        return Vec3(x, 0, z)
    return Vec3(ARENA - 5, 0, ARENA - 5)


def herir(d):
    if S.estado != 'jugando' or S.dash_t > 0:
        return
    S.salud -= d
    S.dano_alpha = min(.6, S.dano_alpha + .35)
    S.combo = 0
    if S.salud <= 0:
        S.salud = 0
        terminar()


def agregar_municion(factor=1.0):
    for i, a in enumerate(ARMAS):
        S.reserva[i] = min(reserva_max(i), S.reserva[i] + int(a['cargador'] * 2 * factor))


def botin(pos, garantizado=False):
    if garantizado or random.random() < .22:
        tipo = random.choices(['salud', 'municion', 'dano'], weights=[.4, .45, .15])[0]
        p = Vec3(pos.x + random.uniform(-1, 1), 0, pos.z + random.uniform(-1, 1))
        recogibles.append(Recogible(tipo, p))


def aplicar_fuego(en):
    if S.perks['fuego'] > 0:
        en.quema_t = 3
        en.quema_dps = 4 + 4 * S.perks['fuego']


def golpear(en, dano, cabeza=False):
    """Dano del jugador: marcador de impacto + municion incendiaria."""
    S.hit_t = .12
    S.hit_cab = cabeza
    aplicar_fuego(en)
    en.recibir_dano(dano)


def danar_auto(en, dano):
    """Dano de torretas y drones."""
    aplicar_fuego(en)
    en.recibir_dano(dano)


def explosion(pos, radio, dano):
    anillo(pos, radio, Vec4(1, .5, 0, .6), .35)
    particulas(pos, color.orange, n=24, vel=4)
    for e in enemigos[:]:
        c = e.world_position + Vec3(0, e.alto / 2, 0)
        d = (c - pos).length()
        if d < radio + e.radio:
            golpear(e, dano * (1 - .5 * min(d / radio, 1)))


# =====================================================================
#  CLASES
# =====================================================================
class Enemigo(Entity):
    def __init__(self, tipo, pos):
        super().__init__(position=pos)
        d = TIPOS[tipo]
        esc = d['escala']
        self.tipo = tipo
        self.alto = esc[1]
        self.radio = esc[0] * .5 + .2
        self.alcance = esc[0] / 2 + 1.1
        self.hp_max = self.hp = d['hp'] * (1 + .12 * (S.oleada - 1))
        self.vel = d['vel'] * random.uniform(.9, 1.1)
        self.dano = d['dano']
        self.ranged = d['ranged']
        self.dispara = d['dispara']
        self.color_base = d['color']
        self.cd_ataque = 0
        self.cd_disparo = random.uniform(1, 2.5)
        self.flash = 0
        self.lado = random.choice([-1, 1])
        self.muerto = False
        self.quema_t = 0
        self.quema_dps = 0
        self.quema_fx = 0
        self.aturdido = 0

        self.cuerpo = _entity_factory(parent=self, model='cube', color=self.color_base, scale=esc,
                             y=esc[1] / 2, collider='box')
        self.cuerpo.enemigo = self
        for sx in (-.22, .22):
            _entity_factory(parent=self.cuerpo, model='cube', color=color.white,
                   scale=(.18, .1, .1), position=(sx, .3, .5))

        self.barra_bg = _entity_factory(parent=self, model='quad', color=color.black,
                               scale=(max(1.2, esc[0]), .13), y=esc[1] + .5, billboard=True)
        self.barra = _entity_factory(parent=self.barra_bg, model='quad', color=color.lime,
                            origin_x=-.5, x=-.5, z=-.01, scale=(1, .7))
        self._vis_timer = random.uniform(0, VISIBILIDAD_INTERVALO)
        self._actualizar_visibilidad()

    def _actualizar_visibilidad(self):
        visible = esta_en_vista(self.world_position + Vec3(0, self.alto * .5, 0))
        if self.cuerpo.enabled != visible:
            self.cuerpo.enabled = visible
        if self.barra_bg.enabled != visible:
            self.barra_bg.enabled = visible

    def recibir_dano(self, d, flash=True):
        if self.muerto:
            return
        self.hp -= d
        ratio = max(self.hp / self.hp_max, .001)
        self.barra.scale_x = ratio
        self.barra.color = color.red if ratio < .35 else color.lime
        if flash:
            self.cuerpo.color = color.white
            self.flash = .08
        if self.hp <= 0:
            self.morir()

    def morir(self):
        self.muerto = True
        d = TIPOS[self.tipo]
        particulas(self.world_position + Vec3(0, self.alto / 2, 0), self.color_base,
                   n=18 if self.tipo == 'jefe' else 8, vel=2.5)
        S.combo += 1
        S.combo_t = 4
        ganar(int(d['puntos'] * mult_combo()))
        S.muertes += 1
        if S.perks['robo'] > 0:
            S.salud = min(S.salud_max, S.salud + 2 * S.perks['robo'])
        if self.tipo == 'jefe':
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
                self.quema_fx = .25
                particulas(self.world_position + Vec3(0, self.alto, 0), color.orange, n=1, vel=.7)

        # --- aturdido (onda de choque) ---
        if self.aturdido > 0:
            self.aturdido -= dt
            return

        dx, dz = jugador.x - self.x, jugador.z - self.z
        dist = max(math.hypot(dx, dz), .001)
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
            mx, mz = (dirx, dirz) if dist > self.alcance * .8 else (0, 0)

        for ox, oz, orad, _h in obstaculos:
            ddx, ddz = self.x - ox, self.z - oz
            dd = max(math.hypot(ddx, ddz), .001)
            if dd < orad + self.radio + .8:
                nx, nz = ddx / dd, ddz / dd
                hacia = mx * nx + mz * nz
                if hacia < 0:
                    tx, tz = -nz, nx
                    s = tx * mx + tz * mz
                    signo = self.lado if abs(s) < .15 else (1 if s > 0 else -1)
                    mx = mx - hacia * nx + tx * signo * abs(hacia)
                    mz = mz - hacia * nz + tz * signo * abs(hacia)

        self.x += mx * self.vel * dt
        self.z += mz * self.vel * dt

        for ox, oz, orad, _h in obstaculos:
            ddx, ddz = self.x - ox, self.z - oz
            dd = max(math.hypot(ddx, ddz), .001)
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
            if .0001 < d2 < lim * lim:
                dd = math.sqrt(d2)
                empuje = (lim - dd) * .5
                self.x += ddx / dd * empuje
                self.z += ddz / dd * empuje
        self.x = clamp(self.x, -ARENA + 2, ARENA - 2)
        self.z = clamp(self.z, -ARENA + 2, ARENA - 2)

        self.cd_ataque -= dt
        if (not self.ranged and dist < self.alcance and jugador.y < self.alto - .3
                and self.cd_ataque <= 0):
            self.cd_ataque = 1.0
            herir(self.dano)

        if self.dispara:
            self.cd_disparo -= dt
            if self.cd_disparo <= 0 and dist < 40:
                self.cd_disparo = 2.2 if self.tipo == 'jefe' else random.uniform(1.8, 2.8)
                origen = self.world_position + Vec3(0, self.alto * .7, 0)
                objetivo = jugador.world_position + Vec3(0, 1.2, 0)
                base = (objetivo - origen).normalized()
                n = 3 if self.tipo == 'jefe' else 1
                for k in range(n):
                    ang = (k - (n - 1) / 2) * .2
                    v = Vec3(base.x * math.cos(ang) - base.z * math.sin(ang), base.y,
                             base.x * math.sin(ang) + base.z * math.cos(ang))
                    proyectiles.append(Proyectil(origen, v.normalized(), 15 if self.tipo == 'jefe' else 12))


class Proyectil(Entity):
    def __init__(self, pos, direccion, dano):
        _entity_init: Any = super().__init__
        _entity_init(model='sphere', color=color.cyan, scale=.45, position=pos)
        self.direccion = direccion
        self.dano = dano
        self.vida = 5


class Recogible(Entity):
    def __init__(self, tipo, pos):
        modelo, col = {'salud': ('sphere', color.lime),
                       'municion': ('cube', color.gold),
                       'dano': ('cube', color.magenta)}[tipo]
        _entity_init: Any = super().__init__
        _entity_init(model=modelo, color=col, scale=.6, position=Vec3(pos.x, 1, pos.z))
        if tipo == 'dano':
            self.rotation_x = 45
            self.rotation_z = 45
        self.tipo = tipo
        self.vida = 22
        self.fase = random.uniform(0, 6.28)


class Dron(Entity):
    """Dron de combate que orbita al jugador y dispara al enemigo mas cercano."""

    def __init__(self, idx):
        _entity_init: Any = super().__init__
        _entity_init(model='sphere', color=color.cyan, scale=.4, position=jugador.world_position)
        _entity_factory(parent=self, model='cube', color=color.black, scale=(.5, .5, 1.6), z=.6)
        self.idx = idx
        self.ang = idx * 2.1
        self.cd = random.uniform(0, .8)

    def actualizar(self, dt):
        self.ang += dt * 1.6
        obj = jugador.world_position + Vec3(math.cos(self.ang) * 2.4,
                                            2.6 + math.sin(S.t * 2 + self.idx) * .2,
                                            math.sin(self.ang) * 2.4)
        self.position += (obj - self.position) * min(1, 8 * dt)
        self.cd -= dt
        if self.cd <= 0 and enemigos:
            objetivo = mas_cercano(self.position, 25)
            if objetivo:
                self.cd = .8
                centro = objetivo.world_position + Vec3(0, objetivo.alto * .6, 0)
                self.look_at(centro)
                rayo(self.position, centro, color.cyan, .05)
                danar_auto(objetivo, 10)


class Torreta(Entity):
    """Torreta desplegable que dispara automaticamente durante un tiempo."""

    def __init__(self, pos, niv):
        super().__init__(position=Vec3(pos.x, 0, pos.z))
        _entity_factory(parent=self, model='cube', color=color.dark_gray, scale=(1.2, .5, 1.2), y=.25)
        self.cabeza = _entity_factory(parent=self, model='sphere', color=color.orange, scale=.8, y=.9)
        _entity_factory(parent=self.cabeza, model='cube', color=color.black, scale=(.25, .25, 1.3), z=.8)
        self.dano = 14 * (1 + .35 * niv)
        self.cadencia = .5 * (.88 ** niv)
        self.vida = self.vida_max = 25 + 5 * niv
        self.cd = .3
        self.sonido_activo = False
        self.sonido = SONIDO_TORRETA_LOOP
        bg = _entity_factory(parent=self, model='quad', color=color.black, scale=(1.2, .12), y=2, billboard=True)
        self.barra = _entity_factory(parent=bg, model='quad', color=color.orange, origin_x=-.5, x=-.5,
                            z=-.01, scale=(1, .7))

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
        self.barra.scale_x = max(self.vida / self.vida_max, .001)
        self.cd -= dt
        objetivo = mas_cercano(self.position, 30)
        if objetivo:
            if not self.sonido_activo:
                reproducir_audio(self.sonido)
                self.sonido_activo = True
            self.cabeza.rotation_y = math.degrees(math.atan2(objetivo.x - self.x, objetivo.z - self.z))
            if self.cd <= 0:
                self.cd = self.cadencia
                origen = self.cabeza.world_position + Vec3(0, .1, 0)
                centro = objetivo.world_position + Vec3(0, objetivo.alto * .6, 0)
                rayo(origen, centro, color.orange, .05)
                danar_auto(objetivo, self.dano)
        elif self.sonido_activo:
            detener_audio(self.sonido)
            self.sonido_activo = False

# =====================================================================
#  ARMAS
# =====================================================================
def aplicar_arma():
    a = ARMAS[S.arma]
    arma_modelo.color = a['color']
    arma_modelo.scale = a['escala']


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
    if S.recarga > 0 or S.mag[S.arma] >= stat(S.arma, 'cargador') or S.reserva[S.arma] <= 0:
        return
    S.recarga = stat(S.arma, 'recarga')
    reproducir_audio(SONIDO_RECARGA)


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
            aviso('¡Sin municion!', .8, color.red)
        return

    if not furia:
        S.mag[S.arma] -= 1

    # El audio se reproduce despues de validar que el disparo es posible.
    reproducir_audio(SONIDOS_ARMAS[S.arma])

    S.cd = stat(S.arma, 'cadencia') * (.5 if furia else 1)
    S.retroceso = 1
    S.fogonazo = .05
    jugador.camera_pivot.rotation_x = max(-85, jugador.camera_pivot.rotation_x - a['kick'])

    origen = camera.world_position
    muzzle = arma_modelo.world_position + camera.forward * .8
    dano_base = stat(S.arma, 'dano') * (2 if S.buff_t > 0 else 1)
    disp = a['dispersion'] * (.4 if _held_keys['right mouse'] else 1)

    for _ in range(a['perdigones']):
        v = (camera.forward + Vec3(random.uniform(-1, 1), random.uniform(-1, 1),
                                   random.uniform(-1, 1)) * disp).normalized()
        ign = [jugador]
        fin = origen + v * 100
        impacto = False
        for _p in range(a['penetra']):
            hit = raycast(origen, v, distance=120, ignore=ign, debug=False)
            if not hit.hit:
                break
            fin = hit.world_point
            impacto = True
            if a['explosion'] > 0:
                break
            en = getattr(hit.entity, 'enemigo', None)
            if en:
                cabeza = hit.world_point.y > en.y + en.alto * .8
                ign.append(hit.entity)
                golpear(en, dano_base * (2 if cabeza else 1), cabeza)
            else:
                particulas(fin, color.light_gray, n=3, vel=1)
                break
        rayo(muzzle, fin, color.yellow, .03)
        if a['explosion'] > 0 and impacto:
            explosion(fin, a['explosion'], dano_base)

    if S.mag[S.arma] <= 0 and S.reserva[S.arma] > 0 and not furia:
        recargar()

# =====================================================================
#  HABILIDADES
# =====================================================================
def usar_dash():
    if S.cdh['dash'] > 0:
        return
    n = S.hab['dash']
    fx, fz = jugador.forward.x, jugador.forward.z
    rx, rz = jugador.right.x, jugador.right.z
    mx = _held_keys['d'] - _held_keys['a']
    mz = _held_keys['w'] - _held_keys['s']
    if mx == 0 and mz == 0:
        mz = 1
    dx, dz = fx * mz + rx * mx, fz * mz + rz * mx
    l = max(math.hypot(dx, dz), .001)
    S.dash_dir = (dx / l, dz / l)
    S.dash_t = .2 + .02 * n
    S.cdh['dash'] = CD_BASE['dash'] * (.85 ** n)


def usar_onda():
    if S.cdh['onda'] > 0:
        return
    n = S.hab['onda']
    radio = 9 + n
    dano = 55 * (1 + .3 * n)
    S.cdh['onda'] = CD_BASE['onda'] * (.85 ** n)
    c = jugador.world_position
    anillo(c, radio, Vec4(.3, .8, 1, .6), .45)
    anillo(c, radio * .6, Vec4(1, 1, 1, .4), .3)
    for e in enemigos[:]:
        dx, dz = e.x - c.x, e.z - c.z
        d = max(math.hypot(dx, dz), .001)
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
    if S.cdh['torreta'] > 0:
        return
    n = S.hab['torreta']
    maximo = 1 + n // 2
    hit = raycast(camera.world_position, camera.forward, distance=18, ignore=[jugador], debug=False)
    p = hit.world_point if hit.hit else camera.world_position + camera.forward * 6
    p = Vec3(clamp(p.x, -ARENA + 3, ARENA - 3), 0, clamp(p.z, -ARENA + 3, ARENA - 3))
    while len(torretas) >= maximo:
        destroy(torretas.pop(0))
    torretas.append(Torreta(p, n))
    S.cdh['torreta'] = CD_BASE['torreta'] * (.85 ** n)
    aviso('Torreta desplegada', 1, color.orange)


def usar_furia():
    if S.cdh['furia'] > 0 or S.furia_t > 0:
        return
    n = S.hab['furia']
    S.furia_t = 8 + 2 * n
    S.cdh['furia'] = CD_BASE['furia'] * (.85 ** n)
    aviso('¡MODO FURIA!', 1.5, color.orange)


def sincronizar_drones():
    n = S.perks['dron']
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
    if c == 'carga':
        S.mag[i] = stat(i, 'cargador')


def mejorar_perk(k):
    S.perks[k] += 1
    if k == 'vida':
        S.salud_max = 100 + 20 * S.perks['vida']
        S.salud = min(S.salud_max, S.salud + 20)
    elif k == 'dron':
        sincronizar_drones()


def mejorar_hab(k):
    S.hab[k] += 1


def curar_todo():
    S.salud = S.salud_max


def rellenar_municion():
    for i in range(len(ARMAS)):
        S.reserva[i] = reserva_max(i)
        S.mag[i] = stat(i, 'cargador')


def item(nombre, nivel, maximo, coste, accion, desc, bloqueado=False):
    return dict(nombre=nombre, nivel=nivel, maximo=maximo, coste=coste,
                accion=accion, desc=desc, bloqueado=bloqueado)


def construir_items():
    i = S.tienda_arma
    a = ARMAS[i]
    bloq = not S.desbloqueadas[i]
    items = []
    if bloq:
        items.append(item(f'Comprar {a["nombre"]}', 0, 1, a['precio'], lambda: comprar_arma(i), a['desc']))
    else:
        items.append(item(f'{a["nombre"]} (tecla {i + 1})', None, None, None, None, a['desc']))
    for clave, nombre, base, desc in MEJORAS_ARMA:
        n = S.niv[i][clave]
        items.append(item(nombre, n, 5, base * (n + 1), lambda c=clave: mejorar_arma(i, c), desc, bloq))

    perks = [
        ('vida', 'Vida maxima', 150, 5, '+20 de vida maxima por nivel (y cura 20).'),
        ('vel', 'Velocidad', 150, 4, '+8% de velocidad al andar y correr por nivel.'),
        ('fuego', 'Municion incendiaria', 300, 3, 'Tus balas, torretas y drones queman al enemigo.'),
        ('robo', 'Robo de vida', 250, 3, 'Recuperas 2 de vida por baja y por nivel.'),
        ('dron', 'Dron de combate', 350, 3, 'Un dron mas que orbita y dispara solo.'),
    ]
    for k, nombre, base, mx, desc in perks:
        n = S.perks[k]
        items.append(item(nombre, n, mx, base * (n + 1), lambda k=k: mejorar_perk(k), desc))

    habs = [
        ('dash', 'Dash (Q)', 200, 3, 'Menos enfriamiento, mas distancia y mas tiempo invulnerable.'),
        ('onda', 'Onda de choque (E)', 250, 3, 'Mas dano, mas radio y menos enfriamiento.'),
        ('torreta', 'Torreta (F)', 300, 4, 'Mas dano, cadencia, duracion y +1 torreta cada 2 niveles.'),
        ('furia', 'Modo furia (C)', 300, 3, 'Mas duracion y menos enfriamiento.'),
    ]
    for k, nombre, base, mx, desc in habs:
        n = S.hab[k]
        items.append(item(nombre, n, mx, base * (n + 1), lambda k=k: mejorar_hab(k), desc))

    items.append(item('Curacion completa', None, None, 100, curar_todo, 'Restaura toda tu vida.'))
    items.append(item('Municion completa', None, None, 150, rellenar_municion,
                      'Rellena cargadores y reservas de todas las armas.'))
    return items


def etiqueta(it):
    n, m, c = it['nivel'], it['maximo'], it['coste']
    if n is None:
        return it['nombre'] if c is None else f'{it["nombre"]}   ${c}'
    if m and n >= m:
        return f'{it["nombre"]}   Nv {n}/{m}  MAX'
    return f'{it["nombre"]}   Nv {n}/{m}   ${c}'


def refrescar_tienda():
    ITEMS[:] = construir_items()
    poner(txt_tienda_cred, f'TIENDA   -   Creditos: ${S.creditos}')
    a = ARMAS[S.tienda_arma]
    estado = 'DISPONIBLE' if S.desbloqueadas[S.tienda_arma] else 'BLOQUEADA'
    poner(txt_hdr_arma, f'ARMA: {a["nombre"]} ({estado})   [A/D para cambiar]')
    for idx, it in enumerate(ITEMS):
        t = filas[idx]
        sel = idx == S.tienda_sel
        maxed = bool(it['maximo']) and it['nivel'] is not None and it['nivel'] >= it['maximo']
        poner(t, ('> ' if sel else '   ') + etiqueta(it))
        if sel:
            t.color = color.yellow
        elif maxed:
            t.color = color.lime
        elif it['coste'] is not None and S.creditos >= it['coste'] and not it['bloqueado']:
            t.color = color.white
        else:
            t.color = color.gray
    poner(txt_tienda_desc, ITEMS[S.tienda_sel]['desc'])


def msg_tienda(s):
    poner(txt_tienda_msg, s)


def comprar_seleccion():
    it = ITEMS[S.tienda_sel]
    if it['accion'] is None:
        msg_tienda('Nada que comprar aqui')
    elif it['bloqueado']:
        msg_tienda('Primero compra esta arma')
    elif it['maximo'] and it['nivel'] >= it['maximo']:
        msg_tienda('Ya esta al maximo')
    elif S.creditos < it['coste']:
        msg_tienda('Creditos insuficientes')
    else:
        S.creditos -= it['coste']
        it['accion']()
        msg_tienda('¡Comprado!')
    refrescar_tienda()


def abrir_tienda():
    S.estado = 'tienda'
    S.tienda_arma = S.arma
    S.tienda_sel = 0
    jugador.enabled = False
    mouse.visible = True
    mouse.locked = False
    camera.fov = 90
    hud.enabled = False
    ui_tienda.enabled = True
    msg_tienda('')
    refrescar_tienda()


def cerrar_tienda():
    S.estado = 'jugando'
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
    pesos = {'normal': 10, 'rapido': 0, 'tirador': 0, 'tanque': 0}
    if n >= 2:
        pesos['rapido'] = 4
    if n >= 3:
        pesos['tirador'] = 3
    if n >= 4:
        pesos['tanque'] = 2
    lista = random.choices(list(pesos), weights=list(pesos.values()), k=total)
    if n % 5 == 0:
        lista.append('jefe')
    return lista


def iniciar_oleada():
    S.oleada += 1
    S.cola = componer_oleada(S.oleada)
    S.spawn_t = 1.5
    if S.oleada % 5 == 0:
        aviso(f'¡¡JEFE!!  Oleada {S.oleada}', 3, color.red)
    else:
        aviso(f'OLEADA {S.oleada}', 2.5, color.white)


def actualizar_oleadas(dt):
    if S.intermedio > 0:
        S.intermedio -= dt
        if S.intermedio <= 0:
            iniciar_oleada()
        return

    if S.cola:
        S.spawn_t -= dt
        max_sim = min(20, 5 + S.oleada * 2)
        if S.spawn_t <= 0 and len(enemigos) < max_sim:
            tipo = S.cola.pop(0)
            e = Enemigo(tipo, pos_spawn())
            enemigos.append(e)
            particulas(e.world_position + Vec3(0, 1, 0), e.color_base, n=6)
            S.spawn_t = max(.45, 1.5 - .06 * S.oleada)
    elif not enemigos:
        bono = 100 * S.oleada
        ganar(bono)
        aviso(f'¡Oleada {S.oleada} superada!  +{bono}', 3, color.lime)
        S.intermedio = INTERMEDIO
        S.salud = min(S.salud_max, S.salud + 15)
        agregar_municion(.5)
        for _ in range(2):
            botin(Vec3(random.uniform(-15, 15), 0, random.uniform(-15, 15)), True)


# =====================================================================
#  ESTADOS DEL JUEGO
# =====================================================================
def iniciar():
    global _radar_timer, _hud_timer
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
    poner(txt_aviso, '')
    S.estado = 'jugando'
    iniciar_oleada()


def pausar():
    S.estado = 'pausa'
    jugador.enabled = False
    mouse.visible = True
    mouse.locked = False
    camera.fov = 90
    ui_pausa.enabled = True


def reanudar():
    S.estado = 'jugando'
    jugador.enabled = True
    mouse.locked = True
    ui_pausa.enabled = False


def terminar():
    S.estado = 'fin'
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
    poner(txt_fin_stats,
          f'Llegaste a la oleada {S.oleada}\n'
          f'Puntos: {S.puntos}     Bajas: {S.muertes}\n\n'
          + ('¡NUEVO RECORD!' if nuevo else f'Record: {S.record}'))


def recoger(r):
    if r.tipo == 'salud':
        S.salud = min(S.salud_max, S.salud + 35)
        aviso('+35 Vida', 1, color.lime)
    elif r.tipo == 'municion':
        agregar_municion(1)
        aviso('+ Municion', 1, color.gold)
    else:
        S.buff_t = 12
        aviso('¡DANO DOBLE!', 1.5, color.magenta)
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
            puntos_radar.append(_entity_factory(parent=radar, model='circle', scale=.05, z=-.01))
        dx, dz = e.x - jugador.x, e.z - jugador.z
        rx = dx * c - dz * s
        ry = dx * s + dz * c
        l = math.hypot(rx, ry)
        k = 1 if l < RADAR_RANGE else RADAR_RANGE / l
        p = puntos_radar[i]
        p.position = (rx * k / RADAR_RANGE * .48, ry * k / RADAR_RANGE * .48, -.01)
        p.color = TIPOS[e.tipo]['color']
        p.enabled = True
    for p in puntos_radar[len(enemigos):]:
        p.enabled = False


def actualizar_hud(dt):
    a = ARMAS[S.arma]
    poner(txt_puntos, f'Puntos: {S.puntos}')
    poner(txt_record, f'Record: {max(S.record, S.puntos)}')
    poner(txt_cred, f'Creditos: ${S.creditos}')
    poner(txt_oleada, f'OLEADA {S.oleada}')
    if S.intermedio > 0:
        poner(txt_enemigos, f'Siguiente oleada en {int(S.intermedio) + 1}')
        poner(txt_hint, 'B: abrir tienda   ·   ENTER: empezar ya')
    else:
        poner(txt_enemigos, f'Enemigos: {len(enemigos) + len(S.cola)}')
        poner(txt_hint, '')
    poner(txt_combo, f'COMBO x{mult_combo():.1f}' if S.combo > 1 else '')
    poner(txt_buff, f'DANO x2: {int(S.buff_t) + 1}s' if S.buff_t > 0 else '')
    poner(txt_furia, f'FURIA: {int(S.furia_t) + 1}s' if S.furia_t > 0 else '')
    poner(txt_vida, f'Vida {int(S.salud)}/{S.salud_max}')
    if S.recarga > 0:
        estado_arma = 'RECARGANDO...'
    elif S.furia_t > 0:
        estado_arma = 'INFINITA'
    else:
        estado_arma = f'{S.mag[S.arma]} / {S.reserva[S.arma]}'
    poner(txt_arma, f'{a["nombre"]} [{S.arma + 1}]\n{estado_arma}')
    barra_vida.scale_x = max(S.salud / S.salud_max, .001)
    barra_stamina.scale_x = max(S.stamina / 100, .001)

    for k, (tecla, nombre) in HABS.items():
        cd = S.cdh[k]
        if k == 'furia' and S.furia_t > 0:
            s, col = f'[{tecla}] {nombre}\nACTIVA', color.orange
        elif cd > 0:
            s, col = f'[{tecla}] {nombre}\n{int(cd) + 1}s', color.gray
        else:
            s, col = f'[{tecla}] {nombre}\nLISTA', color.lime
        poner(txt_hab[k], s)
        txt_hab[k].color = col

    if S.aviso_t > 0:
        S.aviso_t -= dt
        if S.aviso_t <= 0:
            poner(txt_aviso, '')

    S.hit_t -= dt
    visible = S.hit_t > 0
    if hitmarker.enabled != visible:
        hitmarker.enabled = visible
    if visible:
        hitmarker.color = color.red if S.hit_cab else color.white

    S.dano_alpha = max(0, S.dano_alpha - dt * 1.5)
    extra = .12 if S.salud < S.salud_max * .3 else 0
    overlay_dano.color = Vec4(1, 0, 0, S.dano_alpha + extra)

    S.fogonazo -= dt
    f = S.fogonazo > 0
    if fogonazo.enabled != f:
        fogonazo.enabled = f


def update():
    if S.estado != 'jugando':
        return
    dt = min(float(getattr(_ursina_time, 'dt', 0.0)), .05)
    S.t += dt

    global _obstaculos_timer
    _obstaculos_timer -= dt
    if _obstaculos_timer <= 0:
        actualizar_obstaculos_visibles()
        _obstaculos_timer = .20

    # --- correr / energia ---
    moviendo = _held_keys['w'] or _held_keys['a'] or _held_keys['s'] or _held_keys['d']
    correr = _held_keys['left shift'] and moviendo and S.puede_correr
    if correr:
        S.stamina -= 28 * dt
        if S.stamina <= 0:
            S.stamina = 0
            S.puede_correr = False
    else:
        S.stamina = min(100, S.stamina + 18 * dt)
        if S.stamina > 25:
            S.puede_correr = True
    factor_vel = 1 + .08 * S.perks['vel']
    setattr(jugador, 'speed', (9 if correr else 5.5) * factor_vel)

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
        v = 30 * (1 + .15 * S.hab['dash'])
        nx = jugador.x + S.dash_dir[0] * v * dt
        nz = jugador.z + S.dash_dir[1] * v * dt
        libre = (abs(nx) < ARENA - 1.5 and abs(nz) < ARENA - 1.5 and
                 not any(math.hypot(nx - ox, nz - oz) < orad + .7 for ox, oz, orad, _h in obstaculos))
        if libre:
            jugador.x, jugador.z = nx, nz
        S.dash_fx_t -= dt
        if S.dash_fx_t <= 0:
            particulas(jugador.world_position + Vec3(0, 1, 0), color.cyan, n=1, vel=.5)
            S.dash_fx_t = .08

    # --- zoom al apuntar ---
    objetivo_fov = 90
    if _held_keys['right mouse']:
        objetivo_fov = 30 if ARMAS[S.arma]['penetra'] > 1 else 70
    camera.fov = lerp(camera.fov, objetivo_fov, min(1, 12 * dt))

    # --- arma ---
    S.cd = max(0, S.cd - dt)
    if S.recarga > 0:
        S.recarga -= dt
        if S.recarga <= 0:
            n = min(stat(S.arma, 'cargador') - S.mag[S.arma], S.reserva[S.arma])
            S.mag[S.arma] += n
            S.reserva[S.arma] -= n
    if _held_keys['left mouse'] and ARMAS[S.arma]['auto']:
        disparar()
    S.retroceso = max(0, S.retroceso - dt * 9)
    arma_modelo.z = .9 - .12 * S.retroceso
    objetivo_rot = 50 if S.recarga > 0 else 0
    arma_modelo.rotation_x = lerp(arma_modelo.rotation_x, objetivo_rot, min(1, 12 * dt))

    # --- oleadas y enemigos ---
    actualizar_oleadas(dt)
    construir_grid_enemigos()
    for e in enemigos[:]:
        if not e.muerto:
            e.actualizar(dt)
        if S.estado != 'jugando':
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
                if p.y < h and math.hypot(p.x - ox, p.z - oz) < orad - .2:
                    quitar = True
                    break
        if quitar:
            if p in proyectiles:
                proyectiles.remove(p)
            destroy(p)
        if S.estado != 'jugando':
            return

    # --- objetos recogibles ---
    for r in recogibles[:]:
        r.rotation_y += 120 * dt
        r.y = 1 + math.sin(S.t * 3 + r.fase) * .2
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
    if S.estado == 'menu':
        if key == 'enter':
            iniciar()
        elif key == 'escape':
            __application.quit()

    elif S.estado == 'jugando':
        if key in ('escape', 'p'):
            pausar()
        elif key == 'left mouse down':
            disparar()
        elif key == 'r':
            recargar()
        elif key in ('1', '2', '3', '4', '5'):
            equipar(int(key) - 1)
        elif key == 'scroll up':
            siguiente_arma(1)
        elif key == 'scroll down':
            siguiente_arma(-1)
        elif key == 'q':
            usar_dash()
        elif key == 'e':
            usar_onda()
        elif key == 'f':
            usar_torreta()
        elif key == 'c':
            usar_furia()
        elif key == 'b' and S.intermedio > 0:
            abrir_tienda()
        elif key == 'enter' and S.intermedio > 0:
            S.intermedio = .01

    elif S.estado == 'tienda':
        if key in ('w', 'up arrow'):
            S.tienda_sel = (S.tienda_sel - 1) % len(ITEMS)
            refrescar_tienda()
        elif key in ('s', 'down arrow'):
            S.tienda_sel = (S.tienda_sel + 1) % len(ITEMS)
            refrescar_tienda()
        elif key in ('a', 'left arrow'):
            S.tienda_arma = (S.tienda_arma - 1) % len(ARMAS)
            refrescar_tienda()
        elif key in ('d', 'right arrow'):
            S.tienda_arma = (S.tienda_arma + 1) % len(ARMAS)
            refrescar_tienda()
        elif key in ('enter', 'space'):
            comprar_seleccion()
        elif key in ('b', 'escape'):
            cerrar_tienda()

    elif S.estado == 'pausa':
        if key in ('escape', 'p'):
            reanudar()
        elif key == 'q':
            _application.quit()

    elif S.estado == 'fin':
        if key in ('r', 'enter'):
            iniciar()
        elif key == 'escape':
            _application.quit()


poner(txt_menu_record, f'Record: {S.record}')
aplicar_arma()
def run():
    _app.run()