from pathlib import Path
from ursina import Audio


# =====================================================================

# Admite el proyecto tanto si main.py esta en la raiz como si esta dentro de src/.
_RUTAS_AUDIO = (
    Path(__file__).resolve().parent.parent / 'assets' / 'audio' / 'weapons',
    Path(__file__).resolve().parent.parent / 'src' / 'assets' / 'audio' / 'weapons',
    Path(__file__).resolve().parent.parent / 'audio' / 'weapons',
)
AUDIO_DIR = next((ruta for ruta in _RUTAS_AUDIO if ruta.is_dir()), _RUTAS_AUDIO[0])


def cargar_audio(nombres, volumen, loop=False):
    """Carga el primer nombre de archivo existente; no bloquea el juego si falta."""
    if isinstance(nombres, str):
        nombres = (nombres,)
    for nombre in nombres:
        ruta = AUDIO_DIR / nombre
        if ruta.is_file():
            try:
                return Audio(ruta, autoplay=False, volume=volumen, loop=loop)
            except Exception as exc:
                print(f'[AUDIO] No se pudo cargar {ruta}: {exc}')
                return None
    print(f'[AUDIO] No encontrado: {" / ".join(nombres)} (carpeta: {AUDIO_DIR})')
    return None


def reproducir_audio(sonido):
    if sonido is not None:
        try:
            sonido.play()
        except Exception as exc:
            print(f'[AUDIO] Error al reproducir sonido: {exc}')


def detener_audio(sonido):
    if sonido is not None:
        try:
            sonido.stop()
        except Exception as exc:
            print(f'[AUDIO] Error al detener sonido: {exc}')


SONIDOS_ARMAS = [
    cargar_audio(('pistol_shot.wav', 'pistol.wav'), .70),
    cargar_audio(('rifle_shot.wav', 'rifle.wav'), .55),
    cargar_audio(('shotgun_shot.wav', 'shotgun.wav'), .80),
    cargar_audio(('sniper_shot.wav', 'sniper.wav'), .90),
    cargar_audio(('grenade_shot.wav', 'grenade_launcher.wav', 'grenade.wav'), .80),
]
SONIDO_TORRETA_LOOP = cargar_audio(('torreta.wav', 'turret.wav'), .30, loop=True)
SONIDO_RECARGA = cargar_audio('reload.wav', .65)
SONIDO_CAMBIO = cargar_audio(('weapons_switch.wav', 'weapon_switch.wav'), .50)
SONIDO_SIN_MUNICION = cargar_audio('empty.wav', .60)


# =====================================================================
