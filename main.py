"""Punto de entrada del juego.

Ursina descubre los callbacks globales update() e input() en el módulo
principal (__main__). Como el motor vive en game.engine, estos wrappers
reenvían los eventos al motor para que teclado, mouse y actualización funcionen.
"""
from game import engine


def update():
    engine.update()


def input(key):
    engine.input(key)


if __name__ == "__main__":
    engine.run()
