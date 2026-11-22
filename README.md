# OUE — Cazador de Oleadas

OUE es un juego de supervivencia por oleadas desarrollado en **Python + Ursina**.

## Requisitos

- Python 3.10+
- Ursina

## Instalación y ejecución

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

En Windows, activa el entorno con:

```powershell
.venv\Scripts\Activate.ps1
```

## Estructura

- `main.py`: punto de entrada.
- `game/engine.py`: motor y ciclo principal.
- `game/config.py`: configuración del juego.
- `game/audio.py`: carga y reproducción de audio.

- `game/player.py`: personaje 3D (cuerpo, cabeza, brazos, piernas, ancla de la mano).
- `game/player_animation.py`: animacion procedural (idle, caminar, correr, saltar, caer).
- `game/player_camera.py`: camara FPS/TPS con colision y mezcla suave.
- `game/weapon_mount.py`: montaje del arma en la mano y animaciones equipar/recarga/retroceso.
- `game/modelos.py`: carga de modelos `.glb` de armas.

## Perspectivas

`V` alterna FPS/TPS (`TECLA_CAMARA` y `CAMARA_TPS` en `config.py`). El movimiento sigue siendo el
`FirstPersonController`; el raton orbita la camara alrededor del personaje. En TPS, apuntar
(clic derecho) acerca la camara a FPS para usar las miras. Los disparos salen de los ojos y
convergen en la mira, tambien en TPS.

El proyecto mantiene Python + Ursina como única implementación.