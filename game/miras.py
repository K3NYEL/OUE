"""Miras tacticas (clic derecho): una reticula propia por arma.

pistola -> punto rojo | rifle -> holografica | escopeta -> alza de cuenta
francotirador -> mil-dot 4x | lanzagranadas -> visor balistico
"""
from ursina import Entity, Texture, Vec4, color, window
from PIL import Image, ImageDraw

ROJO = color.rgb32(255, 70, 70)
NARANJA = color.rgb32(255, 170, 60)
NEGRO = color.black
BLANCO = color.white


def px(n):
    """n pixeles en unidades de camera.ui (1 = alto de la ventana)."""
    return n / max(1, window.size[1])


def _textura_anillo(n=256, grosor=8):
    """Anillo blanco con borde suavizado (se tine con el color de la entidad)."""
    ss = 4
    img = Image.new('L', (n * ss, n * ss), 0)
    d = ImageDraw.Draw(img)
    r = n * ss // 2 - ss
    d.ellipse((ss, ss, 2 * r + ss, 2 * r + ss), fill=255)
    r2 = r - grosor * ss
    c = n * ss // 2
    d.ellipse((c - r2, c - r2, c + r2, c + r2), fill=0)
    img = img.resize((n, n), Image.LANCZOS)
    rgba = Image.new('RGBA', (n, n), (255, 255, 255, 0))
    rgba.putalpha(img)
    return Texture(rgba)


def _textura_mascara(n=1024, radio=.46):
    """Cuadrado negro con un circulo transparente: bordes oscuros del visor."""
    ss = 2
    hueco = Image.new('L', (n * ss, n * ss), 0)
    c = n * ss // 2
    r = int(n * ss * radio)
    ImageDraw.Draw(hueco).ellipse((c - r, c - r, c + r, c + r), fill=255)
    hueco = hueco.resize((n, n), Image.LANCZOS)
    alfa = hueco.point(lambda v: 255 - v)
    rgba = Image.new('RGBA', (n, n), (0, 0, 0, 255))
    rgba.putalpha(alfa)
    return Texture(rgba)


def _rect(padre, w, h, x=0, y=0, col=BLANCO, z=-.01):
    return Entity(parent=padre, model='quad', scale=(w, h), position=(x, y, z), color=col)


def _punto(padre, diametro, x=0, y=0, col=BLANCO, z=-.01):
    return Entity(parent=padre, model='circle', scale=diametro, position=(x, y, z), color=col)


def _punto_rojo(p):
    _punto(p, px(2), col=ROJO)


def _holografica(p):
    Entity(parent=p, model='quad', texture=_textura_anillo(), scale=px(76), color=ROJO, z=-.01)
    _punto(p, px(3), col=ROJO)
    for sx, sy, x, y in ((px(10), px(2), -px(52), 0), (px(10), px(2), px(52), 0),
                         (px(2), px(10), 0, px(52)), (px(2), px(10), 0, -px(52))):
        _rect(p, sx, sy, x, y, ROJO)


def _alza_cuenta(p):
    _punto(p, px(7), 0, px(26))                      # punto de mira
    for x in (-px(14), px(14)):                      # dos postes del alza
        _rect(p, px(4), px(34), x, -px(12))


def _mildot(p):
    # Bordes oscuros: cuadrado con circulo transparente + barras laterales.
    Entity(parent=p, model='quad', texture=_textura_mascara(), scale=(1, 1), z=.5)
    for lado in (-1.5, 1.5):
        _rect(p, 2, 1, lado, 0, NEGRO, z=.5)
    largo = .86
    _rect(p, largo, px(1.5), col=NEGRO)              # cruz fina
    _rect(p, px(1.5), largo, col=NEGRO)
    for k in (1, 2, 3, 4):                           # marcas mil-dot
        d = k * .07
        for sx, sy in ((d, 0), (-d, 0), (0, d), (0, -d)):
            _punto(p, px(5), sx, sy, NEGRO)


def _visor_balistico(p):
    _rect(p, px(2), px(46), 0, px(30), NARANJA)       # vertical hacia arriba
    _rect(p, px(64), px(2), 0, 0, NARANJA)            # horizontal
    for i, ancho in enumerate((44, 32, 20), start=1):  # escalas de caida 1-3
        _rect(p, px(ancho), px(2), 0, -px(18) * i, NARANJA)


CONSTRUCTORES = {
    'punto_rojo': _punto_rojo,
    'holografica': _holografica,
    'alza_cuenta': _alza_cuenta,
    'mildot': _mildot,
    'visor_balistico': _visor_balistico,
}


def crear_miras(padre):
    """Crea todas las reticulas ocultas bajo `padre`. Devuelve {nombre: Entity}."""
    miras = {}
    for nombre, construir in CONSTRUCTORES.items():
        raiz = Entity(parent=padre, enabled=False)
        construir(raiz)
        miras[nombre] = raiz
    return miras
