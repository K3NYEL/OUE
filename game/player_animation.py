"""Animacion procedural del personaje: idle, caminar, correr, saltar y caer.

Solo mueve piernas/torso cuando el cuerpo se dibuja (TPS); los brazos (balanceo al
andar) siempre, porque en FPS son lo unico visible. La velocidad se deduce del
desplazamiento, asi sirve igual para andar, correr y el dash.
"""
import math
from ursina import lerp

IDLE, CAMINAR, CORRER, SALTAR, CAER = 'idle', 'caminar', 'correr', 'saltar', 'caer'
_AMP = {IDLE: 0, CAMINAR: 32, CORRER: 55, SALTAR: 0, CAER: 0}


class AnimadorPersonaje:
    def __init__(self, personaje, jugador):
        self.p = personaje
        self.j = jugador
        self.estado = IDLE
        self.fase = 0.0
        self.t = 0.0
        self.vel = 0.0
        self.amp = 0.0
        self.lean = 0.0
        self._x, self._y, self._z = jugador.x, jugador.y, jugador.z

    def actualizar(self, dt, correr, cuerpo_visible):
        if dt <= 0:
            return
        j, p = self.j, self.p
        self.t += dt
        dx, dy, dz = j.x - self._x, j.y - self._y, j.z - self._z
        self._x, self._y, self._z = j.x, j.y, j.z
        self.vel = lerp(self.vel, math.hypot(dx, dz) / dt, min(1, 12 * dt))

        if not getattr(j, 'grounded', True):
            self.estado = SALTAR if dy > 0 else CAER
        elif self.vel < .4:
            self.estado = IDLE
        else:
            self.estado = CORRER if correr else CAMINAR

        mov = self.estado in (CAMINAR, CORRER)
        self.fase += self.vel * dt * 1.9 if mov else 0
        self.amp = lerp(self.amp, _AMP[self.estado], min(1, 10 * dt))

        # brazos (siempre): balanceo vertical/lateral al andar
        bob = math.sin(self.fase * 2) * (.018 if self.estado == CAMINAR else .03 if mov and correr else 0)
        p.rig.y = -.30 + bob * (1 if mov else 0)
        p.rig.x = math.sin(self.fase) * (.012 if mov else 0)

        if not cuerpo_visible:
            return

        s = math.sin(self.fase) * self.amp
        if self.estado == SALTAR:
            ang_i, ang_d = 35, -10
        elif self.estado == CAER:
            ang_i = ang_d = 15
        else:
            ang_i, ang_d = s, -s
        k = min(1, 14 * dt)
        p.pierna_i.rotation_x = lerp(p.pierna_i.rotation_x, ang_i, k)
        p.pierna_d.rotation_x = lerp(p.pierna_d.rotation_x, ang_d, k)
        self.lean = lerp(self.lean, 10 if self.estado == CORRER else 0, min(1, 8 * dt))
        p.torso.rotation_x = self.lean
        p.torso.scale_y = 1 + math.sin(self.t * 1.8) * .008 * (self.estado == IDLE)
