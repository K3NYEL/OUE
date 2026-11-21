# Cazador de Oleadas

Shooter en primera persona desarrollado con Python y Ursina.

## Instalación y ejecución

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

En Windows: `.venv\Scripts\activate`.

## Estructura

- `main.py`: punto de entrada.
- `game/config.py`: configuración de armas, enemigos y datos.
- `game/audio.py`: carga y reproducción segura de sonidos.
- `game/engine.py`: escena, entidades, combate, interfaz, tienda, oleadas y bucle principal.

Audio opcional en `assets/audio/weapons/` o `src/assets/audio/weapons/`.
