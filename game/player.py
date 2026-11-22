"""Personaje 3D del jugador: cuerpo, cabeza, brazos y piernas (cubos tacticos).

Jerarquia (todo cuelga del FirstPersonController, que sigue haciendo el movimiento):
  jugador
  |- raiz            cuerpo: torso, piernas (giran con el jugador)
  `- camera_pivot    ojos (cabeceo del raton)
     |- cabeza       sigue el cabeceo
     `- rig          hombros: brazos + manos + arma (animables como un bloque)
Un solo personaje; FPS/TPS solo cambian que partes se dibujan (ver player_camera).
"""
from ursina import Entity, Vec3, color
import math

from .config import PERSONAJE


def _caja(padre, pos, esc, col, **kw):
    return Entity(parent=padre, model='cube', position=pos, scale=esc, color=col, **kw)


class Personaje:
    def __init__(self, jugador):
        c = PERSONAJE
        self.jugador = jugador
        self.pivote = jugador.camera_pivot

        # --- cuerpo ---
        self.raiz = Entity(parent=jugador)
        self.torso = Entity(parent=self.raiz, position=(0, .95, 0))        # pivote en la cadera
        _caja(self.torso, (0, .40, 0), (.46, .80, .26), c['ropa'])
        _caja(self.torso, (0, .45, .02), (.50, .52, .30), c['chaleco'])     # chaleco
        _caja(self.torso, (0, .45, -.20), (.34, .46, .14), c['chaleco'])    # mochila
        _caja(self.torso, (.27, .70, 0), (.06, .12, .12), c['acento'])      # brazalete
        _caja(self.torso, (0, .85, 0), (.14, .16, .14), c['ropa'])          # cuello
        self.pierna_i = self._pierna(-.14)
        self.pierna_d = self._pierna(.14)

        # --- cabeza (sigue el cabeceo de la camara) ---
        self.cabeza = Entity(parent=self.pivote)
        _caja(self.cabeza, (0, 0, 0), (.32, .32, .32), c['casco'])
        _caja(self.cabeza, (0, -.02, .165), (.28, .10, .03), c['visor'])
        _caja(self.cabeza, (0, .17, 0), (.34, .05, .34), c['casco'])

        # --- hombros / brazos / manos (rig animable) ---
        self.rig = Entity(parent=self.pivote, position=(0, -.30, 0))
        self.hombro_d = Entity(parent=self.rig, position=(.28, 0, 0))
        self.hombro_i = Entity(parent=self.rig, position=(-.28, 0, 0))
        self.mano_d = Entity(parent=self.rig, position=(.38, -.04, .72))    # ancla del arma
        self.mano_i = Entity(parent=self.rig, position=(.30, -.17, 1.05))
        self._brazo_d = self._brazo()
        self._brazo_i = self._brazo()
        for m in (self.mano_d, self.mano_i):
            _caja(m, (0, 0, 0), (.11, .11, .11), c['guante'])
        self._orientar(self._brazo_d, self.hombro_d, self.mano_d)
        self.apuntar_mano_izq(self.mano_i.position)

    # ---------------------------------------------------------------
    def _pierna(self, x):
        p = Entity(parent=self.raiz, position=(x, .95, 0))                   # pivote en la cadera
        c = PERSONAJE
        _caja(p, (0, -.47, 0), (.20, .95, .24), c['ropa'])
        _caja(p, (0, -.90, .04), (.22, .12, .32), c['guante'])               # bota
        return p

    def _brazo(self):
        # origin_z=-.5: el cubo crece desde su origen hacia +z (se orienta al escalar)
        return Entity(parent=self.rig, model='cube', origin_z=-.5, color=PERSONAJE['ropa'])

    def _orientar(self, brazo, hombro, mano):
        """Apunta el brazo del hombro a la mano (ambos viven en el espacio del rig)."""
        d = mano.position - hombro.position
        largo = max(.01, d.length())
        brazo.position = hombro.position
        brazo.rotation = (-math.degrees(math.asin(d.y / largo)), math.degrees(math.atan2(d.x, d.z)), 0)
        brazo.scale = (.09, .09, largo)

    def apuntar_mano_izq(self, pos):
        self.mano_i.position = Vec3(*pos)
        self._orientar(self._brazo_i, self.hombro_i, self.mano_i)

    # ---------------------------------------------------------------
    def mostrar_cuerpo(self, visible):
        """FPS: solo brazos y arma. TPS: personaje completo."""
        if self.raiz.enabled != visible:
            self.raiz.enabled = visible
            self.cabeza.enabled = visible
