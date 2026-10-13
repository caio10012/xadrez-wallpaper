"""Desenha o wallpaper: tabuleiro no centro e um cartão com a partida no canto."""

import io

import chess
import chess.svg
import gi
from PIL import Image, ImageDraw, ImageFilter, ImageFont

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402

from . import partidas

TEMAS = {
    "lichess": {
        "nome": "Lichess (azul)",
        "casas": ("#dee3e6", "#8ca2ad", "#c3d887", "#97ac77"),
        "fundo": ("#1f2733", "#0d1117"),
        "destaque": "#5fa8ec",
    },
    "chesscom": {
        "nome": "Chess.com (verde)",
        "casas": ("#ebecd0", "#739552", "#f5f682", "#b9ca43"),
        "fundo": ("#302e2b", "#161512"),
        "destaque": "#81b64c",
    },
    "madeira": {
        "nome": "Madeira clássica",
        "casas": ("#f0d9b5", "#b58863", "#cdd16a", "#aaa23b"),
        "fundo": ("#2e2219", "#120c08"),
        "destaque": "#e0a85e",
    },
}

FONTES = "/usr/share/fonts/truetype/"
_PECAS_PT = str.maketrans("NRQK", "CTDR")


def _fonte(nome, tamanho):
    for caminho in (f"{FONTES}ubuntu/{nome}.ttf", f"{FONTES}dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            pass
    return ImageFont.load_default(tamanho)


def _gradiente(largura, altura, topo, base):
    mascara = Image.linear_gradient("L").resize((largura, altura))
    return Image.composite(Image.new("RGB", (largura, altura), base),
                           Image.new("RGB", (largura, altura), topo), mascara)


def _quebrar(draw, texto, fonte, largura_max):
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fonte) <= largura_max:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def _san_pt(tabuleiro, lance):
    return tabuleiro.san(lance).translate(_PECAS_PT)


def _tabuleiro_png(tabuleiro, ultimo, tema, tamanho):
    clara, escura, clara_ult, escura_ult = tema["casas"]
    rei_em_xeque = tabuleiro.king(tabuleiro.turn) if tabuleiro.is_check() else None
    svg = chess.svg.board(
        tabuleiro,
        lastmove=ultimo,
        check=rei_em_xeque,
        size=tamanho,
        coordinates=True,
        colors={
            "square light": clara,
            "square dark": escura,
            "square light lastmove": clara_ult,
            "square dark lastmove": escura_ult,
            "margin": "#00000000",
            "coord": "#8b949e",
        },
    )
    # librsvg (o mesmo que o GNOME usa para ícones) converte o SVG em imagem
    leitor = GdkPixbuf.PixbufLoader.new_with_type("svg")
    leitor.set_size(tamanho, tamanho)
    leitor.write(svg.encode())
    leitor.close()
    _ok, png = leitor.get_pixbuf().save_to_bufferv("png", [], [])
    return Image.open(io.BytesIO(png)).convert("RGBA")


def _texto_final(partida, tabuleiro):
    resultado = partida["resultado"]
    if tabuleiro.is_checkmate():
        return f"{resultado}  ·  Xeque-mate!"
    perdedor = "Pretas" if resultado == "1-0" else "Brancas"
    return f"{resultado}  ·  {perdedor} abandonam"


def renderizar(partida_id, ply, tema_id, largura, altura, destino,
               tamanho_tabuleiro=80, tamanho_cartao=100):
    partida = partidas.buscar(partida_id)
    lances = partidas.lances(partida_id)
    tema = TEMAS.get(tema_id, TEMAS["lichess"])
    s = altura / 768
    c = s * tamanho_cartao / 100  # escala do cartão

    tabuleiro = chess.Board()
    for lance in lances[: ply - 1]:
        tabuleiro.push(lance)
    ultimo = lances[ply - 1] if ply > 0 else None
    san = _san_pt(tabuleiro, ultimo) if ultimo else None
    if ultimo:
        tabuleiro.push(ultimo)

    img = _gradiente(largura, altura, *tema["fundo"]).convert("RGBA")

    # Cartão: canto inferior direito
    margem = int(28 * s)
    card_w = int(340 * c)
    card_x = largura - card_w - margem

    # Tabuleiro centralizado, mas sem encostar no cartão
    barra = int(32 * s)  # barra superior do GNOME
    tam = min(int(altura * tamanho_tabuleiro / 100), altura - barra - int(24 * s))
    tab_x = min((largura - tam) // 2, card_x - tam - margem)
    tab_x = max(tab_x, margem)
    tab_y = barra + (altura - barra - tam) // 2

    sombra = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rectangle(
        (tab_x + 10 * s, tab_y + 16 * s, tab_x + tam - 10 * s, tab_y + tam + 4 * s), fill=(0, 0, 0, 170))
    img = Image.alpha_composite(img, sombra.filter(ImageFilter.GaussianBlur(22 * s)))
    img.alpha_composite(_tabuleiro_png(tabuleiro, ultimo, tema, tam), (tab_x, tab_y))

    # --- conteúdo do cartão (medido antes de desenhar o fundo) ---
    f_rotulo = _fonte("Ubuntu-M", int(11 * c))
    f_titulo = _fonte("Ubuntu-B", int(25 * c))
    f_jogador = _fonte("Ubuntu-R", int(15 * c))
    f_local = _fonte("Ubuntu-L", int(13 * c))
    f_lance = _fonte("Ubuntu-B", int(22 * c))
    f_coment = _fonte("Ubuntu-RI", int(14 * c))
    f_peq = _fonte("Ubuntu-R", int(12 * c))

    pad = int(22 * c)
    larg_util = card_w - 2 * pad
    medidor = ImageDraw.Draw(img)

    if ply == 0:
        linha_lance = "Posição inicial"
    else:
        numero = (ply + 1) // 2
        linha_lance = f"{numero}. {san}" if ply % 2 == 1 else f"{numero}... {san}"

    comentario = partidas.comentario(partida, ply) if ply else None
    linhas_coment = _quebrar(medidor, comentario, f_coment, larg_util)[:4] if comentario else []
    terminou = ply == len(lances)

    analise = ply > partidas.jogados(partida_id)
    altura_card = ((18 * c if analise else 0) + pad + 16 * c + 34 * c + 2 * 22 * c + 22 * c + 18 * c
                   + 34 * c + len(linhas_coment) * 20 * c + (8 * c if linhas_coment else 0)
                   + 30 * c + (28 * c if terminou else 0) + pad)
    card_y = altura - margem - int(altura_card)

    camada = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    d.rounded_rectangle((card_x, card_y, card_x + card_w, altura - margem),
                        radius=int(16 * c), fill=(255, 255, 255, 18), outline=(255, 255, 255, 34))
    img = Image.alpha_composite(img, camada)
    d = ImageDraw.Draw(img)

    branco, cinza, apagado = "#f0f3f6", "#9aa4af", "#6e7781"
    x, y = card_x + pad, card_y + pad

    d.text((x, y), "PARTIDA LENDÁRIA", font=f_rotulo, fill=tema["destaque"])
    y += 16 * c
    d.text((x, y), partida["nome"], font=f_titulo, fill=branco)
    y += 34 * c

    raio = 5 * c
    for cor, nome in (("#f0f3f6", partida["brancas"]), ("#161b22", partida["pretas"])):
        cy = y + 10 * c
        d.ellipse((x, cy - raio, x + 2 * raio, cy + raio), fill=cor, outline="#9aa4af")
        d.text((x + 18 * c, y), nome, font=f_jogador, fill=branco)
        y += 22 * c
    d.text((x, y), f"{partida['local']}, {partida['ano']}", font=f_local, fill=cinza)
    y += 22 * c

    d.line((x, y + 4 * c, x + larg_util, y + 4 * c), fill="#3d444d", width=max(1, int(s)))
    y += 18 * c

    if analise:
        d.text((x, y), "ANÁLISE · O MATE QUE VIRIA", font=f_rotulo, fill="#d29922")
        y += 18 * c
    d.text((x, y), linha_lance, font=f_lance, fill="#e3b341" if analise else branco)
    y += 34 * c
    for linha in linhas_coment:
        d.text((x, y), linha, font=f_coment, fill="#c9d1d9")
        y += 20 * c
    if linhas_coment:
        y += 8 * c

    # Barra de progresso
    total = len(lances)
    barra_h = max(3, int(4 * c))
    d.rounded_rectangle((x, y + 6 * c, x + larg_util, y + 6 * c + barra_h), radius=barra_h, fill="#30363d")
    if ply:
        d.rounded_rectangle((x, y + 6 * c, x + larg_util * ply / total, y + 6 * c + barra_h),
                            radius=barra_h, fill=tema["destaque"])
    contador = f"{ply} / {total}"
    d.text((x + larg_util - d.textlength(contador, font=f_peq), y + 14 * c), contador,
           font=f_peq, fill=apagado)
    y += 30 * c

    if terminou:
        d.text((x, y), _texto_final(partida, tabuleiro), font=f_lance, fill=tema["destaque"])

    img.convert("RGB").save(destino, "PNG", optimize=False)
