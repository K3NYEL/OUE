from game import engine
from game.start_menu import install as install_start_menu


start_menu_ui = None


def update():
    engine.update()


def input(key):
    if engine.S.estado == "menu" and key == "enter" and start_menu_ui is not None:
        start_menu_ui.enabled = False
    engine.input(key)


if __name__ == "__main__":
    start_menu_ui = install_start_menu(engine)
    engine.run()
