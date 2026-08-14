"""Tela de acesso corporativo com identidade oficial e fallback vetorial."""

from __future__ import annotations

import tkinter as tk

from auth.autenticacao import autenticar_usuario
from auth.sessao import SESSAO
from core.versao import VERSAO_INTERFACE
from core.caminhos import caminho_recurso
from interface.gerenciador_tema import alternar_tema, persistir_tema_autenticado
from interface.icones import icone
from interface.tema import CORES, FONTES, MARCA, tema_atual

try:
    from PIL import Image, ImageChops, ImageTk
except ImportError:  # pragma: no cover - fallback vetorial
    Image = ImageChops = ImageTk = None


class TelaLogin:
    def __init__(self, root, ao_entrar, mensagem_inicial=None):
        self.root = root
        self.ao_entrar = ao_entrar
        self.cores = CORES
        self.mensagem_inicial = mensagem_inicial
        self.usuario_var = tk.StringVar()
        self.senha_var = tk.StringVar()
        self.codigo_mfa_var = tk.StringVar()
        self._status_texto = mensagem_inicial or "Ambiente corporativo protegido"
        self._status_tipo = "warning" if mensagem_inicial else "success"
        self.container = None
        self._recursos_imagem = []
        self.criar_interface()

    def _imagem_marca(self, nome: str, tamanho: tuple[int, int], *, remover_branco: bool = False):
        if Image is None or ImageTk is None:
            return None
        try:
            imagem = Image.open(caminho_recurso("assets", "brand", nome)).convert("RGBA")
            if remover_branco and ImageChops is not None:
                branco = Image.new("RGBA", imagem.size, (255, 255, 255, 255))
                diferenca = ImageChops.difference(imagem, branco).convert("L")
                caixa = diferenca.point(lambda valor: 255 if valor > 10 else 0).getbbox()
                if caixa:
                    imagem = imagem.crop(caixa)
                    diferenca = diferenca.crop(caixa)
                imagem.putalpha(diferenca.point(lambda valor: min(255, valor * 4)))
            imagem.thumbnail(tamanho, Image.Resampling.LANCZOS)
            recurso = ImageTk.PhotoImage(imagem)
            self._recursos_imagem.append(recurso)
            return recurso
        except (OSError, ValueError, tk.TclError):
            return None

    def criar_interface(self):
        if self.container is not None:
            try:
                self.container.destroy()
            except tk.TclError:
                pass
        self._recursos_imagem.clear()

        self.root.title(f"Data Intelligence · Acesso corporativo · {VERSAO_INTERFACE}")
        self.root.configure(bg=self.cores["bg"])
        self.container = tk.Canvas(
            self.root, bg=self.cores["bg"], bd=0, highlightthickness=0,
        )
        self.container.pack(fill="both", expand=True)
        self._criar_identidade()
        self._criar_card_login()
        self._criar_toggle_tema()
        self.container.bind("<Configure>", self._ao_redimensionar)
        self.root.bind("<Return>", lambda _evento: self.entrar())
        self.root.after_idle(self._iniciar_layout)

    def _criar_identidade(self):
        c = self.container
        self._logo_oficial = self._imagem_marca("logo_empresa.png", (285, 105), remover_branco=True)
        self._data_center = self._imagem_marca("login_data_center.png", (520, 420))
        self._logo_oficial_item = c.create_image(0, 0, image=self._logo_oficial, anchor="w") if self._logo_oficial else None
        self._data_center_item = c.create_image(0, 0, image=self._data_center, anchor="center") if self._data_center else None
        # Marca vetorial: três barras e monograma, sem arquivo externo.
        self._marca_barras = []
        for _ in range(3):
            self._marca_barras.append(c.create_rectangle(0, 0, 1, 1, outline=""))
        self._marca_nome = c.create_text(
            0, 0, text=MARCA["nome"], font=FONTES["marca"],
            fill=self.cores["text"], anchor="w",
        )
        self._marca_desc = c.create_text(
            0, 0, text=MARCA["descricao"], font=("Inter", 8, "bold"),
            fill=self.cores["primary"], anchor="w",
        )

        # Malha de operação empresarial: desenho abstrato e profissional.
        self._rede_linhas = []
        self._rede_nos = []
        for _ in range(11):
            self._rede_linhas.append(c.create_line(0, 0, 1, 1, width=1))
        for _ in range(8):
            self._rede_nos.append(c.create_oval(0, 0, 1, 1, width=2))
        self._nucleo_externo = c.create_oval(0, 0, 1, 1, width=2)
        self._nucleo_interno = c.create_oval(0, 0, 1, 1, width=1)
        self._nucleo_texto = c.create_text(
            0, 0, text=MARCA["monograma"], font=("Inter", 18, "bold"),
            fill=self.cores["text"], anchor="center",
        )

        self._eyebrow = c.create_text(
            0, 0, text="PLATAFORMA EMPRESARIAL CONECTADA",
            font=("Inter", 8, "bold"), fill=self.cores["accent"], anchor="nw",
        )
        self._titulo = c.create_text(
            0, 0, text="Operações conectadas.\nDecisões mais claras.",
            font=FONTES["display"], fill=self.cores["text"],
            justify="left", anchor="nw",
        )
        self._descricao = c.create_text(
            0, 0,
            text=(
                "Centralize processos, aprovações, indicadores e automações em "
                "uma experiência empresarial única, segura e orientada por dados."
            ),
            font=FONTES["texto"], fill=self.cores["text_sec"],
            justify="left", anchor="nw", width=470,
        )
        self._beneficios = []
        for simbolo, texto in (
            ("▦", "Módulos integrados"),
            ("✓", "Fluxos auditáveis"),
            ("▥", "Analytics contextual"),
        ):
            simbolo_item = c.create_text(
                0, 0, text=simbolo, font=("Segoe UI Symbol", 11, "bold"),
                fill=self.cores["primary"], anchor="w",
            )
            texto_item = c.create_text(
                0, 0, text=texto.upper(), font=("Inter", 8, "bold"),
                fill=self.cores["text_muted"], anchor="w",
            )
            self._beneficios.append((simbolo_item, texto_item))

    def _criar_card_login(self):
        card = tk.Frame(
            self.container, bg=self.cores["card"], width=410, height=575,
            highlightthickness=1, highlightbackground=self.cores["border"],
        )
        card.pack_propagate(False)
        self.card = card
        self._card_window = self.container.create_window(0, 0, window=card, anchor="center")

        topo = tk.Frame(card, bg=self.cores["card"])
        topo.pack(fill="x", padx=40, pady=(34, 0))
        acesso_imagem = self._imagem_marca("acesso_corporativo.png", (27, 30))
        tk.Label(
            topo, image=acesso_imagem, text="" if acesso_imagem else icone("seguranca"),
            font=("Segoe UI Symbol", 10, "bold"), fg=self.cores["primary"],
            bg=self.cores["card"], width=30 if acesso_imagem else 3, height=32 if acesso_imagem else 1,
        ).pack(side="left", padx=(0, 9))
        tk.Label(
            topo, text="ACESSO CORPORATIVO", font=("Inter", 8, "bold"),
            fg=self.cores["primary"], bg=self.cores["card"],
        ).pack(side="left")

        tk.Label(
            card, text="Bem-vindo", font=FONTES["titulo_grande"],
            fg=self.cores["text"], bg=self.cores["card"],
        ).pack(anchor="w", padx=40, pady=(20, 5))
        tk.Label(
            card, text="Entre com suas credenciais para acessar a plataforma.",
            font=("Inter", 9), fg=self.cores["text_sec"], bg=self.cores["card"],
        ).pack(anchor="w", padx=40, pady=(0, 22))

        self.entry_usuario = self._criar_campo(card, "Usuário", self.usuario_var)
        self.entry_senha = self._criar_campo(card, "Senha", self.senha_var, "•")
        self.entry_mfa = self._criar_campo(
            card, "Código MFA ou de recuperação (quando habilitado)", self.codigo_mfa_var,
        )

        tk.Button(
            card, text="ENTRAR NA PLATAFORMA  →", font=("Inter", 9, "bold"),
            bg=self.cores["primary"], fg=self.cores.get("on_primary", "#FFFFFF"),
            activebackground=self.cores["primary_hover"], activeforeground="#FFFFFF",
            bd=0, relief="flat", cursor="hand2", command=self.entrar, takefocus=True,
            highlightthickness=2, highlightbackground=self.cores["primary"], highlightcolor=self.cores["accent"],
        ).pack(fill="x", padx=40, pady=(22, 12), ipady=10)

        self.label_status = tk.Label(
            card, text="", font=("Inter", 8), bg=self.cores["card"],
            justify="left", anchor="w", wraplength=325,
        )
        self.label_status.pack(fill="x", padx=40)
        self._atualizar_status()

        rodape = tk.Frame(card, bg=self.cores["card"])
        rodape.pack(side="bottom", fill="x", padx=40, pady=24)
        tk.Frame(rodape, bg=self.cores["divider"], height=1).pack(fill="x", pady=(0, 13))
        tk.Label(
            rodape, text=f"{MARCA['assinatura']} · {VERSAO_INTERFACE}",
            font=("Inter", 8), fg=self.cores["text_muted"], bg=self.cores["card"],
        ).pack(anchor="w")

        self.entry_usuario.focus_set()

    def _criar_toggle_tema(self):
        texto = f"{icone('tema_claro')}  CLARO" if tema_atual() == "escuro" else f"{icone('tema_escuro')}  ESCURO"
        self.botao_tema = tk.Button(
            self.container, text=texto, command=self._alternar_tema,
            font=("Segoe UI Symbol", 8, "bold"), bg=self.cores["bg_elevado"],
            fg=self.cores["text_sec"], activebackground=self.cores["card_hover"],
            activeforeground=self.cores["text"], relief="flat", bd=0,
            cursor="hand2", padx=12, pady=7, takefocus=True,
            highlightthickness=2, highlightbackground=self.cores["bg_elevado"], highlightcolor=self.cores["accent"],
        )
        self._tema_window = self.container.create_window(0, 0, window=self.botao_tema, anchor="ne")

    def _criar_campo(self, parent, titulo, variavel, mostrar=None):
        frame = tk.Frame(parent, bg=self.cores["card"])
        frame.pack(fill="x", padx=40, pady=8)
        tk.Label(
            frame, text=titulo.upper(), font=("Inter", 8, "bold"),
            fg=self.cores["text_sec"], bg=self.cores["card"],
        ).pack(anchor="w", pady=(0, 6))
        borda = tk.Frame(frame, bg=self.cores["border"])
        borda.pack(fill="x")
        interior = tk.Frame(borda, bg=self.cores["input"])
        interior.pack(fill="x", padx=1, pady=1)
        entrada = tk.Entry(
            interior, textvariable=variavel, font=("Inter", 11),
            bg=self.cores["input"], fg=self.cores["text"],
            insertbackground=self.cores["primary"], relief="flat", bd=0,
            show=mostrar,
        )
        entrada.pack(fill="x", padx=(11, 8), ipady=9)
        entrada.bind("<FocusIn>", lambda _e: borda.configure(bg=self.cores["primary"]))
        entrada.bind("<FocusOut>", lambda _e: borda.configure(bg=self.cores["border"]))
        return entrada

    def _alternar_tema(self):
        alternar_tema(self.root)
        self.criar_interface()
        if self.senha_var.get():
            self.entry_senha.focus_set()

    def _atualizar_status(self):
        if not hasattr(self, "label_status"):
            return
        simbolo = "●" if self._status_tipo == "success" else "⚠" if self._status_tipo == "warning" else "•"
        self.label_status.configure(
            text=f"{simbolo}  {self._status_texto}",
            fg=self.cores.get(self._status_tipo, self.cores["text_sec"]),
        )

    def _iniciar_layout(self):
        try:
            self.root.update_idletasks()
            self._organizar_layout(max(1, self.container.winfo_width()), max(1, self.container.winfo_height()))
        except tk.TclError:
            return

    def _ao_redimensionar(self, evento):
        self._organizar_layout(max(1, int(evento.width)), max(1, int(evento.height)))

    def _organizar_layout(self, largura, altura):
        c = self.container
        margem = max(42, int(largura * 0.055))
        marca_y = max(38, int(altura * 0.07))

        if self._logo_oficial_item is not None:
            c.coords(self._logo_oficial_item, margem, marca_y + 20)
            for item in (*self._marca_barras, self._marca_nome, self._marca_desc):
                c.itemconfigure(item, state="hidden")

        alturas = (13, 23, 34)
        for indice, item in enumerate(self._marca_barras):
            x = margem + indice * 10
            c.coords(item, x, marca_y + 34 - alturas[indice], x + 6, marca_y + 34)
            c.itemconfigure(item, fill=self.cores["accent"] if indice == 2 else self.cores["primary"])
        c.coords(self._marca_nome, margem + 44, marca_y + 4)
        c.coords(self._marca_desc, margem + 44, marca_y + 29)

        # Rede vetorial central do painel esquerdo.
        centro_x = margem + min(250, max(180, int(largura * 0.20)))
        centro_y = max(220, int(altura * 0.38))
        raio_x = min(210, max(145, int(largura * 0.17)))
        raio_y = min(135, max(105, int(altura * 0.15)))
        pontos = [
            (centro_x - raio_x, centro_y - 35),
            (centro_x - raio_x * .62, centro_y - raio_y),
            (centro_x + 5, centro_y - raio_y * 1.08),
            (centro_x + raio_x * .68, centro_y - raio_y * .72),
            (centro_x + raio_x, centro_y + 10),
            (centro_x + raio_x * .52, centro_y + raio_y),
            (centro_x - raio_x * .35, centro_y + raio_y * 1.02),
            (centro_x - raio_x * .88, centro_y + raio_y * .48),
        ]
        if self._data_center_item is not None:
            c.coords(self._data_center_item, centro_x, centro_y)
            for item in (*self._rede_linhas, *self._rede_nos, self._nucleo_externo, self._nucleo_interno, self._nucleo_texto):
                c.itemconfigure(item, state="hidden")
        pares = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,0),(1,6),(3,6),(0,4)]
        for item, (a,b) in zip(self._rede_linhas, pares):
            c.coords(item, *pontos[a], *pontos[b])
            c.itemconfigure(item, fill=self.cores["border"])
        for indice, (item, (x,y)) in enumerate(zip(self._rede_nos, pontos)):
            r = 8 if indice % 3 else 10
            c.coords(item, x-r, y-r, x+r, y+r)
            c.itemconfigure(
                item, outline=self.cores["accent"] if indice in {2,5} else self.cores["primary"],
                fill=self.cores["bg_elevado"],
            )
        r1, r2 = 44, 26
        c.coords(self._nucleo_externo, centro_x-r1, centro_y-r1, centro_x+r1, centro_y+r1)
        c.coords(self._nucleo_interno, centro_x-r2, centro_y-r2, centro_x+r2, centro_y+r2)
        c.itemconfigure(self._nucleo_externo, outline=self.cores["primary"], fill=self.cores["bg_elevado"])
        c.itemconfigure(self._nucleo_interno, outline=self.cores["accent"])
        c.coords(self._nucleo_texto, centro_x, centro_y)

        texto_y = min(altura - 245, centro_y + raio_y + 45)
        c.coords(self._eyebrow, margem, texto_y)
        c.coords(self._titulo, margem, texto_y + 30)
        c.coords(self._descricao, margem, texto_y + 125)
        c.itemconfigure(self._descricao, width=max(300, min(490, int(largura * 0.42))))
        beneficios_y = texto_y + 210
        for indice, (simbolo, texto) in enumerate(self._beneficios):
            x = margem + indice * 155
            c.coords(simbolo, x, beneficios_y)
            c.coords(texto, x + 24, beneficios_y + 1)

        card_x = min(largura - 230, max(int(largura * 0.76), 720 if largura >= 1024 else int(largura*.72)))
        c.coords(self._card_window, card_x, altura // 2)
        c.coords(self._tema_window, largura - max(24, int(largura * 0.035)), max(25, int(altura * 0.04)))

        # Em janelas estreitas reduz elementos institucionais secundários, sem
        # comprometer o formulário de acesso.
        estado_beneficios = "normal" if largura >= 1180 and altura >= 700 else "hidden"
        for simbolo, texto in self._beneficios:
            c.itemconfigure(simbolo, state=estado_beneficios)
            c.itemconfigure(texto, state=estado_beneficios)

    def entrar(self):
        usuario = self.usuario_var.get().strip()
        senha = self.senha_var.get()
        if not usuario or not senha:
            self._status_texto = "Informe usuário e senha."
            self._status_tipo = "warning"
            self._atualizar_status()
            return
        try:
            usuario_autenticado = autenticar_usuario(
                usuario, senha, self.codigo_mfa_var.get().strip(),
            )
        except (ValueError, PermissionError) as erro:
            self._status_texto = str(erro)
            self._status_tipo = "danger"
            self._atualizar_status()
            return
        SESSAO.iniciar(usuario_autenticado)
        # A escolha feita antes do login passa a valer para esta conta e para
        # as próximas aberturas. Indisponibilidade de rede não bloqueia o uso.
        persistir_tema_autenticado()
        # A navegação de destino destrói o login somente depois de validar o
        # contexto remoto, evitando janela vazia em caso de falha de rede.
        self.ao_entrar()

    def destruir(self):
        self.root.unbind("<Return>")
        try:
            self.container.destroy()
        except tk.TclError:
            pass
