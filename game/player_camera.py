"""Camaras FPS y TPS sobre el mismo FirstPersonController (sin segunda camara).

La camara de Ursina cuelga de `camera_pivot`, asi que el raton la orbita alrededor del
personaje. FPS = camara en el pivote; TPS = desplazada atras/arriba/hombro. Pasar de una
a otra es una mezcla continua (`mezcla` 0..1), sin crear ni destruir nada.
En TPS, apuntar (clic derecho) acerca la camara a FPS, asi las miras tacticas funcionan.
"""
from ursina import Vec3, camera, lerp, raycast, clamp

from .config import CAMARA_TPS


class CamaraJugador:
    def __init__(self, jugador, personaje, es_ignorable):
        self.j = jugador
        self.p = personaje
        self.pivote = jugador.camera_pivot
        self.es_ignorable = es_ignorable     # p. ej. enemigos: no deben acercar la camara
        self.cfg = CAMARA_TPS
        self.modo = 'fps'
        self.mezcla = 0.0
        self.recorte = 1.0
        self._en_reposo = False

    def alternar(self):
        self.modo = 'tps' if self.modo == 'fps' else 'fps'
        return self.modo

    @property
    def ojo(self):
        return self.pivote.world_position

    def _rayo(self, origen, dir, dist, ignorar):
        ign = list(ignorar)
        hit = raycast(origen, dir, distance=dist, ignore=ign, debug=False)
        for _ in range(4):
            if hit.hit and self.es_ignorable(hit.entity):
                ign.append(hit.entity)
                hit = raycast(origen, dir, distance=dist, ignore=ign, debug=False)
            else:
                break
        return hit

    def actualizar(self, dt, ads=False):
        c = self.cfg
        objetivo = 1.0 if (self.modo == 'tps' and not ads) else 0.0
        self.mezcla = lerp(self.mezcla, objetivo, min(1, c['suavizado'] * dt))
        if abs(self.mezcla - objetivo) < .004:
            self.mezcla = objetivo
        m = self.mezcla

        if m == 0:
            self.p.mostrar_cuerpo(False)
            if not self._en_reposo:
                camera.position = Vec3(0, 0, 0)
                self._en_reposo = True
            return
        self._en_reposo = False

        local = Vec3(c['hombro'] * m, c['altura'] * m, -c['distancia'] * m)
        piv = self.pivote
        ojo = piv.world_position
        destino = ojo + piv.right * local.x + piv.up * local.y + piv.forward * local.z
        d = destino - ojo
        largo = d.length()
        k = 1.0
        if largo > .01:
            hit = self._rayo(ojo, d / largo, largo + c['margen'], [self.j])
            if hit.hit:
                k = clamp((hit.distance - c['margen']) / largo, 0, 1)
        # acerca de golpe contra una pared; se aleja suavemente al despejarse
        self.recorte = k if k < self.recorte else lerp(self.recorte, k, min(1, 6 * dt))
        camera.position = local * self.recorte
        self.p.mostrar_cuerpo(m * self.recorte > c['umbral_cuerpo'])

    def apuntar(self):
        """(origen, direccion) del disparo: sale de los ojos y converge en la mira."""
        fwd = Vec3(*camera.forward)
        if self.mezcla < .05:
            return camera.world_position, fwd
        cam = camera.world_position
        hit = raycast(cam, fwd, distance=120, ignore=[self.j], debug=False)
        punto = hit.world_point if hit.hit else cam + fwd * 120
        ojo = self.ojo
        d = punto - ojo
        n = d.length()
        return ojo, (d / n if n > .5 else fwd)
