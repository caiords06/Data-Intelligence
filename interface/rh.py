"""Workspace especializado e funcional de Recursos Humanos."""

from __future__ import annotations

import json
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from auth.sessao import SESSAO
from enterprise.contexto import tem_permissao
from enterprise.rh import (
    ACOES_RH,
    adicionar_candidato,
    adicionar_dependente,
    adicionar_evento_folha,
    agendar_relatorio,
    analisar_rh,
    abrir_folha,
    atualizar_admissao,
    atualizar_colaborador,
    concluir_desligamento,
    criar_solicitacao,
    criar_vaga,
    decidir_ferias_ausencia,
    decidir_solicitacao,
    exportar_dataframe_rh,
    fechar_folha,
    gerar_contracheque,
    gerar_relatorio_rh,
    iniciar_admissao,
    iniciar_desligamento,
    inscrever_treinamento,
    listar_admissoes,
    listar_auditoria_rh,
    listar_catalogos,
    listar_colaboradores,
    listar_secao,
    obter_colaborador,
    registrar_documento,
    registrar_ponto,
    resumo_rh,
    salvar_avaliacao,
    salvar_beneficio,
    salvar_cargo,
    salvar_pdi,
    salvar_permissao_acao,
    salvar_treinamento,
    solicitar_ferias_ausencia,
    tem_permissao_rh,
    verificar_documento,
    vincular_equipamento,
    vincular_beneficio,
)
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_estado_vazio,
    criar_metrica,
    criar_sidebar,
    criar_titulo_secao,
    preparar_janela_secundaria,
)
from interface.grade_editavel import EditorGrade
from interface.tema import (
    CORES,
    FONTES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


COR_RH = "#9C7CFF"

GRUPOS_MENU = (
    ("RECURSOS HUMANOS", (("visao", "⌂", "Visão geral"),)),
    ("PESSOAS", (
        ("colaboradores", "◉", "Colaboradores"),
        ("admissoes", "+", "Admissões"),
        ("desligamentos", "−", "Desligamentos"),
        ("movimentacoes", "⇄", "Movimentações"),
    )),
    ("JORNADA", (
        ("ponto", "◷", "Ponto e jornada"),
        ("ferias", "◴", "Férias e ausências"),
    )),
    ("REMUNERAÇÃO", (
        ("beneficios", "◇", "Benefícios"),
        ("folha", "$", "Folha e custos"),
        ("cargos", "#", "Cargos e salários"),
    )),
    ("TALENTOS", (
        ("recrutamento", "◎", "Recrutamento"),
        ("desempenho", "★", "Desempenho"),
        ("treinamentos", "△", "Treinamentos"),
        ("carreira", "↗", "Carreira e PDI"),
    )),
    ("GESTÃO", (
        ("documentos", "▤", "Documentos"),
        ("solicitacoes", "✓", "Solicitações"),
        ("relatorios", "⇥", "Relatórios"),
        ("auditoria", "◎", "Auditoria RH"),
        ("configuracoes", "⚙", "Configurações RH"),
    )),
)

ROTULOS = {chave: titulo for _grupo, itens in GRUPOS_MENU for chave, _icone, titulo in itens}

SUBTITULOS = {
    "colaboradores": "Cadastro mestre, vínculos, histórico, benefícios, documentos e dados profissionais.",
    "admissoes": "Wizard de admissão, checklist documental, integrações e onboarding.",
    "desligamentos": "Rescisão segura, revogação de acessos, devoluções e encerramento.",
    "movimentacoes": "Promoções, mudanças de cargo, salário, departamento e demais alterações.",
    "ponto": "Registros de jornada, horas trabalhadas, extras, atrasos e ajustes.",
    "ferias": "Saldos, períodos aquisitivos, conflitos, aprovações, férias e afastamentos.",
    "beneficios": "Catálogo, elegibilidade, custos e vínculos por colaborador.",
    "folha": "Competências, eventos, proventos, descontos, encargos e contracheques.",
    "cargos": "Estrutura de cargos, níveis, responsabilidades e faixas salariais.",
    "recrutamento": "Vagas, aprovação de abertura, candidatos e funil seletivo.",
    "desempenho": "Ciclos de avaliação, competências, feedbacks e resultados.",
    "treinamentos": "Catálogo, inscrições, obrigatoriedade, certificados e validade.",
    "carreira": "Planos de desenvolvimento, ações, prazos e progresso de carreira.",
    "documentos": "GED de RH com versão, validade, assinatura, hash e acesso restrito.",
    "solicitacoes": "Portal interno para solicitações, aprovações, respostas e acompanhamento.",
}


def _moeda(centavos):
    if centavos is None:
        return "Acesso restrito"
    valor = int(centavos or 0) / 100
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _formatar(valor, campo=""):
    if valor is None:
        return "—"
    if "centavos" in campo:
        return _moeda(valor)
    if campo in {"obrigatorio", "ativo"}:
        return "Sim" if valor else "Não"
    return str(valor)


class TelaRH:
    def __init__(self, root, navegacao, secao="visao"):
        self.root = root
        self.navegacao = navegacao
        self.secao = secao if secao in ROTULOS else "visao"
        self.tabela = None
        self.registros = []
        if not tem_permissao(SESSAO.usuario, "rh", "ler"):
            raise PermissionError("Seu perfil não possui acesso aos Recursos Humanos.")
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self._criar_interface()

    def _criar_interface(self):
        configurar_estilos_ttk(self.root)
        grupos = []
        for grupo, itens in GRUPOS_MENU:
            grupos.append((grupo, tuple(
                (chave, icone, titulo, lambda destino=chave: self.abrir_secao(destino))
                for chave, icone, titulo in itens
            )))
        grupos.append(("COLABORAÇÃO", (("correio", "✉", "Correio interno", lambda: self.navegacao["correio"]("rh")),)))
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo=self.secao,
            grupos_customizados=tuple(grupos),
            titulo_customizado="RECURSOS HUMANOS",
            rodape_texto="Voltar aos módulos",
            rodape_comando=self.navegacao.get("modulos"),
            grupos_recolhiveis=True,
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(side="left", fill="both", expand=True, padx=LAYOUT["conteudo_padx"], pady=(22, 20))
        self.conteudo = viewport.conteudo
        renderizadores = {
            "visao": self._visao,
            "relatorios": self._relatorios,
            "auditoria": self._auditoria,
            "configuracoes": self._configuracoes,
        }
        renderizadores.get(self.secao, self._secao_operacional)()

    def abrir_secao(self, secao):
        self.container.destroy()
        TelaRH(self.root, self.navegacao, secao=secao)

    def _acoes_cabecalho(self, parent):
        bloco = tk.Frame(parent, bg=CORES["bg"])
        botao = criar_botao(bloco, "+  NOVA OPERAÇÃO", self._nova_operacao, compacto=True)
        botao.pack(side="right")
        if not tem_permissao_rh(SESSAO.usuario, "criar_colaborador"):
            botao.configure(state="disabled", cursor="arrow")
        criar_botao(bloco, "◈  ANALISAR RH", self._mostrar_analise, tipo="secundario", compacto=True).pack(side="right", padx=(0, 8))
        return bloco

    def _cabecalho(self, titulo, subtitulo, *, acoes=True):
        criar_cabecalho(
            self.conteudo,
            titulo,
            subtitulo,
            acao=self._acoes_cabecalho if acoes else None,
            breadcrumb=f"MÓDULOS  /  RECURSOS HUMANOS  /  {titulo.upper()}",
            etiqueta="RH 2.0",
        )

    def _visao(self):
        self._cabecalho(
            "Gestão de pessoas",
            "Central de comando do ciclo completo do colaborador, da admissão ao desenvolvimento e desligamento.",
        )
        resumo = resumo_rh(SESSAO.usuario)
        grade = GradeResponsiva(self.conteudo, max_colunas=4, largura_minima=220, gap=9, bg=CORES["bg"])
        grade.pack(fill="x")
        metricas = (
            ("HEADCOUNT", resumo["total"], "◉", "Pessoas no contexto atual"),
            ("COLABORADORES ATIVOS", resumo["ativos"], "✓", "Vínculos ativos"),
            ("DEPARTAMENTOS", resumo["departamentos"], "▦", "Estrutura com pessoas alocadas"),
            ("FOLHA BASE", _moeda(resumo["folha_base"]), "$", "Salários base ativos"),
            ("PRÉ-ADMISSÕES", resumo["pre_admissoes"], "+", "Processos em preparação"),
            ("DESLIGAMENTOS", resumo["desligamentos"], "−", "Processos em andamento"),
            ("FÉRIAS PENDENTES", resumo["ferias_pendentes"], "◴", "Aguardando decisão"),
            ("TAREFAS PENDENTES", resumo["tarefas_pendentes"], "✓", "Operações do departamento"),
        )
        for titulo, valor, icone, detalhe in metricas:
            grade.adicionar(criar_metrica(grade, titulo, valor, icone=icone, cor=COR_RH, detalhe=detalhe))
        self._atalhos()
        self._jornada(resumo)
        self._pendencias(resumo)

    def _atalhos(self):
        card = criar_card(self.conteudo)
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=17, pady=15)
        criar_titulo_secao(interior, "Acesso rápido", "Operações recorrentes do departamento.")
        grade = GradeResponsiva(interior, max_colunas=5, largura_minima=180, gap=8, bg=CORES["card"])
        grade.pack(fill="x")
        for icone, titulo, detalhe, comando in (
            ("+", "Nova admissão", "Cadastro, documentos e onboarding.", self._nova_admissao),
            ("◴", "Planejar férias", "Saldo, conflitos e aprovação.", self._novas_ferias),
            ("◷", "Registrar jornada", "Ponto, horas extras e atrasos.", self._novo_ponto),
            ("$", "Abrir folha", "Competência e salários base.", self._nova_folha),
            ("⇥", "Gerar relatório", "PDF, Excel ou CSV.", lambda: self.abrir_secao("relatorios")),
        ):
            quadro = criar_card(grade, fundo=CORES["card_secundario"])
            tk.Label(quadro, text=icone, font=("Segoe UI Symbol", 18, "bold"), fg=COR_RH, bg=CORES["card_secundario"]).pack(anchor="w", padx=14, pady=(13, 5))
            tk.Label(quadro, text=titulo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(anchor="w", padx=14)
            tk.Label(quadro, text=detalhe, font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card_secundario"], wraplength=180, justify="left").pack(anchor="w", padx=14, pady=(5, 10))
            criar_botao(quadro, "ABRIR  →", comando, tipo="fantasma", compacto=True).pack(anchor="w", padx=14, pady=(0, 13))
            grade.adicionar(quadro)

    def _jornada(self, resumo):
        card = criar_card(self.conteudo)
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=17, pady=15)
        criar_titulo_secao(interior, "Jornada do colaborador", "Visão integrada das etapas de pessoas.")
        valores = {x["etapa"]: x["total"] for x in resumo["jornada"]}
        grade = GradeResponsiva(interior, max_colunas=6, largura_minima=145, gap=5, bg=CORES["card"]); grade.pack(fill="x")
        for etapa in ("Pré-admissão", "Documentação", "Onboarding", "Ativo", "Desligamento", "Desligado"):
            quadro = criar_card(grade, fundo=CORES["input"])
            tk.Frame(quadro, bg=COR_RH, height=3).pack(fill="x")
            tk.Label(quadro, text=etapa.upper(), font=("Segoe UI", 8, "bold"), fg=CORES["text_sec"], bg=CORES["input"]).pack(pady=(14, 8))
            tk.Label(quadro, text=str(valores.get(etapa, 0)), font=FONTES["display"], fg=CORES["text"], bg=CORES["input"]).pack(pady=(0, 14))
            grade.adicionar(quadro)

    def _pendencias(self, resumo):
        card = criar_card(self.conteudo, destaque=bool(resumo["documentos_vencendo"] or resumo["ferias_pendentes"]))
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=17, pady=15)
        criar_titulo_secao(interior, "Pontos de atenção", "Pendências que exigem acompanhamento humano.")
        itens = (
            (f"{resumo['ferias_pendentes']} solicitação(ões) de férias/ausência pendente(s)", "ferias"),
            (f"{resumo['documentos_vencendo']} documento(s) vencendo nos próximos 30 dias", "documentos"),
            (f"{resumo['tarefas_pendentes']} tarefa(s) operacional(is) de RH em aberto", "admissoes"),
        )
        for texto, destino in itens:
            linha = tk.Frame(interior, bg=CORES["card_secundario"]); linha.pack(fill="x", pady=3)
            tk.Label(linha, text="○  " + texto, font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["card_secundario"]).pack(side="left", padx=12, pady=9)
            criar_botao(linha, "VER", lambda d=destino: self.abrir_secao(d), tipo="fantasma", compacto=True).pack(side="right", padx=8)

    def _secao_operacional(self):
        titulo = ROTULOS[self.secao]
        self._cabecalho(titulo, SUBTITULOS.get(self.secao, "Operação especializada de Recursos Humanos."))
        topo = criar_card(self.conteudo); topo.pack(fill="x", pady=(0, 12))
        filtros = tk.Frame(topo, bg=CORES["card"]); filtros.pack(fill="x", padx=15, pady=12)
        tk.Label(filtros, text="PESQUISAR", font=("Segoe UI", 8, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(side="left")
        self.pesquisa = tk.Entry(filtros, bg=CORES["input"], fg=CORES["text"], insertbackground=CORES["primary"], relief="flat", width=28)
        self.pesquisa.pack(side="left", padx=(8, 8), ipady=6)
        criar_botao(filtros, "APLICAR", self._filtrar_tabela, tipo="secundario", compacto=True).pack(side="left")
        criar_botao(filtros, "+  NOVO", self._nova_operacao, compacto=True).pack(side="right")
        self._carregar_tabela()
        self._barra_acoes()

    def _carregar_tabela(self):
        try:
            self.registros = listar_secao(self.secao, SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Recursos Humanos", str(erro), parent=self.root); self.registros = []
        painel = criar_card(self.conteudo); painel.pack(fill="both", expand=True)
        area = tk.Frame(painel, bg=CORES["input"], height=430); area.pack(fill="both", expand=True, padx=1, pady=1); area.pack_propagate(False)
        colunas = tuple(self.registros[0].keys()) if self.registros else self._colunas_padrao()
        self.tabela = ttk.Treeview(area, columns=colunas, show="headings", style="Dark.Treeview")
        for coluna in colunas:
            titulo = coluna.replace("_centavos", "").replace("_", " ").upper()
            self.tabela.heading(coluna, text=titulo)
            largura = 105
            if coluna in {"nome_completo", "titulo", "motivo", "feedback", "vinculo"}: largura = 200
            self.tabela.column(coluna, width=largura, minwidth=70, stretch=True, anchor="w")
        barra = ttk.Scrollbar(area, orient="vertical", command=self.tabela.yview, style="Dark.Vertical.TScrollbar")
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.pack(side="left", fill="both", expand=True); barra.pack(side="right", fill="y")
        for registro in self.registros:
            self.tabela.insert("", "end", iid=str(registro.get("id")), values=tuple(_formatar(registro.get(c), c) for c in colunas))
        vazio = None
        if not self.registros:
            vazio = criar_estado_vazio(area, "◇", f"Nenhum registro em {ROTULOS[self.secao]}", "Use Nova operação para iniciar este processo.", cor=COR_RH)
            vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
        adicionar_divisorias_treeview(self.tabela, sobreposicao=vazio)
        if self.secao == "colaboradores" and self.registros:
            self.editor_grade = EditorGrade(
                self.tabela, colunas_editaveis={"nome_completo", "cargo_texto", "status"},
                salvar=self._salvar_edicao_colaborador, parent=self.root, titulo="Colaboradores",
            )
            barra_grade = tk.Frame(painel, bg=CORES["card"]); barra_grade.pack(fill="x", padx=12, pady=(5,8))
            tk.Label(barra_grade, text="Duplo clique em nome, cargo ou status para editar diretamente.", bg=CORES["card"], fg=CORES["text_muted"], font=FONTES["micro"]).pack(side="left")
            criar_botao(barra_grade, "XLSX", lambda: self.editor_grade.exportar_xlsx(), tipo="fantasma", compacto=True).pack(side="right", padx=(5,0))
            criar_botao(barra_grade, "CSV", lambda: self.editor_grade.exportar_csv(), tipo="fantasma", compacto=True).pack(side="right")

    def _salvar_edicao_colaborador(self, iid, coluna, valor):
        atualizar_colaborador(int(iid), {coluna: valor}, SESSAO.usuario)

    def _colunas_padrao(self):
        mapas = {
            "colaboradores": ("id", "matricula", "nome_completo", "cargo_texto", "status", "etapa_jornada"),
            "admissoes": ("id", "nome_completo", "cargo_texto", "etapa_atual", "status", "previsao_conclusao"),
            "desligamentos": ("id", "nome_completo", "tipo", "data_prevista", "status", "motivo"),
            "movimentacoes": ("id", "nome_completo", "tipo", "vigencia", "observacao", "criado_em"),
            "ponto": ("id", "nome_completo", "data", "entrada", "saida", "minutos_trabalhados", "status"),
            "ferias": ("id", "nome_completo", "tipo", "inicio", "fim", "dias", "status"),
            "beneficios": ("id", "nome_completo", "beneficio", "tipo", "inicio", "status"),
            "folha": ("id", "competencia", "status", "total_proventos_centavos", "total_descontos_centavos", "total_liquido_centavos"),
            "cargos": ("id", "codigo", "titulo", "nivel", "salario_minimo_centavos", "salario_referencia_centavos", "salario_maximo_centavos"),
            "recrutamento": ("id", "titulo", "quantidade", "status", "motivo", "candidatos"),
            "desempenho": ("id", "nome_completo", "ciclo", "tipo", "nota", "status"),
            "treinamentos": ("id", "titulo", "tipo", "carga_horaria", "obrigatorio", "inscritos"),
            "carreira": ("id", "nome_completo", "titulo", "inicio", "prazo", "progresso", "status"),
            "documentos": ("id", "vinculo", "categoria", "titulo", "versao", "classificacao", "validade", "status"),
            "solicitacoes": ("id", "nome_completo", "tipo", "titulo", "status", "criado_em"),
        }
        return mapas.get(self.secao, ("id", "descricao", "status", "atualizado_em"))

    def _filtrar_tabela(self):
        termo = self.pesquisa.get().strip().lower()
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for registro in self.registros:
            if termo and termo not in " ".join(str(v).lower() for v in registro.values()): continue
            colunas = self.tabela["columns"]
            self.tabela.insert("", "end", iid=str(registro.get("id")), values=tuple(_formatar(registro.get(c), c) for c in colunas))

    def _barra_acoes(self):
        linha = tk.Frame(self.conteudo, bg=CORES["bg"]); linha.pack(fill="x", pady=(10, 0))
        if self.secao == "colaboradores":
            criar_botao(linha, "VER PERFIL", self._ver_colaborador, tipo="secundario", compacto=True).pack(side="left")
            criar_botao(linha, "EDITAR", self._editar_colaborador, tipo="fantasma", compacto=True).pack(side="left", padx=5)
            criar_botao(linha, "DEPENDENTE", self._novo_dependente, tipo="fantasma", compacto=True).pack(side="left")
            criar_botao(linha, "EQUIPAMENTO", self._novo_equipamento, tipo="fantasma", compacto=True).pack(side="left", padx=5)
        if self.secao == "admissoes": criar_botao(linha, "AVANÇAR ETAPA", self._avancar_admissao, tipo="secundario", compacto=True).pack(side="left")
        if self.secao == "desligamentos": criar_botao(linha, "CONCLUIR DESLIGAMENTO", self._concluir_desligamento, tipo="perigo", compacto=True).pack(side="left")
        if self.secao == "ferias":
            criar_botao(linha, "APROVAR", lambda: self._decidir_ferias(True), tipo="sucesso", compacto=True).pack(side="left")
            criar_botao(linha, "REJEITAR", lambda: self._decidir_ferias(False), tipo="perigo", compacto=True).pack(side="left", padx=6)
        if self.secao == "folha":
            criar_botao(linha, "FECHAR FOLHA", self._fechar_folha, tipo="aviso", compacto=True).pack(side="left")
            criar_botao(linha, "ADICIONAR EVENTO", self._novo_evento_folha, tipo="fantasma", compacto=True).pack(side="left", padx=6)
            criar_botao(linha, "CONTRACHEQUE", self._contracheque, tipo="secundario", compacto=True).pack(side="left", padx=6)
        if self.secao == "beneficios": criar_botao(linha, "NOVO BENEFÍCIO", self._novo_beneficio, tipo="secundario", compacto=True).pack(side="left")
        if self.secao == "recrutamento": criar_botao(linha, "ADICIONAR CANDIDATO", self._novo_candidato, tipo="secundario", compacto=True).pack(side="left")
        if self.secao == "treinamentos": criar_botao(linha, "INSCREVER COLABORADOR", self._inscrever_treinamento, tipo="secundario", compacto=True).pack(side="left")
        if self.secao == "documentos": criar_botao(linha, "VERIFICAR INTEGRIDADE", self._verificar_documento, tipo="secundario", compacto=True).pack(side="left")
        if self.secao == "solicitacoes":
            criar_botao(linha, "APROVAR", lambda: self._decidir_solicitacao(True), tipo="sucesso", compacto=True).pack(side="left")
            criar_botao(linha, "REJEITAR", lambda: self._decidir_solicitacao(False), tipo="perigo", compacto=True).pack(side="left", padx=6)
        criar_botao(linha, "ATUALIZAR", lambda: self.abrir_secao(self.secao), tipo="fantasma", compacto=True).pack(side="right")

    def _selecionado(self):
        if self.tabela is None or not self.tabela.selection():
            messagebox.showwarning("Recursos Humanos", "Selecione um registro.", parent=self.root); return None
        return int(self.tabela.selection()[0])

    def _nova_operacao(self):
        acoes = {
            "visao": self._nova_admissao, "colaboradores": self._novo_colaborador,
            "admissoes": self._nova_admissao, "desligamentos": self._novo_desligamento,
            "ponto": self._novo_ponto, "ferias": self._novas_ferias,
            "beneficios": self._vincular_beneficio, "folha": self._nova_folha,
            "cargos": self._novo_cargo, "recrutamento": self._nova_vaga,
            "desempenho": self._nova_avaliacao, "treinamentos": self._novo_treinamento,
            "carreira": self._novo_pdi, "documentos": self._novo_documento,
            "solicitacoes": self._nova_solicitacao,
        }
        acao = acoes.get(self.secao)
        if acao: acao()
        else: messagebox.showinfo("Recursos Humanos", "Esta seção é alimentada automaticamente pelas demais operações.", parent=self.root)

    def _formulario(self, titulo, campos, callback, *, largura=570):
        janela = tk.Toplevel(self.root); janela.title(titulo); janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(janela, self.root, largura, min(760, 190 + len(campos) * 52), minimo=(500, 360))
        corpo = tk.Frame(janela, bg=CORES["bg"]); corpo.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(corpo, text=titulo, font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", pady=(0, 14))
        entradas = {}
        for chave, rotulo, tipo, opcoes in campos:
            linha = tk.Frame(corpo, bg=CORES["bg"]); linha.pack(fill="x", pady=4)
            tk.Label(linha, text=rotulo.upper(), font=("Segoe UI", 8, "bold"), fg=CORES["text_sec"], bg=CORES["bg"], width=24, anchor="w").pack(side="left")
            if tipo == "opcoes":
                campo = ttk.Combobox(linha, values=[v[1] if isinstance(v, tuple) else v for v in opcoes], state="readonly", style="Dark.TCombobox")
                if opcoes: campo.current(0)
            elif tipo == "booleano":
                variavel = tk.BooleanVar(value=False); campo = tk.Checkbutton(linha, variable=variavel, bg=CORES["bg"], activebackground=CORES["bg"]); campo._variavel = variavel
            else:
                campo = tk.Entry(linha, bg=CORES["input"], fg=CORES["text"], insertbackground=CORES["primary"], relief="flat")
            campo.pack(side="left", fill="x", expand=True, ipady=6)
            entradas[chave] = (campo, opcoes)
        def salvar():
            dados = {}
            for chave, (campo, opcoes) in entradas.items():
                if hasattr(campo, "_variavel"): valor = campo._variavel.get()
                else: valor = campo.get().strip()
                if opcoes and isinstance(opcoes[0], tuple):
                    mapa = {rotulo: valor_id for valor_id, rotulo in opcoes}; valor = mapa.get(valor, valor)
                dados[chave] = valor
            try:
                callback(dados); janela.destroy(); self.abrir_secao(self.secao)
            except (ValueError, PermissionError, FileNotFoundError) as erro:
                messagebox.showerror("Recursos Humanos", str(erro), parent=janela)
        criar_botao(corpo, "SALVAR", salvar).pack(anchor="e", pady=(15, 0))
        return janela

    def _opcoes(self, chave, rotulo="nome"):
        catalogos = listar_catalogos(SESSAO.usuario)
        return [(x["id"], x.get(rotulo) or x.get("nome_completo") or str(x["id"])) for x in catalogos.get(chave, [])]

    def _campos_colaborador(self):
        return (
            ("nome_completo", "Nome completo", "texto", ()), ("nome_social", "Nome social", "texto", ()),
            ("matricula", "Matrícula (opcional)", "texto", ()), ("cpf", "CPF", "texto", ()),
            ("email_corporativo", "E-mail corporativo", "texto", ()), ("telefone", "Telefone", "texto", ()),
            ("cargo_texto", "Cargo", "texto", ()), ("departamento_id", "Departamento", "opcoes", self._opcoes("departamentos")),
            ("centro_custo_id", "Centro de custo", "opcoes", self._opcoes("centros_custo", "nome")),
            ("tipo_contrato", "Contrato", "opcoes", ("CLT", "PJ", "Estágio", "Temporário", "Aprendiz")),
            ("modalidade", "Modalidade", "opcoes", ("Presencial", "Híbrido", "Remoto")),
            ("admissao", "Admissão", "texto", ()), ("salario", "Salário", "texto", ()),
        )

    def _novo_colaborador(self): self._formulario("Novo colaborador", self._campos_colaborador(), lambda d: __import__("enterprise.rh", fromlist=["criar_colaborador"]).criar_colaborador(d, SESSAO.usuario))
    def _nova_admissao(self): self._formulario("Iniciar admissão", self._campos_colaborador(), lambda d: iniciar_admissao(d, SESSAO.usuario))

    def _editar_colaborador(self):
        colaborador_id = self._selecionado()
        if not colaborador_id: return
        self._formulario("Editar dados profissionais", (
            ("cargo_texto", "Cargo", "texto", ()),
            ("departamento_id", "Departamento", "opcoes", self._opcoes("departamentos")),
            ("centro_custo_id", "Centro de custo", "opcoes", self._opcoes("centros_custo", "nome")),
            ("tipo_contrato", "Contrato", "opcoes", ("CLT", "PJ", "Estágio", "Temporário", "Aprendiz")),
            ("modalidade", "Modalidade", "opcoes", ("Presencial", "Híbrido", "Remoto")),
            ("salario", "Salário", "texto", ()),
            ("status", "Status", "opcoes", ("Pré-admissão", "Ativo", "Em desligamento", "Afastado")),
        ), lambda d: atualizar_colaborador(colaborador_id, d, SESSAO.usuario))

    def _novo_dependente(self):
        colaborador_id = self._selecionado()
        if not colaborador_id: return
        self._formulario("Adicionar dependente", (
            ("nome", "Nome", "texto", ()), ("parentesco", "Parentesco", "texto", ()),
            ("nascimento", "Nascimento", "texto", ()), ("cpf", "CPF", "texto", ()),
            ("dependente_ir", "Dependente no IR", "booleano", ()),
        ), lambda d: adicionar_dependente(colaborador_id, d, SESSAO.usuario))

    def _novo_equipamento(self):
        colaborador_id = self._selecionado()
        if not colaborador_id: return
        self._formulario("Vincular equipamento", (
            ("patrimonio", "Patrimônio", "texto", ()), ("descricao", "Descrição", "texto", ()),
            ("origem_modulo", "Origem", "opcoes", ("estoque", "ti", "administrativo")),
            ("origem_recurso_id", "ID na origem", "texto", ()), ("entregue_em", "Entrega", "texto", ()),
        ), lambda d: vincular_equipamento(colaborador_id, d, SESSAO.usuario))

    def _novo_desligamento(self):
        self._formulario("Iniciar desligamento", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("tipo", "Tipo", "opcoes", ("Pedido de demissão", "Sem justa causa", "Com justa causa", "Término de contrato")), ("data_prevista", "Data prevista", "texto", ()), ("motivo", "Motivo", "texto", ())), lambda d: iniciar_desligamento(int(d.pop("colaborador_id")), d, SESSAO.usuario))

    def _novo_ponto(self):
        self._formulario("Registrar ponto e jornada", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("data", "Data", "texto", ()), ("entrada", "Entrada HH:MM", "texto", ()), ("intervalo_inicio", "Início intervalo", "texto", ()), ("intervalo_fim", "Fim intervalo", "texto", ()), ("saida", "Saída HH:MM", "texto", ()), ("justificativa", "Justificativa", "texto", ())), lambda d: registrar_ponto(int(d.pop("colaborador_id")), d, SESSAO.usuario))

    def _novas_ferias(self):
        self._formulario("Férias ou ausência", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("tipo", "Tipo", "opcoes", ("Férias", "Licença médica", "Licença maternidade", "Licença paternidade", "Ausência justificada", "Outros")), ("inicio", "Início", "texto", ()), ("fim", "Fim", "texto", ()), ("saldo_antes", "Saldo disponível", "texto", ()), ("motivo", "Motivo", "texto", ())), lambda d: solicitar_ferias_ausencia(d, SESSAO.usuario))

    def _novo_beneficio(self):
        self._formulario("Cadastrar benefício", (("nome", "Nome", "texto", ()), ("tipo", "Tipo", "texto", ()), ("fornecedor", "Fornecedor", "texto", ()), ("custo_empresa", "Custo da empresa", "texto", ()), ("desconto_colaborador", "Desconto colaborador", "texto", ()), ("elegibilidade", "Elegibilidade", "texto", ())), lambda d: salvar_beneficio(d, SESSAO.usuario))

    def _vincular_beneficio(self):
        self._formulario("Vincular benefício", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("beneficio_id", "Benefício", "opcoes", self._opcoes("beneficios")), ("inicio", "Início", "texto", ())), lambda d: vincular_beneficio(int(d["colaborador_id"]), int(d["beneficio_id"]), d["inicio"], SESSAO.usuario))

    def _nova_folha(self): self._formulario("Abrir folha", (("competencia", "Competência AAAA-MM", "texto", ()),), lambda d: abrir_folha(d["competencia"], SESSAO.usuario), largura=500)

    def _novo_evento_folha(self):
        folha_id = self._selecionado()
        if not folha_id: return
        self._formulario("Adicionar evento de folha", (
            ("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")),
            ("codigo", "Código", "texto", ()), ("descricao", "Descrição", "texto", ()),
            ("natureza", "Natureza", "opcoes", ("Provento", "Desconto", "Encargo")),
            ("valor", "Valor", "texto", ()),
        ), lambda d: adicionar_evento_folha(folha_id, int(d.pop("colaborador_id")), d, SESSAO.usuario))
    def _novo_cargo(self): self._formulario("Novo cargo", (("codigo", "Código", "texto", ()), ("titulo", "Título", "texto", ()), ("nivel", "Nível", "texto", ()), ("descricao", "Descrição", "texto", ()), ("salario_minimo", "Faixa mínima", "texto", ()), ("salario_referencia", "Referência", "texto", ()), ("salario_maximo", "Faixa máxima", "texto", ())), lambda d: salvar_cargo(d, SESSAO.usuario))
    def _nova_vaga(self): self._formulario("Nova vaga", (("titulo", "Título", "texto", ()), ("departamento_id", "Departamento", "opcoes", self._opcoes("departamentos")), ("cargo_id", "Cargo", "opcoes", self._opcoes("cargos", "titulo")), ("quantidade", "Quantidade", "texto", ()), ("motivo", "Motivo", "texto", ())), lambda d: criar_vaga(d, SESSAO.usuario))

    def _novo_candidato(self):
        vaga = self._selecionado()
        if not vaga: return
        self._formulario("Adicionar candidato", (("nome", "Nome", "texto", ()), ("email", "E-mail", "texto", ()), ("telefone", "Telefone", "texto", ()), ("etapa", "Etapa", "opcoes", ("Inscrição", "Triagem", "Entrevista RH", "Entrevista gestor", "Proposta", "Contratado", "Reprovado")), ("nota", "Nota", "texto", ()), ("observacao", "Observação", "texto", ())), lambda d: adicionar_candidato(vaga, d, SESSAO.usuario))

    def _nova_avaliacao(self): self._formulario("Nova avaliação", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("ciclo", "Ciclo", "texto", ()), ("tipo", "Tipo", "opcoes", ("Gestor", "Autoavaliação", "360 graus")), ("nota", "Nota", "texto", ()), ("feedback", "Feedback", "texto", ()), ("status", "Status", "opcoes", ("Planejada", "Em andamento", "Concluída"))), lambda d: salvar_avaliacao(d, SESSAO.usuario))
    def _novo_treinamento(self): self._formulario("Novo treinamento", (("titulo", "Título", "texto", ()), ("tipo", "Tipo", "opcoes", ("Interno", "Externo", "Online")), ("carga_horaria", "Carga horária", "texto", ()), ("validade_meses", "Validade em meses", "texto", ()), ("obrigatorio", "Obrigatório", "booleano", ()), ("custo", "Custo", "texto", ())), lambda d: salvar_treinamento(d, SESSAO.usuario))

    def _inscrever_treinamento(self):
        treinamento = self._selecionado()
        if not treinamento: return
        self._formulario("Inscrever colaborador", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")),), lambda d: inscrever_treinamento(treinamento, int(d["colaborador_id"]), SESSAO.usuario), largura=500)

    def _novo_pdi(self): self._formulario("Novo PDI", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("titulo", "Título", "texto", ()), ("objetivo", "Objetivo", "texto", ()), ("inicio", "Início", "texto", ()), ("prazo", "Prazo", "texto", ()), ("progresso", "Progresso %", "texto", ())), lambda d: salvar_pdi(d, SESSAO.usuario))

    def _novo_documento(self):
        caminho = filedialog.askopenfilename(parent=self.root, title="Selecionar documento")
        if not caminho: return
        opcoes = [("", "Corporativo")] + self._opcoes("colaboradores", "nome_completo")
        self._formulario("Registrar documento", (("colaborador_id", "Vínculo", "opcoes", opcoes), ("categoria", "Categoria", "opcoes", ("Pessoal", "Contratual", "Benefícios", "Saúde e segurança", "Treinamento", "Outros")), ("titulo", "Título", "texto", ()), ("classificacao", "Classificação", "opcoes", ("Interno", "Confidencial", "Restrito")), ("validade", "Validade", "texto", ()), ("assinatura_status", "Assinatura", "opcoes", ("Não aplicável", "Pendente", "Assinado"))), lambda d: registrar_documento(int(d["colaborador_id"]) if d["colaborador_id"] else None, d, caminho, SESSAO.usuario))

    def _nova_solicitacao(self): self._formulario("Nova solicitação", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")), ("tipo", "Tipo", "opcoes", ("Férias", "Benefício", "Documento", "Reembolso", "Ajuste de ponto", "Geral")), ("titulo", "Título", "texto", ()), ("descricao", "Descrição", "texto", ())), lambda d: criar_solicitacao(d, SESSAO.usuario))

    def _ver_colaborador(self):
        identificador = self._selecionado()
        if not identificador: return
        try: dados = obter_colaborador(identificador, SESSAO.usuario)
        except (ValueError, PermissionError) as erro: messagebox.showerror("Perfil do colaborador", str(erro), parent=self.root); return
        janela = tk.Toplevel(self.root); janela.title(f"Perfil · {dados['nome_completo']}"); janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(janela, self.root, 940, 680, minimo=(760, 520))
        topo = tk.Frame(janela, bg=CORES["card"]); topo.pack(fill="x", padx=18, pady=18)
        tk.Label(topo, text=dados["nome_social"] or dados["nome_completo"], font=FONTES["titulo"], fg=CORES["text"], bg=CORES["card"]).pack(anchor="w", padx=18, pady=(16, 2))
        tk.Label(topo, text=f"{dados['matricula']}  ·  {dados['cargo_texto']}  ·  {dados['status']}", font=FONTES["texto"], fg=COR_RH, bg=CORES["card"]).pack(anchor="w", padx=18, pady=(0, 16))
        abas = ttk.Notebook(janela, style="Dark.TNotebook"); abas.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        conjuntos = {
            "Profissional": ("filial_nome", "departamento_nome", "centro_custo_nome", "gestor_nome", "tipo_contrato", "modalidade", "admissao", "jornada_semanal"),
            "Pessoal": ("nome_completo", "cpf", "rg", "nascimento", "estado_civil", "nacionalidade", "telefone", "email_pessoal", "endereco", "contato_emergencia"),
            "Remuneração": ("salario_centavos", "banco", "agencia", "conta", "chave_pix"),
        }
        for nome_aba, campos in conjuntos.items():
            aba = tk.Frame(abas, bg=CORES["card"]); abas.add(aba, text=nome_aba)
            for campo in campos:
                linha = tk.Frame(aba, bg=CORES["card_secundario"]); linha.pack(fill="x", padx=14, pady=3)
                tk.Label(linha, text=campo.replace("_centavos", "").replace("_", " ").upper(), width=24, anchor="w", font=("Segoe UI", 8, "bold"), fg=CORES["text_sec"], bg=CORES["card_secundario"]).pack(side="left", padx=10, pady=8)
                tk.Label(linha, text=_formatar(dados.get(campo), campo), anchor="w", font=FONTES["texto"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(side="left", fill="x", expand=True)
        for nome_aba, chave, campos in (("Dependentes", "dependentes", ("nome", "parentesco", "nascimento", "dependente_ir")), ("Histórico", "historico", ("tipo", "vigencia", "observacao", "criado_em")), ("Benefícios", "beneficios", ("nome", "tipo", "inicio", "status")), ("Equipamentos", "equipamentos", ("patrimonio", "descricao", "entregue_em", "status")), ("Documentos", "documentos", ("categoria", "titulo", "validade", "status"))):
            aba = tk.Frame(abas, bg=CORES["card"]); abas.add(aba, text=nome_aba)
            for item in dados.get(chave, []): tk.Label(aba, text="  ·  ".join(_formatar(item.get(c), c) for c in campos), font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["card"], anchor="w").pack(fill="x", padx=16, pady=6)

    def _avancar_admissao(self):
        identificador = self._selecionado()
        if not identificador: return
        registro = next((r for r in self.registros if int(r["id"]) == identificador), None)
        etapa = min(8, int(registro.get("etapa_atual") or 1) + 1)
        concluir = etapa == 8 and messagebox.askyesno("Admissão", "Concluir a admissão e ativar o colaborador?", parent=self.root)
        try: atualizar_admissao(identificador, etapa, {"etapa_confirmada": etapa}, SESSAO.usuario, concluir=concluir); self.abrir_secao("admissoes")
        except (ValueError, PermissionError) as erro: messagebox.showerror("Admissão", str(erro), parent=self.root)

    def _concluir_desligamento(self):
        identificador = self._selecionado()
        if not identificador: return
        try: concluir_desligamento(identificador, SESSAO.usuario); self.abrir_secao("desligamentos")
        except (ValueError, PermissionError) as erro: messagebox.showerror("Desligamento", str(erro), parent=self.root)

    def _decidir_ferias(self, aprovar):
        identificador = self._selecionado()
        if not identificador: return
        try: decidir_ferias_ausencia(identificador, aprovar, "Decisão registrada na interface de RH.", SESSAO.usuario); self.abrir_secao("ferias")
        except (ValueError, PermissionError) as erro: messagebox.showerror("Férias e ausências", str(erro), parent=self.root)

    def _fechar_folha(self):
        identificador = self._selecionado()
        if not identificador: return
        if not messagebox.askyesno("Folha", "Fechar esta competência? A operação ficará auditada.", parent=self.root): return
        try: fechar_folha(identificador, SESSAO.usuario); self.abrir_secao("folha")
        except (ValueError, PermissionError) as erro: messagebox.showerror("Folha", str(erro), parent=self.root)

    def _contracheque(self):
        folha_id = self._selecionado()
        if not folha_id: return
        self._formulario("Gerar contracheque", (("colaborador_id", "Colaborador", "opcoes", self._opcoes("colaboradores", "nome_completo")),), lambda d: messagebox.showinfo("Contracheque", f"Arquivo gerado em:\n{gerar_contracheque(folha_id, int(d['colaborador_id']), SESSAO.usuario)}", parent=self.root), largura=500)

    def _verificar_documento(self):
        documento_id = self._selecionado()
        if not documento_id: return
        try:
            resultado = verificar_documento(documento_id, SESSAO.usuario)
            texto = "Documento íntegro e disponível." if resultado["integro"] else "O arquivo está ausente ou foi alterado."
            messagebox.showinfo("Integridade documental", texto, parent=self.root)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Integridade documental", str(erro), parent=self.root)

    def _decidir_solicitacao(self, aprovar):
        solicitacao_id = self._selecionado()
        if not solicitacao_id: return
        try:
            decidir_solicitacao(solicitacao_id, aprovar, "Decisão registrada pelo RH.", SESSAO.usuario)
            self.abrir_secao("solicitacoes")
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Solicitações", str(erro), parent=self.root)

    def _mostrar_analise(self):
        try: analise = analisar_rh(SESSAO.usuario)
        except (ValueError, PermissionError) as erro: messagebox.showerror("Análise de RH", str(erro), parent=self.root); return
        texto = "PONTOS DE ATENÇÃO\n\n" + "\n".join(f"• {x}" for x in analise["alertas"]) + "\n\nRECOMENDAÇÕES\n\n" + "\n".join(f"• {x}" for x in analise["recomendacoes"])
        messagebox.showinfo("Análise inteligente de RH", texto, parent=self.root)

    def _relatorios(self):
        self._cabecalho("Central de relatórios de RH", "Gere relatórios operacionais, financeiros e gerenciais em PDF, Excel ou CSV.")
        card = criar_card(self.conteudo); card.pack(fill="x")
        interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=18, pady=18)
        criar_titulo_secao(interior, "Gerar agora", "O arquivo respeita o contexto e as permissões de dados sensíveis.")
        for tipo in ("Colaboradores", "Férias", "Folha"):
            linha = tk.Frame(interior, bg=CORES["card_secundario"]); linha.pack(fill="x", pady=3)
            tk.Label(linha, text=tipo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(side="left", padx=12, pady=10)
            for formato in ("PDF", "XLSX", "CSV"):
                criar_botao(linha, formato, lambda t=tipo, f=formato: self._gerar_relatorio(t, f), tipo="fantasma", compacto=True).pack(side="right", padx=3)
        criar_botao(interior, "AGENDAR ENVIO", self._agendar_relatorio, tipo="secundario", compacto=True).pack(anchor="e", pady=(12, 0))

    def _gerar_relatorio(self, tipo, formato):
        extensao = formato.lower()
        caminho = filedialog.asksaveasfilename(parent=self.root, defaultextension=f".{extensao}", initialfile=f"rh_{tipo.lower()}.{extensao}")
        if not caminho: return
        try: gerar_relatorio_rh(tipo, formato, caminho, SESSAO.usuario); messagebox.showinfo("Relatórios", f"Relatório salvo em:\n{caminho}", parent=self.root)
        except (ValueError, PermissionError, OSError) as erro: messagebox.showerror("Relatórios", str(erro), parent=self.root)

    def _agendar_relatorio(self):
        self._formulario("Agendar relatório", (("tipo", "Tipo", "opcoes", ("Colaboradores", "Férias", "Folha")), ("formato", "Formato", "opcoes", ("PDF", "XLSX", "CSV")), ("frequencia", "Frequência", "opcoes", ("Semanal", "Mensal", "Trimestral")), ("destinatarios", "Destinatários", "texto", ())), lambda d: agendar_relatorio(d, SESSAO.usuario))

    def _auditoria(self):
        self._cabecalho("Auditoria de Recursos Humanos", "Rastreabilidade de operações, usuários, dados anteriores e dados posteriores.", acoes=False)
        try: registros = listar_auditoria_rh(SESSAO.usuario)
        except PermissionError as erro: messagebox.showerror("Auditoria", str(erro), parent=self.root); return
        card = criar_card(self.conteudo); card.pack(fill="both", expand=True)
        texto = tk.Text(card, bg=CORES["input"], fg=CORES["text_sec"], insertbackground=CORES["primary"], relief="flat", height=28, wrap="word")
        texto.pack(fill="both", expand=True, padx=1, pady=1)
        for r in registros: texto.insert("end", f"{r['criado_em']}  ·  {r['usuario_nome'] or r['usuario_id']}  ·  {r['acao']}  ·  {r['entidade']} #{r['entidade_id']}\n")
        texto.configure(state="disabled")

    def _configuracoes(self):
        self._cabecalho("Configurações de RH", "Permissões granulares e políticas operacionais do departamento.", acoes=False)
        if str(SESSAO.usuario.get("perfil", "")).lower() != "admin":
            estado = criar_estado_vazio(self.conteudo, "◇", "Acesso administrativo", "Somente administradores podem alterar permissões granulares de RH.", cor=COR_RH); estado.pack(fill="both", expand=True); return
        card = criar_card(self.conteudo); card.pack(fill="x")
        interior = tk.Frame(card, bg=CORES["card"]); interior.pack(fill="x", padx=18, pady=18)
        criar_titulo_secao(interior, "Matriz de ações", "A permissão por ação prevalece sobre a permissão genérica do módulo.")
        for acao, base in ACOES_RH.items():
            linha = tk.Frame(interior, bg=CORES["card_secundario"]); linha.pack(fill="x", pady=2)
            tk.Label(linha, text=acao.replace("_", " ").upper(), font=("Segoe UI", 8, "bold"), fg=CORES["text"], bg=CORES["card_secundario"], width=30, anchor="w").pack(side="left", padx=12, pady=8)
            tk.Label(linha, text=f"Base: {base}", font=FONTES["micro"], fg=CORES["text_muted"], bg=CORES["card_secundario"]).pack(side="left")
        tk.Label(interior, text="A gestão por usuário é realizada em Usuários e acessos. Dados de saúde, pessoais e remuneração devem permanecer restritos.", font=FONTES["texto"], fg=CORES["warning"], bg=CORES["card"], wraplength=760, justify="left").pack(anchor="w", pady=(14, 0))
