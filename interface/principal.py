"""Central da aplicação e cockpit executivo da V7."""

from __future__ import annotations

from datetime import datetime
import tkinter as tk

from auth.sessao import SESSAO
from enterprise.catalogo import MODULOS
from enterprise.central import resumo_cockpit
from enterprise.contexto import obter_contexto
from enterprise.perfis_acesso import nome_perfil_acesso
from interface.componentes import (
    acao_em_preparacao,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_card_acao,
    criar_chip,
    criar_metrica,
    criar_sidebar,
    criar_titulo_secao,
)
from interface.tema import CORES, FONTES, LAYOUT, VERSAO_INTERFACE


class TelaPrincipal:
    def __init__(self, root, navegacao):
        self.root = root
        self.navegacao = navegacao
        self.dados = resumo_cockpit(SESSAO.usuario)
        self.contexto = obter_contexto()
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self.criar_interface()

    def criar_interface(self):
        criar_sidebar(
            self.container,
            self.navegacao,
            ativo="inicio",
            rodape_texto="Sair com segurança",
            rodape_comando=self.navegacao.get("sair"),
        )
        conteudo = tk.Frame(self.container, bg=CORES["bg"])
        conteudo.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(24, 22),
        )

        acoes_cabecalho = tk.Frame(conteudo, bg=CORES["bg"])
        criar_botao(
            acoes_cabecalho,
            "⌕  BUSCAR  Ctrl+K",
            self.navegacao.get("busca"),
            tipo="secundario",
            compacto=True,
        ).pack(side="right")
        criar_cabecalho(
            conteudo,
            "Central da aplicação",
            "Visão geral e acesso seguro às principais áreas da plataforma.",
            acao=acoes_cabecalho,
            breadcrumb=self._breadcrumb(),
            etiqueta=f"INTERFACE {VERSAO_INTERFACE}",
        )

        self._metricas(conteudo)
        self._atalhos(conteudo)
        self._ferramentas_corporativas(conteudo)

        corpo = tk.Frame(conteudo, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True, pady=(14, 0))
        esquerda = tk.Frame(corpo, bg=CORES["bg"])
        esquerda.pack(side="left", fill="both", expand=True, padx=(0, 7))
        direita = tk.Frame(corpo, bg=CORES["bg"], width=330)
        direita.pack(side="right", fill="y", padx=(7, 0))
        direita.pack_propagate(False)
        self._atividades(esquerda)
        self._saude_plataforma(direita)
        self._alertas(direita)

    def _breadcrumb(self):
        usuario = SESSAO.usuario or {}
        perfil = nome_perfil_acesso(
            usuario.get("perfil_acesso"),
            administrador=usuario.get("perfil") == "admin",
        )
        filial = self.contexto.get("filial_nome") or "Todas as filiais"
        return f"{self.contexto['empresa_nome'].upper()}  /  {filial.upper()}  /  {perfil.upper()}"

    def _metricas(self, parent):
        grade = tk.Frame(parent, bg=CORES["bg"])
        grade.pack(fill="x")
        for indice, (titulo, valor, formato, cor, icone) in enumerate(self._selecionar_indicadores()):
            card = criar_metrica(
                grade,
                titulo,
                self._formatar(valor, formato),
                icone=icone,
                cor=cor,
                detalhe="Contexto empresarial atual",
            )
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, 10) if indice < 3 else 0,
            )

    def _ferramentas_corporativas(self, parent):
        card = criar_card(parent)
        card.pack(fill="x", pady=(14, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=17, pady=12)
        titulo = tk.Frame(interior, bg=CORES["card"])
        titulo.pack(side="left", padx=(0, 18))
        tk.Label(
            titulo,
            text="Ferramentas corporativas",
            font=("Segoe UI", 9, "bold"),
            fg=CORES["text"],
            bg=CORES["card"],
        ).pack(anchor="w")
        tk.Label(
            titulo,
            text="Interfaces preparadas para integração",
            font=FONTES["micro"],
            fg=CORES["text_muted"],
            bg=CORES["card"],
        ).pack(anchor="w", pady=(2, 0))
        for icone, texto in (
            ("✓", "Tarefas"),
            ("▤", "Documentos"),
            ("↻", "Workflow Builder"),
            ("∞", "Integrações"),
            ("▥", "Relatórios"),
            ("◉", "Auditoria"),
        ):
            criar_botao(
                interior,
                f"{icone}  {texto}",
                acao_em_preparacao(texto),
                tipo="fantasma",
                compacto=True,
            ).pack(side="left", padx=4)

    def _selecionar_indicadores(self):
        resumos = self.dados["modulos"]

        def card(modulo, indice, alternativo, icone):
            if modulo in resumos and len(resumos[modulo]["cards"]) > indice:
                titulo, valor, formato = resumos[modulo]["cards"][indice]
                return titulo, valor, formato, MODULOS[modulo]["cor"], icone
            return alternativo, 0, "inteiro", CORES["text_muted"], icone

        return (
            card("financeiro", 2, "SALDO FINANCEIRO", "$"),
            card("rh", 1, "COLABORADORES ATIVOS", "◎"),
            card("estoque", 2, "ALERTAS DE ESTOQUE", "!"),
            (
                "APROVAÇÕES PENDENTES",
                self.dados["aprovacoes_pendentes"],
                "inteiro",
                CORES["warning"],
                "✓",
            ),
        )

    def _atalhos(self, parent):
        bloco = tk.Frame(parent, bg=CORES["bg"])
        bloco.pack(fill="x", pady=(15, 0))
        criar_titulo_secao(
            bloco,
            "Acesso rápido",
            "A Central analítica e as áreas departamentais ficam dentro de Módulos.",
        )
        grade = tk.Frame(bloco, bg=CORES["bg"])
        grade.pack(fill="x")
        usuario_admin = SESSAO.eh_admin()
        atalhos = [
            (
                "▦",
                "Módulos empresariais",
                "Acesse departamentos, Analytics e seus painéis especializados.",
                self.navegacao.get("modulos"),
                CORES["primary"],
            ),
            (
                "✓",
                "Aprovações",
                "Analise solicitações e acompanhe decisões centralizadas.",
                self.navegacao.get("aprovacoes"),
                CORES["purple"],
            ),
            (
                "◌",
                "Central de alertas",
                "Acompanhe avisos, pendências e eventos dos workflows.",
                self.navegacao.get("notificacoes"),
                CORES["warning"],
            ),
            (
                "◎",
                "Usuários e acessos" if usuario_admin else "Configurações",
                "Gerencie perfis e permissões." if usuario_admin else "Ajuste preferências e segurança da sessão.",
                self.navegacao.get("usuarios" if usuario_admin else "configuracoes"),
                CORES["success"],
            ),
        ]
        for indice, (icone, titulo, descricao, acao, cor) in enumerate(atalhos):
            card = criar_card_acao(
                grade,
                icone=icone,
                titulo=titulo,
                descricao=descricao,
                acao=acao,
                cor=cor,
            )
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, 10) if indice < 3 else 0,
            )

    def _atividades(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True)
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=18, pady=16)
        botao = criar_botao(
            interior,
            "VER MÓDULOS  →",
            self.navegacao.get("modulos"),
            tipo="fantasma",
            compacto=True,
        )
        criar_titulo_secao(
            interior,
            "Atividade recente",
            "Eventos autorizados no contexto empresarial atual.",
            acao=botao,
        )
        cab = tk.Frame(interior, bg=CORES["card_secundario"])
        cab.pack(fill="x", pady=(4, 2))
        for texto, largura in (("EVENTO", 44), ("MÓDULO", 14), ("HORÁRIO", 10)):
            tk.Label(
                cab,
                text=texto,
                font=("Segoe UI", 7, "bold"),
                fg=CORES["text_muted"],
                bg=CORES["card_secundario"],
                anchor="w",
                width=largura,
            ).pack(side="left", fill="x", expand=texto == "EVENTO", padx=10, pady=8)
        atividades = self.dados["atividades"]
        if not atividades:
            vazio = tk.Frame(interior, bg=CORES["input"])
            vazio.pack(fill="both", expand=True)
            tk.Label(
                vazio,
                text="◇\n\nNenhuma atividade registrada\nAs operações da plataforma aparecerão aqui.",
                font=FONTES["texto_pequeno"],
                fg=CORES["text_muted"],
                bg=CORES["input"],
                justify="center",
            ).pack(expand=True)
            return
        lista = tk.Frame(interior, bg=CORES["card"])
        lista.pack(fill="both", expand=True)
        for atividade in atividades[:7]:
            linha = tk.Frame(lista, bg=CORES["card"])
            linha.pack(fill="x", pady=1)
            modulo = atividade.get("modulo", "")
            cor = MODULOS.get(modulo, {}).get("cor", CORES["primary"])
            tk.Label(
                linha,
                text="●",
                font=("Segoe UI", 7),
                fg=cor,
                bg=CORES["card"],
            ).pack(side="left", padx=(9, 7), pady=9)
            tk.Label(
                linha,
                text=atividade.get("descricao", "Atividade registrada"),
                font=FONTES["texto_pequeno"],
                fg=CORES["text"],
                bg=CORES["card"],
                anchor="w",
            ).pack(side="left", fill="x", expand=True)
            tk.Label(
                linha,
                text=MODULOS.get(modulo, {}).get("nome", modulo.title()),
                font=FONTES["micro"],
                fg=CORES["text_sec"],
                bg=CORES["card"],
                width=16,
                anchor="w",
            ).pack(side="left")
            tk.Label(
                linha,
                text=self._hora(atividade.get("criado_em")),
                font=FONTES["micro"],
                fg=CORES["text_muted"],
                bg=CORES["card"],
                width=9,
            ).pack(side="right")
            tk.Frame(lista, bg=CORES["divider"], height=1).pack(fill="x")

    def _saude_plataforma(self, parent):
        card = criar_card(parent, destaque=True)
        card.pack(fill="x")
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=18, pady=16)
        criar_titulo_secao(interior, "Saúde da plataforma", "Serviços locais da aplicação.")
        tk.Label(
            interior,
            text="✓",
            font=("Segoe UI Symbol", 28, "bold"),
            fg=CORES["success"],
            bg=CORES["success_soft"],
            width=3,
            height=2,
        ).pack(pady=(5, 8))
        tk.Label(
            interior,
            text="Ambiente operacional",
            font=("Segoe UI", 11, "bold"),
            fg=CORES["text"],
            bg=CORES["card"],
        ).pack()
        tk.Label(
            interior,
            text="Core, banco local e motor analítico disponíveis.",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        ).pack(pady=(3, 12))
        for nome, valor, cor in (
            ("Status do serviço", "Operacional", CORES["success"]),
            ("Interface", VERSAO_INTERFACE, CORES["primary"]),
            ("Sessão", "Protegida", CORES["success"]),
        ):
            linha = tk.Frame(interior, bg=CORES["card"])
            linha.pack(fill="x", pady=5)
            tk.Label(
                linha,
                text=nome,
                font=FONTES["texto_pequeno"],
                fg=CORES["text_sec"],
                bg=CORES["card"],
            ).pack(side="left")
            tk.Label(
                linha,
                text=valor,
                font=("Segoe UI", 8, "bold"),
                fg=cor,
                bg=CORES["card"],
            ).pack(side="right")

    def _alertas(self, parent):
        card = criar_card(parent)
        card.pack(fill="both", expand=True, pady=(14, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="both", expand=True, padx=17, pady=16)
        botao = criar_botao(
            interior,
            "VER TODOS",
            self.navegacao.get("notificacoes"),
            tipo="fantasma",
            compacto=True,
        )
        criar_titulo_secao(
            interior,
            "Alertas recentes",
            f"{len(self.dados['notificacoes'])} não lido(s).",
            acao=botao,
        )
        notificacoes = self.dados["notificacoes"]
        if not notificacoes:
            tk.Label(
                interior,
                text="✓\n\nNenhum alerta pendente\nO ambiente está sob controle.",
                font=FONTES["texto_pequeno"],
                fg=CORES["text_muted"],
                bg=CORES["card"],
                justify="center",
            ).pack(expand=True)
            return
        cores = {
            "info": CORES["primary"],
            "sucesso": CORES["success"],
            "aviso": CORES["warning"],
            "critico": CORES["danger"],
        }
        for item in notificacoes[:4]:
            linha = tk.Frame(
                interior,
                bg=CORES["card_secundario"],
                highlightthickness=1,
                highlightbackground=CORES["border_soft"],
            )
            linha.pack(fill="x", pady=4)
            tk.Frame(
                linha,
                bg=cores.get(item.get("nivel"), CORES["primary"]),
                width=3,
            ).pack(side="left", fill="y")
            texto = tk.Frame(linha, bg=CORES["card_secundario"])
            texto.pack(fill="x", expand=True, padx=10, pady=8)
            tk.Label(
                texto,
                text=item.get("titulo", "Alerta"),
                font=("Segoe UI", 8, "bold"),
                fg=CORES["text"],
                bg=CORES["card_secundario"],
            ).pack(anchor="w")
            tk.Label(
                texto,
                text=item.get("mensagem", ""),
                font=FONTES["micro"],
                fg=CORES["text_sec"],
                bg=CORES["card_secundario"],
                wraplength=260,
                justify="left",
            ).pack(anchor="w", pady=(2, 0))

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

    @staticmethod
    def _hora(valor):
        try:
            return datetime.fromisoformat(str(valor)).strftime("%H:%M")
        except (TypeError, ValueError):
            return str(valor or "")[11:16]
