"""Painéis departamentais responsivos e funcionais da V8."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from auth.sessao import SESSAO
from enterprise.catalogo import obter_modulo
from enterprise.contexto import tem_permissao
from enterprise.modulos import calcular_resumo_modulo
from enterprise.recursos import (
    alterar_estado_recurso,
    atualizar_recurso,
    criar_recurso,
    listar_recursos,
    obter_recurso,
    resumo_recursos,
)
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_chip,
    criar_estado_vazio,
    criar_metrica,
    preparar_janela_secundaria,
    criar_sidebar,
    criar_titulo_secao,
)
from interface.grade_editavel import EditorGrade
from interface.configuracao_modulos_ui import (
    PAINEIS_MODULOS,
    obter_esquema_recurso,
)
from interface.tema import (
    CORES,
    FONTES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


STATUS_COMUNS = (
    "Pendente",
    "Planejado",
    "Aberto",
    "Em andamento",
    "Em análise",
    "Aprovado",
    "Concluído",
    "Cancelado",
)


class TelaPainelModulo:
    def __init__(self, root, navegacao, modulo, secao="visao"):
        self.root = root
        self.navegacao = navegacao
        self.modulo = modulo
        self.secao = secao
        self.modulo_config = obter_modulo(modulo)
        self.ui = PAINEIS_MODULOS[modulo]
        self.cor = self.modulo_config["cor"]
        self.pagina = 1
        self.paginas = 1
        self.registros: list[dict] = []
        if not tem_permissao(SESSAO.usuario, modulo, "ler"):
            raise PermissionError("Seu perfil não possui acesso a este módulo.")
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()

    def criar_interface(self):
        configurar_estilos_ttk(self.root)
        itens = tuple(
            (
                chave,
                icone,
                titulo,
                lambda destino=chave: self.abrir_secao(destino),
            )
            for chave, icone, titulo in self.ui["menu"]
        )
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo=self.secao,
            itens_customizados=itens,
            titulo_customizado=self.modulo_config["nome"].upper(),
            rodape_texto="Voltar aos módulos",
            rodape_comando=self.navegacao.get("modulos"),
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(22, 20),
        )
        conteudo = viewport.conteudo
        if self.secao == "visao":
            self._visao_geral(conteudo)
        else:
            self._secao_operacional(conteudo)

    def abrir_secao(self, secao):
        if secao == "registros":
            self.navegacao["registros_modulo"](self.modulo)
            return
        self.container.destroy()
        TelaPainelModulo(self.root, self.navegacao, self.modulo, secao)

    def _visao_geral(self, parent):
        criar_cabecalho(
            parent,
            self.ui["titulo"],
            self.ui["resumo"],
            breadcrumb=f"MÓDULOS  /  {self.modulo_config['nome'].upper()}",
            etiqueta="PAINEL DEPARTAMENTAL",
        )
        self._metricas(parent)

        corpo = tk.Frame(parent, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True, pady=(14, 0))
        esquerda = tk.Frame(corpo, bg=CORES["bg"])
        direita = tk.Frame(corpo, bg=CORES["bg"])

        self._acoes_rapidas(esquerda)
        self._fluxo(esquerda)
        self._acoes_modulo(direita)
        self._status_backend(direita)
        self._recursos_disponiveis(direita)

        def reorganizar(evento=None):
            largura = evento.width if evento else corpo.winfo_width()
            esquerda.grid_forget()
            direita.grid_forget()
            corpo.grid_columnconfigure(0, weight=1)
            corpo.grid_columnconfigure(1, weight=0)
            if largura >= 930:
                corpo.grid_columnconfigure(1, minsize=290)
                esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
                direita.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            else:
                esquerda.grid(row=0, column=0, columnspan=2, sticky="nsew")
                direita.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        corpo.bind("<Configure>", reorganizar, add="+")
        corpo.after_idle(reorganizar)

    def _metricas(self, parent):
        area = GradeResponsiva(parent, max_colunas=4, largura_minima=210, gap=9, bg=CORES["bg"])
        area.pack(fill="x")
        try:
            cards = list(
                calcular_resumo_modulo(self.modulo, SESSAO.usuario)["cards"][:4]
            )
        except (PermissionError, ValueError, TypeError):
            cards = []
        while len(cards) < 4:
            cards.append(("SEM DADOS", 0, "inteiro"))
        for indice, (titulo, valor, formato) in enumerate(cards):
            card = criar_metrica(
                area,
                titulo,
                self._formatar(valor, formato),
                icone=self.modulo_config["icone"],
                cor=self.cor,
                detalhe="Contexto empresarial selecionado",
            )
            area.adicionar(card)

    def _acoes_rapidas(self, parent):
        card = criar_card(parent)
        card.pack(fill="x")
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", padx=17, pady=15)
        criar_titulo_secao(
            interior,
            "Acesso rápido",
            "Atalhos operacionais do departamento.",
        )
        grade = GradeResponsiva(
            interior,
            max_colunas=3,
            largura_minima=215,
            gap=8,
            bg=CORES["card"],
        )
        grade.pack(fill="x")
        destinos = self.ui.get("acao_destinos", ())
        for indice, (titulo, descricao, icone) in enumerate(self.ui["acoes"]):
            destino = destinos[indice] if indice < len(destinos) else "registros"
            bloco = tk.Frame(
                grade,
                bg=CORES["card_secundario"],
                highlightthickness=1,
                highlightbackground=CORES["border_soft"],
            )
            grade.adicionar(bloco)
            tk.Label(
                bloco,
                text=icone,
                font=("Segoe UI Symbol", 14, "bold"),
                fg=self.cor,
                bg=CORES["card_secundario"],
            ).pack(anchor="w", padx=13, pady=(11, 5))
            tk.Label(
                bloco,
                text=titulo,
                font=("Segoe UI", 9, "bold"),
                fg=CORES["text"],
                bg=CORES["card_secundario"],
            ).pack(anchor="w", padx=13)
            tk.Label(
                bloco,
                text=descricao,
                font=FONTES["micro"],
                fg=CORES["text_sec"],
                bg=CORES["card_secundario"],
                wraplength=180,
                justify="left",
            ).pack(anchor="w", padx=13, pady=(4, 5))
            criar_botao(
                bloco,
                "ABRIR  →",
                lambda alvo=destino: self.abrir_secao(alvo),
                tipo="fantasma",
                compacto=True,
            ).pack(side="bottom", anchor="w", padx=3, pady=(0, 5))

    def _fluxo(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True, pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=17, pady=15)
        resumo = resumo_recursos(self.modulo, SESSAO.usuario)
        criar_titulo_secao(
            interior,
            self.ui["fila_titulo"],
            f"{resumo['total']} registro(s) especializado(s) no contexto atual.",
        )
        fluxo = GradeResponsiva(
            interior,
            max_colunas=5,
            largura_minima=130,
            gap=6,
            bg=CORES["card"],
        )
        fluxo.pack(fill="both", expand=True, pady=(7, 0))
        totais = [
            item["total"]
            for item in resumo["por_recurso"].values()
        ] or [0]
        for indice, etapa in enumerate(self.ui["etapas"]):
            valor = totais[indice] if indice < len(totais) else 0
            coluna = tk.Frame(
                fluxo,
                bg=CORES["input"],
                highlightthickness=1,
                highlightbackground=CORES["border_soft"],
            )
            fluxo.adicionar(coluna)
            tk.Frame(coluna, bg=self.cor, height=3).pack(fill="x")
            tk.Label(
                coluna,
                text=etapa,
                font=("Segoe UI", 8, "bold"),
                fg=CORES["text_sec"],
                bg=CORES["input"],
                wraplength=105,
                justify="center",
            ).pack(pady=(15, 6), padx=5)
            tk.Label(
                coluna,
                text=str(valor),
                font=("Segoe UI", 20, "bold"),
                fg=CORES["text"],
                bg=CORES["input"],
            ).pack()
            tk.Label(
                coluna,
                text="registro(s)",
                font=FONTES["micro"],
                fg=CORES["text_muted"],
                bg=CORES["input"],
            ).pack(pady=(0, 13))

    def _acoes_modulo(self, parent):
        card = criar_card(parent, destaque=True)
        card.pack(fill="x")
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=14, pady=14)
        criar_titulo_secao(
            interior,
            "Ações do painel",
            "Operações do módulo selecionado.",
        )
        if tem_permissao(SESSAO.usuario, self.modulo, "escrever"):
            criar_botao(
                interior,
                "+  NOVO REGISTRO",
                lambda: self.navegacao["registros_modulo"](self.modulo),
            ).pack(fill="x", pady=(0, 7))
        if tem_permissao(SESSAO.usuario, "analytics", "escrever"):
            criar_botao(
                interior,
                "◈  ANALISAR MÓDULO",
                lambda: self.navegacao["analisar_modulo"](self.modulo),
                tipo="secundario",
            ).pack(fill="x")

    def _status_backend(self, parent):
        card = criar_card(parent)
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=15, pady=14)
        topo = tk.Frame(interior, bg=CORES["card"])
        topo.pack(fill="x")
        tk.Label(
            topo,
            text="✓",
            font=("Segoe UI Symbol", 18, "bold"),
            fg=CORES["success"],
            bg=CORES["success_soft"],
            width=3,
            height=1,
        ).pack(side="left", padx=(0, 9))
        textos = tk.Frame(topo, bg=CORES["card"])
        textos.pack(side="left", fill="x", expand=True)
        tk.Label(
            textos,
            text="Backend departamental ativo",
            font=("Segoe UI", 9, "bold"),
            fg=CORES["text"],
            bg=CORES["card"],
        ).pack(anchor="w")
        tk.Label(
            textos,
            text="Persistência, permissões e auditoria habilitadas.",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
            wraplength=190,
            justify="left",
        ).pack(anchor="w", pady=(2, 0))

    def _recursos_disponiveis(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True, pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=15, pady=14)
        criar_titulo_secao(interior, "Recursos conectados")
        resumo = resumo_recursos(self.modulo, SESSAO.usuario)["por_recurso"]
        for chave, _icone, titulo in self.ui["menu"]:
            if chave in {"visao", "registros"}:
                continue
            quantidade = resumo.get(chave, {}).get("total", 0)
            linha = tk.Button(
                interior,
                text=f"○  {titulo}    {quantidade}",
                command=lambda destino=chave: self.abrir_secao(destino),
                font=FONTES["texto_pequeno"],
                fg=CORES["text_sec"],
                bg=CORES["card"],
                activebackground=CORES["card_hover"],
                activeforeground=CORES["text"],
                relief="flat",
                bd=0,
                anchor="w",
                cursor="hand2",
                padx=4,
                pady=4,
            )
            linha.pack(fill="x")

    def _rotulo_secao(self):
        return next(
            (
                titulo
                for chave, _icone, titulo in self.ui["menu"]
                if chave == self.secao
            ),
            self.secao.replace("_", " ").title(),
        )

    def _secao_operacional(self, parent):
        self.rotulo_secao = self._rotulo_secao()
        self.esquema_recurso = obter_esquema_recurso(self.secao)
        def acoes(area):
            bloco = tk.Frame(area, bg=CORES["bg"])
            criar_botao(
                bloco,
                "ATUALIZAR",
                self.carregar_recursos,
                tipo="secundario",
                compacto=True,
            ).pack(side="right")
            if tem_permissao(SESSAO.usuario, self.modulo, "escrever"):
                criar_botao(
                    bloco,
                    "+  NOVO",
                    self.abrir_formulario_recurso,
                    compacto=True,
                ).pack(side="right", padx=(0, 8))
            return bloco
        criar_cabecalho(
            parent,
            self.rotulo_secao,
            f"Operação especializada de {self.modulo_config['nome']} com rastreabilidade por empresa e filial.",
            acao=acoes,
            breadcrumb=(
                f"MÓDULOS  /  {self.modulo_config['nome'].upper()}  /  "
                f"{self.rotulo_secao.upper()}"
            ),
            etiqueta="OPERACIONAL V9.0",
        )

        painel = criar_card(parent)
        painel.pack(fill="both", expand=True)
        topo = tk.Frame(painel, bg=CORES["card"])
        topo.pack(fill="x", padx=16, pady=(14, 9))
        tk.Label(
            topo,
            text="REGISTROS ESPECIALIZADOS",
            font=("Segoe UI", 9, "bold"),
            fg=self.cor,
            bg=CORES["card"],
        ).pack(side="left")
        self.label_total = tk.Label(
            topo,
            text="0 registro(s)",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        )
        self.label_total.pack(side="right")

        filtros = tk.Frame(painel, bg=CORES["card"])
        filtros.pack(fill="x", padx=16, pady=(0, 10))
        self.pesquisa_var = tk.StringVar()
        pesquisa = tk.Entry(
            filtros,
            textvariable=self.pesquisa_var,
            font=FONTES["texto_pequeno"],
            bg=CORES["input"],
            fg=CORES["text"],
            insertbackground=CORES["primary"],
            relief="flat",
            bd=0,
        )
        pesquisa.pack(side="left", fill="x", expand=True, ipady=8)
        pesquisa.bind("<Return>", lambda _evento: self.aplicar_filtros())
        criar_botao(
            filtros,
            "PESQUISAR",
            self.aplicar_filtros,
            tipo="secundario",
            compacto=True,
        ).pack(side="left", padx=(8, 0))
        opcoes_status = next(
            (
                campo[3]
                for campo in self.esquema_recurso
                if campo[0] == "status" and len(campo) > 3
            ),
            STATUS_COMUNS,
        )
        self.status_var = tk.StringVar(value="Todos")
        status = ttk.Combobox(
            filtros,
            textvariable=self.status_var,
            values=("Todos", *opcoes_status),
            state="readonly",
            width=17,
            style="Dark.TCombobox",
        )
        status.pack(side="left", padx=(8, 0))
        status.bind("<<ComboboxSelected>>", lambda _evento: self.aplicar_filtros())
        self.estado_var = tk.StringVar(value="Ativo")
        estado = ttk.Combobox(
            filtros,
            textvariable=self.estado_var,
            values=("Ativo", "Arquivado", "Lixeira", "Todos"),
            state="readonly",
            width=12,
            style="Dark.TCombobox",
        )
        estado.pack(side="left", padx=(8, 0))
        estado.bind("<<ComboboxSelected>>", lambda _evento: self.aplicar_filtros())

        area_tabela = tk.Frame(painel, bg=CORES["card"])
        area_tabela.pack(fill="both", expand=True, padx=16)
        colunas = tuple(campo[0] for campo in self.esquema_recurso) + (
            "atualizacao",
        )
        self.tabela = ttk.Treeview(
            area_tabela,
            columns=colunas,
            show="headings",
            style="Dark.Treeview",
        )
        definicoes = tuple(
            (campo[0], campo[1].upper(), self._largura_coluna(campo[2]))
            for campo in self.esquema_recurso
        ) + (("atualizacao", "ATUALIZAÇÃO", 145),)
        for chave, titulo, largura in definicoes:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(
                chave,
                width=largura,
                minwidth=75,
                anchor="w",
                stretch=chave == self.esquema_recurso[0][0],
            )
        barra = ttk.Scrollbar(
            area_tabela,
            orient="vertical",
            command=self.tabela.yview,
            style="Dark.Vertical.TScrollbar",
        )
        barra_horizontal = ttk.Scrollbar(
            area_tabela,
            orient="horizontal",
            command=self.tabela.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.tabela.configure(
            yscrollcommand=barra.set,
            xscrollcommand=barra_horizontal.set,
        )
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        barra_horizontal.grid(row=1, column=0, sticky="ew")
        area_tabela.grid_rowconfigure(0, weight=1, minsize=260)
        area_tabela.grid_columnconfigure(0, weight=1)
        self.tabela.bind("<<TreeviewSelect>>", self._atualizar_botoes)

        self.estado_vazio = criar_estado_vazio(
            area_tabela,
            self.modulo_config["icone"],
            f"Nenhum registro em {self.rotulo_secao}",
            "Crie um registro ou altere os filtros para continuar.",
            cor=self.cor,
        )
        adicionar_divisorias_treeview(
            self.tabela,
            sobreposicao=self.estado_vazio,
        )
        editaveis = {campo[0] for campo in self.esquema_recurso}
        self.editor_grade = EditorGrade(
            self.tabela,
            colunas_editaveis=editaveis,
            salvar=self._salvar_celula_grade,
            parent=self.root,
            titulo=f"{self.modulo_config['nome']} · {self.rotulo_secao}",
        )

        rodape = tk.Frame(painel, bg=CORES["card"])
        rodape.pack(fill="x", padx=16, pady=14)
        self.botao_editar = criar_botao(
            rodape,
            "EDITAR",
            self.editar_recurso,
            tipo="secundario",
            compacto=True,
        )
        self.botao_editar.pack(side="left")
        self.botao_arquivar = criar_botao(
            rodape,
            "ARQUIVAR",
            lambda: self.alterar_estado_selecionado("Arquivado"),
            tipo="secundario",
            compacto=True,
        )
        self.botao_arquivar.pack(side="left", padx=(7, 0))
        self.botao_lixeira = criar_botao(
            rodape,
            "LIXEIRA",
            lambda: self.alterar_estado_selecionado("Lixeira"),
            tipo="perigo",
            compacto=True,
        )
        self.botao_lixeira.pack(side="left", padx=(7, 0))
        self.botao_restaurar = criar_botao(
            rodape,
            "RESTAURAR",
            lambda: self.alterar_estado_selecionado("Ativo"),
            tipo="sucesso",
            compacto=True,
        )
        self.botao_restaurar.pack(side="left", padx=(7, 0))
        criar_botao(rodape, "EXPORTAR CSV", lambda: self.editor_grade.exportar_csv(), tipo="fantasma", compacto=True).pack(side="left", padx=(12, 0))
        criar_botao(rodape, "EXPORTAR XLSX", lambda: self.editor_grade.exportar_xlsx(), tipo="fantasma", compacto=True).pack(side="left", padx=(6, 0))
        self.botao_proximo = criar_botao(
            rodape,
            "PRÓXIMA  →",
            self.proxima_pagina,
            tipo="secundario",
            compacto=True,
        )
        self.botao_proximo.pack(side="right")
        self.label_pagina = tk.Label(
            rodape,
            text="Página 1 de 1",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        )
        self.label_pagina.pack(side="right", padx=10)
        self.botao_anterior = criar_botao(
            rodape,
            "←  ANTERIOR",
            self.pagina_anterior,
            tipo="secundario",
            compacto=True,
        )
        self.botao_anterior.pack(side="right")
        self.carregar_recursos()

    def aplicar_filtros(self):
        self.pagina = 1
        self.carregar_recursos()

    def carregar_recursos(self):
        if not hasattr(self, "tabela"):
            return
        try:
            resultado = listar_recursos(
                self.modulo,
                self.secao,
                SESSAO.usuario,
                pagina=self.pagina,
                tamanho=50,
                pesquisa=self.pesquisa_var.get(),
                status=self.status_var.get(),
                estado=self.estado_var.get(),
            )
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Carregar registros", str(erro), parent=self.root)
            return
        self.registros = resultado["registros"]
        self.pagina = resultado["pagina"]
        self.paginas = resultado["paginas"]
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for registro in self.registros:
            atualizado = str(registro.get("atualizado_em") or "").replace("T", " ")[:19]
            valores = [
                self._valor_campo(registro, campo)
                for campo in self.esquema_recurso
            ]
            self.tabela.insert(
                "",
                tk.END,
                iid=str(registro["id"]),
                values=(*valores, atualizado),
            )
        if self.registros:
            self.estado_vazio.place_forget()
        else:
            self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.estado_vazio.lift()
        self.label_total.configure(text=f"{resultado['total']} registro(s)")
        self.label_pagina.configure(text=f"Página {self.pagina} de {self.paginas}")
        self.botao_anterior.configure(
            state="normal" if self.pagina > 1 else "disabled"
        )
        self.botao_proximo.configure(
            state="normal" if self.pagina < self.paginas else "disabled"
        )
        self._atualizar_botoes()

    def _id_selecionado(self):
        selecao = self.tabela.selection() if hasattr(self, "tabela") else ()
        return int(selecao[0]) if selecao else None

    def _atualizar_botoes(self, _evento=None):
        recurso_id = self._id_selecionado()
        selecionado = recurso_id is not None
        escrever = tem_permissao(SESSAO.usuario, self.modulo, "escrever")
        registro = next(
            (item for item in self.registros if item["id"] == recurso_id),
            None,
        )
        estado = (
            registro.get("estado_registro", "Ativo")
            if registro is not None
            else self.estado_var.get()
        )
        normal = "normal" if selecionado and escrever else "disabled"
        self.botao_editar.configure(state=normal if estado == "Ativo" else "disabled")
        self.botao_arquivar.configure(state=normal if estado == "Ativo" else "disabled")
        self.botao_lixeira.configure(
            state=normal if estado in {"Ativo", "Arquivado"} else "disabled"
        )
        self.botao_restaurar.configure(
            state=normal if estado in {"Arquivado", "Lixeira"} else "disabled"
        )

    def _salvar_celula_grade(self, iid, chave, valor):
        if not tem_permissao(SESSAO.usuario, self.modulo, "escrever"):
            raise PermissionError("Seu perfil não permite editar esta grade.")
        registro = obter_recurso(self.modulo, self.secao, int(iid), SESSAO.usuario)
        extras = dict(registro.get("dados") or {})
        extras[chave] = valor
        dados = self._payload_especializado(extras)
        atualizar_recurso(self.modulo, self.secao, int(iid), dados, SESSAO.usuario)
        self.carregar_recursos()

    def pagina_anterior(self):
        if self.pagina > 1:
            self.pagina -= 1
            self.carregar_recursos()

    def proxima_pagina(self):
        if self.pagina < self.paginas:
            self.pagina += 1
            self.carregar_recursos()

    def editar_recurso(self):
        recurso_id = self._id_selecionado()
        if recurso_id is not None:
            self.abrir_formulario_recurso(recurso_id)

    def alterar_estado_selecionado(self, estado):
        recurso_id = self._id_selecionado()
        if recurso_id is None:
            return
        if not messagebox.askyesno(
            "Confirmar alteração",
            f"Deseja alterar este registro para {estado}?",
            parent=self.root,
        ):
            return
        try:
            alterar_estado_recurso(
                self.modulo,
                self.secao,
                recurso_id,
                estado,
                SESSAO.usuario,
            )
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Alterar registro", str(erro), parent=self.root)
            return
        self.carregar_recursos()

    def abrir_formulario_recurso(self, recurso_id=None):
        registro = None
        if recurso_id is not None:
            try:
                registro = obter_recurso(
                    self.modulo,
                    self.secao,
                    recurso_id,
                    SESSAO.usuario,
                )
            except (PermissionError, ValueError) as erro:
                messagebox.showerror("Editar registro", str(erro), parent=self.root)
                return
        janela = tk.Toplevel(self.root)
        janela.title(
            f"{'Editar' if registro else 'Novo'} · {self.rotulo_secao}"
        )
        preparar_janela_secundaria(
            janela, self.root, 760, 590, minimo=(660, 500)
        )
        janela.configure(bg=CORES["bg"])
        tk.Label(
            janela,
            text=f"{'Editar' if registro else 'Novo registro'} · {self.rotulo_secao}",
            font=FONTES["titulo_grande"],
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=26, pady=(22, 4))
        tk.Label(
            janela,
            text="Os dados serão registrados no contexto empresarial atual.",
            font=FONTES["texto_pequeno"],
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=26, pady=(0, 14))
        viewport = AreaRolavel(janela, bg=CORES["bg"])
        viewport.pack(fill="both", expand=True, padx=26)
        formulario = criar_card(viewport.conteudo)
        formulario.pack(fill="both", expand=True)
        formulario.grid_columnconfigure(0, weight=1)
        formulario.grid_columnconfigure(1, weight=1)
        campos = self.esquema_recurso
        variaveis: dict[str, tk.StringVar] = {}
        for indice, campo_def in enumerate(campos):
            chave, rotulo, tipo, *configuracao = campo_def
            grupo = tk.Frame(formulario, bg=CORES["card"])
            grupo.grid(
                row=indice // 2,
                column=indice % 2,
                sticky="ew",
                padx=(17, 8) if indice % 2 == 0 else (8, 17),
                pady=(14, 0),
            )
            tk.Label(
                grupo,
                text=rotulo.upper(),
                font=("Segoe UI", 8, "bold"),
                fg=CORES["text_sec"],
                bg=CORES["card"],
            ).pack(anchor="w", pady=(0, 5))
            variavel = tk.StringVar()
            variaveis[chave] = variavel
            if tipo == "opcoes":
                campo = ttk.Combobox(
                    grupo,
                    textvariable=variavel,
                    values=configuracao[0] if configuracao else (),
                    state="readonly",
                    style="Dark.TCombobox",
                )
                if configuracao and configuracao[0]:
                    variavel.set(configuracao[0][0])
            else:
                campo = tk.Entry(
                    grupo,
                    textvariable=variavel,
                    font=FONTES["texto"],
                    bg=CORES["input"],
                    fg=CORES["text"],
                    insertbackground=CORES["primary"],
                    relief="flat",
                    bd=0,
                )
            campo.pack(fill="x", ipady=7)
        if registro:
            extras = registro.get("dados") or {}
            tipos = {campo[0]: campo[2] for campo in campos}
            for chave, variavel in variaveis.items():
                valor = extras.get(chave)
                if valor in (None, ""):
                    valor = self._valor_bruto_legado(registro, chave)
                if tipos.get(chave) == "data" and valor:
                    partes = str(valor).split("-")
                    if len(partes) == 3 and len(partes[0]) == 4:
                        valor = "/".join(reversed(partes))
                if tipos.get(chave) == "moeda" and valor not in (None, ""):
                    valor = f"{float(valor or 0):.2f}".replace(".", ",")
                variavel.set("" if valor is None else str(valor))

        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=26, pady=18)
        status_label = tk.Label(
            rodape,
            text="* Campo obrigatório",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        )
        status_label.pack(side="left")

        def salvar():
            extras = {
                chave: variavel.get().strip()
                for chave, variavel in variaveis.items()
            }
            try:
                dados = self._payload_especializado(extras)
                if registro:
                    atualizar_recurso(
                        self.modulo,
                        self.secao,
                        int(registro["id"]),
                        dados,
                        SESSAO.usuario,
                    )
                else:
                    criar_recurso(
                        self.modulo,
                        self.secao,
                        dados,
                        SESSAO.usuario,
                    )
            except (PermissionError, ValueError) as erro:
                status_label.configure(text=str(erro), fg=CORES["danger"])
                return
            janela.destroy()
            self.carregar_recursos()

        criar_botao(rodape, "SALVAR", salvar).pack(side="right")
        criar_botao(
            rodape,
            "CANCELAR",
            janela.destroy,
            tipo="secundario",
        ).pack(side="right", padx=(0, 8))
        janela.bind("<Escape>", lambda _evento: janela.destroy())
        primeiro = next(iter(variaveis.values()), None)
        if primeiro is not None:
            janela.after_idle(lambda: janela.focus_force())

    @staticmethod
    def _largura_coluna(tipo):
        return {
            "texto": 190,
            "data": 120,
            "numero": 105,
            "moeda": 130,
            "opcoes": 135,
        }.get(tipo, 150)

    @staticmethod
    def _valor_bruto_legado(registro, chave):
        aliases = {
            "status": "status",
            "responsavel": "responsavel",
            "gestor": "responsavel",
            "advogado": "responsavel",
            "valor": "valor",
            "custo": "valor",
            "investimento": "valor",
        }
        if chave in registro:
            return registro.get(chave)
        return registro.get(aliases.get(chave, ""), "")

    def _valor_campo(self, registro, campo):
        chave, _rotulo, tipo, *_configuracao = campo
        valor = (registro.get("dados") or {}).get(chave)
        if valor in (None, ""):
            valor = self._valor_bruto_legado(registro, chave)
        if tipo == "moeda":
            return self._formatar(valor, "moeda")
        if tipo == "numero" and valor not in (None, ""):
            try:
                return f"{float(str(valor).replace(',', '.')):,.2f}".replace(
                    ",", "X"
                ).replace(".", ",").replace("X", ".").rstrip("0").rstrip(",")
            except (TypeError, ValueError):
                pass
        return "" if valor is None else str(valor)

    def _payload_especializado(self, extras):
        primeiro = self.esquema_recurso[0][0]
        identificacao = extras.get(primeiro, "").strip()
        if len(identificacao) < 2:
            raise ValueError(
                f"Preencha {self.esquema_recurso[0][1]} com ao menos 2 caracteres."
            )
        campo_status = next(
            (campo[0] for campo in self.esquema_recurso if campo[0] == "status"),
            None,
        )
        responsavel = next(
            (
                extras.get(chave, "")
                for chave in ("responsavel", "gestor", "advogado", "proprietario")
                if extras.get(chave)
            ),
            "",
        )
        valor = next(
            (
                extras.get(campo[0], "")
                for campo in self.esquema_recurso
                if campo[2] == "moeda" and extras.get(campo[0]) not in (None, "")
            ),
            "",
        )
        data_referencia = next(
            (
                extras.get(campo[0], "")
                for campo in self.esquema_recurso
                if campo[2] == "data" and extras.get(campo[0])
            ),
            "",
        )
        descricao = next(
            (
                extras.get(chave, "")
                for chave in (
                    "descricao", "motivo", "demanda", "obrigacao", "finalidade",
                    "equipamento", "categoria", "tipo_alerta",
                )
                if extras.get(chave)
            ),
            self.rotulo_secao,
        )
        prioridade = extras.get("criticidade", "Média")
        if prioridade not in {"Baixa", "Média", "Alta", "Crítica"}:
            prioridade = "Média"
        return {
            "identificacao": identificacao,
            "descricao": descricao,
            "responsavel": responsavel,
            "status": extras.get(campo_status, "Pendente") if campo_status else "Ativo",
            "prioridade": prioridade,
            "valor": valor,
            "data_referencia": data_referencia,
            "dados": extras,
        }

    @staticmethod
    def _formatar(valor, formato):
        try:
            numero = float(valor or 0)
        except (TypeError, ValueError):
            return str(valor or "0")
        if formato == "moeda":
            texto = f"{numero:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            return f"R$ {texto}"
        if formato == "decimal":
            return f"{numero:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{int(numero):,}".replace(",", ".")
