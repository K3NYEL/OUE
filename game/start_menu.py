"""Pantalla de inicio de OUE.

Se mantiene separada del motor para que el menú pueda evolucionar sin tocar
la lógica de combate, oleadas, armas o estado de la partida.
"""
from ursina import Button, Entity, Text, Vec4, camera, color, window


def install(engine):
    """Instala el menú interactivo y oculta el menú de texto legado."""
    engine.ui_menu.enabled = False
    engine.hud.enabled = False
    engine.jugador.enabled = False
    engine.mouse.visible = True
    engine.mouse.locked = False

    ar = window.aspect_ratio
    left = -ar * 0.37
    right = ar * 0.22

    root = Entity(parent=camera.ui, name="oue_start_menu")
    Entity(
        parent=root,
        model="quad",
        scale=(4, 2),
        color=Vec4(0.012, 0.018, 0.028, 0.94),
        z=0.8,
    )

    # Identidad visual y acento lateral.
    Entity(
        parent=root,
        model="quad",
        position=(left - 0.10, 0, 0.72),
        scale=(0.012, 1.25),
        color=color.rgb(225, 65, 75),
    )
    Text(
        "O U E  /  PROTOCOLO DE SUPERVIVENCIA",
        parent=root,
        position=(left, 0.34),
        scale=0.78,
        color=color.rgb(225, 75, 88),
    )
    Text(
        "CAZADOR\nDE OLEADAS",
        parent=root,
        position=(left, 0.08),
        scale=2.65,
        color=color.white,
    )
    Text(
        "SOBREVIVE. ADÁPTATE. RESISTE.",
        parent=root,
        position=(left, -0.18),
        scale=0.82,
        color=color.rgb(170, 181, 198),
    )

    # Panel de misión.
    Entity(
        parent=root,
        model="quad",
        position=(right, 0.015, 0.72),
        scale=(ar * 0.37, 0.70),
        color=Vec4(0.055, 0.068, 0.09, 0.96),
    )
    Entity(
        parent=root,
        model="quad",
        position=(right - ar * 0.185, 0.015, 0.70),
        scale=(0.004, 0.70),
        color=color.rgb(225, 65, 75),
    )
    Text(
        "MISIÓN",
        parent=root,
        position=(right - ar * 0.16, 0.285),
        scale=0.95,
        color=color.rgb(225, 75, 88),
    )
    Text(
        "Resiste oleadas cada vez más difíciles.\n"
        "Cada cinco oleadas aparece un jefe.\n\n"
        "Consigue créditos, mejora tu equipo y\n"
        "prepara tu estrategia entre oleadas.\n\n"
        "Los disparos a la cabeza infligen daño\n"
        "adicional. Busca suministros en la arena.",
        parent=root,
        position=(right - ar * 0.16, 0.19),
        scale=0.72,
        color=color.rgb(220, 226, 235),
    )
    Entity(
        parent=root,
        model="quad",
        position=(right, -0.205, 0.69),
        scale=(ar * 0.31, 0.002),
        color=color.rgb(65, 75, 91),
    )
    Text(
        "RÉCORD PERSONAL",
        parent=root,
        position=(right - ar * 0.16, -0.275),
        scale=0.62,
        color=color.rgb(150, 163, 181),
    )
    Text(
        f"{engine.S.record:,}".replace(",", " "),
        parent=root,
        position=(right - ar * 0.16, -0.365),
        scale=0.95,
        color=color.white,
    )

    def make_button(label, y, button_color, hover_color, callback, height=0.065):
        button = Button(
            text=label,
            parent=root,
            position=(left + ar * 0.12, y, -0.1),
            scale=(ar * 0.34, height),
            color=button_color,
            highlight_color=hover_color,
            pressed_color=color.rgb(105, 28, 40),
        )
        button.on_click = callback
        return button

    def start_game():
        root.enabled = False
        engine.iniciar()

    make_button(
        "INICIAR PARTIDA",
        -0.285,
        color.rgb(174, 38, 54),
        color.rgb(220, 55, 72),
        engine.iniciar,
        0.075,
    )

    # Panel secundario de controles.
    controls = Entity(parent=root, enabled=False)
    Entity(
        parent=controls,
        model="quad",
        scale=(4, 2),
        color=Vec4(0.008, 0.012, 0.020, 0.98),
        z=0.2,
    )
    Entity(
        parent=controls,
        model="quad",
        scale=(1.22, 0.82),
        color=color.rgb(20, 27, 38),
        z=0.1,
    )
    Entity(
        parent=controls,
        model="quad",
        position=(-0.605, 0, 0.08),
        scale=(0.008, 0.82),
        color=color.rgb(225, 65, 75),
    )
    Text(
        "CONTROLES DE CAMPO",
        parent=controls,
        position=(-0.48, 0.31),
        scale=1.45,
        color=color.white,
    )
    Text(
        "MOVIMIENTO       WASD\n"
        "Correr                 SHIFT\n"
        "Saltar                   ESPACIO\n"
        "Disparar                CLIC IZQUIERDO\n"
        "Apuntar                 CLIC DERECHO\n"
        "Recargar                R\n"
        "Cambiar arma          1–5 / RUEDA\n"
        "Cámara                  V (FPS / TPS)\n\n"
        "HABILIDADES\n"
        "Dash  Q       Onda de choque  E\n"
        "Torreta  F    Modo furia  C\n\n"
        "Tienda  B (durante preparación)\n"
        "Pausa  ESC / P",
        parent=controls,
        position=(-0.48, 0.20),
        scale=0.78,
        color=color.rgb(220, 226, 235),
    )
    close_button = Button(
        text="VOLVER",
        parent=controls,
        position=(0.43, -0.34, -0.1),
        scale=(0.28, 0.065),
        color=color.rgb(174, 38, 54),
        highlight_color=color.rgb(220, 55, 72),
    )
    close_button.on_click = lambda: setattr(controls, "enabled", False)

    make_button(
        "CONTROLES",
        -0.375,
        color.rgb(37, 46, 61),
        color.rgb(58, 70, 89),
        lambda: setattr(controls, "enabled", True),
        0.060,
    )
    make_button(
        "SALIR",
        -0.455,
        color.rgb(28, 33, 43),
        color.rgb(54, 61, 74),
        engine._application.quit,
        0.052,
    )

    return root
