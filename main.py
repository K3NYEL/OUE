from game import engine


def update():
    engine.update()


def input(key):
    engine.input(key)


if __name__ == "__main__":
    engine.run()
