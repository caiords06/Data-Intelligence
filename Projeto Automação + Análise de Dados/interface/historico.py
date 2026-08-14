"""Tela funcional de consulta do histórico de análises."""

from core.versao import VERSAO_INTERFACE
import json
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from interface.tema import (
    CORES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)
from auth.sessao import SESSAO
from configuracoes.preferencias import obter_preferencia
from historico.repositorio import excluir_analises, listar_historico, obter_analise
from interface.componentes import (
    AreaRolavel,
    criar_cabecalho,
    criar_estado_vazio,
    criar_sidebar,
    preparar_janela_secundaria,
)


class TelaHistorico:
    def __init__(self, root, navegacao):
        self.root = root
        self.navegacao = navegacao
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()
        self.carregar()

    def criar_interface(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="historico",
            rodape_texto="←   Voltar ao início",
            rodape_comando=self.navegacao.get("inicio"),
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(side="left", fill="both", expand=True, padx=40, pady=32)
        conteudo = viewport.conteudo
        criar_cabecalho(
            conteudo,
            "Histórico de análises",
            "Consulte resultados anteriores sem armazenar as planilhas originais.",
            breadcrumb="CENTRAL DA APLICAÇÃO  /  HISTÓRICO ANALÍTICO",
            etiqueta=f"RASTREÁVEL {VERSAO_INTERFACE}",
        )

        tabela_frame = tk.Frame(
            conteudo,
            bg=CORES["card"],
            highlightthickness=1,
            highlightbackground=CORES["border"],
        )
        tabela_frame.pack(fill="both", expand=True)

        colunas = (
            "data",
            "categoria",
            "arquivos",
            "registros",
            "qualidade",
            "usuario",
        )
        self.tabela = ttk.Treeview(
            tabela_frame,
            columns=colunas,
            show="headings",
            style="Dark.Treeview",
            selectmode="extended",
        )
        configuracoes = {
            "data": ("Data", 145),
            "categoria": ("Categoria", 130),
            "arquivos": ("Arquivos", 75),
            "registros": ("Registros", 95),
            "qualidade": ("Qualidade", 130),
            "usuario": ("Responsável", 160),
        }
        for coluna, (titulo, largura) in configuracoes.items():
            self.tabela.heading(coluna, text=titulo)
            self.tabela.column(coluna, width=largura, anchor="w")
        barra = ttk.Scrollbar(
            tabela_frame,
            orient="vertical",
            command=self.tabela.yview,
            style="Dark.Vertical.TScrollbar",
        )
        barra_horizontal = ttk.Scrollbar(
            tabela_frame, orient="horizontal", command=self.tabela.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.tabela.configure(
            yscrollcommand=barra.set, xscrollcommand=barra_horizontal.set
        )
        self.tabela.grid(row=0, column=0, sticky="nsew", padx=(16, 0), pady=(16, 0))
        barra.grid(row=0, column=1, sticky="ns", padx=(0, 16), pady=(16, 0))
        barra_horizontal.grid(row=1, column=0, sticky="ew", padx=(16, 0), pady=(0, 16))
        tabela_frame.grid_rowconfigure(0, weight=1, minsize=310)
        tabela_frame.grid_columnconfigure(0, weight=1)
        self.tabela.bind("<<TreeviewSelect>>", self._atualizar_estado_acoes)
        self.tabela.bind("<Control-a>", self._selecionar_todos)
        self.tabela.bind("<Control-A>", self._selecionar_todos)
        self.tabela.bind("<Double-1>", self._abrir_detalhes_duplo_clique)

        self.estado_vazio = criar_estado_vazio(
            tabela_frame,
            "◇",
            "Nenhuma análise registrada",
            "Quando o primeiro processamento for concluído, o resumo aparecerá aqui.",
        )
        adicionar_divisorias_treeview(
            self.tabela,
            sobreposicao=self.estado_vazio,
        )
        acoes = tk.Frame(conteudo, bg=CORES["bg"])
        acoes.pack(fill="x", pady=(14, 0))
        self._botao(acoes, "ATUALIZAR", self.carregar, secundario=True).pack(side="left")
        self.botao_detalhes = self._botao(acoes, "VER DETALHES", self.ver_detalhes)
        self.botao_detalhes.pack(side="left", padx=10)
        self.botao_excluir = self._botao(acoes, "EXCLUIR", self.excluir, perigo=True)
        self.botao_excluir.pack(side="left")
        self.status = tk.Label(
            acoes,
            text="",
            font=("Inter", 9),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        )
        self.status.pack(side="right")

    def _botao(self, parent, texto, comando, secundario=False, perigo=False):
        fundo = CORES["danger"] if perigo else (
            CORES["card_secundario"] if secundario else CORES["primary"]
        )
        botao = tk.Button(
            parent,
            text=texto,
            command=comando,
            font=("Inter", 9, "bold"),
            bg=fundo,
            fg="#FFFFFF",
            activebackground=CORES["card_hover"],
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=8,
            disabledforeground=CORES["text_disabled"],
        )
        botao._cor_normal = fundo
        return botao

    def carregar(self):
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        registros = listar_historico(SESSAO.usuario)
        for registro in registros:
            score = registro.get("score_qualidade")
            nivel = registro.get("nivel_qualidade") or "Não calculada"
            qualidade = f"{nivel} · {score:.1f}" if score is not None else nivel
            data = str(registro.get("criado_em") or "").replace("T", " ")[:19]
            self.tabela.insert(
                "",
                tk.END,
                iid=str(registro["id"]),
                values=(
                    data,
                    str(registro["categoria"]).replace("_", " ").title(),
                    registro["quantidade_arquivos"],
                    registro["total_registros"],
                    qualidade,
                    registro.get("nome_usuario") or "Usuário removido",
                ),
            )
        if registros:
            self.estado_vazio.place_forget()
        else:
            self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.estado_vazio.lift()
        self.status.configure(text=f"{len(registros)} análise(s) encontrada(s).")
        self._atualizar_estado_acoes()

    def _atualizar_estado_acoes(self, _evento=None):
        quantidade = len(self.tabela.selection())
        # Detalhes é uma ação de item único. Em seleção múltipla ele fica
        # visualmente apagado e não clicável; Excluir permanece disponível.
        self._definir_estado_botao(self.botao_detalhes, quantidade == 1)
        self._definir_estado_botao(self.botao_excluir, quantidade >= 1)
        if quantidade > 1:
            texto_status = (
                f"{quantidade} análises selecionadas · exclusão múltipla disponível."
            )
        elif quantidade == 1:
            texto_status = "1 análise selecionada."
        else:
            total = len(self.tabela.get_children())
            texto_status = f"{total} análise(s) encontrada(s)."
        self.status.configure(text=texto_status, fg=CORES["text_sec"])

    @staticmethod
    def _definir_estado_botao(botao, habilitado):
        cor_normal = getattr(botao, "_cor_normal", CORES["card_secundario"])
        botao.configure(
            state="normal" if habilitado else "disabled",
            bg=cor_normal if habilitado else CORES["input"],
            fg="#FFFFFF" if habilitado else CORES["text_disabled"],
            cursor="hand2" if habilitado else "arrow",
        )

    def _selecionar_todos(self, _evento=None):
        itens = self.tabela.get_children()
        if itens:
            self.tabela.selection_set(itens)
            self._atualizar_estado_acoes()
        return "break"

    def _abrir_detalhes_duplo_clique(self, _evento=None):
        if len(self.tabela.selection()) == 1:
            self.ver_detalhes()

    def _id_selecionado(self):
        selecao = self.tabela.selection()
        return int(selecao[0]) if selecao else None

    def _ids_selecionados(self):
        return tuple(int(item) for item in self.tabela.selection())

    def ver_detalhes(self):
        ids = self._ids_selecionados()
        if len(ids) != 1:
            self.status.configure(
                text="Selecione somente uma análise para visualizar os detalhes.",
                fg=CORES["warning"],
            )
            return
        historico_id = ids[0]
        registro = obter_analise(historico_id, SESSAO.usuario)
        janela = tk.Toplevel(self.root)
        janela.title(f"Detalhes da análise #{historico_id}")
        preparar_janela_secundaria(
            janela, self.root, 780, 580, minimo=(640, 460), modal=False
        )
        janela.configure(bg=CORES["bg"])
        texto = ScrolledText(
            janela,
            bg=CORES["input"],
            fg=CORES["text"],
            insertbackground=CORES["primary"],
            font=("Consolas", 10),
            relief="flat",
            padx=16,
            pady=16,
        )
        texto.pack(fill="both", expand=True, padx=20, pady=20)
        texto.insert("1.0", json.dumps(registro["resumo"], ensure_ascii=False, indent=2))
        texto.configure(state="disabled")

    def excluir(self):
        ids = self._ids_selecionados()
        if not ids:
            self.status.configure(text="Selecione ao menos uma análise.", fg=CORES["warning"])
            return
        confirmar = True
        if obter_preferencia("confirmar_exclusao_historico", True):
            quantidade = len(ids)
            descricao = (
                "esta análise"
                if quantidade == 1
                else f"as {quantidade} análises selecionadas"
            )
            confirmar = messagebox.askyesno(
                "Excluir histórico",
                f"Deseja mover {descricao} para a lixeira do histórico?",
                parent=self.root,
            )
        if not confirmar:
            return
        quantidade = excluir_analises(ids, SESSAO.usuario)
        self.carregar()
        self.status.configure(
            text=(
                "Registro excluído."
                if quantidade == 1
                else f"{quantidade} registros excluídos."
            ),
            fg=CORES["success"],
        )
