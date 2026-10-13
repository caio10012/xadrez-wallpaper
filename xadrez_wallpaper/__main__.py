"""Uso: xadrez-wallpaper [comando]

  config            abre o app de configuração (padrão)
  daemon            roda o wallpaper animado (usado pelo serviço do systemd)
  proximo           avança um lance
  anterior          volta um lance
  proxima-partida   pula para a próxima partida da fila
  reiniciar         volta a partida atual para o início
  testar [png]      valida todas as partidas e renderiza um quadro de teste
  --version         mostra a versão
"""

import sys

from . import __version__
from . import config as cfg


def testar(destino="/tmp/xadrez-wallpaper-teste.png"):
    import chess

    from . import partidas
    from .render import renderizar

    for p in partidas.PARTIDAS:
        tabuleiro = chess.Board()
        for lance in partidas.lances(p["id"]):
            tabuleiro.push(lance)
        if not tabuleiro.is_checkmate():
            sys.exit(f"{p['id']}: a partida não termina em mate")
    renderizar("imortal", 34, "lichess", 1366, 768, destino)
    print(f"{len(partidas.PARTIDAS)} partidas ok, quadro de teste em {destino}")


def main():
    comando = sys.argv[1] if len(sys.argv) > 1 else "config"
    if comando == "daemon":
        from .daemon import main as rodar
        rodar()
    elif comando == "config":
        from .app import main as abrir
        abrir()
    elif comando in ("proximo", "anterior", "proxima-partida", "reiniciar"):
        cfg.enviar_comando(comando.replace("-", "_"))
    elif comando == "testar":
        testar(*sys.argv[2:3])
    elif comando in ("--version", "-v"):
        print(f"xadrez-wallpaper {__version__}")
    elif comando in ("--help", "-h", "ajuda"):
        print(__doc__)
    else:
        print(__doc__)
        sys.exit(1)


main()
