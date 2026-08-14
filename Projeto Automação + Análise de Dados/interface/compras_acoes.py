"""Workspace especializado e funcional de Compras e Suprimentos 2.0."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from interface.armazenamento_servidor import escolher_destino_gerado, mensagem_arquivo_gerado
from services.departamentos.compras import (
    ACOES_COMPRAS,
    adicionar_aditivo,
    adicionar_comentario,
    adicionar_contato_fornecedor,
    agendar_relatorio,
    analisar_compras,
    aprovar_pedido,
    atualizar_status_pedido,
    avaliar_fornecedor,
    atualizar_fornecedor,
    criar_categoria,
    criar_contrato,
    criar_cotacao,
    criar_fornecedor,
    criar_item_catalogo,
    criar_pedido,
    criar_solicitacao,
    decidir_solicitacao,
    enviar_pedido,
    enviar_solicitacao,
    gerar_alertas_compras,
    gerar_pdf_pedido,
    gerar_relatorio_compras,
    garantir_catalogos,
    homologar_fornecedor,
    integrar_recebimento_financeiro,
    listar_historico,
    listar_secao,
    obter_fornecedores_cotacao,
    obter_itens_pedido,
    obter_itens_solicitacao,
    registrar_negociacao,
    registrar_documento_fornecedor,
    registrar_divergencia_manual,
    registrar_proposta,
    registrar_recebimento,
    resolver_alerta,
    resolver_divergencia,
    resumo_compras,
    selecionar_fornecedor,
    salvar_regra_aprovacao,
    tem_permissao_compras,
)
from services.contexto import tem_permissao
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_campo_pesquisa,
    criar_estado_vazio,
    criar_metrica,
    criar_sidebar,
    criar_titulo_secao,
    preparar_janela_secundaria,
)
from interface.grade_editavel import EditorGrade
from interface.navegacao_modulos import criar_sidebar_modulo
from interface.tema import (
    CORES,
    FONTES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


COR_COMPRAS = "#F97316"

GRUPOS_MENU = (
    ("COMPRAS", (("visao", "⌂", "Visão geral"),)),
    ("DEMANDAS", (
        ("minhas_solicitacoes", "◉", "Minhas solicitações"),
        ("solicitacoes", "▣", "Todas as solicitações"),
        ("aprovacoes", "✓", "Aprovações"),
        ("catalogo", "▦", "Catálogo interno"),
    )),
    ("SOURCING", (
        ("cotacoes", "≡", "Cotações"),
        ("comparativo", "≠", "Mapa comparativo"),
        ("negociacoes", "⇄", "Negociações"),
    )),
    ("PEDIDOS", (
        ("pedidos", "▤", "Pedidos de compra"),
        ("entregas", "→", "Acompanhamento"),
    )),
    ("FORNECEDORES", (
        ("fornecedores", "◇", "Cadastro"),
        ("homologacao", "✔", "Homologação"),
        ("avaliacoes", "☆", "Avaliações"),
        ("documentos", "▧", "Documentos"),
    )),
    ("RECEBIMENTO", (
        ("recebimentos", "↓", "Recebimentos"),
        ("divergencias", "!", "Divergências"),
    )),
    ("CONTRATOS", (
        ("contratos", "▦", "Contratos"),
        ("aditivos", "+", "Aditivos"),
    )),
    ("GESTÃO", (
        ("alertas", "!", "Central de alertas"),
        ("relatorios", "▤", "Relatórios"),
        ("auditoria", "◉", "Auditoria"),
        ("configuracoes", "⚙", "Configurações"),
    )),
)

ROTULOS = {chave: titulo for _grupo, itens in GRUPOS_MENU for chave, _icone, titulo in itens}

SUBTITULOS = {
    "minhas_solicitacoes": "Crie, envie e acompanhe as demandas originadas por você.",
    "solicitacoes": "Necessidade, justificativa, itens, prazo, centro de custo e ciclo de aprovação.",
    "aprovacoes": "Fila humana de aprovação por valor, prioridade, departamento e alçada.",
    "catalogo": "Produtos e serviços padronizados de fornecedores homologados.",
    "cotacoes": "Convites, prazo de resposta, propostas e concorrência por solicitação.",
    "comparativo": "Preço, prazo, qualidade e custo-benefício; a escolha continua humana.",
    "negociacoes": "Rodadas, contrapropostas, saving, condições e responsáveis.",
    "pedidos": "Pedido de compra, aprovação, envio, confirmação e documento profissional.",
    "entregas": "Previsão, atraso, produção, transporte e recebimento parcial.",
    "fornecedores": "Cadastro central conectado a Estoque e Financeiro, contatos e categorias.",
    "homologacao": "Documentação, capacidade, restrições, bloqueio e conformidade.",
    "avaliacoes": "Preço, prazo, qualidade, atendimento, conformidade e score histórico.",
    "documentos": "Certidões, documentos fiscais, contratos, propostas e vencimentos.",
    "recebimentos": "Nota fiscal, conferência, aceite, recusa, lote, série, Estoque e Financeiro.",
    "divergencias": "Quantidade, preço, produto, documento, avaria e atraso com resolução auditada.",
    "contratos": "Objeto, fornecedor, vigência, valor, reajuste, renovação e alertas.",
    "aditivos": "Renovação e alterações sem apagar as condições anteriores.",
    "alertas": "Entregas atrasadas, divergências, documentos e contratos vencendo.",
    "auditoria": "Trilha imutável de quem fez, o que mudou, quando e em qual processo.",
}


def _moeda(centavos):
    if centavos is None:
        return "Acesso restrito"
    return "R$ " + f"{int(centavos or 0)/100:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _numero(valor):
    if valor is None:
        return "—"
    try:
        numero = float(valor)
        return f"{numero:,.3f}".rstrip("0").rstrip(".").replace(",", "_").replace(".", ",").replace("_", ".")
    except (TypeError, ValueError):
        return str(valor)


def _formatar(valor, campo=""):
    if valor in (None, ""):
        return "—"
    if "centavos" in campo:
        return _moeda(valor)
    if isinstance(valor, float):
        return _numero(valor)
    if campo in {"ativo", "selecionado", "possui_divergencia", "homologado", "renovacao_automatica"}:
        return "Sim" if valor else "Não"
    return str(valor)


class ComprasAcoesMixin:
    def _catalogos(self):
        return garantir_catalogos(SESSAO.usuario)


    def _opcoes(self, chave, rotulo="nome"):
        return [(x["id"], x.get(rotulo) or x.get("razao_social") or x.get("codigo") or str(x["id"])) for x in self._catalogos().get(chave, [])]


    def _formulario(self, titulo, campos, callback, *, largura=680, atualizar=True):
        janela = tk.Toplevel(self.root)
        janela.title(titulo)
        janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(janela, self.root, largura, min(850, 190 + len(campos) * 53), minimo=(540, 390))
        viewport = AreaRolavel(janela)
        viewport.pack(fill="both", expand=True, padx=22, pady=18)
        corpo = viewport.conteudo
        tk.Label(corpo, text=titulo, font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", pady=(0, 14))
        entradas = {}
        for chave, rotulo, tipo, opcoes in campos:
            linha = tk.Frame(corpo, bg=CORES["bg"])
            linha.pack(fill="x", pady=4)
            tk.Label(linha, text=rotulo.upper(), font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["bg"], width=27, anchor="w").pack(side="left")
            if tipo == "opcoes":
                valores = [opcao[1] if isinstance(opcao, tuple) else opcao for opcao in opcoes]
                campo = ttk.Combobox(linha, values=valores, state="readonly", style="Dark.TCombobox")
                if valores:
                    campo.current(0)
            elif tipo == "booleano":
                variavel = tk.BooleanVar(value=False)
                campo = tk.Checkbutton(linha, variable=variavel, bg=CORES["bg"], activebackground=CORES["bg"])
                campo._variavel = variavel
            else:
                campo = tk.Entry(linha, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat")
            campo.pack(side="left", fill="x", expand=True, ipady=6)
            entradas[chave] = (campo, opcoes)
        def salvar():
            valores = {}
            for chave, (campo, opcoes) in entradas.items():
                valor = campo._variavel.get() if hasattr(campo, "_variavel") else campo.get().strip()
                if opcoes and isinstance(opcoes[0], tuple):
                    valor = {rotulo: identificador for identificador, rotulo in opcoes}.get(valor, valor)
                valores[chave] = valor
            try:
                callback(valores)
                janela.destroy()
                if atualizar:
                    self.abrir_secao(self.secao)
            except (ValueError, PermissionError, FileNotFoundError, OSError) as erro:
                messagebox.showerror("Compras", str(erro), parent=janela)
        criar_botao(corpo, "SALVAR", salvar).pack(anchor="e", pady=(15, 8))
        return janela


    def _nova_acao(self):
        mapa = {
            "visao": self._nova_solicitacao,
            "minhas_solicitacoes": self._nova_solicitacao,
            "solicitacoes": self._nova_solicitacao,
            "cotacoes": self._nova_cotacao,
            "fornecedores": self._novo_fornecedor,
            "homologacao": self._novo_fornecedor,
            "catalogo": self._novo_item_catalogo,
            "documentos": self._novo_documento,
            "pedidos": self._novo_pedido,
            "entregas": self._novo_recebimento,
            "recebimentos": self._novo_recebimento,
            "contratos": self._novo_contrato,
        }
        acao = mapa.get(self.secao)
        if acao:
            acao()
        else:
            messagebox.showinfo("Compras", "Esta seção é alimentada pelas operações do ciclo de compras.", parent=self.root)


    def _nova_solicitacao(self):
        catalogos = self._catalogos()
        janela = tk.Toplevel(self.root)
        janela.title("Nova solicitação de compra")
        janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(janela, self.root, 960, 850, minimo=(760, 620))
        viewport = AreaRolavel(janela)
        viewport.pack(fill="both", expand=True, padx=22, pady=18)
        corpo = viewport.conteudo
        tk.Label(corpo, text="Nova solicitação de compra", font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w")
        tk.Label(corpo, text="Registre a necessidade e inclua todos os produtos ou serviços da mesma demanda.", font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["bg"]).pack(anchor="w", pady=(3, 14))

        metadados = criar_card(corpo)
        metadados.pack(fill="x")
        grade_meta = tk.Frame(metadados, bg=CORES["card"])
        grade_meta.pack(fill="x", padx=14, pady=12)
        grade_meta.grid_columnconfigure(1, weight=1)
        entradas = {}

        def campo_meta(linha, chave, rotulo, widget):
            tk.Label(grade_meta, text=rotulo.upper(), font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["card"], anchor="w").grid(row=linha, column=0, sticky="w", padx=(0, 12), pady=4)
            widget.grid(row=linha, column=1, sticky="ew", pady=4, ipady=5)
            entradas[chave] = widget

        campo_meta(0, "titulo", "Necessidade / título", tk.Entry(grade_meta, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat"))
        campo_meta(1, "justificativa", "Justificativa", tk.Entry(grade_meta, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat"))
        seletores = tk.Frame(grade_meta, bg=CORES["card"])
        seletores.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        for indice in range(5):
            seletores.grid_columnconfigure(indice, weight=1)
        mapas = {}
        definicoes = (
            ("tipo", "Tipo", ("Produto", "Serviço")),
            ("prioridade", "Prioridade", ("Baixa", "Normal", "Alta", "Urgente", "Crítica")),
            ("departamento_id", "Departamento", [("", "Não definido")] + [(x["id"], x["nome"]) for x in catalogos["departamentos"]]),
            ("centro_custo_id", "Centro de custo", [("", "Não definido")] + [(x["id"], f"{x['codigo']} · {x['nome']}") for x in catalogos["centros_custo"]]),
        )
        for coluna, (chave, rotulo, opcoes) in enumerate(definicoes):
            bloco = tk.Frame(seletores, bg=CORES["card"]); bloco.grid(row=0, column=coluna, sticky="ew", padx=3)
            tk.Label(bloco, text=rotulo.upper(), font=("Inter", 7, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w")
            nomes = [x[1] if isinstance(x, tuple) else x for x in opcoes]
            combo = ttk.Combobox(bloco, values=nomes, state="readonly", style="Dark.TCombobox")
            combo.pack(fill="x", ipady=4)
            if nomes: combo.current(0)
            entradas[chave] = combo
            mapas[chave] = {x[1]: x[0] for x in opcoes if isinstance(x, tuple)}
        bloco_prazo = tk.Frame(seletores, bg=CORES["card"]); bloco_prazo.grid(row=0, column=4, sticky="ew", padx=3)
        tk.Label(bloco_prazo, text="NECESSÁRIO EM", font=("Inter", 7, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w")
        entradas["necessario_em"] = tk.Entry(bloco_prazo, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat")
        entradas["necessario_em"].pack(fill="x", ipady=5)
        recorrencia = tk.Frame(grade_meta, bg=CORES["card"]); recorrencia.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        variavel_recorrente = tk.BooleanVar(value=False)
        tk.Checkbutton(recorrencia, text="Compra recorrente", variable=variavel_recorrente, bg=CORES["card"], fg=CORES["text"], selectcolor=CORES["input"], activebackground=CORES["card"], activeforeground=CORES["text"]).pack(side="left")
        entradas["recorrencia"] = tk.Entry(recorrencia, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat")
        entradas["recorrencia"].pack(side="left", fill="x", expand=True, padx=(12, 0), ipady=5)

        itens: list[dict] = []
        quadro_item = criar_card(corpo)
        quadro_item.pack(fill="x", pady=(12, 0))
        interior = tk.Frame(quadro_item, bg=CORES["card"]); interior.pack(fill="x", padx=14, pady=12)
        criar_titulo_secao(interior, "Itens da solicitação", "Adicione quantos produtos ou serviços forem necessários.")
        item_campos = {}
        linha_item = tk.Frame(interior, bg=CORES["card"]); linha_item.pack(fill="x", pady=(8, 5))
        for indice, (chave, rotulo, largura) in enumerate((("descricao", "Descrição", 22), ("especificacao", "Especificação", 24), ("quantidade", "Quantidade", 10), ("unidade", "Unidade", 8), ("valor_estimado_unitario", "Valor unitário", 12))):
            bloco = tk.Frame(linha_item, bg=CORES["card"]); bloco.pack(side="left", fill="x", expand=indice < 2, padx=2)
            tk.Label(bloco, text=rotulo.upper(), font=("Inter", 7, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w")
            entrada = tk.Entry(bloco, width=largura, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat")
            entrada.pack(fill="x", ipady=5); item_campos[chave] = entrada
        if not item_campos["unidade"].get(): item_campos["unidade"].insert(0, "UN")
        mapas["estoque_item_id"] = {"Não relacionado": "", **{f"{x['codigo']} · {x['nome']}": x["id"] for x in catalogos["itens_estoque"]}}
        combo_estoque = ttk.Combobox(interior, values=list(mapas["estoque_item_id"]), state="readonly", style="Dark.TCombobox")
        combo_estoque.pack(fill="x", pady=(4, 7), ipady=4)
        combo_estoque.current(0)
        tabela_itens = ttk.Treeview(interior, columns=("descricao", "quantidade", "unidade", "unitario", "estoque"), show="headings", height=6, style="Dark.Treeview")
        for chave, titulo, largura in (("descricao", "Item", 360), ("quantidade", "Qtd.", 75), ("unidade", "Un.", 65), ("unitario", "Estimado unitário", 125), ("estoque", "Estoque relacionado", 220)):
            tabela_itens.heading(chave, text=titulo); tabela_itens.column(chave, width=largura, minwidth=55, anchor="w")
        tabela_itens.pack(fill="x", pady=(4, 6))
        adicionar_divisorias_treeview(tabela_itens, cor=CORES["border"])

        def redesenhar_itens():
            for iid in tabela_itens.get_children(): tabela_itens.delete(iid)
            nomes_estoque = {valor: nome for nome, valor in mapas["estoque_item_id"].items()}
            for indice, item in enumerate(itens):
                tabela_itens.insert("", "end", iid=str(indice), values=(item["descricao"], item["quantidade"], item["unidade"], item["valor_estimado_unitario"], nomes_estoque.get(item.get("estoque_item_id"), "Não relacionado")))

        def adicionar_item():
            dados = {chave: entrada.get().strip() for chave, entrada in item_campos.items()}
            if not dados["descricao"] or not dados["quantidade"]:
                messagebox.showwarning("Solicitação", "Informe descrição e quantidade do item.", parent=janela)
                return
            dados["estoque_item_id"] = mapas["estoque_item_id"].get(combo_estoque.get(), "")
            itens.append(dados); redesenhar_itens()
            for chave, entrada in item_campos.items():
                entrada.delete(0, "end")
            item_campos["unidade"].insert(0, "UN")

        def remover_item():
            if not tabela_itens.selection(): return
            itens.pop(int(tabela_itens.selection()[0])); redesenhar_itens()

        botoes_item = tk.Frame(interior, bg=CORES["card"]); botoes_item.pack(fill="x")
        criar_botao(botoes_item, "+ ADICIONAR ITEM", adicionar_item, tipo="secundario", compacto=True).pack(side="left")
        criar_botao(botoes_item, "REMOVER ITEM", remover_item, tipo="fantasma", compacto=True).pack(side="left", padx=5)

        def salvar(enviar):
            if not itens:
                messagebox.showwarning("Solicitação", "Adicione ao menos um item.", parent=janela)
                return
            dados = {
                "titulo": entradas["titulo"].get().strip(),
                "justificativa": entradas["justificativa"].get().strip(),
                "tipo": entradas["tipo"].get(), "prioridade": entradas["prioridade"].get(),
                "necessario_em": entradas["necessario_em"].get().strip(),
                "departamento_id": mapas["departamento_id"].get(entradas["departamento_id"].get(), ""),
                "centro_custo_id": mapas["centro_custo_id"].get(entradas["centro_custo_id"].get(), ""),
                "recorrente": variavel_recorrente.get(), "recorrencia": entradas["recorrencia"].get().strip(),
            }
            try:
                criar_solicitacao(dados, itens, SESSAO.usuario, enviar=enviar)
                janela.destroy(); self.abrir_secao("minhas_solicitacoes")
            except (ValueError, PermissionError) as erro:
                messagebox.showerror("Solicitação", str(erro), parent=janela)

        rodape = tk.Frame(corpo, bg=CORES["bg"]); rodape.pack(fill="x", pady=(12, 8))
        criar_botao(rodape, "SALVAR E ENVIAR", lambda: salvar(True), tipo="sucesso").pack(side="right")
        criar_botao(rodape, "SALVAR RASCUNHO", lambda: salvar(False), tipo="secundario").pack(side="right", padx=7)


    def _enviar_solicitacao(self):
        registro = self._registro_selecionado()
        if not registro:
            return
        try:
            enviar_solicitacao(registro["id"], SESSAO.usuario)
            self.abrir_secao(self.secao)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Solicitação", str(erro), parent=self.root)


    def _decidir_solicitacao(self, decisao):
        registro = self._registro_selecionado()
        if not registro:
            return
        comentario = simpledialog.askstring("Decisão", "Comentário / justificativa:", parent=self.root) or "Decisão registrada na interface."
        try:
            decidir_solicitacao(registro["id"], decisao, comentario, SESSAO.usuario)
            self.abrir_secao("aprovacoes")
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Aprovação", str(erro), parent=self.root)


    def _nova_cotacao(self):
        solicitacoes = [x for x in listar_secao("solicitacoes", SESSAO.usuario) if x["status"] in {"Aprovada", "Em cotação"}]
        fornecedores = self._catalogos()["fornecedores"]
        if not solicitacoes or not fornecedores:
            messagebox.showwarning("Cotação", "Cadastre fornecedores e aprove uma solicitação antes de cotar.", parent=self.root)
            return
        janela = tk.Toplevel(self.root)
        janela.title("Criar cotação")
        janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(janela, self.root, 720, 680, minimo=(620, 520))
        corpo = tk.Frame(janela, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True, padx=22, pady=18)
        tk.Label(corpo, text="Criar cotação", font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w")
        opcoes_sol = {f"{x['numero']} · {x['titulo']}": x["id"] for x in solicitacoes}
        combo = ttk.Combobox(corpo, values=list(opcoes_sol), state="readonly", style="Dark.TCombobox")
        combo.pack(fill="x", pady=(14, 8), ipady=5)
        combo.current(0)
        tk.Label(corpo, text="FORNECEDORES · SELECIONE UM OU MAIS", font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["bg"]).pack(anchor="w", pady=(6, 4))
        lista = tk.Listbox(corpo, selectmode="multiple", bg=CORES["input"], fg=CORES["text"], selectbackground=CORES["primary"], relief="flat", height=12)
        lista.pack(fill="both", expand=True)
        for fornecedor in fornecedores:
            lista.insert("end", f"{fornecedor['razao_social']} · {fornecedor['status_homologacao']}")
        prazo = tk.Entry(corpo, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat")
        prazo.pack(fill="x", pady=(10, 5), ipady=6)
        prazo.insert(0, "Prazo de resposta DD/MM/AAAA")
        condicoes = tk.Entry(corpo, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat")
        condicoes.pack(fill="x", pady=5, ipady=6)
        condicoes.insert(0, "Condições desejadas")
        def salvar():
            selecionados = [fornecedores[i]["id"] for i in lista.curselection()]
            try:
                criar_cotacao(opcoes_sol[combo.get()], selecionados, {"resposta_ate": prazo.get(), "condicoes_desejadas": condicoes.get()}, SESSAO.usuario)
                janela.destroy()
                self.abrir_secao("cotacoes")
            except (ValueError, PermissionError) as erro:
                messagebox.showerror("Cotação", str(erro), parent=janela)
        criar_botao(corpo, "CRIAR COTAÇÃO", salvar).pack(anchor="e", pady=(12, 0))


    def _nova_proposta(self):
        cotacao = self._registro_selecionado()
        if not cotacao:
            return
        fornecedores = [x for x in obter_fornecedores_cotacao(cotacao["id"], SESSAO.usuario) if x["status"] in {"Convidado", "Respondida", "Em negociação"}]
        itens = obter_itens_solicitacao(cotacao["solicitacao_id"], SESSAO.usuario)
        if not fornecedores or not itens:
            messagebox.showwarning("Proposta", "A cotação não possui fornecedores ou itens.", parent=self.root)
            return
        janela = tk.Toplevel(self.root)
        janela.title("Registrar proposta")
        janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(janela, self.root, 820, 760, minimo=(680, 560))
        viewport = AreaRolavel(janela)
        viewport.pack(fill="both", expand=True, padx=22, pady=18)
        corpo = viewport.conteudo
        tk.Label(corpo, text=f"Proposta · {cotacao['numero']}", font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w")
        mapa_fornecedores = {x["razao_social"]: x["fornecedor_id"] for x in fornecedores}
        combo = ttk.Combobox(corpo, values=list(mapa_fornecedores), state="readonly", style="Dark.TCombobox")
        combo.pack(fill="x", pady=(12, 8), ipady=5)
        combo.current(0)
        entradas_itens = []
        for item in itens:
            linha = tk.Frame(corpo, bg=CORES["card"])
            linha.pack(fill="x", pady=3)
            tk.Label(linha, text=f"{item['descricao']} · {float(item['quantidade']):g} {item['unidade']}", font=FONTES["texto"], fg=CORES["text"], bg=CORES["card"], anchor="w").pack(side="left", fill="x", expand=True, padx=10, pady=8)
            entrada = tk.Entry(linha, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat", width=18)
            entrada.insert(0, "Valor unitário")
            entrada.pack(side="right", padx=8, ipady=5)
            entradas_itens.append((item, entrada))
        campos = {}
        for chave, rotulo in (("frete", "Frete"), ("impostos", "Impostos"), ("desconto", "Desconto"), ("prazo_entrega_dias", "Prazo de entrega/dias"), ("validade_proposta", "Validade"), ("forma_pagamento", "Forma de pagamento"), ("parcelamento", "Parcelamento"), ("garantia", "Garantia")):
            linha = tk.Frame(corpo, bg=CORES["bg"])
            linha.pack(fill="x", pady=3)
            tk.Label(linha, text=rotulo.upper(), font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["bg"], width=25, anchor="w").pack(side="left")
            entrada = tk.Entry(linha, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat")
            entrada.pack(side="left", fill="x", expand=True, ipady=5)
            campos[chave] = entrada
        def salvar():
            try:
                linhas = [{"solicitacao_item_id": item["id"], "quantidade": item["quantidade"], "valor_unitario": entrada.get()} for item, entrada in entradas_itens]
                registrar_proposta(cotacao["id"], mapa_fornecedores[combo.get()], {chave: entrada.get() for chave, entrada in campos.items()}, linhas, SESSAO.usuario)
                janela.destroy()
                self.abrir_secao("comparativo")
            except (ValueError, PermissionError) as erro:
                messagebox.showerror("Proposta", str(erro), parent=janela)
        criar_botao(corpo, "REGISTRAR PROPOSTA", salvar).pack(anchor="e", pady=(12, 8))


    def _nova_negociacao(self):
        registro = self._registro_selecionado()
        if not registro:
            return
        self._formulario("Registrar negociação", (
            ("valor_novo", "Novo valor total", "texto", ()),
            ("prazo_novo_dias", "Novo prazo em dias", "texto", ()),
            ("condicoes", "Condições negociadas", "texto", ()),
            ("observacao", "Observação", "texto", ()),
        ), lambda d: registrar_negociacao(registro["id"], d, SESSAO.usuario))


    def _selecionar_fornecedor(self):
        registro = self._registro_selecionado()
        if not registro:
            return
        motivo = simpledialog.askstring("Escolha do fornecedor", "Justificativa da escolha:", parent=self.root)
        if motivo is None:
            return
        try:
            selecionar_fornecedor(registro["cotacao_id"], registro["fornecedor_id"], motivo, SESSAO.usuario)
            self.abrir_secao("cotacoes")
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Fornecedor", str(erro), parent=self.root)


    def _novo_pedido(self):
        registro = self._registro_selecionado()
        cotacoes = [x for x in listar_secao("cotacoes", SESSAO.usuario) if x["status"] == "Encerrada"]
        cotacao_id = registro.get("id") if registro and self.secao == "cotacoes" else None
        if not cotacao_id:
            if not cotacoes:
                messagebox.showwarning("Pedido", "Finalize uma cotação antes de criar o pedido.", parent=self.root)
                return
            escolha = simpledialog.askstring("Pedido", "Informe o ID da cotação encerrada:\n" + "\n".join(f"{x['id']} · {x['numero']}" for x in cotacoes[:12]), parent=self.root)
            if not escolha:
                return
            cotacao_id = int(escolha)
        self._formulario("Gerar pedido de compra", (
            ("entrega_endereco", "Endereço de entrega", "texto", ()),
            ("entrega_contato", "Contato no recebimento", "texto", ()),
            ("previsao_entrega", "Previsão de entrega", "texto", ()),
            ("condicao_pagamento", "Condição de pagamento", "texto", ()),
            ("vencimento", "Vencimento", "texto", ()),
            ("parcelas", "Parcelas", "texto", ()),
        ), lambda d: criar_pedido(cotacao_id, d, SESSAO.usuario))


    def _aprovar_pedido(self, aprovar):
        registro = self._registro_selecionado()
        if not registro:
            return
        comentario = simpledialog.askstring("Pedido", "Comentário:", parent=self.root) or "Decisão registrada."
        try:
            aprovar_pedido(registro["id"], aprovar, comentario, SESSAO.usuario)
            self.abrir_secao(self.secao)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Pedido", str(erro), parent=self.root)


    def _enviar_pedido(self):
        registro = self._registro_selecionado()
        if not registro:
            return
        try:
            enviar_pedido(registro["id"], SESSAO.usuario)
            self.abrir_secao(self.secao)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Pedido", str(erro), parent=self.root)


    def _mudar_status_pedido(self):
        registro = self._registro_selecionado()
        if not registro:
            return
        status = simpledialog.askstring("Etapa do pedido", "Novo status:\nConfirmado pelo fornecedor\nEm produção\nEm transporte", parent=self.root)
        if not status:
            return
        try:
            atualizar_status_pedido(registro["id"], status, SESSAO.usuario)
            self.abrir_secao(self.secao)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Pedido", str(erro), parent=self.root)


    def _pdf_pedido(self):
        registro = self._registro_selecionado()
        if not registro:
            return
        nome = f"pedido_{int(registro['id'])}.pdf"
        destino, remoto = escolher_destino_gerado(
            parent=self.root, nome_sugerido=nome, titulo="Gerar pedido",
            defaultextension=".pdf", filetypes=(("PDF", "*.pdf"),),
        )
        if not destino:
            return
        try:
            resultado = gerar_pdf_pedido(registro["id"], destino, SESSAO.usuario)
            messagebox.showinfo("Pedido", mensagem_arquivo_gerado(resultado, remoto=remoto, nome=nome), parent=self.root)
        except (ValueError, PermissionError, OSError) as erro:
            messagebox.showerror("Pedido", str(erro), parent=self.root)


    def _novo_recebimento(self):
        registro = self._registro_selecionado()
        pedidos = [x for x in listar_secao("pedidos", SESSAO.usuario) if x["status"] in {"Enviado ao fornecedor", "Confirmado pelo fornecedor", "Em produção", "Em transporte", "Parcialmente recebido"}]
        pedido_id = registro.get("id") if registro and self.secao in {"pedidos", "entregas"} else None
        if not pedido_id:
            if not pedidos:
                messagebox.showwarning("Recebimento", "Nenhum pedido está disponível para recebimento.", parent=self.root)
                return
            escolha = simpledialog.askstring("Recebimento", "Informe o ID do pedido:\n" + "\n".join(f"{x['id']} · {x['numero']}" for x in pedidos[:12]), parent=self.root)
            if not escolha:
                return
            pedido_id = int(escolha)
        itens = obter_itens_pedido(pedido_id, SESSAO.usuario)
        catalogos = self._catalogos()
        janela = tk.Toplevel(self.root)
        janela.title("Registrar recebimento")
        janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(janela, self.root, 900, 780, minimo=(720, 560))
        viewport = AreaRolavel(janela)
        viewport.pack(fill="both", expand=True, padx=22, pady=18)
        corpo = viewport.conteudo
        tk.Label(corpo, text="Conferência do recebimento", font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w")
        campos = {}
        for chave, rotulo in (("nota_fiscal", "Nota fiscal"), ("chave_nfe", "Chave NF-e"), ("documento_valor", "Valor do documento"), ("recebido_em", "Data de recebimento"), ("observacao", "Observação")):
            linha = tk.Frame(corpo, bg=CORES["bg"]); linha.pack(fill="x", pady=3)
            tk.Label(linha, text=rotulo.upper(), font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["bg"], width=24, anchor="w").pack(side="left")
            entrada = tk.Entry(linha, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat")
            if chave == "recebido_em": entrada.insert(0, date.today().strftime("%d/%m/%Y"))
            entrada.pack(side="left", fill="x", expand=True, ipady=5); campos[chave] = entrada
        opcoes_deposito = {f"{x['codigo']} · {x['nome']}": x["id"] for x in catalogos["depositos"]}
        combo_deposito = ttk.Combobox(corpo, values=list(opcoes_deposito), state="readonly", style="Dark.TCombobox")
        combo_deposito.pack(fill="x", pady=8, ipady=5)
        if opcoes_deposito: combo_deposito.current(0)
        entradas_itens = []
        for item in itens:
            quadro = criar_card(corpo, fundo=CORES["card"]); quadro.pack(fill="x", pady=4)
            tk.Label(quadro, text=f"{item['descricao']} · pedido {float(item['quantidade']):g} · recebido {float(item['quantidade_recebida']):g}", font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card"]).pack(anchor="w", padx=10, pady=(8, 5))
            linha = tk.Frame(quadro, bg=CORES["card"]); linha.pack(fill="x", padx=10, pady=(0, 8))
            valores = {}
            for chave, rotulo in (("quantidade_recebida", "Recebido"), ("quantidade_aceita", "Aceito"), ("quantidade_recusada", "Recusado"), ("lote_numero", "Lote"), ("validade", "Validade"), ("motivo_recusa", "Motivo")):
                bloco = tk.Frame(linha, bg=CORES["card"]); bloco.pack(side="left", fill="x", expand=True, padx=2)
                tk.Label(bloco, text=rotulo.upper(), font=("Inter", 7, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w")
                entrada = tk.Entry(bloco, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_COMPRAS, relief="flat")
                entrada.pack(fill="x", ipady=4); valores[chave] = entrada
            entradas_itens.append((item, valores))
        def salvar():
            try:
                linhas = [{"pedido_item_id": item["id"], **{chave: entrada.get() for chave, entrada in valores.items()}} for item, valores in entradas_itens]
                registrar_recebimento(pedido_id, {**{chave: entrada.get() for chave, entrada in campos.items()}, "deposito_id": opcoes_deposito.get(combo_deposito.get())}, linhas, SESSAO.usuario)
                janela.destroy(); self.abrir_secao("recebimentos")
            except (ValueError, PermissionError) as erro:
                messagebox.showerror("Recebimento", str(erro), parent=janela)
        criar_botao(corpo, "CONFIRMAR RECEBIMENTO", salvar).pack(anchor="e", pady=(12, 8))


    def _integrar_financeiro(self):
        registro = self._registro_selecionado()
        if not registro:
            return
        self._formulario("Gerar conta a pagar", (("vencimento", "Vencimento", "texto", ()), ("parcelas", "Parcelas", "texto", ())), lambda d: integrar_recebimento_financeiro(registro["id"], d, SESSAO.usuario))


    def _resolver_divergencia(self):
        registro = self._registro_selecionado()
        if not registro:
            return
        resolucao = simpledialog.askstring("Divergência", "Descreva a resolução:", parent=self.root)
        if not resolucao:
            return
        try:
            resolver_divergencia(registro["id"], resolucao, SESSAO.usuario)
            self.abrir_secao("divergencias")
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Divergência", str(erro), parent=self.root)


    def _registrar_divergencia(self):
        recebimento = self._registro_selecionado()
        if not recebimento:
            return
        self._formulario("Registrar divergência", (
            ("tipo", "Tipo", "opcoes", ("Quantidade diferente", "Preço divergente", "Produto incorreto", "Produto danificado", "Documento divergente", "Atraso", "Outro")),
            ("severidade", "Severidade", "opcoes", ("Baixa", "Média", "Alta", "Crítica")),
            ("descricao", "Descrição da evidência", "texto", ()),
        ), lambda d: registrar_divergencia_manual(recebimento["id"], d, SESSAO.usuario))


    def _novo_fornecedor(self):
        self._formulario("Cadastrar fornecedor", (
            ("codigo", "Código interno", "texto", ()), ("razao_social", "Razão social", "texto", ()),
            ("nome_fantasia", "Nome fantasia", "texto", ()), ("cnpj_cpf", "CNPJ / CPF", "texto", ()),
            ("inscricao_estadual", "Inscrição estadual", "texto", ()), ("endereco", "Endereço", "texto", ()),
            ("cidade", "Cidade", "texto", ()), ("uf", "UF", "texto", ()),
            ("telefone", "Telefone", "texto", ()), ("email", "E-mail", "texto", ()),
            ("site", "Site", "texto", ()), ("categorias", "Categorias fornecidas", "texto", ()),
            ("dados_bancarios", "Dados bancários", "texto", ()), ("pix", "Chave PIX", "texto", ()),
        ), lambda d: criar_fornecedor(d, SESSAO.usuario), largura=760)


    def _novo_contato(self):
        fornecedor = self._registro_selecionado()
        if not fornecedor:
            return
        self._formulario("Novo contato do fornecedor", (("tipo", "Tipo", "opcoes", ("Comercial", "Financeiro", "Suporte", "Logística", "Executivo")), ("nome", "Nome", "texto", ()), ("cargo", "Cargo", "texto", ()), ("email", "E-mail", "texto", ()), ("telefone", "Telefone", "texto", ()), ("principal", "Contato principal", "booleano", ())), lambda d: adicionar_contato_fornecedor(fornecedor["id"], d, SESSAO.usuario))


    def _homologar(self, status):
        fornecedor = self._registro_selecionado()
        if not fornecedor:
            return
        restricoes = simpledialog.askstring("Homologação", "Restrições / justificativa:", parent=self.root) or ""
        try:
            homologar_fornecedor(fornecedor["id"], status, restricoes, SESSAO.usuario)
            self.abrir_secao("homologacao")
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Homologação", str(erro), parent=self.root)


    def _avaliar_fornecedor(self):
        fornecedor = self._registro_selecionado()
        if not fornecedor:
            return
        self._formulario("Avaliar fornecedor", (("preco", "Preço 0-10", "texto", ()), ("prazo", "Prazo 0-10", "texto", ()), ("qualidade", "Qualidade 0-10", "texto", ()), ("atendimento", "Atendimento 0-10", "texto", ()), ("conformidade", "Conformidade 0-10", "texto", ()), ("comentario", "Comentário", "texto", ())), lambda d: avaliar_fornecedor(fornecedor["id"], d, SESSAO.usuario))


    def _novo_documento(self):
        fornecedores = self._catalogos()["fornecedores"]
        if not fornecedores:
            messagebox.showwarning("Documentos", "Cadastre o fornecedor antes de anexar documentos.", parent=self.root)
            return
        arquivo = filedialog.askopenfilename(
            parent=self.root,
            title="Selecionar documento do fornecedor",
            filetypes=(("Documentos", "*.pdf *.doc *.docx *.xls *.xlsx *.csv *.txt *.png *.jpg *.jpeg"), ("Todos", "*.*")),
        )
        if not arquivo:
            return
        opcoes = [(x["id"], f"{x['codigo']} · {x['razao_social']}") for x in fornecedores]
        self._formulario("Classificar documento do fornecedor", (
            ("fornecedor_id", "Fornecedor", "opcoes", opcoes),
            ("titulo", "Título", "texto", ()),
            ("tipo", "Tipo", "opcoes", ("Certidão", "Documento fiscal", "Contrato", "Proposta", "Dados bancários", "Comprovante", "Outro")),
            ("numero", "Número", "texto", ()),
            ("emissao", "Emissão", "texto", ()),
            ("validade", "Validade", "texto", ()),
            ("classificacao", "Classificação", "opcoes", ("Público", "Interno", "Confidencial", "Restrito")),
            ("status", "Status", "opcoes", ("Válido", "Pendente", "Vencido")),
            ("observacao", "Observação", "texto", ()),
        ), lambda d: registrar_documento_fornecedor(d.pop("fornecedor_id"), d, arquivo, SESSAO.usuario), largura=760)


    def _verificar_documento(self):
        registro = self._registro_selecionado()
        if not registro:
            return
        from services.ferramentas import verificar_documento
        try:
            resultado = verificar_documento(registro["documento_id"], SESSAO.usuario)
            estado = "íntegro e disponível" if resultado["integro"] else "ausente ou alterado"
            messagebox.showinfo("Integridade documental", f"O arquivo está {estado}.\n\n{resultado.get('caminho') or 'Caminho indisponível'}", parent=self.root)
        except (ValueError, PermissionError, OSError) as erro:
            messagebox.showerror("Documentos", str(erro), parent=self.root)


    def _novo_item_catalogo(self):
        catalogos = self._catalogos()
        self._formulario("Item de catálogo interno", (("fornecedor_id", "Fornecedor homologado", "opcoes", [(x["id"], x["razao_social"]) for x in catalogos["fornecedores"]]), ("codigo", "Código", "texto", ()), ("descricao", "Descrição", "texto", ()), ("especificacao", "Especificação", "texto", ()), ("categoria_id", "Categoria", "opcoes", [("", "Não definida")] + [(x["id"], x["nome"]) for x in catalogos["categorias"]]), ("estoque_item_id", "Item de Estoque", "opcoes", [("", "Não relacionado")] + [(x["id"], f"{x['codigo']} · {x['nome']}") for x in catalogos["itens_estoque"]]), ("unidade", "Unidade", "texto", ()), ("preco", "Preço", "texto", ()), ("prazo_dias", "Prazo em dias", "texto", ()), ("validade_preco", "Validade do preço", "texto", ())), lambda d: criar_item_catalogo(d, SESSAO.usuario), largura=740)


    def _novo_contrato(self):
        catalogos = self._catalogos()
        self._formulario("Novo contrato de fornecedor", (("numero", "Número", "texto", ()), ("fornecedor_id", "Fornecedor", "opcoes", [(x["id"], x["razao_social"]) for x in catalogos["fornecedores"]]), ("objeto", "Objeto", "texto", ()), ("responsavel_id", "Responsável", "opcoes", [(x["id"], x["nome"]) for x in catalogos["usuarios"]]), ("departamento_id", "Departamento", "opcoes", [("", "Não definido")] + [(x["id"], x["nome"]) for x in catalogos["departamentos"]]), ("inicio", "Início", "texto", ()), ("termino", "Término", "texto", ()), ("valor", "Valor", "texto", ()), ("periodicidade", "Periodicidade", "texto", ()), ("indice_reajuste", "Índice de reajuste", "texto", ()), ("percentual_reajuste", "Percentual", "texto", ()), ("renovacao_automatica", "Renovação automática", "booleano", ()), ("prazo_cancelamento_dias", "Prazo de cancelamento", "texto", ())), lambda d: criar_contrato(d, SESSAO.usuario), largura=760)


    def _novo_aditivo(self):
        contrato = self._registro_selecionado()
        if not contrato:
            return
        self._formulario("Novo aditivo", (("numero", "Número", "texto", ()), ("tipo", "Tipo", "opcoes", ("Renovação", "Reajuste", "Escopo", "Prazo", "Valor")), ("descricao", "Descrição", "texto", ()), ("valor_novo", "Novo valor", "texto", ()), ("termino_novo", "Novo término", "texto", ())), lambda d: adicionar_aditivo(contrato["id"], d, SESSAO.usuario))


    def _resolver_alerta(self):
        registro = self._registro_selecionado()
        if not registro:
            return
        try:
            resolver_alerta(registro["id"], SESSAO.usuario)
            self.abrir_secao("alertas")
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Alerta", str(erro), parent=self.root)


    def _comentar(self, recurso_tipo):
        registro = self._registro_selecionado()
        if not registro:
            return
        comentario = simpledialog.askstring("Comentário interno", "Comentário:", parent=self.root)
        if not comentario:
            return
        try:
            adicionar_comentario(recurso_tipo, registro["id"], comentario, SESSAO.usuario)
            messagebox.showinfo("Compras", "Comentário registrado.", parent=self.root)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Compras", str(erro), parent=self.root)


    def _historico(self, recurso_tipo):
        registro = self._registro_selecionado()
        if not registro:
            return
        historico = listar_historico(recurso_tipo, registro["id"], SESSAO.usuario)
        texto = "\n\n".join(f"{x['criado_em']} · {x.get('usuario_nome') or 'Sistema'}\n{x['acao']}\n{x.get('observacao') or ''}" for x in historico) or "Nenhum evento registrado."
        messagebox.showinfo("Histórico do processo", texto, parent=self.root)


    def _mostrar_analise(self):
        try:
            analise = analisar_compras(SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Análise de Compras", str(erro), parent=self.root)
            return
        texto = "RESUMO INTELIGENTE\n\n" + "\n".join(f"• {item}" for item in analise["pontos_atencao"])
        if analise["concentracao"]:
            texto += "\n\nCONCENTRAÇÃO\n\n" + "\n".join(f"• {x['razao_social']}: {_moeda(x['valor_centavos'])}" for x in analise["concentracao"][:5])
        messagebox.showinfo("Inteligência de Compras", texto, parent=self.root)


    def _relatorios(self):
        self._cabecalho("Central de relatórios", "Relatórios operacionais, financeiros, de fornecedores, performance e auditoria.")
        card = criar_card(self.conteudo); card.pack(fill="x")
        interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=18, pady=18)
        criar_titulo_secao(interior, "Gerar agora", "PDF informa explicitamente quando precisar limitar grandes volumes; Excel e CSV preservam o universo completo.")
        for tipo in ("Solicitações", "Cotações", "Pedidos", "Fornecedores", "Recebimentos", "Divergências", "Contratos", "Auditoria"):
            linha = tk.Frame(interior, bg=CORES["card_secundario"]); linha.pack(fill="x", pady=3)
            tk.Label(linha, text=tipo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(side="left", padx=12, pady=10)
            for formato in ("PDF", "XLSX", "CSV"):
                criar_botao(linha, formato, lambda t=tipo, f=formato: self._gerar_relatorio(t, f), tipo="fantasma", compacto=True).pack(side="right", padx=3)
        criar_botao(interior, "AGENDAR ENVIO", self._agendar_relatorio, tipo="secundario", compacto=True).pack(anchor="e", pady=(12, 0))


    def _gerar_relatorio(self, tipo, formato):
        extensao = formato.lower()
        nome = f"compras_{tipo.lower().replace(' ', '_')}.{extensao}"
        destino, remoto = escolher_destino_gerado(
            parent=self.root, nome_sugerido=nome, titulo=f"Gerar {tipo}",
            defaultextension=f".{extensao}", filetypes=((formato, f"*.{extensao}"),),
        )
        if not destino:
            return
        try:
            resultado = gerar_relatorio_compras(tipo, formato, destino, SESSAO.usuario)
            messagebox.showinfo("Relatório", mensagem_arquivo_gerado(resultado, remoto=remoto, nome=nome), parent=self.root)
        except (ValueError, PermissionError, OSError) as erro:
            messagebox.showerror("Relatório", str(erro), parent=self.root)


    def _agendar_relatorio(self):
        self._formulario("Agendar relatório", (("nome", "Nome", "texto", ()), ("tipo", "Relatório", "opcoes", ("Solicitações", "Cotações", "Pedidos", "Fornecedores", "Contratos")), ("formato", "Formato", "opcoes", ("PDF", "XLSX", "CSV")), ("frequencia", "Frequência", "texto", ()), ("proxima_execucao", "Próxima execução", "texto", ()), ("destinatarios", "Destinatários", "texto", ())), lambda d: agendar_relatorio(d, SESSAO.usuario), atualizar=False)


    def _auditoria(self):
        self._cabecalho("Auditoria de Compras", "Histórico imutável de solicitações, propostas, negociações, pedidos e recebimentos.", acoes=False)
        self.secao = "auditoria"
        self._secao_operacional_sem_cabecalho()


    def _secao_operacional_sem_cabecalho(self):
        self.registros = listar_secao("auditoria", SESSAO.usuario)
        colunas = (("criado_em", "Data / hora", 155), ("usuario_nome", "Usuário", 160), ("acao", "Ação", 190), ("recurso_tipo", "Recurso", 190), ("recurso_id", "ID", 70), ("antes_json", "Antes", 300), ("depois_json", "Depois", 300), ("observacao", "Observação", 260))
        card = criar_card(self.conteudo); card.pack(fill="both", expand=True)
        area = tk.Frame(card, bg=CORES["input"]); area.pack(fill="both", expand=True, padx=1, pady=1)
        self.tabela = ttk.Treeview(area, columns=[x[0] for x in colunas], show="headings", height=24, style="Dark.Treeview")
        for chave, titulo, largura in colunas:
            self.tabela.heading(chave, text=titulo); self.tabela.column(chave, width=largura, minwidth=60, anchor="w")
        by = ttk.Scrollbar(area, orient="vertical", command=self.tabela.yview); bx = ttk.Scrollbar(area, orient="horizontal", command=self.tabela.xview)
        self.tabela.configure(yscrollcommand=by.set, xscrollcommand=bx.set); area.grid_rowconfigure(0, weight=1); area.grid_columnconfigure(0, weight=1)
        self.tabela.grid(row=0, column=0, sticky="nsew"); by.grid(row=0, column=1, sticky="ns"); bx.grid(row=1, column=0, sticky="ew")
        adicionar_divisorias_treeview(self.tabela, cor=CORES["border"]); self.estado_vazio = criar_estado_vazio(area, "◉", "Nenhum evento de auditoria", "As operações do módulo aparecerão aqui.", cor=COR_COMPRAS); self._preencher_tabela()


    def _configuracoes(self):
        self._cabecalho("Configurações de Compras", "Alçadas, categorias, perfis, integrações e parâmetros departamentais.", acoes=False)
        grade = GradeResponsiva(self.conteudo, max_colunas=2, largura_minima=360, gap=10, bg=CORES["bg"]); grade.pack(fill="x")
        for titulo, descricao, comando in (
            ("Alçadas de aprovação", "Faixas por valor, prioridade e departamento. Crie ou edite regras sem alterar decisões anteriores.", self._nova_regra),
            ("Categorias de compra", "Classificação hierárquica para solicitações, catálogo e relatórios.", self._nova_categoria),
            ("Permissões granulares", f"{len(ACOES_COMPRAS)} ações controláveis por perfil e usuário.", lambda: messagebox.showinfo("Compras", "Configure os perfis em Usuários e acessos.", parent=self.root)),
            ("Integrações", "Estoque, Patrimônio, Financeiro, Documentos, Aprovações, Notificações e Analytics.", lambda: messagebox.showinfo("Compras", "As integrações internas estão ativas. APIs externas exigem credenciais homologadas.", parent=self.root)),
        ):
            card = criar_card(grade); tk.Label(card, text=titulo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card"]).pack(anchor="w", padx=16, pady=(15, 6)); tk.Label(card, text=descricao, font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["card"], wraplength=420, justify="left").pack(anchor="w", padx=16); criar_botao(card, "ABRIR", comando, tipo="fantasma", compacto=True).pack(anchor="w", padx=16, pady=15); grade.adicionar(card)


    def _nova_categoria(self):
        self._formulario("Nova categoria de compra", (("codigo", "Código", "texto", ()), ("nome", "Nome", "texto", ()), ("descricao", "Descrição", "texto", ())), lambda d: criar_categoria(d, SESSAO.usuario), atualizar=False)


    def _mostrar_regras(self):
        regras = listar_secao("regras", SESSAO.usuario)
        texto = "\n".join(f"{x['nivel']}. {x['nome']}: {_moeda(x['valor_minimo_centavos'])} até {_moeda(x['valor_maximo_centavos']) if x['valor_maximo_centavos'] is not None else 'sem limite'}" for x in regras)
        messagebox.showinfo("Alçadas de Compras", texto or "Nenhuma regra cadastrada.", parent=self.root)


    def _nova_regra(self):
        catalogos = self._catalogos()
        regras = listar_secao("regras", SESSAO.usuario)
        identificadores = "\n".join(f"{x['id']} · {x['nome']}" for x in regras)
        if identificadores:
            messagebox.showinfo("Alçadas atuais", identificadores, parent=self.root)
        self._formulario("Configurar alçada de aprovação", (
            ("id", "ID para editar (vazio = nova)", "texto", ()),
            ("nome", "Nome da alçada", "texto", ()),
            ("valor_minimo", "Valor mínimo", "texto", ()),
            ("valor_maximo", "Valor máximo (vazio = ilimitado)", "texto", ()),
            ("prioridade", "Prioridade específica", "opcoes", ("", "Baixa", "Normal", "Alta", "Urgente", "Crítica")),
            ("departamento_id", "Departamento", "opcoes", [("", "Todos")] + [(x["id"], x["nome"]) for x in catalogos["departamentos"]]),
            ("nivel", "Nível", "texto", ()),
            ("exige_financeiro", "Exige Financeiro", "booleano", ()),
            ("exige_diretor", "Exige Diretoria", "booleano", ()),
        ), lambda d: salvar_regra_aprovacao(d, SESSAO.usuario), atualizar=False)

