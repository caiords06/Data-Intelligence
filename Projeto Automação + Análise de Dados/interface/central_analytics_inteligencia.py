"""Cockpit de Inteligência Empresarial — V10.4.0/V10.4.1."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from interface.componentes import (
    GradeResponsiva, criar_botao, criar_cabecalho, criar_card, criar_chip,
    criar_estado_vazio, criar_metrica, criar_titulo_secao,
)
from interface.tema import CORES, FONTES
from services.analytics import (
    alterar_status_insight, definir_regra_ativa, gerar_insights,
    listar_insights, listar_regras, obter_painel_executivo, salvar_regra,
)
from services.orquestracao import listar_orquestracoes, resumo_orquestracoes


_ROTULOS_MODULOS = {
    "financeiro": "Financeiro", "rh": "RH", "compras": "Compras",
    "estoque": "Estoque", "ti": "Tecnologia", "marketing": "Marketing",
    "comercial": "Comercial", "administrativo": "Administrativo", "juridico": "Jurídico",
}
_CORES_SEVERIDADE = {
    "Crítica": ("danger", "danger_soft"),
    "Atenção": ("warning", "warning_soft"),
    "Informativa": ("primary", "primary_soft"),
}


class CentralAnalyticsInteligenciaMixin:
    def _acao_insight(self, item):
        modulo = str(item.get("acao_modulo") or item.get("modulo") or "").strip().lower()
        secao = str(item.get("acao_secao") or "visao").strip().lower()
        callback = self.navegacao.get("secao_modulo")
        if callback and modulo:
            callback(modulo, secao)
        else:
            messagebox.showinfo("Insight", item.get("descricao") or "Sem ação de navegação disponível.")

    def _painel_insights(self, parent, itens, *, limite=8, vazio="Nenhum insight ativo no contexto atual."):
        if not itens:
            criar_estado_vazio(parent, "✓", "Operação sem alerta relevante", vazio, cor=CORES["success"]).pack(fill="x")
            return
        for item in itens[:limite]:
            sev = str(item.get("severidade") or "Informativa")
            cor_key, fundo_key = _CORES_SEVERIDADE.get(sev, ("primary", "primary_soft"))
            card = criar_card(parent)
            card.pack(fill="x", pady=(0, 9))
            interior = tk.Frame(card, bg=CORES["card"])
            interior.pack(fill="x", padx=16, pady=13)
            topo = tk.Frame(interior, bg=CORES["card"])
            topo.pack(fill="x")
            criar_chip(topo, sev.upper(), cor=CORES[cor_key], fundo=CORES[fundo_key]).pack(side="left")
            tk.Label(topo, text=_ROTULOS_MODULOS.get(item.get("modulo"), str(item.get("modulo") or "").title()),
                     font=("Inter", 8, "bold"), fg=CORES["text_muted"], bg=CORES["card"]).pack(side="right")
            tk.Label(interior, text=item.get("titulo") or "Insight", font=("Inter", 11, "bold"),
                     fg=CORES["text"], bg=CORES["card"], anchor="w", justify="left").pack(fill="x", pady=(9, 3))
            desc = tk.Label(interior, text=item.get("descricao") or "", font=FONTES["texto_pequeno"],
                            fg=CORES["text_sec"], bg=CORES["card"], anchor="w", justify="left")
            desc.pack(fill="x")
            desc.bind("<Configure>", lambda e, w=desc: w.configure(wraplength=max(260, e.width - 8)), add="+")
            acoes = tk.Frame(interior, bg=CORES["card"])
            acoes.pack(fill="x", pady=(10, 0))
            if item.get("acao_rotulo") or item.get("acao_modulo"):
                criar_botao(acoes, item.get("acao_rotulo") or "ABRIR CONTEXTO", lambda x=item: self._acao_insight(x), compacto=True).pack(side="left")
            if item.get("id"):
                criar_botao(acoes, "IGNORAR", lambda iid=item["id"]: self._mudar_insight(iid, "Ignorado"), tipo="fantasma", compacto=True).pack(side="right")

    def _mudar_insight(self, insight_id, status):
        try:
            alterar_status_insight(int(insight_id), status, SESSAO.usuario)
            self.abrir_secao(self.secao)
        except Exception as exc:
            messagebox.showerror("Analytics", str(exc))

    def _visao_executiva(self, parent):
        criar_cabecalho(
            parent, "Visão executiva",
            "Um cockpit transversal para entender o que exige atenção e chegar diretamente à operação responsável.",
            breadcrumb="MÓDULOS  /  ANALYTICS  /  VISÃO EXECUTIVA",
            etiqueta="INTELIGÊNCIA EMPRESARIAL",
            acao=lambda area: criar_botao(area, "ATUALIZAR INSIGHTS", self._atualizar_insights),
        )
        try:
            resultado = gerar_insights(SESSAO.usuario, persistir=True)
            painel = resultado.get("painel") or {}
            itens = resultado.get("insights") or []
        except Exception as exc:
            painel = obter_painel_executivo(SESSAO.usuario)
            itens = []
            messagebox.showwarning("Analytics", f"O painel foi carregado, mas a geração de insights encontrou um problema:\n{exc}")

        try:
            resumo_fluxos = resumo_orquestracoes(SESSAO.usuario)
            fluxos_ativos = int(resumo_fluxos.get("abertas", 0)) + int(resumo_fluxos.get("andamento", 0))
        except Exception:
            resumo_fluxos = {}; fluxos_ativos = 0

        grade = GradeResponsiva(parent, max_colunas=4, largura_minima=220, bg=CORES["bg"])
        grade.pack(fill="x")
        metricas = (
            ("Módulos integrados", painel.get("modulos_processados", len(painel.get("modulos") or {})), "▦", CORES["primary"], "Fontes operacionais autorizadas"),
            ("Insights críticos", sum(1 for x in itens if x.get("severidade") == "Crítica"), "!", CORES["danger"], "Prioridade imediata"),
            ("Pontos de atenção", sum(1 for x in itens if x.get("severidade") == "Atenção"), "△", CORES["warning"], "Acompanhar e decidir"),
            ("Fluxos integrados", fluxos_ativos, "⇄", CORES["success"], "Orquestrações abertas/em andamento"),
        )
        for titulo, valor, icone, cor, detalhe in metricas:
            grade.adicionar(criar_metrica(grade, titulo, valor, icone=icone, cor=cor, detalhe=detalhe))

        corpo = tk.Frame(parent, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True, pady=(14, 0))
        esquerda = tk.Frame(corpo, bg=CORES["bg"])
        direita = tk.Frame(corpo, bg=CORES["bg"])
        card = criar_card(esquerda); card.pack(fill="both", expand=True)
        area = tk.Frame(card, bg=CORES["card"]); area.pack(fill="both", expand=True, padx=17, pady=16)
        criar_titulo_secao(area, "O que precisa da sua atenção", "Insights priorizados por impacto e encaminhados ao módulo responsável.",
                           acao=lambda x: criar_botao(x, "VER TODOS", lambda: self.abrir_secao("insights"), tipo="fantasma", compacto=True))
        self._painel_insights(area, itens, limite=7)

        card2 = criar_card(direita); card2.pack(fill="x")
        area2 = tk.Frame(card2, bg=CORES["card"]); area2.pack(fill="x", padx=17, pady=16)
        criar_titulo_secao(area2, "Saúde dos módulos", "Resumo operacional das áreas que o seu perfil pode consultar.")
        for modulo, dados in (painel.get("modulos") or {}).items():
            linha = tk.Frame(area2, bg=CORES["card"]); linha.pack(fill="x", pady=5)
            tk.Label(linha, text=_ROTULOS_MODULOS.get(modulo, modulo.title()), font=FONTES["texto_pequeno"],
                     fg=CORES["text_sec"], bg=CORES["card"]).pack(side="left")
            alerta = sum(1 for x in itens if x.get("modulo") == modulo)
            texto = "Sem alertas" if alerta == 0 else f"{alerta} insight(s)"
            tk.Label(linha, text=texto, font=("Inter", 8, "bold"),
                     fg=CORES["success"] if alerta == 0 else CORES["warning"], bg=CORES["card"]).pack(side="right")
        if painel.get("erros"):
            tk.Label(area2, text=f"{len(painel['erros'])} módulo(s) não puderam ser processados; nenhum dado restrito foi exposto.",
                     font=FONTES["micro"], fg=CORES["warning"], bg=CORES["card"], wraplength=300, justify="left").pack(fill="x", pady=(12, 0))

        try:
            fluxos = listar_orquestracoes(SESSAO.usuario, limite=5)
        except Exception:
            fluxos = []
        if fluxos:
            tk.Frame(area2, bg=CORES["divider"], height=1).pack(fill="x", pady=(14, 12))
            tk.Label(area2, text="FLUXOS INTERDEPARTAMENTAIS", font=("Inter", 8, "bold"),
                     fg=CORES["text_muted"], bg=CORES["card"], anchor="w").pack(fill="x")
            for fluxo in fluxos[:5]:
                linha = tk.Frame(area2, bg=CORES["card"]); linha.pack(fill="x", pady=(7, 0))
                tk.Label(linha, text=str(fluxo.get("titulo") or fluxo.get("tipo") or "Fluxo"),
                         font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card"], anchor="w",
                         wraplength=230, justify="left").pack(side="left", fill="x", expand=True)
                status = str(fluxo.get("status") or "Aberta")
                criar_chip(linha, status.upper(), cor=CORES["success"] if status == "Concluída" else CORES["primary"]).pack(side="right", padx=(8, 0))

        def reorganizar(evento=None):
            largura = evento.width if evento else corpo.winfo_width()
            esquerda.grid_forget(); direita.grid_forget()
            corpo.grid_columnconfigure(0, weight=1); corpo.grid_columnconfigure(1, weight=0)
            if largura >= 920:
                corpo.grid_columnconfigure(1, minsize=330)
                esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
                direita.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
            else:
                esquerda.grid(row=0, column=0, columnspan=2, sticky="nsew")
                direita.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        corpo.bind("<Configure>", reorganizar, add="+"); corpo.after_idle(reorganizar)

    def _atualizar_insights(self):
        try:
            r = gerar_insights(SESSAO.usuario, persistir=True)
            messagebox.showinfo("Analytics", f"Inteligência atualizada: {r.get('total', 0)} insight(s), {r.get('criticos', 0)} crítico(s).")
            self.abrir_secao(self.secao)
        except Exception as exc:
            messagebox.showerror("Analytics", str(exc))

    def _insights_empresariais(self, parent, *, somente_alertas=False):
        titulo = "Alertas" if somente_alertas else "Insights"
        subtitulo = ("Fila de situações críticas e de atenção, com contexto e ação recomendada." if somente_alertas
                     else "Leitura explicável da operação empresarial. Cada insight conduz ao local em que a decisão deve acontecer.")
        criar_cabecalho(parent, titulo, subtitulo, breadcrumb=f"MÓDULOS  /  ANALYTICS  /  {titulo.upper()}",
                        acao=lambda area: criar_botao(area, "RECALCULAR", self._atualizar_insights))
        try:
            itens = listar_insights(SESSAO.usuario, status="Ativo", limite=500)
            if somente_alertas:
                itens = [x for x in itens if x.get("severidade") in {"Crítica", "Atenção"}]
        except Exception as exc:
            messagebox.showerror("Analytics", str(exc)); itens = []
        card = criar_card(parent); card.pack(fill="both", expand=True)
        area = tk.Frame(card, bg=CORES["card"]); area.pack(fill="both", expand=True, padx=17, pady=16)
        criar_titulo_secao(area, f"{len(itens)} item(ns) ativo(s)", "A fila é atualizada quando a inteligência é recalculada.")
        self._painel_insights(area, itens, limite=200, vazio="Não há alertas ativos para os módulos do seu perfil.")

    def _regras_analiticas(self, parent):
        criar_cabecalho(parent, "Regras analíticas", "Configure limites adicionais sem apresentar um catálogo de modelos que ainda não existe.",
                        breadcrumb="MÓDULOS  /  ANALYTICS  /  REGRAS ANALÍTICAS",
                        acao=lambda area: criar_botao(area, "+ NOVA REGRA", self._nova_regra))
        regras = listar_regras(SESSAO.usuario)
        card = criar_card(parent); card.pack(fill="both", expand=True)
        area = tk.Frame(card, bg=CORES["card"]); area.pack(fill="both", expand=True, padx=17, pady=16)
        criar_titulo_secao(area, "Regras personalizadas", "As regras complementam — não substituem — os detectores nativos da plataforma.")
        if not regras:
            criar_estado_vazio(area, "⚙", "Nenhuma regra personalizada", "Os detectores nativos continuam ativos. Crie regras apenas para políticas específicas da empresa.").pack(fill="x")
            return
        for regra in regras:
            linha = tk.Frame(area, bg=CORES["card"]); linha.pack(fill="x", pady=4)
            texto = f"{regra['nome']}  ·  {regra['modulo']}  ·  {regra['metrica']} {regra['operador']} {regra.get('limite')}"
            tk.Label(linha, text=texto, font=FONTES["texto_pequeno"], fg=CORES["text"], bg=CORES["card"], anchor="w").pack(side="left", fill="x", expand=True)
            ativa = bool(regra.get("ativo"))
            criar_chip(linha, "ATIVA" if ativa else "PAUSADA", cor=CORES["success"] if ativa else CORES["text_muted"]).pack(side="left", padx=8)
            criar_botao(linha, "PAUSAR" if ativa else "ATIVAR", lambda r=regra, a=ativa: self._toggle_regra(r["id"], not a), tipo="fantasma", compacto=True).pack(side="right")
            tk.Frame(area, bg=CORES["divider"], height=1).pack(fill="x")

    def _toggle_regra(self, rid, ativa):
        try:
            definir_regra_ativa(int(rid), bool(ativa), SESSAO.usuario); self.abrir_secao("regras")
        except Exception as exc: messagebox.showerror("Analytics", str(exc))

    def _nova_regra(self):
        # Diálogo intencionalmente simples: a regra continua auditável no backend.
        nome = simpledialog.askstring("Nova regra", "Nome da regra:", parent=self.container)
        if not nome: return
        modulo = simpledialog.askstring("Nova regra", "Módulo (ex.: financeiro, estoque, comercial):", parent=self.container)
        metrica = simpledialog.askstring("Nova regra", "Métrica do resumo (ex.: vencidas, criticos, abertas):", parent=self.container)
        operador = simpledialog.askstring("Nova regra", "Operador (>, >=, <, <=, =, !=):", initialvalue=">", parent=self.container)
        limite = simpledialog.askfloat("Nova regra", "Limite numérico:", parent=self.container)
        if not modulo or not metrica or limite is None: return
        codigo = "regra_" + "_".join(nome.lower().split())[:60]
        try:
            salvar_regra({"codigo": codigo, "nome": nome, "modulo": modulo, "metrica": metrica,
                           "operador": operador or ">", "limite": limite, "severidade": "Atenção",
                           "acao_modulo": modulo, "acao_secao": "visao", "ativo": True}, SESSAO.usuario)
            gerar_insights(SESSAO.usuario, persistir=True)
            self.abrir_secao("regras")
        except Exception as exc: messagebox.showerror("Analytics", str(exc))
