# Cazador de Oleadas

Shooter en primera persona desarrollado con Python y Ursina.

## Requisitos

- Python 3.10 o superior
- Ursina: `pip install -r requirements.txt`

## Ejecutar

```bash
python main.py
```

## Estructura

```text
OUE/
├── main.py
├── requirements.txt
└── game/
    ├── __init__.py
    ├── config.py
    ├── audio.py
    └── engine.py
```

Los efectos de audio son opcionales. Si falta un archivo, el juego continúa y muestra un aviso en consola.

## Controles

- WASD: movimiento; Shift: correr; Espacio: saltar.
- Clic izquierdo: disparar; clic derecho: apuntar.
- R: recargar; 1-5 o rueda: cambiar arma.
- Q/E/F/C: habilidades; B: tienda entre oleadas; Esc/P: pausa.
