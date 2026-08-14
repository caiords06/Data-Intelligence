"""Workspace especializado de Tecnologia e Serviços 3.0.1."""

from __future__ import annotations

import webbrowser
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from core.nodo import carregar_config_nodo, usa_servidor_remoto
from services.contexto import tem_permissao
from services.contexto import obter_contexto
from services.departamentos.tecnologia import (
    adicionar_comentario,
    analisar_tecnologia,
    atribuir_licenca,
    atualizar_chamado,
    atualizar_ativo,
    atualizar_dispositivo_rede,
    atualizar_segmento_rede,
    autorizar_segmento_rede,
    concluir_manutencao,
    criar_artigo_conhecimento,
    criar_ativo,
    criar_chamado,
    criar_contrato,
    criar_credencial_agente,
    criar_incidente_seguranca,
    criar_licenca,
    criar_monitor,
    criar_mudanca,
    criar_problema,
    criar_segmento_rede,
    criar_sistema,
    contar_segmentos_ativos,
    detalhar_ativo,
    detalhar_dispositivo_rede,
    diagnosticar_segmento_rede,
    descobrir_segmento_rede,
    decidir_mudanca,
    encerrar_acesso_remoto,
    gerar_alertas_tecnologia,
    gerar_relatorio_tecnologia,
    garantir_catalogos,
    iniciar_manutencao,
    listar_secao,
    obter_credencial_agente,
    listar_usuarios_escopo,
    registrar_dispositivo_descoberto,
    registrar_evento_monitoramento,
    registrar_heartbeat,
    remover_ativo,
    remover_dispositivo_rede,
    remover_firewall_segmento,
    remover_segmento_rede,
    revogar_credencial_agente,
    resolver_alerta,
    revogar_autorizacao_segmento_rede,
    preparar_firewall_segmento,
    vincular_dispositivo_ativo,
    resumo_tecnologia,
    solicitar_acesso_remoto,
    tem_permissao_tecnologia,
)
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
from interface.navegacao_modulos import criar_sidebar_modulo
from interface.tema import CORES, FONTES, LAYOUT, adicionar_divisorias_treeview, configurar_estilos_ttk
from servidor_ti import status_servidor
from servidor_ti.config import url_lan_sugerida


COR_TI = "#06B6D4"

GRUPOS_PUBLICOS = (
    ("SUPORTE", (
        ("portal", "⌂", "Início do suporte"),
        ("abrir_chamado", "+", "Abrir chamado"),
        ("meus_chamados", "◎", "Meus chamados"),
    )),
)

GRUPOS_OPERACAO = (
    ("CENTRO DE OPERAÇÕES", (
        ("cockpit", "◈", "Cockpit de TI"),
        ("rede", "⌘", "Rede ao vivo"),
        ("ativos", "▣", "Ativos gerenciados"),
        ("chamados", "◉", "Service Desk"),
        ("acessos", "⇱", "Acesso remoto"),
    )),
    ("INFRAESTRUTURA", (
        ("segmentos", "≋", "Segmentos / firewall"),
        ("monitoramento", "◎", "Monitoramento"),
        ("sistemas", "≡", "Sistemas"),
        ("manutencoes", "⚒", "Manutenções"),
    )),
    ("SOFTWARE E CONHECIMENTO", (
        ("licencas", "#", "Licenças"),
        ("contratos", "▧", "Contratos"),
        ("conhecimento", "▤", "Base de conhecimento"),
    )),
    ("GOVERNANÇA", (
        ("mudancas", "⇄", "Mudanças"),
        ("problemas", "!", "Problemas"),
        ("seguranca", "◈", "Segurança"),
        ("alertas", "◌", "Central de alertas"),
        ("relatorios", "▤", "Relatórios"),
        ("auditoria", "◉", "Auditoria"),
    )),
)

GRUPOS_MENU = GRUPOS_PUBLICOS + GRUPOS_OPERACAO

ROTULOS = {chave: titulo for _grupo, itens in GRUPOS_MENU for chave, _icone, titulo in itens}

SUBTITULOS = {
    "portal": "Suporte acessível a qualquer usuário: abra solicitações e acompanhe o próprio atendimento.",
    "abrir_chamado": "Registre uma solicitação de suporte sem precisar navegar pela operação técnica.",
    "cockpit": "Visão operacional em tempo real de chamados, ativos, segmentos, conectividade e alertas.",
    "chamados": "Central ITSM com prioridade, impacto, urgência, SLA, ativo e sistema relacionados.",
    "meus_chamados": "Acompanhe solicitações abertas pelo usuário atual e seu histórico de atendimento.",
    "conhecimento": "Procedimentos, tutoriais e soluções reutilizáveis para reduzir reincidência.",
    "ativos": "Inventário tecnológico, responsabilidade, configuração, saúde e ciclo de vida.",
    "manutencoes": "Triagem, reparo, fornecedor, custo, previsão e retorno do equipamento.",
    "acessos": "Sessões remotas iniciadas com consentimento, justificativa e auditoria.",
    "rede": "Dispositivos observados por agentes ou conectores em segmentos previamente autorizados.",
    "segmentos": "Escopos privados administrados; nenhuma descoberta é autorizada implicitamente.",
    "sistemas": "Aplicações, criticidade, ambiente, responsáveis e dependências operacionais.",
    "monitoramento": "Saúde de infraestrutura, sistemas e serviços com eventos e alertas.",
    "licencas": "Assinaturas, utilização, disponibilidade, custos e renovações.",
    "contratos": "Contratos de tecnologia, fornecedores, vigência, custo, SLA e documentos.",
    "mudancas": "Plano, risco, rollback, janela e aprovação humana antes da execução.",
    "problemas": "Causa raiz, workaround, solução definitiva e chamados reincidentes relacionados.",
    "seguranca": "Incidentes, severidade, contenção, ativos e sistemas afetados.",
    "alertas": "Eventos que exigem reconhecimento, investigação ou resolução operacional.",
    "auditoria": "Trilha imutável de mudanças, acessos e decisões do módulo.",
}

COLUNAS = {
    "chamados": (("numero", "Chamado", 125), ("titulo", "Título", 260), ("prioridade", "Prioridade", 90), ("status", "Status", 130), ("solicitante_nome", "Solicitante", 145), ("tecnico_nome", "Técnico", 140), ("sla_restante_minutos", "SLA/min", 80)),
    "meus_chamados": (("numero", "Chamado", 125), ("titulo", "Título", 280), ("prioridade", "Prioridade", 90), ("status", "Status", 135), ("tecnico_nome", "Técnico", 150), ("ativo_patrimonio", "Ativo", 110)),
    "conhecimento": (("titulo", "Artigo", 300), ("categoria", "Categoria", 130), ("status", "Status", 105), ("autor_nome", "Autor", 150), ("visualizacoes", "Visualizações", 90), ("criado_em", "Criado em", 145)),
    "ativos": (("patrimonio", "Patrimônio", 115), ("nome", "Ativo", 205), ("tipo", "Tipo", 105), ("hostname", "Hostname", 125), ("usuario_responsavel", "Responsável", 145), ("status", "Ciclo", 110), ("estado_conectividade", "Conectividade", 115), ("saude_percentual", "Saúde %", 80)),
    "manutencoes": (("patrimonio", "Ativo", 115), ("problema", "Problema", 280), ("status", "Status", 120), ("inicio_em", "Início", 145), ("previsao_em", "Previsão", 115), ("custo_centavos", "Custo", 105)),
    "acessos": (("patrimonio", "Ativo", 115), ("tecnico_nome", "Técnico", 155), ("provedor", "Provedor", 105), ("status", "Status", 100), ("chamado_numero", "Chamado", 120), ("criado_em", "Iniciado em", 150), ("duracao_segundos", "Duração/s", 90)),
    "rede": (("endereco_ip", "IP", 115), ("hostname", "Hostname", 155), ("endereco_mac", "MAC", 145), ("fabricante", "Fabricante", 130), ("tipo_estimado", "Tipo", 110), ("status", "Status", 100), ("patrimonio", "Patrimônio", 115), ("segmento_nome", "Segmento", 130)),
    "segmentos": (("nome", "Segmento", 180), ("cidr", "CIDR", 140), ("vlan", "VLAN", 80), ("gateway", "Gateway", 125), ("autorizado", "Autorizado", 90), ("autorizado_por_nome", "Autorizado por", 150), ("autorizado_em", "Data", 145)),
    "sistemas": (("nome", "Sistema", 210), ("ambiente", "Ambiente", 105), ("criticidade", "Criticidade", 95), ("status", "Status", 115), ("versao", "Versão", 90), ("servidor_patrimonio", "Servidor", 120), ("responsavel_ti_nome", "Responsável TI", 145), ("sla_disponibilidade", "SLA %", 75)),
    "monitoramento": (("nome", "Monitor", 220), ("tipo", "Tipo", 115), ("patrimonio", "Ativo", 110), ("sistema_nome", "Sistema", 135), ("status", "Status", 110), ("ultimo_valor", "Valor", 90), ("ultima_verificacao", "Última verificação", 150)),
    "licencas": (("nome", "Licença", 220), ("tipo", "Tipo", 105), ("quantidade_contratada", "Contratadas", 90), ("quantidade_utilizada", "Utilizadas", 85), ("quantidade_disponivel", "Disponíveis", 85), ("custo_centavos", "Custo", 110), ("vencimento_em", "Renovação", 115), ("status", "Status", 90)),
    "contratos": (("numero", "Contrato", 125), ("titulo", "Título", 230), ("fornecedor_nome", "Fornecedor", 170), ("termino_em", "Término", 115), ("valor_centavos", "Valor", 110), ("status", "Status", 90)),
    "mudancas": (("numero", "Mudança", 125), ("titulo", "Título", 250), ("risco", "Risco", 90), ("status", "Status", 125), ("aprovacao_status", "Aprovação", 120), ("responsavel_nome", "Responsável", 145), ("janela_inicio", "Janela", 145)),
    "problemas": (("numero", "Problema", 125), ("titulo", "Título", 270), ("impacto", "Impacto", 160), ("status", "Status", 120), ("responsavel_nome", "Responsável", 145), ("chamados_relacionados", "Chamados", 85)),
    "seguranca": (("numero", "Incidente", 125), ("titulo", "Título", 250), ("tipo", "Tipo", 120), ("severidade", "Severidade", 90), ("status", "Status", 105), ("patrimonio", "Ativo", 110), ("sistema_nome", "Sistema", 130), ("detectado_em", "Detectado", 145)),
    "alertas": (("severidade", "Severidade", 95), ("titulo", "Alerta", 245), ("mensagem", "Mensagem", 350), ("status", "Status", 100), ("criado_em", "Criado em", 145), ("responsavel_nome", "Responsável", 140)),
    "auditoria": (("criado_em", "Data", 150), ("usuario_nome", "Usuário", 150), ("acao", "Ação", 180), ("recurso_tipo", "Recurso", 170), ("recurso_id", "ID", 75), ("observacao", "Observação", 300)),
}


def _moeda(valor):
    return "R$ " + f"{int(valor or 0)/100:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _formatar(valor, campo=""):
    if valor in (None, ""):
        return "—"
    if "centavos" in campo:
        return _moeda(valor)
    if campo in {"autorizado", "renovacao_automatica", "consentimento_confirmado"}:
        return "Sim" if valor else "Não"
    if isinstance(valor, float):
        return f"{valor:.1f}".replace(".", ",")
    return str(valor)


from interface.tecnologia_operacoes import TecnologiaOperacoesMixin
from interface.tecnologia_acoes import TecnologiaAcoesMixin

class TelaTecnologia(TecnologiaOperacoesMixin, TecnologiaAcoesMixin):
    def __init__(self, root, navegacao, secao="portal"):
        self.root = root
        self.navegacao = navegacao
        self.operador_ti = tem_permissao(SESSAO.usuario, "ti", "ler")
        secao = "portal" if secao == "visao" else secao
        permitidas_publicas = {"portal", "abrir_chamado", "meus_chamados"}
        if secao not in ROTULOS or (not self.operador_ti and secao not in permitidas_publicas):
            secao = "portal"
        self.secao = secao
        self.tabela = None
        self.registros = []
        self.segmentos = []
        self.dispositivos = []
        self._segmento_id = None
        self._detalhe_widgets = {}
        if self.operador_ti:
            garantir_catalogos(SESSAO.usuario)
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self._criar_interface()

    def _ui_ativa(self) -> bool:
        try:
            return bool(self.container.winfo_exists() and self.root.winfo_exists())
        except tk.TclError:
            return False

    def _agendar_ui(self, callback) -> None:
        if not self._ui_ativa():
            return
        try:
            self.root.after(0, lambda: callback() if self._ui_ativa() else None)
        except tk.TclError:
            return

    def _criar_interface(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar_modulo(
            self.container,
            self.navegacao,
            modulo="ti",
            titulo="TECNOLOGIA",
            ativo=self.secao,
            grupos_menu=GRUPOS_MENU if self.operador_ti else GRUPOS_PUBLICOS,
            grupos_recolhiveis=True,
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(side="left", fill="both", expand=True, padx=LAYOUT["conteudo_padx"], pady=(22, 20))
        self.conteudo = viewport.conteudo
        if self.secao == "portal":
            self._portal_suporte()
        elif self.secao == "abrir_chamado":
            self._pagina_abrir_chamado()
        elif self.secao == "cockpit":
            self._cockpit()
        elif self.secao in {"rede", "segmentos"}:
            self._rede_interativa()
        elif self.secao == "ativos":
            self._ativos_interativos()
        elif self.secao == "relatorios":
            self._relatorios()
        else:
            self._secao_operacional()

    def abrir_secao(self, secao):
        callback = self.navegacao.get("secao_modulo")
        if callable(callback):
            callback("ti", secao)
            return
        self.container.destroy()
        TelaTecnologia(self.root, self.navegacao, secao=secao)

    def _acoes_cabecalho(self, parent):
        bloco = tk.Frame(parent, bg=CORES["bg"])
        if self.secao in {"portal", "abrir_chamado", "meus_chamados"}:
            criar_botao(bloco, "+  ABRIR CHAMADO", lambda: self.abrir_secao("abrir_chamado"), compacto=True).pack(side="right")
            if self.operador_ti:
                criar_botao(bloco, "◈  COCKPIT", lambda: self.abrir_secao("cockpit"), tipo="secundario", compacto=True).pack(side="right", padx=(0, 8))
            return bloco
        criar_botao(bloco, self._rotulo_novo(), self._nova_acao, compacto=True).pack(side="right")
        criar_botao(bloco, "◈  ANALISAR TI", self._mostrar_analise, tipo="secundario", compacto=True).pack(side="right", padx=(0, 8))
        return bloco

    def _rotulo_novo(self):
        return {
            "portal": "+  ABRIR CHAMADO", "abrir_chamado": "+  ABRIR CHAMADO", "cockpit": "+  ABRIR CHAMADO",
            "chamados": "+  ABRIR CHAMADO", "meus_chamados": "+  ABRIR CHAMADO",
            "ativos": "+  CADASTRAR ATIVO", "segmentos": "+  SEGMENTO",
            "licencas": "+  LICENÇA", "sistemas": "+  SISTEMA",
            "monitoramento": "+  MONITOR", "conhecimento": "+  ARTIGO",
            "contratos": "+  CONTRATO", "mudancas": "+  MUDANÇA",
            "problemas": "+  PROBLEMA", "seguranca": "+  INCIDENTE",
        }.get(self.secao, "+  NOVO REGISTRO")

    def _cabecalho(self, titulo, subtitulo, *, acoes=True):
        criar_cabecalho(
            self.conteudo, titulo, subtitulo,
            acao=self._acoes_cabecalho if acoes else None,
            breadcrumb=f"MÓDULOS  /  TECNOLOGIA  /  {titulo.upper()}",
            etiqueta="IT OPERATIONS 3.0.1",
        )




















    def _visao(self):
        gerar_alertas_tecnologia(SESSAO.usuario)
        self._cabecalho("Tecnologia e serviços", "Centro de operações para atendimento, ativos, infraestrutura, software e governança.")
        resumo = resumo_tecnologia(SESSAO.usuario)
        grade = GradeResponsiva(self.conteudo, max_colunas=4, largura_minima=220, gap=9, bg=CORES["bg"])
        grade.pack(fill="x")
        metricas = (
            ("CHAMADOS ABERTOS", resumo["chamados_abertos"], "◉", f"{resumo['chamados_criticos']} crítico(s)"),
            ("SLA VENCIDO", resumo["sla_vencido"], "!", "Exigem priorização"),
            ("ATIVOS TI", resumo["ativos"], "▣", f"{resumo['online']} online · {resumo['offline']} offline"),
            ("SAÚDE DO AMBIENTE", f"{resumo['saude_percentual']:.1f}%".replace(".", ","), "◎", f"{resumo['manutencao']} em manutenção"),
            ("SISTEMAS INDISPONÍVEIS", resumo["sistemas_indisponiveis"], "≡", "Produção e serviços"),
            ("DISPOSITIVOS NOVOS", resumo["desconhecidos"], "?", "Aguardando identificação"),
            ("LICENÇAS VENCENDO", resumo["licencas_vencendo"], "#", "Próximos 30 dias"),
            ("ALERTAS ABERTOS", resumo["alertas"], "◌", "Infraestrutura e governança"),
        )
        for titulo, valor, icone, detalhe in metricas:
            grade.adicionar(criar_metrica(grade, titulo, valor, icone=icone, cor=COR_TI, detalhe=detalhe))
        self._atalhos()
        self._centro_operacoes(resumo)

    def _atalhos(self):
        card = criar_card(self.conteudo)
        card.pack(fill="x", pady=(13, 0))
        interior = tk.Frame(card, bg=CORES["card"])
        interior.pack(fill="x", padx=17, pady=15)
        criar_titulo_secao(interior, "Acesso rápido", "Ações recorrentes da operação de TI.")
        grade = GradeResponsiva(interior, max_colunas=5, largura_minima=180, gap=8, bg=CORES["card"])
        grade.pack(fill="x")
        atalhos = (
            ("+", "Abrir chamado", "Solicitação, incidente e SLA.", self._novo_chamado),
            ("▣", "Cadastrar ativo", "Patrimônio e configuração.", self._novo_ativo),
            ("◎", "Verificar ambiente", "Monitores, sistemas e alertas.", lambda: self.abrir_secao("monitoramento")),
            ("⌘", "Rede autorizada", "Segmentos e dispositivos.", lambda: self.abrir_secao("segmentos")),
            ("⇄", "Solicitar mudança", "Risco, rollback e aprovação.", self._nova_mudanca),
        )
        for icone, titulo, detalhe, comando in atalhos:
            quadro = criar_card(grade, fundo=CORES["card_secundario"])
            tk.Label(quadro, text=icone, font=("Segoe UI Symbol", 18, "bold"), fg=COR_TI, bg=CORES["card_secundario"]).pack(anchor="w", padx=14, pady=(13, 5))
            tk.Label(quadro, text=titulo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(anchor="w", padx=14)
            tk.Label(quadro, text=detalhe, font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card_secundario"], wraplength=190, justify="left").pack(anchor="w", padx=14, pady=(4, 9))
            criar_botao(quadro, "ABRIR  →", comando, tipo="fantasma", compacto=True).pack(anchor="w", padx=10, pady=(0, 10))
            grade.adicionar(quadro)

    def _centro_operacoes(self, resumo):
        linha = tk.Frame(self.conteudo, bg=CORES["bg"])
        linha.pack(fill="x", pady=(13, 0))
        fila = criar_card(linha)
        fila.pack(side="left", fill="both", expand=True, padx=(0, 8))
        interno = tk.Frame(fila, bg=CORES["card"])
        interno.pack(fill="both", expand=True, padx=17, pady=15)
        criar_titulo_secao(interno, "Fila operacional", "Chamados mais recentes e seu estado atual.")
        chamados = listar_secao("chamados", SESSAO.usuario, limite=6)
        if not chamados:
            tk.Label(interno, text="Nenhum chamado registrado. O ambiente está pronto para receber solicitações.", font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w", pady=15)
        for chamado in chamados:
            item = tk.Frame(interno, bg=CORES["card"])
            item.pack(fill="x", pady=3)
            tk.Label(item, text=f"{chamado['numero']}  ·  {chamado['titulo']}", font=FONTES["texto"], fg=CORES["text"], bg=CORES["card"], anchor="w").pack(side="left", fill="x", expand=True)
            tk.Label(item, text=f"{chamado['prioridade']}  ·  {chamado['status']}", font=FONTES["micro"], fg=COR_TI if chamado["prioridade"] != "Crítica" else CORES["danger"], bg=CORES["card"]).pack(side="right")
        saude = criar_card(linha)
        saude.pack(side="right", fill="both", padx=(8, 0))
        bloco = tk.Frame(saude, bg=CORES["card"], width=290)
        bloco.pack(fill="both", expand=True, padx=18, pady=15)
        bloco.pack_propagate(False)
        criar_titulo_secao(bloco, "Saúde da plataforma", "Sinais operacionais consolidados.")
        tk.Label(bloco, text=f"{resumo['saude_percentual']:.1f}%".replace(".", ","), font=("Inter", 30, "bold"), fg=CORES["success"] if resumo["saude_percentual"] >= 90 else CORES["warning"], bg=CORES["card"]).pack(pady=(10, 2))
        tk.Label(bloco, text=f"{resumo['online']} ativos online · {resumo['alertas']} alerta(s)", font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card"]).pack()

    def _secao_operacional(self):
        titulo = ROTULOS[self.secao]
        self._cabecalho(titulo, SUBTITULOS.get(self.secao, "Operação especializada de Tecnologia."), acoes=self.secao != "auditoria")
        controles = tk.Frame(self.conteudo, bg=CORES["bg"])
        controles.pack(fill="x", pady=(0, 9))
        pesquisa = criar_campo_pesquisa(
            controles, placeholder="Pesquisar nesta seção...", cor_cursor=COR_TI,
            ao_alterar=self._preencher_tabela,
        )
        pesquisa.pack(side="left", fill="x", expand=True, ipady=8)
        criar_botao(controles, "ATUALIZAR", lambda: self.abrir_secao(self.secao), tipo="secundario", compacto=True).pack(side="right", padx=(8, 0))
        area = criar_card(self.conteudo)
        area.pack(fill="both", expand=True)
        colunas = COLUNAS[self.secao]
        self.tabela = ttk.Treeview(area, columns=[x[0] for x in colunas], show="headings", height=22, style="Dark.Treeview")
        for chave, rotulo, largura in colunas:
            self.tabela.heading(chave, text=rotulo)
            self.tabela.column(chave, width=largura, minwidth=60, anchor="w", stretch=True)
        barra_y = ttk.Scrollbar(area, orient="vertical", command=self.tabela.yview, style="Dark.Vertical.TScrollbar")
        barra_x = ttk.Scrollbar(area, orient="horizontal", command=self.tabela.xview, style="Dark.Horizontal.TScrollbar")
        self.tabela.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        area.grid_rowconfigure(0, weight=1)
        area.grid_columnconfigure(0, weight=1)
        self.tabela.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")
        adicionar_divisorias_treeview(self.tabela, cor=CORES["border"])
        self.estado_vazio = criar_estado_vazio(area, "◎", f"Nenhum registro em {titulo}", "Use a ação de cadastro ou aguarde a integração operacional.", cor=COR_TI)
        self.registros = listar_secao(self.secao, SESSAO.usuario)
        self._preencher_tabela()
        self._barra_acoes()

    def _preencher_tabela(self, termo=""):
        if self.tabela is None:
            return
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        termo = termo.strip().lower()
        for registro in self.registros:
            if termo and termo not in " ".join(str(valor).lower() for valor in registro.values()):
                continue
            iid = str(registro.get("id") or len(self.tabela.get_children()) + 1)
            if self.tabela.exists(iid):
                iid += f"-{len(self.tabela.get_children())}"
            self.tabela.insert("", "end", iid=iid, values=tuple(_formatar(registro.get(chave), chave) for chave in self.tabela["columns"]))
        if self.tabela.get_children():
            self.estado_vazio.place_forget()
        else:
            self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.estado_vazio.lift()

    def _registro_selecionado(self):
        if self.tabela is None or not self.tabela.selection():
            messagebox.showwarning("Tecnologia", "Selecione um registro.", parent=self.root)
            return None
        base = int(self.tabela.selection()[0].split("-")[0])
        return next((x for x in self.registros if int(x.get("id") or -1) == base), None)

    def _barra_acoes(self):
        linha = tk.Frame(self.conteudo, bg=CORES["bg"])
        linha.pack(fill="x", pady=(9, 0))
        def botao(texto, comando, tipo="secundario"):
            criar_botao(linha, texto, comando, tipo=tipo, compacto=True).pack(side="left", padx=(0, 5))
        if self.secao in {"chamados", "meus_chamados"}:
            if self.operador_ti:
                botao("INICIAR ATENDIMENTO", lambda: self._mudar_chamado("Em atendimento"), "sucesso")
                botao("AGUARDAR USUÁRIO", lambda: self._mudar_chamado("Aguardando usuário"), "aviso")
                botao("RESOLVER", lambda: self._mudar_chamado("Resolvido"), "sucesso")
                botao("COMENTAR", self._comentar_chamado, "fantasma")
            else:
                botao("+ ABRIR NOVO CHAMADO", lambda: self.abrir_secao("abrir_chamado"), "sucesso")
        elif self.secao == "ativos":
            botao("REGISTRAR HEARTBEAT", self._heartbeat, "sucesso")
            botao("INICIAR MANUTENÇÃO", self._manutencao, "aviso")
            botao("ACESSO REMOTO", self._acesso_remoto, "perigo")
        elif self.secao == "manutencoes":
            botao("CONCLUIR MANUTENÇÃO", self._concluir_manutencao, "sucesso")
        elif self.secao == "segmentos":
            botao("AUTORIZAR DESCOBERTA", self._autorizar_segmento, "aviso")
            botao("REGISTRAR DISPOSITIVO", self._novo_dispositivo, "sucesso")
        elif self.secao == "licencas":
            botao("ATRIBUIR LICENÇA", self._atribuir_licenca, "sucesso")
        elif self.secao == "monitoramento":
            botao("REGISTRAR EVENTO", self._evento_monitor, "sucesso")
        elif self.secao == "mudancas":
            botao("APROVAR", lambda: self._decidir_mudanca("Aprovar"), "sucesso")
            botao("SOLICITAR ALTERAÇÃO", lambda: self._decidir_mudanca("Solicitar alteração"), "aviso")
            botao("REJEITAR", lambda: self._decidir_mudanca("Rejeitar"), "perigo")
        elif self.secao == "alertas":
            botao("MARCAR RESOLVIDO", self._resolver_alerta, "sucesso")












































