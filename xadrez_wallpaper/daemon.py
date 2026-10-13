"""Processo em segundo plano que avança as partidas e troca o wallpaper."""

import os
import random
import signal
import time

import gi
from gi.repository import Gio

from . import config as cfg
from . import partidas
from .render import renderizar

SCHEMA = "org.gnome.desktop.background"


_fundo = Gio.Settings.new(SCHEMA)


def _gsettings_get(chave):
    return _fundo.get_string(chave)


def _gsettings_aplicar(**chaves):
    """Muda todas as chaves numa transação só: o GNOME recarrega o fundo uma vez."""
    _fundo.delay()
    for chave, valor in chaves.items():
        _fundo.set_string(chave.replace("_", "-"), valor)
    _fundo.apply()
    Gio.Settings.sync()


def resolucao():
    """Resolução real do monitor principal (em pixels físicos)."""
    try:
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk
        Gtk.init()
        from gi.repository import Gdk
        monitor = Gdk.Display.get_default().get_monitors().get_item(0)
        geo, escala = monitor.get_geometry(), monitor.get_scale()
        return int(geo.width * escala), int(geo.height * escala)
    except Exception:
        return 1920, 1080


class Tocador:
    def __init__(self):
        cfg.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.largura, self.altura = resolucao()
        self.config = cfg.carregar_config()
        self.estado = cfg.ler_json(cfg.ESTADO_FILE, {}) or {}
        self.ultimo_comando = (cfg.ler_json(cfg.COMANDO_FILE, {}) or {}).get("t", 0)
        self.config_mtime = self._mtime(cfg.CONFIG_FILE)
        self.proximo = 0.0
        self.rodando = True

        # Guarda o wallpaper original para devolver ao sair
        uri = _gsettings_get("picture-uri")
        if str(cfg.STATE_DIR) not in uri:
            self.estado["uri_original"] = uri
            self.estado["uri_original_dark"] = _gsettings_get("picture-uri-dark")
            self.estado["opcao_original"] = _gsettings_get("picture-options")

        if self.estado.get("partida") not in self.config["fila"]:
            self._iniciar_partida(self._primeira())

    @staticmethod
    def _mtime(caminho):
        try:
            return os.stat(caminho).st_mtime
        except OSError:
            return 0

    def _fila(self):
        fila = [p for p in self.config["fila"] if partidas.buscar(p)]
        return fila or [partidas.PARTIDAS[0]["id"]]

    def _primeira(self):
        return self._fila()[0]

    def _seguinte(self):
        fila = self._fila()
        atual = self.estado.get("partida")
        if self.config["aleatorio"] and len(fila) > 1:
            return random.choice([p for p in fila if p != atual])
        if atual not in fila:
            return fila[0]
        return fila[(fila.index(atual) + 1) % len(fila)]

    def _iniciar_partida(self, partida_id):
        self.estado["partida"] = partida_id
        self.estado["ply"] = 0

    def _total(self):
        return len(partidas.lances(self.estado["partida"]))

    # --- passos ---

    def avancar(self):
        if self.estado["ply"] >= self._total():
            self._iniciar_partida(self._seguinte())
        else:
            self.estado["ply"] += 1

    def voltar(self):
        self.estado["ply"] = max(0, self.estado["ply"] - 1)

    def _agendar(self):
        terminou = self.estado["ply"] >= self._total()
        espera = self.config["pausa_final"] if terminou else self.config["segundos_por_lance"]
        self.proximo = time.monotonic() + max(0.5, float(espera))

    def desenhar(self):
        # Um arquivo novo por quadro: o GNOME guarda imagens em cache pelo caminho,
        # e reaproveitar um nome faz ele mostrar por um instante o quadro antigo.
        destino = cfg.STATE_DIR / f"quadro-{time.time_ns()}.png"
        renderizar(self.estado["partida"], self.estado["ply"], self.config["tema"],
                   self.largura, self.altura, destino,
                   self.config["tamanho_tabuleiro"], self.config["tamanho_cartao"])
        uri = destino.as_uri()
        _gsettings_aplicar(picture_options="zoom", picture_uri=uri, picture_uri_dark=uri)
        anterior = self.estado.get("imagem")
        self.estado.update(imagem=str(destino), total=self._total(), atualizado=time.time())
        cfg.salvar_json(cfg.ESTADO_FILE, self.estado)
        self._limpar_quadros(manter={destino.name, os.path.basename(anterior or "")})

    @staticmethod
    def _limpar_quadros(manter):
        for arquivo in cfg.STATE_DIR.glob("*.png"):
            if arquivo.name not in manter:
                arquivo.unlink(missing_ok=True)

    # --- reações a mudanças externas ---

    def _ver_config(self):
        mtime = self._mtime(cfg.CONFIG_FILE)
        if mtime == self.config_mtime:
            return False
        self.config_mtime = mtime
        antigo = self.config
        self.config = cfg.carregar_config()
        if self.estado["partida"] not in self._fila():
            self._iniciar_partida(self._primeira())
            return True
        visual = ("tema", "tamanho_tabuleiro", "tamanho_cartao")
        return any(antigo[k] != self.config[k] for k in visual)

    def _ver_comando(self):
        comando = cfg.ler_json(cfg.COMANDO_FILE, {}) or {}
        if comando.get("t", 0) <= self.ultimo_comando:
            return False
        self.ultimo_comando = comando["t"]
        acao = comando.get("acao")
        if acao == "proximo":
            self.avancar()
        elif acao == "anterior":
            self.voltar()
        elif acao == "proxima_partida":
            self._iniciar_partida(self._seguinte())
        elif acao == "tocar" and partidas.buscar(comando.get("id")):
            self._iniciar_partida(comando["id"])
        elif acao == "reiniciar":
            self.estado["ply"] = 0
        else:
            return False
        return True

    def restaurar(self):
        if self.estado.get("uri_original"):
            _gsettings_aplicar(
                picture_uri=self.estado["uri_original"],
                picture_uri_dark=self.estado.get("uri_original_dark") or self.estado["uri_original"],
                picture_options=self.estado.get("opcao_original") or "zoom")

    def rodar(self):
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "rodando", False))
        signal.signal(signal.SIGINT, lambda *_: setattr(self, "rodando", False))
        self.desenhar()
        self._agendar()
        voltas = 0
        while self.rodando:
            # Se o pacote foi desinstalado com o serviço rodando, devolve o wallpaper e sai
            voltas += 1
            if voltas % 20 == 0 and not os.path.exists(__file__):
                break
            mudou = self._ver_config() | self._ver_comando()
            if not mudou and not self.config["pausado"] and time.monotonic() >= self.proximo:
                self.avancar()
                mudou = True
            if mudou:
                self.desenhar()
                self._agendar()
            time.sleep(0.25)
        self.restaurar()


def main():
    Tocador().rodar()
