"""Modelo de retroceso, bloom y dispersion en cono.

No depende de Ursina para poder probarse por separado. Los angulos van en
grados; las direcciones son tuplas (x, y, z).
"""
import math
import random


def punto_en_disco(radio, rng=random):
    """Punto uniforme dentro de un disco (sqrt evita agrupar en el centro)."""
    ang = rng.uniform(0, math.tau)
    r = radio * math.sqrt(rng.random())
    return r * math.cos(ang), r * math.sin(ang)


def direccion_en_cono(fwd, right, up, dispersion, rng=random):
    """Desvia `fwd` dentro de un cono uniforme.

    Antes se sumaba un vector aleatorio de un cubo: los disparos se agrupaban
    en las diagonales. Con un disco, el reparto es el mismo en todas direcciones.
    """
    if dispersion <= 0:
        return fwd
    dx, dy = punto_en_disco(dispersion, rng)
    v = [fwd[i] + right[i] * dx + up[i] * dy for i in range(3)]
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return v[0] / n, v[1] / n, v[2] / n


class Retroceso:
    """Retroceso acumulado de camara (vertical + horizontal) con recuperacion.

    `x` es lo que la mira ha subido (grados, positivo = arriba) e `y` el giro
    horizontal acumulado. `recuperar` devuelve cuanto hay que devolver este
    frame: solo se revierte lo acumulado, nunca el movimiento del jugador.
    """

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.recup = 8.0

    def disparar(self, kick_v, kick_h, tope=0.0, recup=8.0, rng=random):
        """Registra un disparo. Devuelve (sube, giro) a aplicar a la camara."""
        sube = kick_v
        if tope > 0:
            sube = max(0.0, min(sube, tope - self.x))   # tope de ascenso por rafaga
        giro = rng.uniform(-kick_h, kick_h)
        self.x += sube
        self.y += giro
        self.recup = recup
        return sube, giro

    def corregir(self, sube_pedido, sube_real):
        """La camara puede toparse con su limite; no se acumula lo que no subio."""
        self.x -= sube_pedido - sube_real

    def recuperar(self, dt):
        """x -= x * (1 - e^(-R*dt)). Devuelve (dx, dy) a devolver a la camara."""
        f = 1.0 - math.exp(-self.recup * dt)
        dx, dy = self.x * f, self.y * f
        self.x -= dx
        self.y -= dy
        return dx, dy

    def reiniciar(self):
        self.x = self.y = 0.0


class Bloom:
    """La dispersion sube un % de la base por disparo y decae con el tiempo."""

    def __init__(self, por_disparo=.15, decae=.4, maximo=1.0):
        self.por_disparo = por_disparo
        self.decae = decae
        self.maximo = maximo
        self.valor = 0.0

    @property
    def factor(self):
        return 1.0 + self.valor

    def disparo(self):
        self.valor = min(self.maximo, self.valor + self.por_disparo)

    def actualizar(self, dt):
        # Cada disparo se "olvida" en `decae` segundos.
        self.valor = max(0.0, self.valor - dt * self.por_disparo / self.decae)

    def reiniciar(self):
        self.valor = 0.0
