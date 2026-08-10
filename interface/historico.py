"""Tela funcional de consulta do histórico de análises."""

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
from historico.repositorio import excluir_analise, listar_historico, obter_analise
from interface.componentes import criar_sidebar


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
        conteudo = tk.Frame(self.container, bg=CORES["bg"])
        conteudo.pack(side="left", fill="both", expand=True, padx=40, pady=32)

        cabecalho = tk.Frame(conteudo, bg=CORES["bg"])
        cabecalho.pack(fill="x")
        tk.Label(
            cabecalho,
            text="Histórico de análises",
            font=("Segoe UI", 24, "bold"),
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w")
        tk.Label(
            cabecalho,
            text="Consulte resultados anteriores sem armazenar as planilhas originais.",
            font=("Segoe UI", 10),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        ).pack(anchor="w", pady=(5, 22))

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
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.pack(side="left", fill="both", expand=True, padx=(16, 0), pady=16)
        barra.pack(side="right", fill="y", padx=(0, 16), pady=16)
        self.tabela.bind("<<TreeviewSelect>>", self._atualizar_estado_acoes)

        self.estado_vazio = tk.Frame(tabela_frame, bg=CORES["input"], padx=32, pady=20)
        tk.Label(
            self.estado_vazio,
            text="◇",
            font=("Segoe UI Symbol", 30),
            fg=CORES["primary"],
            bg=CORES["input"],
        ).pack()
        tk.Label(
            self.estado_vazio,
            text="Nenhuma análise registrada",
            font=("Segoe UI", 13, "bold"),
            fg=CORES["text"],
            bg=CORES["input"],
        ).pack(pady=(8, 4))
        tk.Label(
            self.estado_vazio,
            text=(
                "Quando o primeiro processamento for concluído, o resumo aparecerá aqui."
            ),
            font=("Segoe UI", 9),
            fg=CORES["text_sec"],
            bg=CORES["input"],
        ).pack()
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
            font=("Segoe UI", 9),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        )
        self.status.pack(side="right")

    def _botao(self, parent, texto, comando, secundario=False, perigo=False):
        fundo = CORES["danger"] if perigo else (
            CORES["card_secundario"] if secundario else CORES["primary"]
        )
        return tk.Button(
            parent,
            text=texto,
            command=comando,
            font=("Segoe UI", 9, "bold"),
            bg=fundo,
            fg="#FFFFFF",
            activebackground=CORES["card_hover"],
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=14,
            pady=8,
        )

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
            self.estado_vazio.place(relx=0.5, rely=0.54, anchor="center")
            self.estado_vazio.lift()
        self.status.configure(text=f"{len(registros)} análise(s) encontrada(s).")
        self._atualizar_estado_acoes()

    def _atualizar_estado_acoes(self, _evento=None):
        estado = "normal" if self.tabela.selection() else "disabled"
        self.botao_detalhes.configure(state=estado)
        self.botao_excluir.configure(state=estado)

    def _id_selecionado(self):
        selecao = self.tabela.selection()
        return int(selecao[0]) if selecao else None

    def ver_detalhes(self):
        historico_id = self._id_selecionado()
        if historico_id is None:
            self.status.configure(text="Selecione uma análise.", fg=CORES["warning"])
            return
        registro = obter_analise(historico_id, SESSAO.usuario)
        janela = tk.Toplevel(self.root)
        janela.title(f"Detalhes da análise #{historico_id}")
        janela.geometry("780x580")
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
        historico_id = self._id_selecionado()
        if historico_id is None:
            self.status.configure(text="Selecione uma análise.", fg=CORES["warning"])
            return
        confirmar = True
        if obter_preferencia("confirmar_exclusao_historico", True):
            confirmar = messagebox.askyesno(
                "Excluir histórico",
                "Deseja excluir somente este resumo de análise?",
                parent=self.root,
            )
        if not confirmar:
            return
        excluir_analise(historico_id, SESSAO.usuario)
        self.carregar()
        self.status.configure(text="Registro excluído.", fg=CORES["success"])
