"""Administração visual da topologia Servidor · Central · Agentes."""

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from enterprise.nos_plataforma import alterar_status_no, cadastrar_no, listar_nos
from interface.componentes import AreaRolavel, criar_botao, criar_cabecalho, criar_card, criar_sidebar
from interface.tema import CORES, LAYOUT, configurar_estilos_ttk


class TelaNosPlataforma:
    def __init__(self, root, navegacao):
        if not SESSAO.eh_admin():
            raise PermissionError("Somente administradores podem gerenciar a infraestrutura.")
        self.root, self.navegacao = root, navegacao
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self._criar(); self.carregar()

    def _criar(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar(self.container, self.navegacao, ativo="infraestrutura",
                      rodape_texto="←   Voltar às configurações",
                      rodape_comando=self.navegacao.get("configuracoes"))
        area = AreaRolavel(self.container)
        area.pack(side="left", fill="both", expand=True,
                  padx=LAYOUT["conteudo_padx"], pady=(28, 24))
        conteudo = area.conteudo
        criar_cabecalho(conteudo, "Infraestrutura distribuída",
                        "Cadastre o servidor central, computadores administrativos e agentes autorizados.",
                        breadcrumb="GESTÃO  /  INFRAESTRUTURA", etiqueta="OPERAÇÃO DISTRIBUÍDA")
        topo = criar_card(conteudo); topo.pack(fill="x", pady=(0, 14))
        tk.Label(topo, text="TOPOLOGIA AUTORIZADA", font=("Segoe UI", 9, "bold"),
                 fg=CORES["primary"], bg=CORES["card"]).pack(side="left", padx=18, pady=16)
        criar_botao(topo, "+ CADASTRAR NÓ", self.novo).pack(side="right", padx=14, pady=8)
        criar_botao(topo, "ATUALIZAR", self.carregar, tipo="secundario").pack(side="right", pady=8)
        card = criar_card(conteudo); card.pack(fill="both", expand=True)
        colunas = ("nome", "tipo", "identificador", "sistema", "ip", "status", "heartbeat")
        self.tabela = ttk.Treeview(card, columns=colunas, show="headings", style="Dark.Treeview", height=20)
        for coluna, titulo, largura in zip(
            colunas, ("Nome", "Tipo", "Identificador", "Sistema", "IP", "Status", "Último contato"),
            (180, 90, 210, 150, 110, 90, 150),
        ):
            self.tabela.heading(coluna, text=titulo)
            self.tabela.column(coluna, width=largura, minwidth=70, anchor="w")
        barra = ttk.Scrollbar(card, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        barra.pack(side="right", fill="y", padx=(0, 12), pady=14)
        self.tabela.pack(fill="both", expand=True, padx=(14, 0), pady=14)
        acoes = tk.Frame(conteudo, bg=CORES["bg"]); acoes.pack(fill="x", pady=(12, 0))
        criar_botao(acoes, "ATIVAR", lambda: self.alterar("Ativo"), tipo="secundario").pack(side="left")
        criar_botao(acoes, "BLOQUEAR", lambda: self.alterar("Bloqueado"), tipo="secundario").pack(side="left", padx=8)
        criar_botao(acoes, "REVOGAR", lambda: self.alterar("Revogado"), tipo="perigo").pack(side="left")
        self.status = tk.Label(acoes, text="", font=("Segoe UI", 9), fg=CORES["text_sec"], bg=CORES["bg"])
        self.status.pack(side="right")

    def carregar(self):
        self.tabela.delete(*self.tabela.get_children())
        try: registros = listar_nos(SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Infraestrutura", str(erro), parent=self.root); return
        for item in registros:
            self.tabela.insert("", "end", iid=str(item["id"]), values=(
                item["nome"], item["tipo"], item["identificador"], item.get("sistema") or "—",
                item.get("endereco_ip") or "—", item["status"], item.get("ultimo_heartbeat") or "Nunca",
            ))
        self.status.configure(text=f"{len(registros)} nó(s) cadastrado(s).")

    def novo(self):
        nome = simpledialog.askstring("Cadastrar nó", "Nome do computador ou servidor:", parent=self.root)
        if not nome: return
        tipo = simpledialog.askstring("Cadastrar nó", "Tipo: Servidor, Central ou Agente", initialvalue="Agente", parent=self.root)
        if not tipo: return
        sistema = simpledialog.askstring("Cadastrar nó", "Sistema operacional (opcional):", parent=self.root) or ""
        try: criado = cadastrar_no({"nome": nome, "tipo": tipo, "sistema": sistema}, SESSAO.usuario)
        except (PermissionError, ValueError, OSError) as erro:
            messagebox.showerror("Cadastrar nó", str(erro), parent=self.root); return
        self.carregar()
        messagebox.showinfo("Credencial criada — copie agora",
            f"Identificador:\n{criado['identificador']}\n\nSegredo do agente:\n{criado['token']}\n\n"
            "A credencial não será exibida novamente. Salve-a no arquivo .env do agente.", parent=self.root)

    def alterar(self, status):
        selecao = self.tabela.selection()
        if not selecao:
            messagebox.showwarning("Infraestrutura", "Selecione um nó.", parent=self.root); return
        if status == "Revogado" and not messagebox.askyesno(
            "Revogar nó", "A credencial deixará de ser aceita. Deseja continuar?", parent=self.root): return
        try: alterar_status_no(int(selecao[0]), status, SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Infraestrutura", str(erro), parent=self.root); return
        self.carregar()
