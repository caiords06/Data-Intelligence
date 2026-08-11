"""Dashboard e cadastro operacional reutilizável dos módulos empresariais."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from enterprise.catalogo import obter_modulo
from enterprise.contexto import tem_permissao
from enterprise.modulos import (
    alterar_estado_registro,
    atualizar_registro,
    calcular_resumo_modulo,
    criar_registro,
    listar_registros_paginados,
    movimentar_estoque,
    obter_registro,
)
from enterprise.organizacao import listar_centros_custo, listar_departamentos
from interface.componentes import (
    AreaRolavel,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_estado_vazio,
    preparar_janela_secundaria,
    criar_sidebar,
)
from interface.configuracao_modulos_ui import PAINEIS_MODULOS
from interface.tema import (
    CORES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


class TelaModuloEmpresarial:
    def __init__(self, root, navegacao, modulo):
        self.root = root
        self.navegacao = navegacao
        self.modulo = modulo
        self.configuracao = obter_modulo(modulo)
        if not tem_permissao(SESSAO.usuario, modulo, "ler"):
            raise PermissionError("Seu perfil não possui acesso a este módulo.")
        self.registros = []
        self.pagina = 1
        self.paginas = 1
        self.total = 0
        self.ordenar_por = "id"
        self.direcao = "DESC"
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()
        self.carregar()

    def criar_interface(self):
        configurar_estilos_ttk(self.root)
        itens_modulo = tuple(
            (
                chave,
                icone,
                titulo,
                (
                    None
                    if chave == "registros"
                    else lambda destino=chave: self.navegacao["secao_modulo"](
                        self.modulo, destino
                    )
                ),
            )
            for chave, icone, titulo in PAINEIS_MODULOS[self.modulo]["menu"]
        )
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="registros",
            itens_customizados=itens_modulo,
            titulo_customizado=self.configuracao["nome"].upper(),
            rodape_texto="Voltar ao painel do módulo",
            rodape_comando=lambda: self.navegacao["modulo"](self.modulo),
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(26, 22),
        )
        conteudo = viewport.conteudo
        self._cabecalho(conteudo)
        self.area_cards = tk.Frame(conteudo, bg=CORES["bg"])
        self.area_cards.pack(fill="x", pady=(0, 16))
        self._tabela(conteudo)

    def _cabecalho(self, parent):
        def acoes(area):
            bloco = tk.Frame(area, bg=CORES["bg"])
            if tem_permissao(SESSAO.usuario, "analytics", "escrever"):
                criar_botao(
                    bloco,
                    "◈  ANALISAR MÓDULO",
                    lambda: self.navegacao["analisar_modulo"](self.modulo),
                    tipo="secundario",
                    compacto=True,
                ).pack(side="right", padx=(8, 0))
            if tem_permissao(SESSAO.usuario, self.modulo, "escrever"):
                criar_botao(
                    bloco,
                    "+  NOVO REGISTRO",
                    self.abrir_formulario,
                    compacto=True,
                ).pack(side="right")
            if self.modulo == "estoque" and tem_permissao(
                SESSAO.usuario, "estoque", "escrever"
            ):
                criar_botao(
                    bloco,
                    "MOVIMENTAR",
                    self.abrir_movimentacao,
                    tipo="secundario",
                    compacto=True,
                ).pack(side="right", padx=(0, 8))
            return bloco
        criar_cabecalho(
            parent,
            f'{self.configuracao["icone"]}  {self.configuracao["nome"]}',
            self.configuracao["descricao"],
            acao=acoes,
            breadcrumb=(
                f"MÓDULOS  /  {self.configuracao['nome'].upper()}  /  "
                "REGISTROS OPERACIONAIS"
            ),
            etiqueta="CADASTRO V9.0",
        )

    def _tabela(self, parent):
        painel = criar_card(parent)
        painel.pack(fill="both", expand=True)
        topo = tk.Frame(painel, bg=CORES["card"])
        topo.pack(fill="x", padx=18, pady=(15, 10))
        tk.Label(
            topo,
            text="REGISTROS OPERACIONAIS",
            font=("Segoe UI", 9, "bold"),
            fg=self.configuracao["cor"],
            bg=CORES["card"],
        ).pack(side="left")
        self.status = tk.Label(
            topo,
            text="",
            font=("Segoe UI", 8),
            fg=CORES["text_sec"],
            bg=CORES["card"],
        )
        self.status.pack(side="right")

        filtros = tk.Frame(painel, bg=CORES["card"])
        filtros.pack(fill="x", padx=18, pady=(0, 10))
        self.filtro_pesquisa = tk.StringVar()
        campo_pesquisa = tk.Entry(
            filtros,
            textvariable=self.filtro_pesquisa,
            font=("Segoe UI", 9),
            bg=CORES["input"],
            fg=CORES["text"],
            insertbackground=CORES["primary"],
            relief="flat",
            bd=0,
        )
        campo_pesquisa.pack(side="left", fill="x", expand=True, ipady=7)
        campo_pesquisa.bind("<Return>", lambda _evento: self.aplicar_filtros())
        criar_botao(
            filtros,
            "PESQUISAR",
            self.aplicar_filtros,
            tipo="secundario",
        ).pack(side="left", padx=(8, 0))

        self.filtro_estado = tk.StringVar(value="Ativo")
        estado = ttk.Combobox(
            filtros,
            textvariable=self.filtro_estado,
            values=("Ativo", "Arquivado", "Lixeira", "Todos"),
            state="readonly",
            width=12,
            style="Dark.TCombobox",
        )
        estado.pack(side="left", padx=(8, 0))
        estado.bind("<<ComboboxSelected>>", lambda _evento: self.aplicar_filtros())

        self.tamanho_pagina = tk.StringVar(value="50")
        tamanho = ttk.Combobox(
            filtros,
            textvariable=self.tamanho_pagina,
            values=("25", "50", "100", "200"),
            state="readonly",
            width=5,
            style="Dark.TCombobox",
        )
        tamanho.pack(side="left", padx=(8, 0))
        tamanho.bind("<<ComboboxSelected>>", lambda _evento: self.aplicar_filtros())

        area_tabela = tk.Frame(painel, bg=CORES["card"])
        area_tabela.pack(fill="both", expand=True)

        colunas = tuple(item[0] for item in self.configuracao["colunas_tabela"])
        self.tabela = ttk.Treeview(
            area_tabela,
            columns=colunas,
            show="headings",
            style="Dark.Treeview",
        )
        for chave, titulo, largura in self.configuracao["colunas_tabela"]:
            self.tabela.heading(
                chave,
                text=titulo,
                command=lambda coluna=chave: self.ordenar(coluna),
            )
            self.tabela.column(chave, width=largura, anchor="w")
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
        self.tabela.grid(row=0, column=0, sticky="nsew", padx=(18, 0))
        barra.grid(row=0, column=1, sticky="ns", padx=(0, 18))
        barra_horizontal.grid(row=1, column=0, sticky="ew", padx=(18, 0))
        area_tabela.grid_rowconfigure(0, weight=1, minsize=280)
        area_tabela.grid_columnconfigure(0, weight=1)
        self.tabela.bind("<<TreeviewSelect>>", self._atualizar_acoes)

        self.estado_vazio = criar_estado_vazio(
            area_tabela,
            self.configuracao["icone"],
            "Nenhum registro neste módulo",
            "Utilize Novo registro para iniciar a operação.",
            cor=self.configuracao["cor"],
        )

        adicionar_divisorias_treeview(
            self.tabela,
            sobreposicao=self.estado_vazio,
        )

        rodape = tk.Frame(painel, bg=CORES["card"])
        rodape.pack(fill="x", padx=18, pady=(0, 15))
        self.botao_editar = criar_botao(
            rodape,
            "EDITAR",
            self.editar_selecionado,
            tipo="secundario",
        )
        self.botao_editar.pack(side="left")
        self.botao_arquivar = criar_botao(
            rodape,
            "ARQUIVAR",
            lambda: self.mudar_estado_selecionado("Arquivado"),
            tipo="secundario",
        )
        self.botao_arquivar.pack(side="left", padx=(8, 0))
        self.botao_lixeira = criar_botao(
            rodape,
            "ENVIAR À LIXEIRA",
            lambda: self.mudar_estado_selecionado("Lixeira"),
            tipo="perigo",
        )
        self.botao_lixeira.pack(side="left", padx=(8, 0))
        self.botao_restaurar = criar_botao(
            rodape,
            "RESTAURAR",
            lambda: self.mudar_estado_selecionado("Ativo"),
            tipo="sucesso",
        )
        self.botao_restaurar.pack(side="left", padx=(8, 0))

        self.botao_proxima = criar_botao(
            rodape,
            "PRÓXIMA  →",
            self.proxima_pagina,
            tipo="secundario",
        )
        self.botao_proxima.pack(side="right")
        self.label_pagina = tk.Label(
            rodape,
            text="Página 1 de 1",
            font=("Segoe UI", 8),
            fg=CORES["text_sec"],
            bg=CORES["card"],
        )
        self.label_pagina.pack(side="right", padx=12)
        self.botao_anterior = criar_botao(
            rodape,
            "←  ANTERIOR",
            self.pagina_anterior,
            tipo="secundario",
        )
        self.botao_anterior.pack(side="right")
        self._atualizar_acoes()

    def carregar(self):
        resultado = listar_registros_paginados(
            self.modulo,
            SESSAO.usuario,
            pagina=self.pagina,
            tamanho=int(self.tamanho_pagina.get()),
            pesquisa=self.filtro_pesquisa.get(),
            estado=self.filtro_estado.get(),
            ordenar_por=self.ordenar_por,
            direcao=self.direcao,
        )
        self.registros = resultado["registros"]
        self.pagina = resultado["pagina"]
        self.paginas = resultado["paginas"]
        self.total = resultado["total"]
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for registro in self.registros:
            valores = []
            for chave, _titulo, _largura in self.configuracao["colunas_tabela"]:
                valores.append(self._formatar_celula(chave, registro.get(chave)))
            self.tabela.insert(
                "",
                tk.END,
                iid=str(registro["id"]),
                values=valores,
            )
        if self.registros:
            self.estado_vazio.place_forget()
        else:
            self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.estado_vazio.lift()

            # Garante que a mensagem fique acima das divisórias
            self.estado_vazio.lift()

        self.status.configure(text=f"{self.total} registro(s)")
        self.label_pagina.configure(text=f"Página {self.pagina} de {self.paginas}")
        self.botao_anterior.configure(
            state="normal" if self.pagina > 1 else "disabled"
        )
        self.botao_proxima.configure(
            state="normal" if self.pagina < self.paginas else "disabled"
        )
        self._atualizar_acoes()
        self._atualizar_cards()

    def aplicar_filtros(self):
        self.pagina = 1
        self.carregar()

    def ordenar(self, coluna):
        if self.ordenar_por == coluna:
            self.direcao = "ASC" if self.direcao == "DESC" else "DESC"
        else:
            self.ordenar_por = coluna
            self.direcao = "ASC"
        self.pagina = 1
        self.carregar()

    def pagina_anterior(self):
        if self.pagina > 1:
            self.pagina -= 1
            self.carregar()

    def proxima_pagina(self):
        if self.pagina < self.paginas:
            self.pagina += 1
            self.carregar()

    def _id_selecionado(self):
        selecao = self.tabela.selection()
        return int(selecao[0]) if selecao else None

    def _atualizar_acoes(self, _evento=None):
        registro_id = self._id_selecionado()
        selecionado = registro_id is not None
        pode_escrever = tem_permissao(SESSAO.usuario, self.modulo, "escrever")
        registro = next(
            (item for item in self.registros if item["id"] == registro_id),
            None,
        )
        estado_atual = (
            registro.get("estado_registro", "Ativo")
            if registro is not None
            else self.filtro_estado.get()
        )
        normal = "normal" if selecionado and pode_escrever else "disabled"
        self.botao_editar.configure(
            state=normal if estado_atual == "Ativo" else "disabled"
        )
        self.botao_arquivar.configure(
            state=normal if estado_atual == "Ativo" else "disabled"
        )
        self.botao_lixeira.configure(
            state=normal if estado_atual in {"Ativo", "Arquivado"} else "disabled"
        )
        self.botao_restaurar.configure(
            state=normal if estado_atual in {"Arquivado", "Lixeira"} else "disabled"
        )

    def _atualizar_cards(self):
        for filho in self.area_cards.winfo_children():
            filho.destroy()
        resumo = calcular_resumo_modulo(self.modulo, SESSAO.usuario)
        for indice, (titulo, valor, formato) in enumerate(resumo["cards"]):
            card = criar_card(self.area_cards)
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, 8) if indice < 3 else (0, 0),
            )
            tk.Label(
                card,
                text=titulo,
                font=("Segoe UI", 8, "bold"),
                fg=self.configuracao["cor"],
                bg=CORES["card"],
            ).pack(anchor="w", padx=16, pady=(13, 5))
            tk.Label(
                card,
                text=self._formatar_valor(valor, formato),
                font=("Segoe UI", 17, "bold"),
                fg=CORES["text"],
                bg=CORES["card"],
            ).pack(anchor="w", padx=16, pady=(0, 13))

    def abrir_formulario(self, registro_id=None):
        registro = None
        if registro_id is not None:
            try:
                registro = obter_registro(self.modulo, registro_id, SESSAO.usuario)
            except (PermissionError, ValueError) as erro:
                messagebox.showerror("Editar registro", str(erro), parent=self.root)
                return
        titulo_formulario = (
            f"Editar · {self.configuracao['nome']}"
            if registro is not None
            else self.configuracao["titulo_registro"]
        )
        janela = tk.Toplevel(self.root)
        janela.title(titulo_formulario)
        preparar_janela_secundaria(
            janela, self.root, 700, 520, minimo=(620, 480)
        )
        janela.configure(bg=CORES["bg"])
        tk.Label(
            janela,
            text=titulo_formulario,
            font=("Segoe UI", 18, "bold"),
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=28, pady=(24, 4))
        tk.Label(
            janela,
            text="Preencha somente informações necessárias e autorizadas.",
            font=("Segoe UI", 9),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=28, pady=(0, 15))

        formulario = criar_card(janela)
        formulario.pack(fill="both", expand=True, padx=28)
        formulario.grid_columnconfigure(0, weight=1)
        formulario.grid_columnconfigure(1, weight=1)
        self.form_vars = {}
        self.form_maps = {}
        for indice, (nome, rotulo, tipo, obrigatorio) in enumerate(
            self.configuracao["campos"]
        ):
            grupo = tk.Frame(formulario, bg=CORES["card"])
            grupo.grid(
                row=indice // 2,
                column=indice % 2,
                sticky="ew",
                padx=(18, 9) if indice % 2 == 0 else (9, 18),
                pady=(14, 0),
            )
            tk.Label(
                grupo,
                text=f"{rotulo.upper()}{'  *' if obrigatorio else ''}",
                font=("Segoe UI", 8, "bold"),
                fg=CORES["text_sec"],
                bg=CORES["card"],
            ).pack(anchor="w", pady=(0, 5))
            variavel = tk.StringVar()
            self.form_vars[nome] = variavel
            valores = None
            if isinstance(tipo, tuple):
                valores = list(tipo)
            elif tipo == "departamento":
                registros = [item for item in listar_departamentos() if item["ativo"]]
                self.form_maps[nome] = {item["nome"]: item["id"] for item in registros}
                valores = list(self.form_maps[nome])
            elif tipo == "centro_custo":
                registros = [item for item in listar_centros_custo() if item["ativo"]]
                self.form_maps[nome] = {
                    f'{item["codigo"]} · {item["nome"]}': item["id"]
                    for item in registros
                }
                valores = list(self.form_maps[nome])
            if valores is not None:
                campo = ttk.Combobox(
                    grupo,
                    textvariable=variavel,
                    values=valores,
                    state="readonly",
                    style="Dark.TCombobox",
                )
                if valores:
                    variavel.set(valores[0])
            else:
                campo = tk.Entry(
                    grupo,
                    textvariable=variavel,
                    font=("Segoe UI", 10),
                    bg=CORES["input"],
                    fg=CORES["text"],
                    insertbackground=CORES["primary"],
                    relief="flat",
                    bd=0,
                )
            campo.pack(fill="x", ipady=7)
            if registro is not None:
                valor_atual = registro.get(nome)
                if nome in self.form_maps:
                    valor_atual = next(
                        (
                            rotulo
                            for rotulo, identificador in self.form_maps[nome].items()
                            if identificador == valor_atual
                        ),
                        "",
                    )
                variavel.set("" if valor_atual is None else str(valor_atual))

        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=28, pady=20)
        self.form_status = tk.Label(
            rodape,
            text="* Campos obrigatórios",
            font=("Segoe UI", 8),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        )
        self.form_status.pack(side="left")
        criar_botao(
            rodape,
            "CANCELAR",
            janela.destroy,
            tipo="secundario",
        ).pack(side="right")
        criar_botao(
            rodape,
            "SALVAR ALTERAÇÕES" if registro is not None else "SALVAR REGISTRO",
            lambda: self._salvar_formulario(janela, registro_id),
        ).pack(side="right", padx=(0, 8))

    def _salvar_formulario(self, janela, registro_id=None):
        dados = {}
        for nome, variavel in self.form_vars.items():
            valor = variavel.get()
            if nome in self.form_maps:
                valor = self.form_maps[nome].get(valor)
            dados[nome] = valor
        try:
            if registro_id is None:
                criar_registro(self.modulo, dados, SESSAO.usuario)
            else:
                atualizar_registro(
                    self.modulo,
                    registro_id,
                    dados,
                    SESSAO.usuario,
                )
        except (PermissionError, ValueError) as erro:
            self.form_status.configure(text=str(erro), fg=CORES["danger"])
            return
        janela.destroy()
        self.carregar()
        mensagem = (
            "Registro criado com sucesso."
            if registro_id is None
            else "Registro atualizado com sucesso."
        )
        self.status.configure(text=mensagem, fg=CORES["success"])

    def editar_selecionado(self):
        registro_id = self._id_selecionado()
        if registro_id is None:
            return
        self.abrir_formulario(registro_id)

    def mudar_estado_selecionado(self, estado):
        registro_id = self._id_selecionado()
        if registro_id is None:
            return
        verbos = {
            "Ativo": "restaurar",
            "Arquivado": "arquivar",
            "Lixeira": "enviar à lixeira",
        }
        if not messagebox.askyesno(
            "Confirmar alteração",
            f"Deseja {verbos[estado]} o registro selecionado?",
            parent=self.root,
        ):
            return
        try:
            alterar_estado_registro(
                self.modulo,
                registro_id,
                estado,
                SESSAO.usuario,
            )
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Registro", str(erro), parent=self.root)
            return
        self.carregar()
        self.status.configure(
            text=f"Registro alterado para {estado}.",
            fg=CORES["success"],
        )

    def abrir_movimentacao(self):
        selecao = self.tabela.selection()
        if not selecao:
            messagebox.showwarning(
                "Movimentar estoque",
                "Selecione um item na tabela.",
                parent=self.root,
            )
            return
        item_id = int(selecao[0])
        tipo = simpledialog.askstring(
            "Movimentar estoque",
            "Informe Entrada, Saída ou Ajuste:",
            parent=self.root,
        )
        if not tipo:
            return
        mapa = {"entrada": "Entrada", "saida": "Saída", "saída": "Saída", "ajuste": "Ajuste"}
        tipo = mapa.get(tipo.strip().lower())
        quantidade = simpledialog.askstring(
            "Movimentar estoque",
            "Quantidade:",
            parent=self.root,
        )
        if not tipo or not quantidade:
            messagebox.showerror("Movimentar estoque", "Operação inválida.", parent=self.root)
            return
        try:
            movimentar_estoque(item_id, tipo, quantidade, SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Movimentar estoque", str(erro), parent=self.root)
            return
        self.carregar()

    @staticmethod
    def _formatar_valor(valor, formato):
        # Consultas sem registros podem retornar None
        if valor is None or valor == "":
            numero = 0.0
        else:
            try:
                numero = float(valor)
            except (TypeError, ValueError):
                return "—"

        if formato == "moeda":
            texto = (
                f"{numero:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            return f"R$ {texto}"

        if formato == "decimal":
            return (
                f"{numero:,.1f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        return f"{int(numero):,}".replace(",", ".")

    @classmethod
    def _formatar_celula(cls, chave, valor):
        if valor is None or valor == "":
            return "—"
        if chave in {"salario", "valor", "valor_estimado", "investimento", "receita"}:
            return cls._formatar_valor(valor, "moeda")
        if chave in {"quantidade", "estoque_minimo"}:
            return cls._formatar_valor(valor, "decimal")
        return str(valor)
