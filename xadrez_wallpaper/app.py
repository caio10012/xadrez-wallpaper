"""App de configuração (GTK4 + libadwaita)."""

import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk  # noqa: E402

from . import config as cfg  # noqa: E402
from . import partidas  # noqa: E402
from .render import TEMAS  # noqa: E402

SERVICO = "xadrez-wallpaper.service"

CSS = """
.tocando { background-color: alpha(@accent_bg_color, 0.18); }
.alvo-cima { box-shadow: inset 0 3px 0 @accent_bg_color; }
.alvo-baixo { box-shadow: inset 0 -3px 0 @accent_bg_color; }
.preview { border-radius: 12px; }
"""


def _systemctl(*args):
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True)


def _subtitulo(p):
    lances = (len(partidas.lances(p["id"])) + 1) // 2
    return f"{p['brancas']} × {p['pretas']} · {p['ano']} · {lances} lances"


class Janela(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Xadrez Wallpaper", default_width=580, default_height=700)
        self.config = cfg.carregar_config()
        self.config["fila"] = [p for p in self.config["fila"] if partidas.buscar(p)] or ["imortal"]
        self.estado = {}
        self.imagem_atual = None
        self.salvar_pendente = None

        # Abas: Tocando | Fila | Aparência
        self.abas = abas = Adw.ViewStack()
        abas.add_titled_with_icon(self._pagina_tocando(), "tocando", "Tocando", "media-playback-start-symbolic")
        abas.add_titled_with_icon(self._pagina_fila(), "fila", "Fila", "view-list-symbolic")
        abas.add_titled_with_icon(self._pagina_aparencia(), "aparencia", "Aparência", "applications-graphics-symbolic")

        cabecalho = Adw.HeaderBar(title_widget=Adw.ViewSwitcher(stack=abas, policy=Adw.ViewSwitcherPolicy.WIDE))
        vista = Adw.ToolbarView(content=abas)
        vista.add_top_bar(cabecalho)
        self.toasts = Adw.ToastOverlay(child=vista)
        self.set_content(self.toasts)

        self._montar_listas()
        self._atualizar_status()
        GLib.timeout_add(700, self._atualizar_status)

    # ---------- páginas ----------

    def _pagina_tocando(self):
        pagina = Adw.PreferencesPage()

        self.preview = Gtk.Picture(content_fit=Gtk.ContentFit.CONTAIN, can_shrink=True,
                                   height_request=240, overflow=Gtk.Overflow.HIDDEN,
                                   css_classes=["preview"])
        grupo = Adw.PreferencesGroup()
        grupo.add(self.preview)
        pagina.add(grupo)

        grupo = Adw.PreferencesGroup(title="Tocando agora")
        self.linha_agora = Adw.ActionRow(title="—", subtitle="—")
        caixa = Gtk.Box(spacing=4, valign=Gtk.Align.CENTER)
        for icone, dica, acao in (
            ("media-skip-backward-symbolic", "Lance anterior", "anterior"),
            ("media-seek-forward-symbolic", "Próximo lance", "proximo"),
            ("media-skip-forward-symbolic", "Próxima partida", "proxima_partida"),
        ):
            botao = Gtk.Button(icon_name=icone, tooltip_text=dica, css_classes=["flat", "circular"])
            botao.connect("clicked", lambda _b, a=acao: cfg.enviar_comando(a))
            caixa.append(botao)
        self.botao_pausa = Gtk.Button(css_classes=["circular", "suggested-action"])
        self.botao_pausa.connect("clicked", self._alternar_pausa)
        caixa.append(self.botao_pausa)
        self.linha_agora.add_suffix(caixa)
        grupo.add(self.linha_agora)

        self.linha_ativo = Adw.SwitchRow(title="Wallpaper animado",
                                         subtitle="Desligado, volta o seu wallpaper original")
        self.linha_ativo.set_active(_systemctl("is-active", SERVICO).stdout.strip() == "active")
        self.linha_ativo.connect("notify::active", self._alternar_servico)
        grupo.add(self.linha_ativo)
        self._atualizar_botao_pausa()
        pagina.add(grupo)

        grupo = Adw.PreferencesGroup(title="Velocidade")
        lance = Adw.SpinRow.new_with_range(0.5, 600, 0.5)
        lance.set_digits(1)
        lance.set_title("Segundos por lance")
        lance.set_subtitle("Menos segundos = partida mais rápida")
        lance.set_value(self.config["segundos_por_lance"])
        lance.connect("notify::value", lambda r, _p: self._salvar_depois(segundos_por_lance=r.get_value()))
        grupo.add(lance)

        atalhos = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        for rotulo, valor in (("Blitz", 1), ("Rápida", 3), ("Clássica", 10)):
            b = Gtk.Button(label=rotulo, css_classes=["flat"])
            b.connect("clicked", lambda _b, v=valor: lance.set_value(v))
            atalhos.append(b)
        linha_atalhos = Adw.ActionRow(title="Atalhos de ritmo")
        linha_atalhos.add_suffix(atalhos)
        grupo.add(linha_atalhos)

        pausa = Adw.SpinRow.new_with_range(0, 3600, 5)
        pausa.set_title("Pausa no fim da partida")
        pausa.set_subtitle("Segundos mostrando a posição final")
        pausa.set_value(self.config["pausa_final"])
        pausa.connect("notify::value", lambda r, _p: self._salvar_depois(pausa_final=int(r.get_value())))
        grupo.add(pausa)
        pagina.add(grupo)
        return pagina

    def _pagina_fila(self):
        pagina = Adw.PreferencesPage()

        self.grupo_fila = Adw.PreferencesGroup(
            title="Fila", description="Arraste pela alça ⋮⋮ para mudar a ordem, ou use as setas")
        self.lista_fila = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        self.grupo_fila.add(self.lista_fila)
        pagina.add(self.grupo_fila)

        grupo = Adw.PreferencesGroup()
        aleatorio = Adw.SwitchRow(title="Ordem aleatória", subtitle="Sorteia a próxima partida da fila")
        aleatorio.set_active(self.config["aleatorio"])
        aleatorio.connect("notify::active", lambda r, _p: self._salvar(aleatorio=r.get_active()))
        grupo.add(aleatorio)
        pagina.add(grupo)

        self.grupo_disp = Adw.PreferencesGroup(title="Partidas lendárias", description="Clique em + para pôr na fila")
        self.lista_disp = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"])
        self.grupo_disp.add(self.lista_disp)
        pagina.add(self.grupo_disp)
        return pagina

    def _pagina_aparencia(self):
        pagina = Adw.PreferencesPage()
        grupo = Adw.PreferencesGroup(title="Tamanho", description="O wallpaper muda na hora enquanto você ajusta")
        grupo.add(self._linha_slider("Tabuleiro", "% da altura da tela", "tamanho_tabuleiro", 50, 95))
        grupo.add(self._linha_slider("Cartão da partida", "% do tamanho original", "tamanho_cartao", 70, 160))
        pagina.add(grupo)

        grupo = Adw.PreferencesGroup(title="Estilo")
        ids = list(TEMAS)
        tema = Adw.ComboRow(title="Tabuleiro", model=Gtk.StringList.new([TEMAS[t]["nome"] for t in ids]))
        tema.set_selected(ids.index(self.config["tema"]) if self.config["tema"] in ids else 0)
        tema.connect("notify::selected", lambda r, _p: self._salvar(tema=ids[r.get_selected()]))
        grupo.add(tema)
        pagina.add(grupo)
        return pagina

    def _linha_slider(self, titulo, subtitulo, chave, minimo, maximo):
        escala = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, minimo, maximo, 1)
        escala.set_value(self.config[chave])
        escala.set_draw_value(True)
        escala.set_value_pos(Gtk.PositionType.LEFT)
        escala.set_format_value_func(lambda _e, v: f"{v:.0f}%")
        escala.set_size_request(220, -1)
        escala.set_valign(Gtk.Align.CENTER)
        escala.connect("value-changed", lambda e: self._salvar_depois(**{chave: int(e.get_value())}))
        linha = Adw.ActionRow(title=titulo, subtitle=subtitulo)
        linha.add_suffix(escala)
        return linha

    # ---------- listas ----------

    def _montar_listas(self):
        self.lista_fila.remove_all()
        self.lista_disp.remove_all()
        fila = self.config["fila"]
        tocando = self.estado.get("partida")

        for i, pid in enumerate(fila):
            p = partidas.buscar(pid)
            if p:
                self.lista_fila.append(self._linha_fila(p, i, len(fila), pid == tocando))

        for p in partidas.PARTIDAS:
            if p["id"] in fila:
                continue
            linha = Adw.ActionRow(title=p["nome"], subtitle=_subtitulo(p))
            botao = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Adicionar à fila",
                               valign=Gtk.Align.CENTER, css_classes=["flat", "circular"])
            botao.connect("clicked", lambda _b, pid=p["id"]: self._salvar(fila=self.config["fila"] + [pid]))
            linha.add_suffix(botao)
            linha.set_activatable_widget(botao)
            self.lista_disp.append(linha)
        self.grupo_disp.set_visible(len(fila) < len(partidas.PARTIDAS))

    def _linha_fila(self, p, indice, total, tocando):
        linha = Adw.ActionRow(title=p["nome"], subtitle=_subtitulo(p))
        linha.partida_id = p["id"]
        if tocando:
            linha.add_css_class("tocando")
        alca = Gtk.Image(icon_name="list-drag-handle-symbolic")
        linha.add_prefix(alca)

        def botao(icone, dica, callback, sensivel=True):
            b = Gtk.Button(icon_name=icone, tooltip_text=dica, valign=Gtk.Align.CENTER,
                           css_classes=["flat", "circular"], sensitive=sensivel)
            b.connect("clicked", lambda _b: callback())
            linha.add_suffix(b)

        pid = p["id"]
        botao("media-playback-start-symbolic", "Tocar agora", lambda: cfg.enviar_comando("tocar", id=pid))
        botao("go-up-symbolic", "Subir", lambda: self._mover(pid, indice - 1), indice > 0)
        botao("go-down-symbolic", "Descer", lambda: self._mover(pid, indice + 1), indice < total - 1)
        botao("list-remove-symbolic", "Tirar da fila", lambda: self._remover(pid), total > 1)

        # Arrastar e soltar
        origem = Gtk.DragSource(actions=Gdk.DragAction.MOVE)
        origem.connect("prepare", lambda *_: Gdk.ContentProvider.new_for_value(
            GObject.Value(GObject.TYPE_STRING, pid)))
        origem.connect("drag-begin", lambda src, _drag: src.set_icon(Gtk.WidgetPaintable.new(linha), 0, 0))
        linha.add_controller(origem)

        alvo = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        alvo.connect("motion", self._sobre_alvo, linha)
        alvo.connect("leave", lambda *_: self._limpar_alvo(linha))
        alvo.connect("drop", self._soltar, linha)
        linha.add_controller(alvo)
        return linha

    def _sobre_alvo(self, _alvo, _x, y, linha):
        abaixo = y > linha.get_height() / 2
        linha.remove_css_class("alvo-baixo" if not abaixo else "alvo-cima")
        linha.add_css_class("alvo-baixo" if abaixo else "alvo-cima")
        return Gdk.DragAction.MOVE

    def _limpar_alvo(self, linha):
        linha.remove_css_class("alvo-cima")
        linha.remove_css_class("alvo-baixo")

    def _soltar(self, _alvo, origem, _x, y, linha):
        self._limpar_alvo(linha)
        destino = linha.partida_id
        if origem == destino:
            return False
        fila = [p for p in self.config["fila"] if p != origem]
        posicao = fila.index(destino) + (1 if y > linha.get_height() / 2 else 0)
        fila.insert(posicao, origem)
        # Reconstruir a lista durante o drop destruiria o widget em uso
        GLib.idle_add(lambda: self._salvar(fila=fila) and False)
        return True

    def _mover(self, pid, novo_indice):
        fila = list(self.config["fila"])
        fila.remove(pid)
        fila.insert(novo_indice, pid)
        self._salvar(fila=fila)

    def _remover(self, pid):
        self._salvar(fila=[p for p in self.config["fila"] if p != pid])

    # ---------- estado ----------

    def _salvar(self, **mudancas):
        fila_mudou = "fila" in mudancas and mudancas["fila"] != self.config["fila"]
        self.config.update(mudancas)
        cfg.salvar_config(self.config)
        if fila_mudou:
            self._montar_listas()

    def _salvar_depois(self, **mudancas):
        self.config.update(mudancas)
        if self.salvar_pendente:
            GLib.source_remove(self.salvar_pendente)
        self.salvar_pendente = GLib.timeout_add(250, self._salvar_agora)

    def _salvar_agora(self):
        self.salvar_pendente = None
        cfg.salvar_config(self.config)
        return False

    def _alternar_pausa(self, _botao):
        self._salvar(pausado=not self.config["pausado"])
        self._atualizar_botao_pausa()

    def _atualizar_botao_pausa(self):
        pausado = self.config["pausado"]
        self.botao_pausa.set_icon_name("media-playback-start-symbolic" if pausado else "media-playback-pause-symbolic")
        self.botao_pausa.set_tooltip_text("Continuar" if pausado else "Pausar")

    def _alternar_servico(self, linha, _p):
        acao = ["enable", "--now"] if linha.get_active() else ["disable", "--now"]
        resultado = _systemctl(*acao, SERVICO)
        if resultado.returncode != 0:
            self.toasts.add_toast(Adw.Toast(title="Não consegui ligar o serviço: " + (resultado.stderr.strip() or "erro desconhecido")))

    def _atualizar_status(self):
        estado = cfg.ler_json(cfg.ESTADO_FILE, {}) or {}
        mudou_partida = estado.get("partida") != self.estado.get("partida")
        self.estado = estado
        p = partidas.buscar(estado.get("partida"))
        if p:
            ply, total = estado.get("ply", 0), estado.get("total", 0)
            self.linha_agora.set_title(p["nome"])
            self.linha_agora.set_subtitle(f"Lance {(ply + 1) // 2} · {ply}/{total} meios-lances")
        imagem = estado.get("imagem")
        if imagem and (imagem, estado.get("atualizado")) != self.imagem_atual:
            self.imagem_atual = (imagem, estado.get("atualizado"))
            self.preview.set_file(Gio.File.new_for_path(imagem))
        if mudou_partida:
            self._montar_listas()
        return True


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.xadrez_wallpaper", flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_startup(self):
        Adw.Application.do_startup(self)
        Gtk.Window.set_default_icon_name("xadrez-wallpaper")
        provedor = Gtk.CssProvider()
        provedor.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provedor,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def do_activate(self):
        janela = self.props.active_window or Janela(self)
        janela.present()


def main():
    App().run([])
