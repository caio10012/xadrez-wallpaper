"""Catálogo de partidas lendárias — todas terminam em xeque-mate.

Cada partida guarda os lances em notação algébrica e comentários opcionais
indexados pelo lance: "17." é o 17º lance das brancas, "17..." o das pretas.
Quando o perdedor abandonou antes do mate, "continuacao" traz o mate que viria;
esses lances aparecem no wallpaper marcados como análise.
"""

import re
from functools import lru_cache

import chess

PARTIDAS = [
    {
        "id": "imortal",
        "nome": "A Imortal",
        "brancas": "Adolf Anderssen",
        "pretas": "Lionel Kieseritzky",
        "local": "Londres",
        "ano": 1851,
        "resultado": "1-0",
        "lances": """
            1.e4 e5 2.f4 exf4 3.Bc4 Qh4+ 4.Kf1 b5 5.Bxb5 Nf6 6.Nf3 Qh6 7.d3 Nh5
            8.Nh4 Qg5 9.Nf5 c6 10.g4 Nf6 11.Rg1 cxb5 12.h4 Qg6 13.h5 Qg5 14.Qf3 Ng8
            15.Bxf4 Qf6 16.Nc3 Bc5 17.Nd5 Qxb2 18.Bd6 Bxg1 19.e5 Qxa1+ 20.Ke2 Na6
            21.Nxg7+ Kd8 22.Qf6+ Nxf6 23.Be7#
        """,
        "comentarios": {
            "11.": "Anderssen abandona o bispo para ganhar tempo no ataque.",
            "17.": "Cd5! Ignora a ameaça e oferece as duas torres.",
            "18.": "Bd6!! Mais uma torre entregue de presente.",
            "19...": "As pretas têm duas torres a mais... e estão perdidas.",
            "22.": "Df6+!! E agora a dama também!",
            "23.": "Be7# — mate só com peças menores. Imortal.",
        },
    },
    {
        "id": "sempre-viva",
        "nome": "A Sempre-Viva",
        "brancas": "Adolf Anderssen",
        "pretas": "Jean Dufresne",
        "local": "Berlim",
        "ano": 1852,
        "resultado": "1-0",
        "lances": """
            1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5 4.b4 Bxb4 5.c3 Ba5 6.d4 exd4 7.O-O d3
            8.Qb3 Qf6 9.e5 Qg6 10.Re1 Nge7 11.Ba3 b5 12.Qxb5 Rb8 13.Qa4 Bb6
            14.Nbd2 Bb7 15.Ne4 Qf5 16.Bxd3 Qh5 17.Nf6+ gxf6 18.exf6 Rg8 19.Rad1 Qxf3
            20.Rxe7+ Nxe7 21.Qxd7+ Kxd7 22.Bf5+ Ke8 23.Bd7+ Kf8 24.Bxe7#
        """,
        "comentarios": {
            "4.": "O Gambito Evans: um peão pelo desenvolvimento.",
            "19...": "As pretas ameaçam mate em g2. Mas é tarde demais.",
            "20.": "Txe7+! O começo do fim.",
            "21.": "Dxd7+!! Sacrifício de dama.",
            "24.": "Bxe7# — mate com dois bispos.",
        },
    },
    {
        "id": "opera",
        "nome": "A Partida da Ópera",
        "brancas": "Paul Morphy",
        "pretas": "Duque de Brunswick e Conde Isouard",
        "local": "Paris",
        "ano": 1858,
        "resultado": "1-0",
        "lances": """
            1.e4 e5 2.Nf3 d6 3.d4 Bg4 4.dxe5 Bxf3 5.Qxf3 dxe5 6.Bc4 Nf6 7.Qb3 Qe7
            8.Nc3 c6 9.Bg5 b5 10.Nxb5 cxb5 11.Bxb5+ Nbd7 12.O-O-O Rd8 13.Rxd7 Rxd7
            14.Rd1 Qe6 15.Bxd7+ Nxd7 16.Qb8+ Nxb8 17.Rd8#
        """,
        "comentarios": {
            "1.": "Jogada num camarote, durante O Barbeiro de Sevilha.",
            "10.": "Cxb5! Morphy sacrifica para abrir as linhas.",
            "13.": "Txd7! Mais madeira no fogo.",
            "16.": "Db8+!! Sacrifício de dama.",
            "17.": "Td8# — aula de desenvolvimento em 17 lances.",
        },
    },
    {
        "id": "legall",
        "nome": "O Mate de Legall",
        "brancas": "Kermur de Legall",
        "pretas": "Saint Brie",
        "local": "Paris",
        "ano": 1750,
        "resultado": "1-0",
        "lances": """
            1.e4 e5 2.Bc4 d6 3.Nf3 Bg4 4.Nc3 g6 5.Nxe5 Bxd1 6.Bxf7+ Ke7 7.Nd5#
        """,
        "comentarios": {
            "5.": "Cxe5!? Legall deixa a dama pendurada.",
            "5...": "Bxd1? As pretas mordem a isca.",
            "7.": "Cd5# — três peças menores derrubam o rei.",
        },
    },
    {
        "id": "reti-tartakower",
        "nome": "Mate em 11",
        "brancas": "Richard Réti",
        "pretas": "Savielly Tartakower",
        "local": "Viena",
        "ano": 1910,
        "resultado": "1-0",
        "lances": """
            1.e4 c6 2.d4 d5 3.Nc3 dxe4 4.Nxe4 Nf6 5.Qd3 e5 6.dxe5 Qa5+ 7.Bd2 Qxe5
            8.O-O-O Nxe4 9.Qd8+ Kxd8 10.Bg5+ Kc7 11.Bd8#
        """,
        "comentarios": {
            "8...": "Cxe4? Ganha um cavalo e perde a partida.",
            "9.": "Dd8+!! A dama se entrega no meio do tabuleiro.",
            "11.": "Bd8# — mate com o bispo no lugar onde estava a dama.",
        },
    },
    {
        "id": "lasker-thomas",
        "nome": "A Caçada ao Rei",
        "brancas": "Edward Lasker",
        "pretas": "George Thomas",
        "local": "Londres",
        "ano": 1912,
        "resultado": "1-0",
        "lances": """
            1.d4 e6 2.Nf3 f5 3.Nc3 Nf6 4.Bg5 Be7 5.Bxf6 Bxf6 6.e4 fxe4 7.Nxe4 b6
            8.Ne5 O-O 9.Bd3 Bb7 10.Qh5 Qe7 11.Qxh7+ Kxh7 12.Nxf6+ Kh6 13.Neg4+ Kg5
            14.h4+ Kf4 15.g3+ Kf3 16.Be2+ Kg2 17.Rh2+ Kg1 18.Kd2#
        """,
        "comentarios": {
            "11.": "Dxh7+!! Começa a caçada.",
            "13...": "O rei preto é arrastado para fora de casa...",
            "16...": "...até a outra ponta do tabuleiro.",
            "18.": "Rd2# — o rei preto morre na 1ª fileira.",
        },
    },
    {
        "id": "ouro",
        "nome": "As Moedas de Ouro",
        "brancas": "Stefan Levitsky",
        "pretas": "Frank Marshall",
        "local": "Breslau",
        "ano": 1912,
        "resultado": "0-1",
        "lances": """
            1.d4 e6 2.e4 d5 3.Nc3 c5 4.Nf3 Nc6 5.exd5 exd5 6.Be2 Nf6 7.O-O Be7
            8.Bg5 O-O 9.dxc5 Be6 10.Nd4 Bxc5 11.Nxe6 fxe6 12.Bg4 Qd6 13.Bh3 Rae8
            14.Qd2 Bb4 15.Bxf6 Rxf6 16.Rad1 Qc5 17.Qe2 Bxc3 18.bxc3 Qxc3 19.Rxd5 Nd4
            20.Qh5 Ref8 21.Re5 Rh6 22.Qg5 Rxh3 23.Rc5 Qg3
        """,
        "continuacao": "24.hxg3 Ne2#",
        "comentarios": {
            "23...": "Dg3!!! Dizem que o público jogou moedas de ouro no tabuleiro.",
            "24.": "Levitsky abandonou aqui. Tomar a dama leva ao mate:",
            "24...": "Ce2# — por isso as brancas desistiram.",
        },
    },
    {
        "id": "steinitz-bardeleben",
        "nome": "A Torre Intocável",
        "brancas": "Wilhelm Steinitz",
        "pretas": "Curt von Bardeleben",
        "local": "Hastings",
        "ano": 1895,
        "resultado": "1-0",
        "lances": """
            1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5 4.c3 Nf6 5.d4 exd4 6.cxd4 Bb4+ 7.Nc3 d5
            8.exd5 Nxd5 9.O-O Be6 10.Bg5 Be7 11.Bxd5 Bxd5 12.Nxd5 Qxd5 13.Bxe7 Nxe7
            14.Re1 f6 15.Qe2 Qd7 16.Rac1 c6 17.d5 cxd5 18.Nd4 Kf7 19.Ne6 Rhc8
            20.Qg4 g6 21.Ng5+ Ke8 22.Rxe7+ Kf8 23.Rf7+ Kg8 24.Rg7+ Kh8 25.Rxh7+
        """,
        "continuacao": """
            25...Kg8 26.Rg7+ Kh8 27.Qh4+ Kxg7 28.Qh7+ Kf8 29.Qh8+ Ke7 30.Qg7+ Ke8
            31.Qg8+ Ke7 32.Qf7+ Kd8 33.Qf8+ Qe8 34.Nf7+ Kd7 35.Qd6#
        """,
        "comentarios": {
            "17.": "d5! Um peão para abrir o caminho.",
            "22.": "Txe7+!! A torre fica pendurada, mas ninguém pode tocá-la.",
            "25.": "Von Bardeleben saiu do salão sem abandonar. Steinitz mostrou o mate em 10:",
            "35.": "Dd6# — o mate que Steinitz mostrou à plateia.",
        },
    },
    {
        "id": "seculo",
        "nome": "A Partida do Século",
        "brancas": "Donald Byrne",
        "pretas": "Bobby Fischer (13 anos)",
        "local": "Nova York",
        "ano": 1956,
        "resultado": "0-1",
        "lances": """
            1.Nf3 Nf6 2.c4 g6 3.Nc3 Bg7 4.d4 O-O 5.Bf4 d5 6.Qb3 dxc4 7.Qxc4 c6
            8.e4 Nbd7 9.Rd1 Nb6 10.Qc5 Bg4 11.Bg5 Na4 12.Qa3 Nxc3 13.bxc3 Nxe4
            14.Bxe7 Qb6 15.Bc4 Nxc3 16.Bc5 Rfe8+ 17.Kf1 Be6 18.Bxb6 Bxc4+ 19.Kg1 Ne2+
            20.Kf1 Nxd4+ 21.Kg1 Ne2+ 22.Kf1 Nc3+ 23.Kg1 axb6 24.Qb4 Ra4 25.Qxb6 Nxd1
            26.h3 Rxa2 27.Kh2 Nxf2 28.Re1 Rxe1 29.Qd8+ Bf8 30.Nxe1 Bd5 31.Nf3 Ne4
            32.Qb8 b5 33.h4 h5 34.Ne5 Kg7 35.Kg1 Bc5+ 36.Kf1 Ng3+ 37.Ke1 Bb4+
            38.Kd1 Bb3+ 39.Kc1 Ne2+ 40.Kb1 Nc3+ 41.Kc1 Rc2#
        """,
        "comentarios": {
            "11...": "Ca4!! Um garoto de 13 anos começa a mágica.",
            "17...": "Be6!! Fischer entrega a dama.",
            "18...": "Começa o moinho: xeques descobertos em sequência.",
            "25...": "Torre, dois bispos e cavalo contra a dama.",
            "41...": "Tc2# — torre, bispos e cavalo cercam o rei branco.",
        },
    },
]

_POR_ID = {p["id"]: p for p in PARTIDAS}
_NUMERO = re.compile(r"^\d+\.(\.\.)?")


def buscar(partida_id):
    return _POR_ID.get(partida_id)


@lru_cache(maxsize=None)
def lances(partida_id):
    """Retorna a lista de chess.Move da partida (com a continuação), validando cada lance."""
    partida = _POR_ID[partida_id]
    tabuleiro = chess.Board()
    resultado = []
    for token in (partida["lances"] + " " + partida.get("continuacao", "")).split():
        san = _NUMERO.sub("", token)
        if not san:
            continue
        lance = tabuleiro.parse_san(san)
        tabuleiro.push(lance)
        resultado.append(lance)
    return tuple(resultado)


def jogados(partida_id):
    """Quantos meios-lances foram de fato jogados (o resto é a continuação)."""
    tokens = _POR_ID[partida_id]["lances"].split()
    return sum(1 for t in tokens if _NUMERO.sub("", t))


def comentario(partida, ply):
    """Comentário do meio-lance `ply` (1 = primeiro lance das brancas)."""
    numero = (ply + 1) // 2
    chave = f"{numero}." if ply % 2 == 1 else f"{numero}..."
    return partida["comentarios"].get(chave)
