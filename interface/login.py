import tkinter as tk

from auth.autenticacao import autenticar_usuario
from auth.sessao import SESSAO
from interface.imagens import abrir_imagem, criar_photoimage
from interface.tema import CORES, MARCA


class TelaLogin:

    def __init__(self, root, ao_entrar, mensagem_inicial=None):
        self.root = root
        self.ao_entrar = ao_entrar
        self.cores = CORES
        self.mensagem_inicial = mensagem_inicial

        self._agendamento_imagens = None
        self._imagem_fundo_tk = None
        self._imagem_ecossistema_tk = None
        self._fallback_centro = (0, 0)

        self.criar_interface()

    def criar_interface(self):
        self.root.title("Data Intelligence · Acesso corporativo · V9.0")

        self.container = tk.Canvas(
            self.root,
            bg=self.cores["bg"],
            bd=0,
            highlightthickness=0,
        )
        self.container.pack(fill="both", expand=True)

        self._imagem_fundo_original = abrir_imagem(
            "backgrounds/login_background_v7.png"
        )
        self._imagem_ecossistema_original = abrir_imagem(
            "illustrations/login_ecossistema_transparente_v8.png"
        )

        self._item_fundo = self.container.create_image(
            0,
            0,
            anchor="nw",
        )
        self._item_ecossistema = self.container.create_image(0, 0)

        self._criar_fallback_ecossistema()
        self._criar_identidade_canvas()
        self._criar_card_login()

        self.container.bind("<Configure>", self._ao_redimensionar)
        self.root.bind("<Return>", lambda _evento: self.entrar())
        self.root.after_idle(self._iniciar_layout)

    def _criar_identidade_canvas(self):
        c = self.container

        self._marca_simbolo = c.create_text(
            0,
            0,
            text=MARCA["simbolo"],
            font=("Segoe UI Symbol", 27),
            fill=self.cores["primary"],
            anchor="w",
        )
        self._marca_nome = c.create_text(
            0,
            0,
            text=MARCA["nome"],
            font=("Segoe UI", 18, "bold"),
            fill=self.cores["text"],
            anchor="w",
        )
        self._marca_descricao = c.create_text(
            0,
            0,
            text=MARCA["descricao"],
            font=("Segoe UI", 9, "bold"),
            fill=self.cores["primary"],
            anchor="nw",
        )

        self._eyebrow = c.create_text(
            0,
            0,
            text="ECOSSISTEMA EMPRESARIAL CONECTADO",
            font=("Segoe UI", 8, "bold"),
            fill=self.cores["accent"],
            anchor="nw",
        )
        self._linha_destaque = c.create_line(
            0,
            0,
            65,
            0,
            fill=self.cores["primary"],
            width=3,
        )
        self._chamada = c.create_text(
            0,
            0,
            text="Operações conectadas.\nDecisões inteligentes.",
            font=("Segoe UI", 24, "bold"),
            fill=self.cores["text"],
            justify="left",
            anchor="nw",
        )
        self._descricao = c.create_text(
            0,
            0,
            text=(
                "Uma plataforma empresarial modular para dados, processos, "
                "aprovações, automações e inteligência operacional."
            ),
            font=("Segoe UI", 10),
            fill=self.cores["text_sec"],
            justify="left",
            anchor="nw",
            width=480,
        )

        self._estatisticas = []
        for valor, rotulo in (
            ("9", "MÓDULOS"),
            ("1", "MOTOR CENTRAL"),
            ("24/7", "CONTROLE"),
        ):
            item_valor = c.create_text(
                0,
                0,
                text=valor,
                font=("Segoe UI", 11, "bold"),
                fill=self.cores["text"],
                anchor="nw",
            )
            item_rotulo = c.create_text(
                0,
                0,
                text=rotulo,
                font=("Segoe UI", 9, "bold"),
                fill=self.cores["text_muted"],
                anchor="nw",
            )
            self._estatisticas.append((item_valor, item_rotulo))

        self._divisores_estatisticas = (
            c.create_line(0, 0, 0, 30, fill=self.cores["divider"]),
            c.create_line(0, 0, 0, 30, fill=self.cores["divider"]),
        )

    def _criar_card_login(self):
        card = tk.Frame(
            self.container,
            bg=self.cores["card"],
            width=410,
            height=500,
            highlightthickness=1,
            highlightbackground=self.cores["border"],
        )
        card.pack_propagate(False)
        self.card = card

        tk.Label(
            card,
            text="ACESSO CORPORATIVO",
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["primary"],
            bg=self.cores["card"],
        ).pack(anchor="w", padx=40, pady=(40, 8))

        tk.Label(
            card,
            text="Bem-vindo",
            font=("Segoe UI", 22, "bold"),
            fg=self.cores["text"],
            bg=self.cores["card"],
        ).pack(anchor="w", padx=40)

        tk.Label(
            card,
            text="Entre com suas credenciais para acessar a plataforma.",
            font=("Segoe UI", 9),
            fg=self.cores["text_sec"],
            bg=self.cores["card"],
            wraplength=300,
            justify="left",
        ).pack(anchor="w", padx=40, pady=(5, 25))

        self.entry_usuario = self.criar_campo(card, "Usuário")
        self.entry_senha = self.criar_campo(card, "Senha", mostrar="•")

        tk.Button(
            card,
            text="ENTRAR NA PLATAFORMA  →",
            font=("Segoe UI", 9, "bold"),
            bg=self.cores["primary"],
            fg="#FFFFFF",
            activebackground=self.cores["primary_hover"],
            activeforeground="#FFFFFF",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=self.entrar,
        ).pack(fill="x", padx=40, pady=(25, 12), ipady=9)

        self.label_status = tk.Label(
            card,
            text="●  Ambiente protegido",
            font=("Segoe UI", 8),
            fg=self.cores["success"],
            bg=self.cores["card"],
        )
        self.label_status.pack(anchor="w", padx=40)

        if self.mensagem_inicial:
            self.label_status.configure(
                text=self.mensagem_inicial,
                fg=self.cores["warning"],
            )

        tk.Label(
            card,
            text="Data Intelligence · Enterprise Platform · V9.0",
            font=("Segoe UI", 8),
            fg=self.cores["text_muted"],
            bg=self.cores["card"],
        ).pack(side="bottom", pady=25)

        self.entry_usuario.focus_set()

    def _criar_fallback_ecossistema(self):
        c = self.container
        centro = (0, 0)
        nos = (
            (-170, -100, self.cores["success"]),
            (0, -145, self.cores["warning"]),
            (170, -100, self.cores["purple"]),
            (205, 0, self.cores["accent"]),
            (170, 105, self.cores["danger"]),
            (0, 145, self.cores["primary"]),
            (-170, 105, self.cores["teal"]),
            (-205, 0, self.cores["accent"]),
            (-100, 0, self.cores["purple"]),
        )

        for x, y, cor in nos:
            c.create_line(
                centro[0],
                centro[1],
                x,
                y,
                fill=self.cores["primary_soft"],
                width=2,
                tags="fallback_ecossistema",
            )
            c.create_oval(
                x - 15,
                y - 15,
                x + 15,
                y + 15,
                outline=cor,
                width=2,
                fill=self.cores["card"],
                tags="fallback_ecossistema",
            )

        c.create_oval(
            -55,
            -55,
            55,
            55,
            outline=self.cores["primary"],
            width=3,
            fill=self.cores["card"],
            tags="fallback_ecossistema",
        )
        c.create_oval(
            -31,
            -31,
            31,
            31,
            outline=self.cores["accent"],
            width=2,
            tags="fallback_ecossistema",
        )

        estado = "hidden" if self._imagem_ecossistema_original is not None else "normal"
        c.itemconfigure("fallback_ecossistema", state=estado)

    def _iniciar_layout(self):
        try:
            self.root.update_idletasks()
            largura = max(1, self.container.winfo_width())
            altura = max(1, self.container.winfo_height())
        except tk.TclError:
            return
        self._organizar_layout(largura, altura)
        self._renderizar_imagens(largura, altura)

    def _ao_redimensionar(self, evento):
        largura = max(1, int(evento.width))
        altura = max(1, int(evento.height))
        self._organizar_layout(largura, altura)

        if self._agendamento_imagens is not None:
            try:
                self.container.after_cancel(self._agendamento_imagens)
            except tk.TclError:
                pass
        self._agendamento_imagens = self.container.after(
            70,
            lambda: self._renderizar_imagens(largura, altura),
        )

    def _organizar_layout(self, largura, altura):
        c = self.container
        margem = max(54, int(largura * 0.055))
        marca_y = max(48, int(altura * 0.075))

        c.coords(self._marca_simbolo, margem, marca_y)
        c.coords(self._marca_nome, margem + 120, marca_y - 7)
        c.coords(self._marca_descricao, margem + 120, marca_y + 17)

        # Mantém a ilustração entre a marca e o texto institucional mesmo
        # na altura mínima suportada pela janela.
        eyebrow_y = max(
            marca_y + 330,
            min(int(altura * 0.58), altura - 290),
        )
        limite_esquerdo = max(310, int(largura * 0.43))
        espaco_vertical = max(280, eyebrow_y - (marca_y + 65) - 22)
        self._ecossistema_tamanho = max(
            250,
            min(470, espaco_vertical, limite_esquerdo),
        )
        ecossistema_x = margem + limite_esquerdo // 2
        ecossistema_y = marca_y + 65 + self._ecossistema_tamanho // 2
        c.coords(self._item_ecossistema, ecossistema_x, ecossistema_y)

        delta_x = ecossistema_x - self._fallback_centro[0]
        delta_y = ecossistema_y - self._fallback_centro[1]
        c.move("fallback_ecossistema", delta_x, delta_y)
        self._fallback_centro = (ecossistema_x, ecossistema_y)

        c.coords(self._eyebrow, margem, eyebrow_y)
        c.coords(self._linha_destaque, margem, eyebrow_y + 26, margem + 65, eyebrow_y + 26)
        c.coords(self._chamada, margem, eyebrow_y + 48)
        c.coords(self._descricao, margem, eyebrow_y + 138)
        c.itemconfigure(self._descricao, width=min(500, int(largura * 0.42)))

        estatisticas_y = eyebrow_y + 220
        posicoes_x = (margem, margem + 110, margem + 255)
        for (item_valor, item_rotulo), x in zip(self._estatisticas, posicoes_x):
            c.coords(item_valor, x, estatisticas_y)
            c.coords(item_rotulo, x, estatisticas_y + 23)

        for divisor, x in zip(
            self._divisores_estatisticas,
            (margem + 85, margem + 230),
        ):
            c.coords(divisor, x, estatisticas_y, x, estatisticas_y + 30)

        card_x = min(int(largura * 0.78), largura - 245)
        self.card.place(x=card_x, y=altura // 2, anchor="center")

    def _renderizar_imagens(self, largura, altura):
        self._agendamento_imagens = None
        if not self.container.winfo_exists():
            return

        if self._imagem_fundo_original is not None:
            self._imagem_fundo_tk = criar_photoimage(
                self._imagem_fundo_original,
                tamanho=(largura, altura),
                preencher=True,
                master=self.root,
            )
            self.container.itemconfigure(
                self._item_fundo,
                image=self._imagem_fundo_tk,
                state="normal",
            )
            self.container.coords(self._item_fundo, 0, 0)
            self.container.tag_lower(self._item_fundo)
        else:
            self.container.itemconfigure(self._item_fundo, state="hidden")

        if self._imagem_ecossistema_original is not None:
            tamanho = int(getattr(self, "_ecossistema_tamanho", 420))
            self._imagem_ecossistema_tk = criar_photoimage(
                self._imagem_ecossistema_original,
                tamanho=(tamanho, tamanho),
                master=self.root,
            )
            self.container.itemconfigure(
                self._item_ecossistema,
                image=self._imagem_ecossistema_tk,
                state="normal",
            )
            self.container.itemconfigure("fallback_ecossistema", state="hidden")
        else:
            self.container.itemconfigure(self._item_ecossistema, state="hidden")
            self.container.itemconfigure("fallback_ecossistema", state="normal")

    def criar_campo(self, parent, titulo, mostrar=None):
        frame = tk.Frame(parent, bg=self.cores["card"])
        frame.pack(fill="x", padx=40, pady=8)

        tk.Label(
            frame,
            text=titulo.upper(),
            font=("Segoe UI", 8, "bold"),
            fg=self.cores["text_sec"],
            bg=self.cores["card"],
        ).pack(anchor="w", pady=(0, 6))

        entrada_frame = tk.Frame(frame, bg=self.cores["border"])
        entrada_frame.pack(fill="x")

        entrada_interior = tk.Frame(
            entrada_frame,
            bg=self.cores["input"],
        )
        entrada_interior.pack(fill="x", padx=1, pady=1)

        entry = tk.Entry(
            entrada_interior,
            font=("Segoe UI", 11),
            bg=self.cores["input"],
            fg=self.cores["text"],
            insertbackground=self.cores["primary"],
            relief="flat",
            bd=0,
            show=mostrar,
        )
        entry.pack(fill="x", padx=(10, 6), ipady=9)

        entry.bind(
            "<FocusIn>",
            lambda _evento: entrada_frame.configure(bg=self.cores["primary"]),
        )
        entry.bind(
            "<FocusOut>",
            lambda _evento: entrada_frame.configure(bg=self.cores["border"]),
        )
        return entry

    def entrar(self):
        usuario = self.entry_usuario.get().strip()
        senha = self.entry_senha.get()

        if not usuario or not senha:
            self.label_status.configure(
                text="Informe usuário e senha.",
                fg=self.cores["warning"],
            )
            return

        try:
            usuario_autenticado = autenticar_usuario(usuario, senha)
        except (ValueError, PermissionError) as erro:
            self.label_status.configure(
                text=str(erro),
                fg=self.cores["danger"],
            )
            return

        SESSAO.iniciar(usuario_autenticado)
        self.destruir()
        self.ao_entrar()

    def destruir(self):
        if self._agendamento_imagens is not None:
            try:
                self.container.after_cancel(self._agendamento_imagens)
            except tk.TclError:
                pass
        self.root.unbind("<Return>")
        self.container.destroy()
