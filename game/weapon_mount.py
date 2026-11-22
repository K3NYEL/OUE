"""Montaje de armas en la mano del personaje.

`pivote` (alias arma_modelo en engine.py) cuelga de la mano derecha: el arma pertenece al
personaje, no a la camara. Cada arma se coloca sola segun su entrada en ARMAS:
  - sin `modelo`: cubo provisional (escala/color de siempre)
  - con `modelo=dict(archivo, escala, pos, rot, colores, mano_izq)`: modelo .glb
Animaciones procedurales (equipar, reposo, disparo, recarga) sobre el rig de brazos;
`evento()` es el punto de enganche para animaciones propias de un modelo.
"""
from ursina import Entity, color, lerp

from .modelos import cargar_modelo_arma

T_EQUIPAR = .30
ROT_EQUIPAR = 55     # grados que baja el arma antes de subirla al equipar
ROT_RECARGA = 38


class MontajeArma:
    def __init__(self, personaje):
        self.p = personaje
        self.pivote = Entity(parent=personaje.mano_d)
        self.cubo = Entity(parent=self.pivote, model='cube', position=(0, 0, .18))
        self.canon = Entity(parent=self.cubo, model='cube', position=(0, .25, .7),
                            scale=(.6, .4, .7), color=color.black)
        self.fogonazo = Entity(parent=self.pivote, model='quad', position=(0, .02, 1.0),
                               scale=.35, color=color.yellow, billboard=True, enabled=False)
        self._glb = {}
        self._t_equipar = 0.0

    def equipar(self, i, a, animar=True):
        for ent in self._glb.values():
            if ent:
                ent.enabled = False
        cfg = a.get('modelo')
        if cfg and i not in self._glb:
            self._glb[i] = cargar_modelo_arma(cfg, self.pivote)
        modelo = self._glb.get(i) if cfg else None
        if modelo:
            self.cubo.enabled = False
            modelo.enabled = True
            mano = cfg.get('mano_izq', (.30, -.17, 1.05))
        else:
            self.cubo.enabled = True
            self.cubo.color = a['color']
            self.cubo.scale = a['escala']
            mano = (.25, -.10, .90 + max(0, a['escala'][2] - .5) * .35)
        self.p.apuntar_mano_izq(mano)
        self.fogonazo.z = cfg.get('boca', 1.0) if cfg else 0.9 + a['escala'][2] * .5
        if animar:
            self.evento('equipar')

    def evento(self, nombre):
        """Gancho de animaciones: 'equipar' | 'disparo' | 'recarga' (ampliable por modelo)."""
        if nombre == 'equipar':
            self._t_equipar = T_EQUIPAR

    def actualizar(self, dt, retroceso, recargando):
        self._t_equipar = max(0.0, self._t_equipar - dt)
        objetivo = ROT_RECARGA if recargando else 0
        objetivo += ROT_EQUIPAR * (self._t_equipar / T_EQUIPAR)
        rig = self.p.rig
        rig.rotation_x = lerp(rig.rotation_x, objetivo, min(1, 12 * dt))
        rig.z = -0.12 * retroceso
