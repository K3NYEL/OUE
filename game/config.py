from pathlib import Path
from typing import Any

from ursina import color


# =====================================================================
ARENA = 40
RADAR_RANGE = 30
RECORD_FILE = Path(__file__).resolve().parent.parent / 'record.txt'
INTERMEDIO = 20       # segundos entre oleadas

TIPOS: dict[str, dict[str, Any]] = {
    'normal':  dict(hp=40,  vel=3.6, dano=10, color=color.red,     escala=(1.0, 1.8, 1.0), puntos=10,
                    ranged=False, dispara=False),
    'rapido':  dict(hp=22,  vel=6.8, dano=7,  color=color.orange,  escala=(0.8, 1.4, 0.8), puntos=15,
                    ranged=False, dispara=False),
    'tanque':  dict(hp=170, vel=2.1, dano=24, color=color.violet,  escala=(1.8, 2.6, 1.8), puntos=40,
                    ranged=False, dispara=False),
    'tirador': dict(hp=35,  vel=3.0, dano=12, color=color.azure,   escala=(1.0, 1.8, 1.0), puntos=25,
                    ranged=True, dispara=True),
    'jefe':    dict(hp=900, vel=2.6, dano=35, color=color.magenta, escala=(3.2, 4.5, 3.2), puntos=300,
                    ranged=False, dispara=True),
}

ARMAS: list[dict[str, Any]] = [
    dict(nombre='Pistola', dano=28, cadencia=.28, cargador=12, reserva_ini=48, reserva_max=120,
         recarga=1.0, perdigones=1, dispersion=.004, auto=False, kick=.8, explosion=0, penetra=1,
         precio=0, color=color.dark_gray, escala=(.10, .14, .50),
         desc='Precisa y fiable. Buena para empezar.'),
    dict(nombre='Rifle', dano=14, cadencia=.09, cargador=30, reserva_ini=90, reserva_max=240,
         recarga=1.6, perdigones=1, dispersion=.018, auto=True, kick=.5, explosion=0, penetra=1,
         precio=0, color=color.gray, escala=(.10, .13, .80),
         desc='Fuego automatico a gran cadencia.'),
    dict(nombre='Escopeta', dano=11, cadencia=.85, cargador=6, reserva_ini=18, reserva_max=48,
         recarga=2.0, perdigones=8, dispersion=.07, auto=False, kick=3.0, explosion=0, penetra=1,
         precio=0, color=color.brown, escala=(.14, .14, .75),
         desc='8 perdigones. Devastadora a corta distancia.'),
    dict(nombre='Francotirador', dano=120, cadencia=1.3, cargador=5, reserva_ini=15, reserva_max=40,
         recarga=2.2, perdigones=1, dispersion=.0, auto=False, kick=4.0, explosion=0, penetra=3,
         precio=600, color=color.hsv(210, .3, .25), escala=(.08, .12, 1.10),
         desc='Atraviesa hasta 3 enemigos. Clic der = zoom.'),
    dict(nombre='Lanzagranadas', dano=90, cadencia=1.0, cargador=4, reserva_ini=8, reserva_max=24,
         recarga=2.4, perdigones=1, dispersion=.005, auto=False, kick=3.5, explosion=6, penetra=1,
         precio=900, color=color.hsv(100, .5, .35), escala=(.16, .16, .60),
         desc='Explosion en area (radio 6). Ideal contra hordas.'),
]

HABS: dict[str, tuple[str, str]] = {'dash': ('Q', 'Dash'), 'onda': ('E', 'Onda'), 'torreta': ('F', 'Torreta'), 'furia': ('C', 'Furia')}
CD_BASE = dict(dash=5, onda=14, torreta=18, furia=45)

MEJORAS_ARMA: list[tuple[str, str, int, str]] = [
    ('dano', 'Dano', 120, '+25% de dano por nivel.'),
    ('carga', 'Cargador', 80, '+25% de cargador y de municion maxima. Rellena el cargador.'),
    ('cad', 'Cadencia', 100, 'Dispara 10% mas rapido por nivel.'),
    ('rec', 'Recarga', 80, 'Recarga 15% mas rapida por nivel.'),
]

# =====================================================================
