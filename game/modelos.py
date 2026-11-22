"""Carga de modelos 3D (.glb) de las armas para la vista en primera persona."""
from pathlib import Path

from ursina import Entity, color, load_model

_RAIZ = Path(__file__).resolve().parent.parent

# Acepta las dos grafias de la carpeta (el repo la tiene como 'wepaons_models')
# y que los assets esten en la raiz o dentro de src/.
_CARPETAS = tuple(
    _RAIZ / base / nombre
    for base in ('src/assets', 'assets')
    for nombre in ('weapons_models', 'wepaons_models')
)
MODELOS_DIR = next((c for c in _CARPETAS if c.is_dir()), _CARPETAS[0])


def cargar_modelo_arma(cfg, padre):
    """Crea la Entity del modelo bajo `padre`. Devuelve None si no se puede cargar.

    cfg = dict(archivo=..., escala=..., pos=(x, y, z), rot=(rx, ry, rz))
    """
    ruta = MODELOS_DIR / cfg['archivo']
    if not ruta.is_file():
        print(f'[MODELO] No encontrado: {ruta}')
        return None
    try:
        # Ursina no acepta rutas absolutas en model=: hay que pasar la carpeta a load_model.
        modelo = load_model(cfg['archivo'], folder=MODELOS_DIR)
        if modelo is None:
            print(f'[MODELO] Ursina no pudo leer: {ruta}')
            return None
        ent = Entity(
            parent=padre,
            model=modelo,
            scale=cfg.get('escala', 1),
            position=cfg.get('pos', (0, 0, 0)),
            rotation=cfg.get('rot', (0, 0, 0)),
            color=color.white,
            enabled=False,
        )
    except Exception as exc:
        print(f'[MODELO] No se pudo cargar {ruta}: {exc}')
        return None
    _pintar_piezas(ent, cfg.get('colores', {}))
    return ent


def _pintar_piezas(ent, colores):
    """Ursina no usa los materiales del .glb (render sin luz): se tine cada pieza por nombre."""
    for nombre, col in colores.items():
        pieza = ent.model.find(f'**/{nombre}')
        if pieza.isEmpty():
            print(f'[MODELO] Pieza no encontrada: {nombre}')
            continue
        pieza.setColorScale(col)