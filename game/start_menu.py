"""Menú principal de OUE, separado de la lógica de la partida."""
from ursina import Button, Entity, Text, Vec4, camera, color, window

RED = color.rgb(226, 52, 69)
RED_HOVER = color.rgb(248, 72, 88)
INK = color.rgb(8, 11, 17)
PANEL = color.rgb(17, 23, 33)
PANEL_ALT = color.rgb(25, 33, 46)
WHITE = color.rgb(239, 243, 249)
MUTED = color.rgb(153, 166, 184)
LINE = color.rgb(48, 59, 75)


def panel(parent, x, y, w, h, tint, z=0):
    return Entity(parent=parent, model="quad", position=(x, y, z),
                  scale=(w, h), color=tint)


def label(parent, value, x, y, scale=1, tint=WHITE):
    return Text(value, parent=parent, position=(x, y), scale=scale, color=tint)


def install(engine):
    """Instala el menú interactivo sin modificar el motor de combate."""
    engine.ui_menu.enabled = False
    engine.hud.enabled = False
    engine.jugador.enabled = False
    engine.mouse.visible = True
    engine.mouse.locked = False

    ar = max(window.aspect_ratio, 1.25)
    root = Entity(parent=camera.ui, name="oue_start_menu")

    # Fondo dividido en dos zonas y marco de identidad.
    panel(root, 0, 0, 4, 2, Vec4(0.012, 0.017, 0.026, 1), 0.9)
    panel(root, -ar * 0.30, 0, ar * 0.40, 2,
          Vec4(0.025, 0.032, 0.046, 1), 0.8)
    panel(root, ar * 0.20, 0, ar * 0.54, 2,
          Vec4(0.017, 0.023, 0.034, 1), 0.8)
    panel(root, -ar * 0.10, 0, 0.002, 1.72, LINE, 0.7)
    panel(root, -ar * 0.475, 0, 0.006, 1.62, RED, 0.7)
    panel(root, ar * 0.47, 0, 0.006, 1.62, RED, 0.7)
    panel(root, ar * 0.20, 0.43, ar * 0.50, 0.002, LINE, 0.7)
    panel(root, ar * 0.20, -0.43, ar * 0.50, 0.002, LINE, 0.7)

    # Identidad y título.
    label(root, "O U E", -ar * 0.435, 0.405, 1.35, RED)
    label(root, "UNDER OUR EYES  /  SURVIVAL PROTOCOL",
          -ar * 0.345, 0.414, 0.58, MUTED)
    label(root, "CAZADOR", -ar * 0.435, 0.19, 2.5, WHITE)
    label(root, "DE OLEADAS", -ar * 0.435, 0.055, 2.5, WHITE)
    label(root, "SOBREVIVE. ADÁPTATE. RESISTE.",
          -ar * 0.43, -0.055, 0.72, MUTED)

    # Indicadores del modo.
    for x, heading, value in (
        (-ar * 0.43, "MODO", "SUPERVIVENCIA"),
        (-ar * 0.23, "OBJETIVO", "RESISTIR"),
        (-ar * 0.03, "AMENAZA", "CRECIENTE"),
    ):
        label(root, heading, x, -0.19, 0.52, MUTED)
        label(root, value, x, -0.265, 0.62, WHITE)

    def make_button(text, x, y, w, h, base, hover, callback, parent=root):
        button = Button(text=text, parent=parent, position=(x, y, -0.15),
                        scale=(w, h), color=base, highlight_color=hover,
                        pressed_color=color.rgb(120, 27, 42))
        button.on_click = callback
        return button

    def start_game():
        root.enabled = False
        engine.iniciar()

    make_button("INICIAR PARTIDA   >", -ar * 0.315, -0.375,
                ar * 0.30, 0.085, RED, RED_HOVER, start_game)

    # Panel informativo.
    label(root, "01  /  INFORME DE MISIÓN", ar * 0.005, 0.335, 0.68, RED)
    label(root, "La arena no perdona.", ar * 0.005, 0.235, 1.0, WHITE)
    label(root,
          "Enfréntate a oleadas cada vez más difíciles.\n"
          "Cada cinco oleadas aparece un jefe.\n\n"
          "Elimina enemigos para conseguir créditos.\n"
          "Úsalos durante la preparación para mejorar\n"
          "armas, equipo y habilidades.\n\n"
          "Apunta a la cabeza para infligir daño extra.",
          ar * 0.005, 0.155, 0.64, MUTED)
    panel(root, ar * 0.20, -0.205, ar * 0.43, 0.002, LINE, 0.65)
    label(root, "RÉCORD PERSONAL", ar * 0.005, -0.285, 0.56, MUTED)
    label(root, f"{engine.S.record:,}".replace(",", " "),
          ar * 0.005, -0.385, 1.15, WHITE)
    label(root, "BEST SCORE", ar * 0.30, -0.365, 0.48, MUTED)

    # Controles en una capa independiente.
    controls = Entity(parent=root, enabled=False, name="oue_controls_overlay")
    panel(controls, 0, 0, 4, 2, Vec4(0.006, 0.009, 0.016, 0.985), 0.2)
    panel(controls, 0, 0, 1.18, 0.86, PANEL, 0.1)
    panel(controls, -0.585, 0, 0.008, 0.86, RED, 0.05)
    label(controls, "CONTROLES DE CAMPO", -0.48, 0.325, 1.05, WHITE)
    label(controls, "MOVIMIENTO", -0.47, 0.20, 0.62, RED)
    label(controls, "WASD mover   ·   SHIFT correr   ·   ESPACIO saltar",
          -0.47, 0.12, 0.55, WHITE)
    label(controls, "COMBATE", -0.47, 0.025, 0.62, RED)
    label(controls, "CLIC IZQ. disparar   ·   CLIC DER. apuntar\n"
                    "R recargar   ·   1–5 / RUEDA cambiar arma\n"
                    "V alternar cámara FPS / TPS",
          -0.47, -0.055, 0.58, WHITE)
    label(controls, "HABILIDADES Y SISTEMAS", -0.47, -0.19, 0.62, RED)
    label(controls, "Q Dash   ·   E Onda   ·   F Torreta   ·   C Furia\n"
                    "B tienda durante preparación   ·   ESC / P pausa",
          -0.47, -0.27, 0.56, WHITE)
    make_button("VOLVER", 0.40, -0.355, 0.25, 0.06,
                RED, RED_HOVER,
                lambda: setattr(controls, "enabled", False), controls)

    make_button("CONTROLES", -ar * 0.13, -0.375, ar * 0.16, 0.085,
                PANEL_ALT, color.rgb(43, 55, 72),
                lambda: setattr(controls, "enabled", True))
    make_button("SALIR", -ar * 0.015, -0.375, ar * 0.075, 0.085,
                color.rgb(29, 35, 46), color.rgb(53, 62, 77),
                engine._application.quit)

    label(root, "BUILD / OUE", -ar * 0.435, -0.485, 0.45, MUTED)
    label(root, "PREPÁRATE PARA LA SIGUIENTE OLEADA",
          ar * 0.005, -0.485, 0.45, MUTED)
    return root
