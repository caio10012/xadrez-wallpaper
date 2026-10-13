"""Arquivos compartilhados entre o daemon e o app de configuração.

- config.json: escrito só pelo app (fila, velocidade, tema...)
- estado.json: escrito só pelo daemon (partida e lance atuais)
- comando.json: pedidos pontuais do app ao daemon (pular lance, tocar partida)
"""

import json
import os
import time
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "xadrez-wallpaper"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "xadrez-wallpaper"

CONFIG_FILE = CONFIG_DIR / "config.json"
ESTADO_FILE = STATE_DIR / "estado.json"
COMANDO_FILE = STATE_DIR / "comando.json"

PADRAO = {
    "fila": ["imortal", "opera", "seculo", "sempre-viva", "lasker-thomas"],
    "segundos_por_lance": 5,
    "pausa_final": 20,
    "tema": "lichess",
    "tamanho_tabuleiro": 80,
    "tamanho_cartao": 100,
    "aleatorio": False,
    "pausado": False,
}


def ler_json(caminho, padrao=None):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return padrao


def salvar_json(caminho, dados):
    """Escrita atômica, para o outro processo nunca ler um arquivo pela metade."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    os.replace(tmp, caminho)


def carregar_config():
    return {**PADRAO, **(ler_json(CONFIG_FILE) or {})}


def salvar_config(config):
    salvar_json(CONFIG_FILE, config)


def enviar_comando(acao, **extra):
    salvar_json(COMANDO_FILE, {"acao": acao, "t": time.time(), **extra})
