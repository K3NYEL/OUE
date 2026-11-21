# OUE — Cazador de Oleadas

OUE es un shooter de supervivencia por oleadas. El repositorio conserva dos implementaciones separadas:

- `main`: version original desarrollada en Python + Ursina.
- `luau-migration`: port en desarrollo para Roblox Studio usando Luau + Rojo.

## Roblox / Luau

Consulta [ROBLOX_MIGRATION.md](ROBLOX_MIGRATION.md) para requisitos, estructura, controles, sincronizacion con Rojo y estado de la migracion.

Proyecto Rojo: `default.project.json`.

## Python / Ursina

Para ejecutar la version original, cambia a la rama `main`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

En Windows: `.venv\Scripts\activate`.

## Nota

La version Luau ya implementa el nucleo de juego y la interfaz FPS inicial, pero requiere pruebas en Roblox Studio. Los WAV locales necesitan publicarse en Roblox y configurarse con sus asset IDs antes de recuperar el audio original.
