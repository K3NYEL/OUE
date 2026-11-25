from game import engine
from game.start_menu import install as install_start_menu


def update():
    engine.update()


def input(key):
    engine.input(key)


if __name__ == "__main__":
    install_start_menu(engine)
    engine.run()
