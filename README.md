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

El proyecto mantiene Python + Ursina como única implementación.