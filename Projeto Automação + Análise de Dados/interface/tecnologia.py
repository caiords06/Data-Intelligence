"""Workspace especializado de Tecnologia e Serviços 3.0.1."""

from __future__ import annotations

import webbrowser
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from core.nodo import carregar_config_nodo, usa_servidor_remoto
from enterprise.contexto import tem_permissao
from enterprise.contexto import obter_contexto
from enterprise.tecnologia import (
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


class TelaTecnologia:
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
        grupos_base = GRUPOS_MENU if self.operador_ti else GRUPOS_PUBLICOS
        grupos = [
            (grupo, tuple((chave, icone, titulo, lambda destino=chave: self.abrir_secao(destino)) for chave, icone, titulo in itens))
            for grupo, itens in grupos_base
        ]
        grupos.append(("COLABORAÇÃO", (("correio", "✉", "Correio interno", lambda: self.navegacao["correio"]("ti")),)))
        criar_sidebar(
            self.container, self.navegacao, ativo=self.secao,
            grupos_customizados=tuple(grupos), titulo_customizado="TECNOLOGIA",
            rodape_texto="Voltar aos módulos", rodape_comando=self.navegacao.get("modulos"),
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

    def _portal_suporte(self):
        """Portal simples disponível a qualquer usuário autenticado."""
        self._cabecalho(
            "Suporte de Tecnologia",
            "Abra solicitações e acompanhe seus atendimentos. A operação técnica permanece separada e protegida por permissões.",
        )
        hero = criar_card(self.conteudo, destaque=True)
        hero.pack(fill="x")
        corpo = tk.Frame(hero, bg=CORES["card"])
        corpo.pack(fill="x", padx=22, pady=20)
        esquerda = tk.Frame(corpo, bg=CORES["card"])
        esquerda.pack(side="left", fill="x", expand=True)
        tk.Label(esquerda, text="Precisa de ajuda?", font=("Segoe UI", 20, "bold"), fg=CORES["text"], bg=CORES["card"]).pack(anchor="w")
        tk.Label(
            esquerda,
            text="Registre o problema, informe a urgência e acompanhe a resposta da equipe de TI sem precisar acessar ferramentas administrativas.",
            font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["card"], justify="left", wraplength=680,
        ).pack(anchor="w", pady=(6, 0))
        criar_botao(corpo, "+  ABRIR CHAMADO", lambda: self.abrir_secao("abrir_chamado")).pack(side="right", padx=(18, 0))

        linha = tk.Frame(self.conteudo, bg=CORES["bg"])
        linha.pack(fill="x", pady=(12, 0))
        meus = criar_card(linha)
        meus.pack(side="left", fill="both", expand=True, padx=(0, 7))
        dentro = tk.Frame(meus, bg=CORES["card"])
        dentro.pack(fill="both", expand=True, padx=18, pady=16)
        criar_titulo_secao(dentro, "Meus chamados", "Últimas solicitações abertas por você.")
        chamados = listar_secao("meus_chamados", SESSAO.usuario, limite=6)
        if not chamados:
            tk.Label(dentro, text="Nenhum chamado aberto ainda.", font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w", pady=12)
        for chamado in chamados:
            item = tk.Frame(dentro, bg=CORES["card_secundario"])
            item.pack(fill="x", pady=3)
            texto = tk.Frame(item, bg=CORES["card_secundario"])
            texto.pack(side="left", fill="x", expand=True, padx=12, pady=9)
            tk.Label(texto, text=f"{chamado['numero']} · {chamado['titulo']}", font=FONTES["texto"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(anchor="w")
            tk.Label(texto, text=f"{chamado['prioridade']} · {chamado['status']}", font=FONTES["micro"], fg=COR_TI, bg=CORES["card_secundario"]).pack(anchor="w", pady=(2, 0))
        criar_botao(dentro, "VER TODOS", lambda: self.abrir_secao("meus_chamados"), tipo="fantasma", compacto=True).pack(anchor="w", pady=(8, 0))

        status = criar_card(linha)
        status.pack(side="right", fill="both", padx=(7, 0))
        painel = tk.Frame(status, bg=CORES["card"], width=320)
        painel.pack(fill="both", expand=True, padx=18, pady=16)
        criar_titulo_secao(painel, "Canal de atendimento", "O que acontece depois de abrir o chamado.")
        for icone, titulo, detalhe in (
            ("1", "Registro", "O chamado recebe número e SLA."),
            ("2", "Triagem", "A equipe classifica e assume o atendimento."),
            ("3", "Acompanhamento", "Você acompanha o status em Meus chamados."),
        ):
            linha_item = tk.Frame(painel, bg=CORES["card"])
            linha_item.pack(fill="x", pady=5)
            tk.Label(linha_item, text=icone, font=("Segoe UI", 9, "bold"), fg=CORES["primary"], bg=CORES["primary_soft"], width=3, pady=4).pack(side="left")
            textos = tk.Frame(linha_item, bg=CORES["card"])
            textos.pack(side="left", fill="x", expand=True, padx=(9, 0))
            tk.Label(textos, text=titulo, font=FONTES["texto"], fg=CORES["text"], bg=CORES["card"]).pack(anchor="w")
            tk.Label(textos, text=detalhe, font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card"], wraplength=220, justify="left").pack(anchor="w")

    def _pagina_abrir_chamado(self):
        self._cabecalho("Abrir chamado", "Descreva o problema com contexto suficiente para a equipe diagnosticar antes de chegar ao equipamento.")
        card = criar_card(self.conteudo, destaque=True)
        card.pack(fill="x")
        corpo = tk.Frame(card, bg=CORES["card"])
        corpo.pack(fill="x", padx=22, pady=20)
        corpo.grid_columnconfigure(0, weight=1)
        corpo.grid_columnconfigure(1, weight=1)
        entradas = {}

        def campo_texto(rotulo, chave, linha, coluna=0, colspan=1):
            bloco = tk.Frame(corpo, bg=CORES["card"])
            bloco.grid(row=linha, column=coluna, columnspan=colspan, sticky="ew", padx=(0 if coluna == 0 else 7, 7 if coluna == 0 else 0), pady=6)
            tk.Label(bloco, text=rotulo.upper(), font=("Segoe UI", 9, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w")
            entrada = tk.Entry(bloco, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_TI, relief="flat")
            entrada.pack(fill="x", ipady=9, pady=(4, 0))
            entradas[chave] = entrada
            return entrada

        campo_texto("Título", "titulo", 0, 0, 2)
        for coluna, (rotulo, chave, valores) in enumerate((
            ("Categoria", "categoria", ("Acesso", "Hardware", "Software", "Rede", "Sistema", "Segurança", "Serviço")),
            ("Prioridade", "prioridade", ("Baixa", "Média", "Alta", "Crítica")),
        )):
            bloco = tk.Frame(corpo, bg=CORES["card"])
            bloco.grid(row=1, column=coluna, sticky="ew", padx=(0 if coluna == 0 else 7, 7 if coluna == 0 else 0), pady=6)
            tk.Label(bloco, text=rotulo.upper(), font=("Segoe UI", 9, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w")
            combo = ttk.Combobox(bloco, values=valores, state="readonly", style="Dark.TCombobox")
            combo.current(0 if chave == "categoria" else 1)
            combo.pack(fill="x", pady=(4, 0), ipady=5)
            entradas[chave] = combo
        bloco_desc = tk.Frame(corpo, bg=CORES["card"])
        bloco_desc.grid(row=2, column=0, columnspan=2, sticky="ew", pady=6)
        tk.Label(bloco_desc, text="DESCRIÇÃO / SINTOMAS", font=("Segoe UI", 9, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w")
        descricao = tk.Text(bloco_desc, height=8, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_TI, relief="flat", wrap="word", font=FONTES["texto"])
        descricao.pack(fill="x", pady=(4, 0))
        entradas["descricao"] = descricao
        ajuda = tk.Label(
            corpo,
            text="Inclua mensagem de erro, quando começou, se afeta outras pessoas e o nome do computador se souber. Não inclua senhas.",
            font=FONTES["micro"], fg=CORES["text_muted"], bg=CORES["card"], justify="left",
        )
        ajuda.grid(row=3, column=0, columnspan=2, sticky="w", pady=(2, 12))
        botoes = tk.Frame(corpo, bg=CORES["card"])
        botoes.grid(row=4, column=0, columnspan=2, sticky="e")
        criar_botao(botoes, "CANCELAR", lambda: self.abrir_secao("portal"), tipo="fantasma").pack(side="left", padx=(0, 8))

        def salvar():
            dados = {
                "titulo": entradas["titulo"].get().strip(),
                "categoria": entradas["categoria"].get().strip(),
                "prioridade": entradas["prioridade"].get().strip(),
                "descricao": entradas["descricao"].get("1.0", "end").strip(),
                "impacto": "Individual",
                "urgencia": "Normal",
            }
            try:
                chamado_id = criar_chamado(dados, SESSAO.usuario)
                messagebox.showinfo("Chamado aberto", f"Solicitação registrada com sucesso.\nID interno: {chamado_id}", parent=self.root)
                self.abrir_secao("meus_chamados")
            except (ValueError, PermissionError) as erro:
                messagebox.showerror("Abrir chamado", str(erro), parent=self.root)
        criar_botao(botoes, "ABRIR CHAMADO", salvar).pack(side="left")

    def _cockpit(self):
        if not self.operador_ti:
            self.abrir_secao("portal")
            return
        gerar_alertas_tecnologia(SESSAO.usuario)
        self._cabecalho("Centro de Operações de TI", "Cockpit vivo de suporte, rede, ativos, telemetria, disponibilidade e alertas.")
        resumo = resumo_tecnologia(SESSAO.usuario)
        segmentos = listar_secao("segmentos", SESSAO.usuario)
        dispositivos = listar_secao("rede", SESSAO.usuario)
        autorizados = sum(1 for s in segmentos if s.get("autorizado"))
        grade = GradeResponsiva(self.conteudo, max_colunas=5, largura_minima=205, gap=9, bg=CORES["bg"])
        grade.pack(fill="x")
        for titulo, valor, detalhe, icone, cor in (
            ("CHAMADOS ABERTOS", resumo["chamados_abertos"], f"{resumo['chamados_criticos']} críticos", "◉", CORES["warning"]),
            ("ATIVOS GERENCIADOS", resumo["ativos"], f"{resumo['online']} online", "▣", CORES["success"]),
            ("SEGMENTOS", len(segmentos), f"{autorizados} autorizados", "⌘", COR_TI),
            ("DISPOSITIVOS VISTOS", len(dispositivos), f"{resumo['desconhecidos']} sem vínculo", "◎", COR_TI),
            ("ALERTAS", resumo["alertas"], "Exigem investigação", "!", CORES["danger"] if resumo["alertas"] else CORES["success"]),
        ):
            grade.adicionar(criar_metrica(grade, titulo, valor, icone=icone, cor=cor, detalhe=detalhe))

        linha = tk.Frame(self.conteudo, bg=CORES["bg"])
        linha.pack(fill="x", pady=(12, 0))
        rede = criar_card(linha, destaque=True)
        rede.pack(side="left", fill="both", expand=True, padx=(0, 7))
        dentro = tk.Frame(rede, bg=CORES["card"])
        dentro.pack(fill="both", expand=True, padx=18, pady=16)
        criar_titulo_secao(dentro, "Mapa operacional da rede", "Nada é descoberto implicitamente: somente segmentos privados adicionados e autorizados.")
        if not segmentos:
            tk.Label(dentro, text="Nenhum segmento cadastrado. A plataforma não assume sua rede local como padrão.", font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w", pady=(6, 10))
            criar_botao(dentro, "+  ADICIONAR PRIMEIRO SEGMENTO", self._novo_segmento, compacto=True).pack(anchor="w")
        else:
            for segmento in segmentos[:6]:
                encontrados = sum(1 for d in dispositivos if int(d.get("segmento_id") or -1) == int(segmento["id"]))
                item = tk.Frame(dentro, bg=CORES["card_secundario"])
                item.pack(fill="x", pady=3)
                tk.Label(item, text="●" if segmento.get("autorizado") else "○", font=("Segoe UI Symbol", 12, "bold"), fg=CORES["success"] if segmento.get("autorizado") else CORES["warning"], bg=CORES["card_secundario"]).pack(side="left", padx=(11, 7), pady=9)
                tk.Label(item, text=f"{segmento['nome']}  ·  {segmento['cidr']}", font=FONTES["texto"], fg=CORES["text"], bg=CORES["card_secundario"]).pack(side="left", fill="x", expand=True)
                tk.Label(item, text=f"{encontrados} dispositivo(s)", font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["card_secundario"]).pack(side="right", padx=12)
            criar_botao(dentro, "ABRIR REDE AO VIVO  →", lambda: self.abrir_secao("rede"), tipo="fantasma", compacto=True).pack(anchor="w", pady=(8, 0))

        fila = criar_card(linha)
        fila.pack(side="right", fill="both", padx=(7, 0))
        bloco = tk.Frame(fila, bg=CORES["card"], width=365)
        bloco.pack(fill="both", expand=True, padx=18, pady=16)
        criar_titulo_secao(bloco, "Ações imediatas", "Rotinas mais comuns do técnico.")
        for texto, comando, tipo in (
            ("+ ABRIR CHAMADO", lambda: self.abrir_secao("abrir_chamado"), "primario"),
            ("DESCOBRIR DISPOSITIVOS", lambda: self.abrir_secao("rede"), "secundario"),
            ("ATIVOS / ACESSO REMOTO", lambda: self.abrir_secao("ativos"), "secundario"),
            ("SERVICE DESK", lambda: self.abrir_secao("chamados"), "fantasma"),
        ):
            criar_botao(bloco, texto, comando, tipo=tipo, compacto=True).pack(fill="x", pady=3)

    def _rede_interativa(self):
        if not self.operador_ti:
            self.abrir_secao("portal")
            return
        self._cabecalho(
            "Rede ao vivo" if self.secao == "rede" else "Segmentos e firewall",
            "Descubra apenas redes privadas adicionadas por você, monitore conectividade e identifique cada dispositivo antes de vinculá-lo ao patrimônio.",
            acoes=False,
        )
        self.segmentos = listar_secao("segmentos", SESSAO.usuario)
        self.dispositivos = listar_secao("rede", SESSAO.usuario)

        gerencia = criar_card(self.conteudo, destaque=True)
        gerencia.pack(fill="x")
        topo = tk.Frame(gerencia, bg=CORES["card"])
        topo.pack(fill="x", padx=16, pady=14)
        tk.Label(topo, text="SEGMENTO ATIVO", font=("Segoe UI", 9, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(side="left")
        self.segmento_combo = ttk.Combobox(topo, state="readonly", style="Dark.TCombobox", width=36)
        valores = [f"{s['id']} · {s['nome']} · {s['cidr']}" for s in self.segmentos]
        self.segmento_combo.configure(values=valores)
        self.segmento_combo.pack(side="left", padx=(10, 10), ipady=4)
        if valores:
            self.segmento_combo.current(0)
            self._segmento_id = int(self.segmentos[0]["id"])
        self.segmento_combo.bind("<<ComboboxSelected>>", self._trocar_segmento)
        criar_botao(topo, "+ SEGMENTO", self._novo_segmento, compacto=True).pack(side="right")
        criar_botao(topo, "EDITAR", self._editar_segmento, tipo="secundario", compacto=True).pack(side="right", padx=(0, 5))
        criar_botao(topo, "REMOVER", self._remover_segmento, tipo="perigo", compacto=True).pack(side="right", padx=(0, 5))

        self.segmento_info = tk.Frame(gerencia, bg=CORES["card"])
        self.segmento_info.pack(fill="x", padx=16, pady=(0, 14))
        self.info_segmento_labels = {}
        for chave, titulo in (("cidr", "CIDR"), ("gateway", "Gateway"), ("autorizado", "Descoberta"), ("firewall_status", "Firewall local"), ("ultima_varredura_em", "Última descoberta")):
            bloco = tk.Frame(self.segmento_info, bg=CORES["card_secundario"])
            bloco.pack(side="left", fill="x", expand=True, padx=(0, 6))
            tk.Label(bloco, text=titulo.upper(), font=("Segoe UI", 8, "bold"), fg=CORES["text_muted"], bg=CORES["card_secundario"]).pack(anchor="w", padx=11, pady=(8, 2))
            valor = tk.Label(bloco, text="—", font=FONTES["texto"], fg=CORES["text"], bg=CORES["card_secundario"])
            valor.pack(anchor="w", padx=11, pady=(0, 8))
            self.info_segmento_labels[chave] = valor

        acoes = tk.Frame(self.conteudo, bg=CORES["bg"])
        acoes.pack(fill="x", pady=(9, 9))
        criar_botao(acoes, "DESCOBRIR AGORA", self._descobrir_rede_async, tipo="sucesso", compacto=True).pack(side="left", padx=(0, 5))
        criar_botao(acoes, "TESTAR CONECTIVIDADE", self._diagnosticar_rede_async, tipo="secundario", compacto=True).pack(side="left", padx=(0, 5))
        self.botao_autorizar = criar_botao(acoes, "AUTORIZAR DESCOBERTA", self._alternar_autorizacao, tipo="aviso", compacto=True)
        self.botao_autorizar.pack(side="left", padx=(0, 5))
        criar_botao(acoes, "PREPARAR FIREWALL", self._preparar_firewall, tipo="secundario", compacto=True).pack(side="left", padx=(0, 5))
        criar_botao(acoes, "REMOVER REGRA", self._remover_firewall, tipo="fantasma", compacto=True).pack(side="left")
        self.status_rede = tk.Label(acoes, text="", font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["bg"])
        self.status_rede.pack(side="right")

        if not self.segmentos:
            vazio = criar_card(self.conteudo)
            vazio.pack(fill="both", expand=True)
            interno = tk.Frame(vazio, bg=CORES["card"])
            interno.pack(fill="both", expand=True, padx=24, pady=28)
            tk.Label(interno, text="⌘", font=("Segoe UI Symbol", 34, "bold"), fg=COR_TI, bg=CORES["card"]).pack()
            tk.Label(interno, text="Nenhuma rede cadastrada", font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card"]).pack(pady=(10, 4))
            tk.Label(interno, text="A plataforma não escolhe sua LAN automaticamente. Adicione explicitamente o CIDR privado que deseja administrar.", font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["card"], wraplength=650, justify="center").pack()
            criar_botao(interno, "+  ADICIONAR SEGMENTO", self._novo_segmento).pack(pady=(16, 0))
            self._render_segmento_status()
            return

        area = tk.Frame(self.conteudo, bg=CORES["bg"])
        area.pack(fill="both", expand=True)
        area.grid_columnconfigure(0, weight=1)
        area.grid_columnconfigure(1, weight=0, minsize=365)
        area.grid_rowconfigure(0, weight=1)
        esquerda = criar_card(area)
        esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        colunas = (("endereco_ip", "IP", 115), ("hostname", "Hostname", 150), ("endereco_mac", "MAC", 150), ("status", "Status", 105), ("patrimonio", "Ativo", 110), ("tipo_estimado", "Tipo", 110), ("ultima_deteccao", "Última detecção", 145))
        self.tabela = ttk.Treeview(esquerda, columns=[c[0] for c in colunas], show="headings", height=19, style="Dark.Treeview")
        for chave, titulo, largura in colunas:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(chave, width=largura, minwidth=70, anchor="w", stretch=True)
        barra_y = ttk.Scrollbar(esquerda, orient="vertical", command=self.tabela.yview, style="Dark.Vertical.TScrollbar")
        barra_x = ttk.Scrollbar(esquerda, orient="horizontal", command=self.tabela.xview, style="Dark.Horizontal.TScrollbar")
        self.tabela.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        barra_y.pack(side="right", fill="y")
        barra_x.pack(side="bottom", fill="x")
        self.tabela.pack(fill="both", expand=True, padx=1, pady=1)
        self.tabela.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_detalhe_dispositivo())
        adicionar_divisorias_treeview(self.tabela, cor=CORES["border"])

        direita = criar_card(area)
        direita.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        detalhe = tk.Frame(direita, bg=CORES["card"], width=365)
        detalhe.pack(fill="both", expand=True, padx=17, pady=15)
        detalhe.pack_propagate(False)
        criar_titulo_secao(detalhe, "Identidade do dispositivo", "Rede detecta presença; o agente/ativo adiciona informações avançadas.")
        self.detalhe_dispositivo = tk.Frame(detalhe, bg=CORES["card"])
        self.detalhe_dispositivo.pack(fill="both", expand=True)
        self.detalhe_dispositivo_labels = {}
        for chave, titulo in (
            ("endereco_ip", "IP"), ("hostname", "Hostname"), ("endereco_mac", "MAC"), ("segmento_nome", "Segmento"),
            ("status", "Estado na rede"), ("ultimo_ping_ms", "Ping ms"), ("patrimonio", "Patrimônio"),
            ("usuario_responsavel", "Responsável"), ("usuario_sessao", "Usuário da sessão"),
            ("sistema_operacional", "Sistema operacional"), ("versao_sistema", "Versão do SO"),
            ("processador", "Processador"), ("memoria_gb", "RAM GB"), ("armazenamento_gb", "Disco GB"),
            ("cpu_percentual", "CPU %"), ("memoria_percentual", "Memória %"), ("disco_percentual", "Disco %"),
            ("latencia_ms", "Latência agente"), ("agente_versao", "Agente"),
            ("remote_provider", "Acesso remoto"), ("remote_status", "Status remoto"),
        ):
            linha_d = tk.Frame(self.detalhe_dispositivo, bg=CORES["card"])
            linha_d.pack(fill="x", pady=2)
            tk.Label(linha_d, text=titulo, font=FONTES["micro"], fg=CORES["text_muted"], bg=CORES["card"], width=18, anchor="w").pack(side="left")
            valor = tk.Label(linha_d, text="—", font=FONTES["micro"], fg=CORES["text"], bg=CORES["card"], anchor="w", justify="left", wraplength=185)
            valor.pack(side="left", fill="x", expand=True)
            self.detalhe_dispositivo_labels[chave] = valor
        botoes_d = tk.Frame(detalhe, bg=CORES["card"])
        botoes_d.pack(fill="x", pady=(8, 0))
        criar_botao(botoes_d, "IDENTIFICAR", self._editar_dispositivo, tipo="secundario", compacto=True).pack(fill="x", pady=2)
        criar_botao(botoes_d, "VINCULAR A ATIVO", self._vincular_dispositivo, tipo="secundario", compacto=True).pack(fill="x", pady=2)
        criar_botao(botoes_d, "CRIAR ATIVO", self._criar_ativo_dispositivo, tipo="sucesso", compacto=True).pack(fill="x", pady=2)
        criar_botao(botoes_d, "ACESSAR REMOTAMENTE", self._acesso_remoto_dispositivo, tipo="perigo", compacto=True).pack(fill="x", pady=2)
        criar_botao(botoes_d, "REMOVER DA VISÃO", self._remover_dispositivo, tipo="fantasma", compacto=True).pack(fill="x", pady=2)
        self._render_segmento_status()
        self._render_dispositivos_rede()

    def _segmento_atual(self):
        if self._segmento_id is None:
            return None
        return next((x for x in self.segmentos if int(x.get("id") or -1) == int(self._segmento_id)), None)

    def _trocar_segmento(self, _evento=None):
        valor = self.segmento_combo.get().split("·", 1)[0].strip() if hasattr(self, "segmento_combo") else ""
        try:
            self._segmento_id = int(valor)
        except ValueError:
            self._segmento_id = None
        self._render_segmento_status()
        self._render_dispositivos_rede()

    def _render_segmento_status(self):
        segmento = self._segmento_atual()
        if not hasattr(self, "info_segmento_labels"):
            return
        valores = {
            "cidr": segmento.get("cidr") if segmento else "—",
            "gateway": segmento.get("gateway") if segmento and segmento.get("gateway") else "—",
            "autorizado": "Autorizada" if segmento and segmento.get("autorizado") else "Bloqueada",
            "firewall_status": segmento.get("firewall_status") if segmento and segmento.get("firewall_status") else "Não configurado",
            "ultima_varredura_em": segmento.get("ultima_varredura_em") if segmento and segmento.get("ultima_varredura_em") else "Nunca",
        }
        for chave, label in self.info_segmento_labels.items():
            label.configure(text=valores.get(chave, "—"), fg=CORES["success"] if chave == "autorizado" and segmento and segmento.get("autorizado") else CORES["text"])
        if hasattr(self, "botao_autorizar"):
            self.botao_autorizar.configure(text="REVOGAR AUTORIZAÇÃO" if segmento and segmento.get("autorizado") else "AUTORIZAR DESCOBERTA")

    def _render_dispositivos_rede(self):
        if self.tabela is None:
            return
        for iid in self.tabela.get_children():
            self.tabela.delete(iid)
        if self._segmento_id is None:
            return
        filtrados = [x for x in self.dispositivos if int(x.get("segmento_id") or -1) == int(self._segmento_id)]
        self.registros = filtrados
        for item in filtrados:
            valores = tuple(_formatar(item.get(chave), chave) for chave in self.tabela["columns"])
            self.tabela.insert("", "end", iid=str(item["id"]), values=valores)
        filhos = self.tabela.get_children()
        if filhos:
            self.tabela.selection_set(filhos[0])
            self.tabela.focus(filhos[0])
            self._mostrar_detalhe_dispositivo()
        if hasattr(self, "status_rede"):
            online = sum(1 for x in filtrados if x.get("status") == "Online")
            self.status_rede.configure(text=f"{len(filtrados)} conhecido(s) · {online} online")

    def _registro_rede_selecionado(self):
        if self.tabela is None or not self.tabela.selection():
            messagebox.showwarning("Rede", "Selecione um dispositivo.", parent=self.root)
            return None
        iid = int(self.tabela.selection()[0])
        return next((x for x in self.registros if int(x.get("id") or -1) == iid), None)

    def _mostrar_detalhe_dispositivo(self):
        registro = self._registro_rede_selecionado() if self.tabela and self.tabela.selection() else None
        if not registro or not hasattr(self, "detalhe_dispositivo_labels"):
            return
        try:
            detalhe = detalhar_dispositivo_rede(registro["id"], SESSAO.usuario)
        except (ValueError, PermissionError):
            detalhe = registro
        for chave, label in self.detalhe_dispositivo_labels.items():
            valor = detalhe.get(chave)
            if chave == "remote_provider" and detalhe.get("remote_id"):
                valor = f"{detalhe.get('remote_provider') or 'Remoto'} · {detalhe.get('remote_id')}"
            label.configure(text=_formatar(valor, chave))

    def _descobrir_rede_async(self):
        segmento = self._segmento_atual()
        if not segmento:
            messagebox.showwarning("Descoberta", "Cadastre ou selecione um segmento.", parent=self.root)
            return
        if not segmento.get("autorizado"):
            messagebox.showwarning("Descoberta", "Autorize explicitamente este segmento antes de descobrir dispositivos.", parent=self.root)
            return
        self.status_rede.configure(text="Descobrindo dispositivos...")
        contexto = obter_contexto()
        ator = {
            **dict(SESSAO.usuario),
            "_empresa_id": contexto["empresa_id"],
            "_filial_id": contexto["filial_id"],
        }
        def executar():
            try:
                resultado = descobrir_segmento_rede(segmento["id"], ator)
                self._agendar_ui(lambda: self._descoberta_concluida(resultado))
            except Exception as erro:
                self._agendar_ui(lambda e=erro: messagebox.showerror("Descoberta de rede", str(e), parent=self.root))
        threading.Thread(target=executar, daemon=True, name="ti-network-discovery").start()

    def _descoberta_concluida(self, resultado):
        if not self.container.winfo_exists():
            return
        messagebox.showinfo(
            "Descoberta concluída",
            f"CIDR: {resultado['cidr']}\nHosts testados: {resultado['total_testados']}\nRespondendo ICMP: {resultado['online']}\nDetectados: {resultado.get('detectados', len(resultado.get('dispositivos', [])))}\nDuração: {resultado['duracao_segundos']} s",
            parent=self.root,
        )
        self.abrir_secao("rede")

    def _diagnosticar_rede_async(self):
        segmento = self._segmento_atual()
        if not segmento:
            messagebox.showwarning("Conectividade", "Selecione um segmento.", parent=self.root)
            return
        self.status_rede.configure(text="Testando gateway, DNS e Internet...")
        contexto = obter_contexto()
        ator = {
            **dict(SESSAO.usuario),
            "_empresa_id": contexto["empresa_id"],
            "_filial_id": contexto["filial_id"],
        }
        def executar():
            try:
                resultado = diagnosticar_segmento_rede(segmento["id"], ator)
                self._agendar_ui(lambda: self._mostrar_diagnostico(resultado))
            except Exception as erro:
                self._agendar_ui(lambda e=erro: messagebox.showerror("Conectividade", str(e), parent=self.root))
        threading.Thread(target=executar, daemon=True, name="ti-network-diagnostics").start()

    def _mostrar_diagnostico(self, resultado):
        if hasattr(self, "status_rede"):
            self.status_rede.configure(text="Diagnóstico concluído")
        gateway_estado = "OK" if resultado.get("gateway_ok") else ("Sem resposta" if resultado.get("gateway_ok") is False else "Não informado")
        gateway_extra = f" · {resultado.get('gateway_latencia_ms')} ms" if resultado.get("gateway_latencia_ms") is not None else ""
        dns_estado = "OK" if resultado.get("dns_ok") else "Falha"
        dns_extra = f" · {resultado.get('dns_endereco')}" if resultado.get("dns_endereco") else ""
        internet_estado = "OK" if resultado.get("internet_ok") else "Sem conectividade detectada"
        internet_extra = f" · {resultado.get('internet_latencia_ms')} ms" if resultado.get("internet_latencia_ms") is not None else ""
        texto = (
            f"Segmento: {resultado['segmento']} · {resultado['cidr']}\n\n"
            f"Gateway: {gateway_estado}{gateway_extra}\n"
            f"DNS: {dns_estado}{dns_extra}\n"
            f"Internet: {internet_estado}{internet_extra}"
        )
        messagebox.showinfo("Diagnóstico de conectividade", texto, parent=self.root)

    def _ativos_interativos(self):
        if not self.operador_ti:
            self.abrir_secao("portal")
            return
        self._cabecalho("Ativos gerenciados", "Inventário técnico com identidade, usuário, sistema operacional, telemetria e acesso remoto.", acoes=False)
        topo = tk.Frame(self.conteudo, bg=CORES["bg"])
        topo.pack(fill="x", pady=(0, 9))
        pesquisa = tk.Entry(topo, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_TI, relief="flat")
        pesquisa.insert(0, "Pesquisar patrimônio, hostname, usuário ou IP...")
        pesquisa.pack(side="left", fill="x", expand=True, ipady=8)
        criar_botao(topo, "+ ATIVO", self._novo_ativo, compacto=True).pack(side="right", padx=(8, 0))
        criar_botao(topo, "EDITAR", self._editar_ativo, tipo="secundario", compacto=True).pack(side="right", padx=(8, 0))
        criar_botao(topo, "REMOVER", self._remover_ativo, tipo="perigo", compacto=True).pack(side="right", padx=(8, 0))

        area = tk.Frame(self.conteudo, bg=CORES["bg"])
        area.pack(fill="both", expand=True)
        area.grid_columnconfigure(0, weight=1)
        area.grid_columnconfigure(1, weight=0, minsize=390)
        area.grid_rowconfigure(0, weight=1)
        tabela_card = criar_card(area)
        tabela_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        colunas = (("patrimonio", "Patrimônio", 110), ("nome", "Ativo", 190), ("hostname", "Hostname", 125), ("usuario_responsavel", "Responsável", 135), ("endereco_ip", "IP", 110), ("sistema_operacional", "Sistema", 140), ("estado_conectividade", "Conectividade", 120), ("saude_percentual", "Saúde %", 75))
        self.tabela = ttk.Treeview(tabela_card, columns=[c[0] for c in colunas], show="headings", height=20, style="Dark.Treeview")
        for chave, titulo, largura in colunas:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(chave, width=largura, minwidth=70, anchor="w", stretch=True)
        by = ttk.Scrollbar(tabela_card, orient="vertical", command=self.tabela.yview, style="Dark.Vertical.TScrollbar")
        bx = ttk.Scrollbar(tabela_card, orient="horizontal", command=self.tabela.xview, style="Dark.Horizontal.TScrollbar")
        self.tabela.configure(yscrollcommand=by.set, xscrollcommand=bx.set)
        by.pack(side="right", fill="y"); bx.pack(side="bottom", fill="x"); self.tabela.pack(fill="both", expand=True)
        adicionar_divisorias_treeview(self.tabela, cor=CORES["border"])
        self.tabela.bind("<<TreeviewSelect>>", lambda _e: self._mostrar_detalhe_ativo())

        detalhe_card = criar_card(area)
        detalhe_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        detalhe = tk.Frame(detalhe_card, bg=CORES["card"], width=390)
        detalhe.pack(fill="both", expand=True, padx=18, pady=15)
        detalhe.pack_propagate(False)
        criar_titulo_secao(detalhe, "Diagnóstico do ativo", "Dados consolidados do inventário e do último heartbeat do agente.")
        self.detalhe_ativo_labels = {}
        for chave, titulo in (
            ("patrimonio", "Patrimônio"), ("hostname", "Hostname"), ("fqdn", "FQDN"), ("endereco_ip", "IP"), ("endereco_mac", "MAC"),
            ("usuario_responsavel", "Responsável"), ("usuario_sessao", "Usuário da sessão"), ("sistema_operacional", "Sistema"), ("versao_sistema", "Versão do SO"),
            ("processador", "Processador"), ("memoria_gb", "RAM GB"), ("armazenamento_gb", "Disco GB"), ("cpu_percentual", "CPU %"), ("memoria_percentual", "Memória %"),
            ("disco_percentual", "Disco %"), ("latencia_ms", "Latência ms"), ("agente_versao", "Versão agente"), ("agent_status", "Estado agente"),
            ("agent_heartbeat", "Heartbeat agente"), ("ultimo_contato", "Último contato"), ("remote_provider", "Remoto"), ("remote_status", "Status remoto"),
        ):
            linha = tk.Frame(detalhe, bg=CORES["card"]); linha.pack(fill="x", pady=1)
            tk.Label(linha, text=titulo, font=FONTES["micro"], fg=CORES["text_muted"], bg=CORES["card"], width=18, anchor="w").pack(side="left")
            valor = tk.Label(linha, text="—", font=FONTES["micro"], fg=CORES["text"], bg=CORES["card"], anchor="w", justify="left", wraplength=205)
            valor.pack(side="left", fill="x", expand=True); self.detalhe_ativo_labels[chave] = valor
        botoes = tk.Frame(detalhe, bg=CORES["card"]); botoes.pack(fill="x", pady=(8, 0))
        criar_botao(botoes, "ACESSO REMOTO", self._acesso_remoto, tipo="perigo", compacto=True).pack(fill="x", pady=2)
        criar_botao(botoes, "GERAR / ROTACIONAR AGENTE", self._provisionar_agente_ativo, tipo="sucesso", compacto=True).pack(fill="x", pady=2)
        criar_botao(botoes, "REVOGAR AGENTE", self._revogar_agente_ativo, tipo="fantasma", compacto=True).pack(fill="x", pady=2)
        criar_botao(botoes, "REGISTRAR HEARTBEAT", self._heartbeat, tipo="secundario", compacto=True).pack(fill="x", pady=2)
        criar_botao(botoes, "MANUTENÇÃO", self._manutencao, tipo="aviso", compacto=True).pack(fill="x", pady=2)

        self.registros = listar_secao("ativos", SESSAO.usuario)
        def preencher(termo=""):
            for iid in self.tabela.get_children(): self.tabela.delete(iid)
            termo = termo.strip().lower()
            if termo.startswith("pesquisar "): termo = ""
            for item in self.registros:
                if termo and termo not in " ".join(str(v or "").lower() for v in item.values()): continue
                self.tabela.insert("", "end", iid=str(item["id"]), values=tuple(_formatar(item.get(chave), chave) for chave in self.tabela["columns"]))
            filhos = self.tabela.get_children()
            if filhos:
                self.tabela.selection_set(filhos[0])
                self.tabela.focus(filhos[0])
                self._mostrar_detalhe_ativo()
        pesquisa.bind("<KeyRelease>", lambda _e: preencher(pesquisa.get()))
        preencher()

    def _mostrar_detalhe_ativo(self):
        registro = self._registro_selecionado() if self.tabela and self.tabela.selection() else None
        if not registro or not hasattr(self, "detalhe_ativo_labels"):
            return
        try:
            detalhe = detalhar_ativo(registro["id"], SESSAO.usuario)
        except (ValueError, PermissionError):
            detalhe = registro
        for chave, label in self.detalhe_ativo_labels.items():
            valor = detalhe.get(chave)
            if chave == "remote_provider" and detalhe.get("remote_id"):
                valor = f"{detalhe.get('remote_provider') or 'Remoto'} · {detalhe.get('remote_id')}"
            label.configure(text=_formatar(valor, chave))

    def _provisionar_agente_ativo(self):
        registro = self._registro_selecionado() if self.tabela and self.tabela.selection() else None
        if not registro:
            messagebox.showwarning("Agente TI", "Selecione um ativo gerenciado.", parent=self.root)
            return
        if not tem_permissao_tecnologia(SESSAO.usuario, "gerenciar_ativos"):
            messagebox.showerror("Agente TI", "Seu perfil não pode provisionar agentes.", parent=self.root)
            return
        existente = None
        try:
            existente = obter_credencial_agente(registro["id"], SESSAO.usuario)
        except (ValueError, PermissionError):
            pass
        if existente and existente.get("ativo"):
            if not messagebox.askyesno(
                "Rotacionar credencial",
                "Este ativo já possui agente provisionado. Gerar uma nova credencial invalidará o token anterior. Continuar?",
                parent=self.root,
            ):
                return
        try:
            credencial = criar_credencial_agente(registro["id"], SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Agente TI", str(erro), parent=self.root)
            return
        if usa_servidor_remoto():
            cfg = carregar_config_nodo()
            url = str(cfg.servidor_url or "").rstrip("/")
            try:
                from enterprise.servidor_cliente import testar_servidor
                saude = testar_servidor()
                servidor = {
                    "ativo": bool(saude.get("ok") and saude.get("agentes_ti")),
                    "url": url,
                    "erro": None,
                }
            except Exception as erro:
                servidor = {"ativo": False, "url": url, "erro": str(erro)}
        else:
            servidor = status_servidor()
            url = servidor.get("url") or url_lan_sugerida()
        if not servidor.get("ativo"):
            detalhe_erro = str(servidor.get("erro") or "O receptor de agentes TI não está ativo neste momento.")
            messagebox.showwarning(
                "Servidor TI indisponível",
                "A credencial foi gerada, mas o receptor de agentes não está ativo.\n\n"
                f"{detalhe_erro}",
                parent=self.root,
            )
        self._janela_credencial_agente(credencial, url)
        self._mostrar_detalhe_ativo()

    def _revogar_agente_ativo(self):
        registro = self._registro_selecionado() if self.tabela and self.tabela.selection() else None
        if not registro:
            messagebox.showwarning("Agente TI", "Selecione um ativo gerenciado.", parent=self.root)
            return
        try:
            existente = obter_credencial_agente(registro["id"], SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Agente TI", str(erro), parent=self.root)
            return
        if not existente or not existente.get("ativo"):
            messagebox.showinfo("Agente TI", "Este ativo não possui agente ativo.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Revogar agente",
            f"Revogar a credencial do agente de {registro.get('patrimonio') or registro.get('nome')}?\n\nO computador deixará de enviar telemetria até novo provisionamento.",
            parent=self.root,
        ):
            return
        try:
            revogar_credencial_agente(registro["id"], SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Agente TI", str(erro), parent=self.root)
            return
        messagebox.showinfo("Agente TI", "Credencial revogada.", parent=self.root)
        self._mostrar_detalhe_ativo()

    def _janela_credencial_agente(self, credencial: dict, servidor_url: str):
        janela = tk.Toplevel(self.root)
        janela.title("Provisionamento do agente TI")
        janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(
            janela,
            self.root,
            760,
            600,
            minimo=(680, 500),
            modal=True,
        )
        corpo = tk.Frame(janela, bg=CORES["bg"])
        corpo.pack(fill="both", expand=True, padx=22, pady=20)
        tk.Label(corpo, text="AGENTE TI · CREDENCIAL DE INSTALAÇÃO", font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w")
        tk.Label(
            corpo,
            text="O token abaixo é exibido somente agora. Use-o no computador do ativo e apague qualquer arquivo temporário depois da instalação.",
            font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["bg"], justify="left", wraplength=700,
        ).pack(anchor="w", pady=(5, 14))
        privado_http = str(servidor_url).lower().startswith("http://") and "127.0.0.1" not in str(servidor_url) and "localhost" not in str(servidor_url).lower()
        comando = (
            'DataIntelligenceTIAgent.exe configure '
            f'--server-url "{servidor_url}" '
            f'--patrimonio "{credencial["patrimonio"]}" '
            f'--agent-id "{credencial["agent_id"]}" '
            '--provider "AnyDesk"'
            + (' --allow-private-http' if privado_http else '')
        )
        conteudo = (
            f"Servidor: {servidor_url}\n"
            f"Patrimônio: {credencial['patrimonio']}\n"
            f"Agent ID: {credencial['agent_id']}\n"
            f"Token: {credencial['token']}\n\n"
            "Comando de configuração:\n" + comando + "\n\n"
            "Depois execute como Administrador:\n"
            "DataIntelligenceTIAgent.exe once\n"
            "DataIntelligenceTIAgent.exe install\n"
        )
        caixa = tk.Text(corpo, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_TI, relief="flat", wrap="word", height=18)
        caixa.insert("1.0", conteudo)
        caixa.configure(state="disabled")
        caixa.pack(fill="both", expand=True)
        botoes = tk.Frame(corpo, bg=CORES["bg"]); botoes.pack(fill="x", pady=(12, 0))

        def copiar():
            self.root.clipboard_clear(); self.root.clipboard_append(conteudo); self.root.update_idletasks()
            messagebox.showinfo("Agente TI", "Instruções copiadas para a área de transferência.", parent=janela)

        def salvar():
            destino = filedialog.asksaveasfilename(
                parent=janela,
                title="Salvar provisionamento temporário",
                defaultextension=".txt",
                initialfile=f"Agente-{credencial['patrimonio']}.txt",
                filetypes=(("Texto", "*.txt"),),
            )
            if destino:
                with open(destino, "w", encoding="utf-8") as arquivo:
                    arquivo.write(conteudo)
                messagebox.showwarning(
                    "Arquivo temporário",
                    "O arquivo contém um token de autenticação. Transfira-o com cuidado e apague-o depois que o agente for configurado.",
                    parent=janela,
                )

        criar_botao(botoes, "COPIAR", copiar, tipo="secundario", compacto=True).pack(side="left")
        criar_botao(botoes, "SALVAR ARQUIVO TEMPORÁRIO", salvar, tipo="fantasma", compacto=True).pack(side="left", padx=(8, 0))
        criar_botao(botoes, "FECHAR", janela.destroy, compacto=True).pack(side="right")

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
        tk.Label(bloco, text=f"{resumo['saude_percentual']:.1f}%".replace(".", ","), font=("Segoe UI", 30, "bold"), fg=CORES["success"] if resumo["saude_percentual"] >= 90 else CORES["warning"], bg=CORES["card"]).pack(pady=(10, 2))
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

    def _formulario(self, titulo, campos, callback, *, largura=720, atualizar=True, valores_iniciais=None):
        janela = tk.Toplevel(self.root)
        janela.title(titulo)
        janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(janela, self.root, largura, min(850, 200 + len(campos) * 54), minimo=(560, 410))
        viewport = AreaRolavel(janela)
        viewport.pack(fill="both", expand=True, padx=22, pady=18)
        corpo = viewport.conteudo
        tk.Label(corpo, text=titulo, font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", pady=(0, 14))
        entradas = {}
        valores_iniciais = valores_iniciais or {}
        for chave, rotulo, tipo, opcoes in campos:
            linha = tk.Frame(corpo, bg=CORES["bg"])
            linha.pack(fill="x", pady=4)
            tk.Label(linha, text=rotulo.upper(), font=("Segoe UI", 8, "bold"), fg=CORES["text_sec"], bg=CORES["bg"], width=29, anchor="w").pack(side="left")
            if tipo == "opcoes":
                valores = [x[1] if isinstance(x, tuple) else x for x in opcoes]
                campo = ttk.Combobox(linha, values=valores, state="readonly", style="Dark.TCombobox")
                if valores:
                    inicial = valores_iniciais.get(chave)
                    if opcoes and isinstance(opcoes[0], tuple):
                        mapa_rotulos = {identificador: rotulo for identificador, rotulo in opcoes}
                        inicial = mapa_rotulos.get(inicial, inicial)
                    if inicial in valores:
                        campo.set(inicial)
                    else:
                        campo.current(0)
            elif tipo == "booleano":
                variavel = tk.BooleanVar(value=bool(valores_iniciais.get(chave, False)))
                campo = tk.Checkbutton(linha, variable=variavel, bg=CORES["bg"], selectcolor=CORES["input"], activebackground=CORES["bg"])
                campo._variavel = variavel
            else:
                campo = tk.Entry(linha, bg=CORES["input"], fg=CORES["text"], insertbackground=COR_TI, relief="flat")
                if valores_iniciais.get(chave) not in (None, ""):
                    campo.insert(0, str(valores_iniciais.get(chave)))
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
            except (ValueError, PermissionError, OSError) as erro:
                messagebox.showerror("Tecnologia", str(erro), parent=janela)
        criar_botao(corpo, "SALVAR", salvar).pack(anchor="e", pady=(15, 8))
        return janela

    def _usuarios(self):
        return [(x["id"], x["nome"]) for x in listar_usuarios_escopo(SESSAO.usuario)]

    def _ativos(self):
        return [(x["id"], f"{x['patrimonio']} · {x['nome']}") for x in listar_secao("ativos", SESSAO.usuario)]

    def _sistemas(self):
        return [(x["id"], x["nome"]) for x in listar_secao("sistemas", SESSAO.usuario)]

    def _nova_acao(self):
        mapa = {
            "visao": self._novo_chamado, "chamados": self._novo_chamado, "meus_chamados": self._novo_chamado,
            "ativos": self._novo_ativo, "segmentos": self._novo_segmento, "licencas": self._nova_licenca,
            "sistemas": self._novo_sistema, "monitoramento": self._novo_monitor, "conhecimento": self._novo_artigo,
            "contratos": self._novo_contrato, "mudancas": self._nova_mudanca, "problemas": self._novo_problema,
            "seguranca": self._novo_incidente,
        }
        acao = mapa.get(self.secao)
        if acao:
            acao()
        else:
            messagebox.showinfo("Tecnologia", "Esta seção é alimentada pelas operações relacionadas.", parent=self.root)

    def _novo_chamado(self):
        self._formulario("Abrir chamado", (
            ("titulo", "Título", "texto", ()), ("descricao", "Descrição", "texto", ()),
            ("categoria", "Categoria", "opcoes", ("Acesso", "Hardware", "Software", "Rede", "Sistema", "Segurança", "Serviço")),
            ("subcategoria", "Subcategoria", "texto", ()), ("prioridade", "Prioridade", "opcoes", ("Baixa", "Média", "Alta", "Crítica")),
            ("impacto", "Impacto", "opcoes", ("Individual", "Equipe", "Departamento", "Empresa")),
            ("urgencia", "Urgência", "opcoes", ("Baixa", "Normal", "Alta", "Imediata")),
            ("ativo_id", "Ativo relacionado", "opcoes", [("", "Nenhum")] + self._ativos()),
            ("sistema_id", "Sistema relacionado", "opcoes", [("", "Nenhum")] + self._sistemas()),
        ), lambda d: criar_chamado(d, SESSAO.usuario))

    def _novo_ativo(self):
        self._formulario("Cadastrar ativo de TI", (
            ("patrimonio", "Patrimônio", "texto", ()), ("nome", "Nome do ativo", "texto", ()),
            ("tipo", "Tipo", "opcoes", ("Desktop", "Notebook", "Servidor", "Monitor", "Impressora", "Smartphone", "Switch", "Roteador", "Firewall", "Access Point", "Outro")),
            ("fabricante", "Fabricante", "texto", ()), ("modelo", "Modelo", "texto", ()),
            ("numero_serie", "Número de série", "texto", ()), ("hostname", "Hostname", "texto", ()),
            ("endereco_ip", "Endereço IP", "texto", ()), ("endereco_mac", "Endereço MAC", "texto", ()),
            ("sistema_operacional", "Sistema operacional", "texto", ()), ("memoria_gb", "Memória GB", "texto", ()),
            ("armazenamento_gb", "Armazenamento GB", "texto", ()), ("usuario_responsavel_id", "Usuário responsável", "opcoes", [("", "Não atribuído")] + self._usuarios()),
            ("localizacao", "Localização", "texto", ()), ("status", "Status", "opcoes", ("Disponível", "Em uso", "Reserva", "Em manutenção", "Desativado")),
            ("criticidade", "Criticidade", "opcoes", ("Baixa", "Média", "Alta", "Crítica")),
            ("comprado_em", "Compra", "texto", ()), ("garantia_ate", "Garantia até", "texto", ()),
            ("valor", "Valor", "texto", ()), ("remote_provider", "Provedor remoto", "opcoes", ("", "AnyDesk", "TeamViewer", "RustDesk")),
            ("remote_id", "Identificador remoto", "texto", ()),
        ), lambda d: criar_ativo(d, SESSAO.usuario), largura=780)

    def _novo_segmento(self):
        primeiro = self.operador_ti and contar_segmentos_ativos(SESSAO.usuario) == 0

        def salvar(dados):
            segmento_id = criar_segmento_rede(dados, SESSAO.usuario)
            if primeiro and tem_permissao_tecnologia(SESSAO.usuario, "autorizar_descoberta"):
                autorizar = messagebox.askyesno(
                    "Primeiro segmento",
                    "Este é o primeiro segmento da operação de TI.\n\n"
                    "Deseja autorizá-lo agora para descoberta controlada? Nenhuma outra rede será usada automaticamente.",
                    parent=self.root,
                )
                if autorizar:
                    autorizar_segmento_rede(
                        segmento_id,
                        "Primeiro segmento privado cadastrado pelo administrador para descoberta controlada da infraestrutura.",
                        SESSAO.usuario,
                    )
                    preparar = messagebox.askyesno(
                        "Firewall local",
                        "Deseja preparar o Firewall do Windows deste computador?\n\n"
                        "A plataforma NÃO desativará o firewall. Será criada somente uma regra ICMP de entrada, perfil Privado, limitada ao CIDR cadastrado.",
                        parent=self.root,
                    )
                    if preparar:
                        resultado = preparar_firewall_segmento(segmento_id, SESSAO.usuario)
                        messagebox.showinfo("Firewall local", resultado.get("mensagem") or resultado.get("status"), parent=self.root)
            return segmento_id

        self._formulario(
            "Cadastrar segmento de rede",
            (("nome", "Nome", "texto", ()), ("cidr", "Rede CIDR privada", "texto", ()),
             ("vlan", "VLAN", "texto", ()), ("gateway", "Gateway", "texto", ()), ("dns", "DNS", "texto", ())),
            salvar,
        )

    def _editar_segmento(self):
        segmento = self._segmento_atual()
        if not segmento:
            messagebox.showwarning("Segmentos", "Selecione um segmento.", parent=self.root)
            return
        self._formulario(
            "Editar segmento de rede",
            (("nome", "Nome", "texto", ()), ("cidr", "Rede CIDR privada", "texto", ()),
             ("vlan", "VLAN", "texto", ()), ("gateway", "Gateway", "texto", ()), ("dns", "DNS", "texto", ())),
            lambda d: atualizar_segmento_rede(segmento["id"], d, SESSAO.usuario),
            valores_iniciais=segmento,
        )

    def _remover_segmento(self):
        segmento = self._segmento_atual()
        if not segmento:
            messagebox.showwarning("Segmentos", "Selecione um segmento.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Remover segmento",
            f"Arquivar {segmento['nome']} · {segmento['cidr']}?\n\n"
            "Os dispositivos descobertos deixarão a visão operacional, mas a trilha de auditoria será preservada.",
            parent=self.root,
        ):
            return
        try:
            resultado = remover_segmento_rede(segmento["id"], SESSAO.usuario)
            if resultado.get("aviso"):
                messagebox.showwarning("Segmento removido", resultado["aviso"], parent=self.root)
            self.abrir_secao("rede")
        except (ValueError, PermissionError, OSError) as erro:
            messagebox.showerror("Segmentos", str(erro), parent=self.root)

    def _alternar_autorizacao(self):
        segmento = self._segmento_atual()
        if not segmento:
            messagebox.showwarning("Segmentos", "Selecione um segmento.", parent=self.root)
            return
        try:
            if segmento.get("autorizado"):
                if not messagebox.askyesno("Revogar descoberta", "Revogar a autorização de descoberta deste CIDR?", parent=self.root):
                    return
                revogar_autorizacao_segmento_rede(segmento["id"], SESSAO.usuario, "Revogada pela interface de operações de rede.")
            else:
                justificativa = simpledialog.askstring(
                    "Autorizar descoberta",
                    "Justificativa e escopo da autorização:",
                    parent=self.root,
                )
                if not justificativa:
                    return
                autorizar_segmento_rede(segmento["id"], justificativa, SESSAO.usuario)
            self.abrir_secao("rede")
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Segmentos", str(erro), parent=self.root)

    def _preparar_firewall(self):
        segmento = self._segmento_atual()
        if not segmento:
            messagebox.showwarning("Firewall", "Selecione um segmento.", parent=self.root)
            return
        if not messagebox.askyesno(
            "Preparar firewall local",
            f"Criar neste computador uma regra ICMP de entrada limitada a {segmento['cidr']} e somente ao perfil Privado?\n\n"
            "O firewall não será desligado e nenhuma porta de administração remota será aberta.",
            parent=self.root,
        ):
            return
        try:
            resultado = preparar_firewall_segmento(segmento["id"], SESSAO.usuario)
            messagebox.showinfo("Firewall local", resultado.get("mensagem") or resultado.get("status"), parent=self.root)
            self.abrir_secao("rede")
        except (ValueError, PermissionError, OSError) as erro:
            messagebox.showerror("Firewall", str(erro), parent=self.root)

    def _remover_firewall(self):
        segmento = self._segmento_atual()
        if not segmento:
            return
        try:
            remover_firewall_segmento(segmento["id"], SESSAO.usuario)
            self.abrir_secao("rede")
        except Exception as erro:
            messagebox.showerror("Firewall", str(erro), parent=self.root)

    def _editar_dispositivo(self):
        dispositivo = self._registro_rede_selecionado()
        if not dispositivo:
            return
        try:
            detalhe = detalhar_dispositivo_rede(dispositivo["id"], SESSAO.usuario)
        except (ValueError, PermissionError):
            detalhe = dispositivo
        self._formulario(
            "Identificar dispositivo",
            (("hostname", "Hostname", "texto", ()), ("fabricante", "Fabricante", "texto", ()),
             ("tipo_estimado", "Tipo", "opcoes", ("Desktop", "Notebook", "Servidor", "Impressora", "Switch", "Roteador", "Firewall", "Access Point", "Smartphone", "IoT", "Outro")),
             ("observacao", "Observação", "texto", ())),
            lambda d: atualizar_dispositivo_rede(dispositivo["id"], d, SESSAO.usuario),
            valores_iniciais=detalhe,
        )

    def _vincular_dispositivo(self):
        dispositivo = self._registro_rede_selecionado()
        if not dispositivo:
            return
        ativos = self._ativos()
        if not ativos:
            messagebox.showinfo("Vincular ativo", "Nenhum ativo cadastrado. Use CRIAR ATIVO para cadastrar este dispositivo.", parent=self.root)
            return
        self._formulario(
            "Vincular dispositivo a ativo",
            (("ativo_id", "Ativo", "opcoes", ativos),),
            lambda d: vincular_dispositivo_ativo(dispositivo["id"], int(d["ativo_id"]), SESSAO.usuario),
        )

    def _criar_ativo_dispositivo(self):
        dispositivo = self._registro_rede_selecionado()
        if not dispositivo:
            return
        try:
            detalhe = detalhar_dispositivo_rede(dispositivo["id"], SESSAO.usuario)
        except (ValueError, PermissionError):
            detalhe = dispositivo
        iniciais = {
            "nome": detalhe.get("hostname") or f"Dispositivo {detalhe.get('endereco_ip')}",
            "tipo": detalhe.get("tipo_estimado") or "Desktop",
            "hostname": detalhe.get("hostname") or "",
            "endereco_ip": detalhe.get("endereco_ip") or "",
            "endereco_mac": detalhe.get("endereco_mac") or "",
        }
        criado = {"id": None}
        def salvar(d):
            ativo_id = criar_ativo(d, SESSAO.usuario)
            vincular_dispositivo_ativo(dispositivo["id"], ativo_id, SESSAO.usuario)
            criado["id"] = ativo_id
        self._formulario(
            "Criar ativo a partir do dispositivo",
            (("patrimonio", "Patrimônio", "texto", ()), ("nome", "Nome do ativo", "texto", ()),
             ("tipo", "Tipo", "opcoes", ("Desktop", "Notebook", "Servidor", "Impressora", "Switch", "Roteador", "Firewall", "Access Point", "Smartphone", "Outro")),
             ("hostname", "Hostname", "texto", ()), ("endereco_ip", "IP", "texto", ()), ("endereco_mac", "MAC", "texto", ()),
             ("remote_provider", "Provedor remoto", "opcoes", ("", "AnyDesk", "TeamViewer", "RustDesk")),
             ("remote_id", "Identificador remoto", "texto", ())),
            salvar,
            valores_iniciais=iniciais,
        )

    def _remover_dispositivo(self):
        dispositivo = self._registro_rede_selecionado()
        if not dispositivo:
            return
        if not messagebox.askyesno("Remover dispositivo", f"Remover {dispositivo.get('endereco_ip')} da visão operacional?", parent=self.root):
            return
        try:
            remover_dispositivo_rede(dispositivo["id"], SESSAO.usuario)
            self.abrir_secao("rede")
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Rede", str(erro), parent=self.root)

    def _acesso_remoto_dispositivo(self):
        dispositivo = self._registro_rede_selecionado()
        if not dispositivo:
            return
        try:
            detalhe = detalhar_dispositivo_rede(dispositivo["id"], SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Acesso remoto", str(erro), parent=self.root)
            return
        if not detalhe.get("ativo_id"):
            messagebox.showwarning("Acesso remoto", "Vincule o dispositivo a um ativo antes de iniciar acesso remoto.", parent=self.root)
            return
        try:
            ativo = detalhar_ativo(int(detalhe["ativo_id"]), SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Acesso remoto", str(erro), parent=self.root)
            return
        self._acesso_remoto_registro(ativo)

    def _editar_ativo(self):
        ativo = self._registro_selecionado()
        if not ativo:
            return
        try:
            detalhe = detalhar_ativo(ativo["id"], SESSAO.usuario)
        except (ValueError, PermissionError):
            detalhe = ativo
        self._formulario(
            f"Editar ativo {ativo.get('patrimonio')}",
            (("nome", "Nome", "texto", ()), ("tipo", "Tipo", "opcoes", ("Desktop", "Notebook", "Servidor", "Monitor", "Impressora", "Smartphone", "Switch", "Roteador", "Firewall", "Access Point", "Outro")),
             ("fabricante", "Fabricante", "texto", ()), ("modelo", "Modelo", "texto", ()), ("numero_serie", "Número de série", "texto", ()),
             ("hostname", "Hostname", "texto", ()), ("endereco_ip", "IP", "texto", ()), ("endereco_mac", "MAC", "texto", ()),
             ("sistema_operacional", "Sistema operacional", "texto", ()), ("processador", "Processador", "texto", ()),
             ("memoria_gb", "Memória GB", "texto", ()), ("armazenamento_gb", "Armazenamento GB", "texto", ()),
             ("usuario_responsavel_id", "Usuário responsável", "opcoes", [("", "Não atribuído")] + self._usuarios()),
             ("localizacao", "Localização", "texto", ()), ("status", "Status", "opcoes", ("Disponível", "Em uso", "Reserva", "Em manutenção", "Desativado")),
             ("criticidade", "Criticidade", "opcoes", ("Baixa", "Média", "Alta", "Crítica")),
             ("remote_provider", "Provedor remoto", "opcoes", ("", "AnyDesk", "TeamViewer", "RustDesk")), ("remote_id", "ID remoto", "texto", ())),
            lambda d: atualizar_ativo(ativo["id"], d, SESSAO.usuario),
            largura=800,
            valores_iniciais=detalhe,
        )

    def _remover_ativo(self):
        ativo = self._registro_selecionado()
        if not ativo:
            return
        if not messagebox.askyesno("Remover ativo", f"Arquivar o ativo {ativo.get('patrimonio')} · {ativo.get('nome')}?", parent=self.root):
            return
        try:
            remover_ativo(ativo["id"], SESSAO.usuario)
            self.abrir_secao("ativos")
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Ativos", str(erro), parent=self.root)

    def _nova_licenca(self):
        self._formulario("Cadastrar licença", (
            ("nome", "Nome", "texto", ()), ("tipo", "Tipo", "opcoes", ("Assinatura", "Perpétua", "Usuário", "Dispositivo", "Volume")),
            ("quantidade_contratada", "Quantidade contratada", "texto", ()), ("custo", "Custo", "texto", ()),
            ("periodicidade", "Periodicidade", "opcoes", ("Mensal", "Anual", "Único")),
            ("inicio_em", "Início", "texto", ()), ("vencimento_em", "Vencimento", "texto", ()),
            ("renovacao_automatica", "Renovação automática", "booleano", ()),
        ), lambda d: criar_licenca(d, SESSAO.usuario))

    def _novo_sistema(self):
        self._formulario("Cadastrar sistema", (
            ("nome", "Nome", "texto", ()), ("descricao", "Descrição", "texto", ()),
            ("ambiente", "Ambiente", "opcoes", ("Produção", "Homologação", "Desenvolvimento", "Teste")),
            ("criticidade", "Criticidade", "opcoes", ("Baixa", "Média", "Alta", "Crítica")),
            ("status", "Status", "opcoes", ("Operacional", "Degradado", "Indisponível", "Manutenção")),
            ("versao", "Versão", "texto", ()), ("url", "URL", "texto", ()),
            ("servidor_ativo_id", "Servidor", "opcoes", [("", "Não relacionado")] + self._ativos()),
            ("responsavel_ti_id", "Responsável TI", "opcoes", [("", "Não atribuído")] + self._usuarios()),
            ("sla_disponibilidade", "SLA de disponibilidade %", "texto", ()),
        ), lambda d: criar_sistema(d, SESSAO.usuario))

    def _novo_monitor(self):
        self._formulario("Cadastrar monitor", (
            ("nome", "Nome", "texto", ()), ("tipo", "Tipo", "opcoes", ("CPU", "Memória", "Disco", "Latência", "Disponibilidade", "Serviço", "Backup", "API")),
            ("ativo_id", "Ativo", "opcoes", [("", "Nenhum")] + self._ativos()),
            ("sistema_id", "Sistema", "opcoes", [("", "Nenhum")] + self._sistemas()),
            ("alvo", "Alvo / endpoint", "texto", ()), ("intervalo_segundos", "Intervalo em segundos", "texto", ()),
            ("limite_aviso", "Limite de aviso", "texto", ()), ("limite_critico", "Limite crítico", "texto", ()),
        ), lambda d: criar_monitor(d, SESSAO.usuario))

    def _novo_artigo(self):
        self._formulario("Novo artigo de conhecimento", (
            ("titulo", "Título", "texto", ()), ("categoria", "Categoria", "texto", ()),
            ("resumo", "Resumo", "texto", ()), ("conteudo", "Conteúdo", "texto", ()),
            ("palavras_chave", "Palavras-chave", "texto", ()), ("status", "Status", "opcoes", ("Rascunho", "Em revisão", "Publicado", "Arquivado")),
        ), lambda d: criar_artigo_conhecimento(d, SESSAO.usuario))

    def _novo_contrato(self):
        self._formulario("Novo contrato de Tecnologia", (
            ("numero", "Número", "texto", ()), ("titulo", "Título", "texto", ()),
            ("tipo", "Tipo", "opcoes", ("Software", "Suporte", "Internet", "Cloud", "Telefonia", "Manutenção", "Outro")),
            ("inicio_em", "Início", "texto", ()), ("termino_em", "Término", "texto", ()),
            ("valor", "Valor", "texto", ()), ("periodicidade", "Periodicidade", "opcoes", ("Mensal", "Anual", "Único")),
            ("sla", "SLA contratual", "texto", ()), ("renovacao_automatica", "Renovação automática", "booleano", ()),
            ("responsavel_id", "Responsável", "opcoes", [("", "Não atribuído")] + self._usuarios()),
        ), lambda d: criar_contrato(d, SESSAO.usuario))

    def _nova_mudanca(self):
        self._formulario("Solicitar mudança", (
            ("titulo", "Título", "texto", ()), ("descricao", "Descrição", "texto", ()),
            ("motivo", "Motivo", "texto", ()), ("risco", "Risco", "opcoes", ("Baixo", "Médio", "Alto", "Crítico")),
            ("impacto", "Impacto", "texto", ()), ("plano_execucao", "Plano de execução", "texto", ()),
            ("plano_rollback", "Plano de rollback", "texto", ()), ("janela_inicio", "Início da janela", "texto", ()),
            ("janela_fim", "Fim da janela", "texto", ()), ("responsavel_id", "Responsável", "opcoes", self._usuarios()),
        ), lambda d: criar_mudanca(d, SESSAO.usuario))

    def _novo_problema(self):
        self._formulario("Registrar problema", (
            ("titulo", "Título", "texto", ()), ("descricao", "Descrição", "texto", ()),
            ("impacto", "Impacto", "texto", ()), ("causa_raiz", "Causa raiz", "texto", ()),
            ("workaround", "Workaround", "texto", ()), ("solucao_definitiva", "Solução definitiva", "texto", ()),
            ("responsavel_id", "Responsável", "opcoes", [("", "Não atribuído")] + self._usuarios()),
            ("status", "Status", "opcoes", ("Investigando", "Causa identificada", "Solução em andamento", "Resolvido", "Encerrado")),
        ), lambda d: criar_problema(d, SESSAO.usuario))

    def _novo_incidente(self):
        self._formulario("Registrar incidente de segurança", (
            ("titulo", "Título", "texto", ()), ("tipo", "Tipo", "opcoes", ("Malware", "Acesso indevido", "Phishing", "Vulnerabilidade", "Vazamento", "Dispositivo desconhecido", "Outro")),
            ("severidade", "Severidade", "opcoes", ("Baixa", "Média", "Alta", "Crítica")),
            ("descricao", "Descrição", "texto", ()), ("contencao", "Contenção", "texto", ()),
            ("ativo_id", "Ativo", "opcoes", [("", "Nenhum")] + self._ativos()),
            ("sistema_id", "Sistema", "opcoes", [("", "Nenhum")] + self._sistemas()),
            ("responsavel_id", "Responsável", "opcoes", [("", "Não atribuído")] + self._usuarios()),
        ), lambda d: criar_incidente_seguranca(d, SESSAO.usuario))

    def _mudar_chamado(self, status):
        registro = self._registro_selecionado()
        if not registro:
            return
        dados = {"status": status}
        if status == "Resolvido":
            dados["solucao"] = simpledialog.askstring("Resolver chamado", "Solução aplicada:", parent=self.root) or ""
            if not dados["solucao"]:
                return
        try:
            atualizar_chamado(registro["id"], dados, SESSAO.usuario)
            self.abrir_secao(self.secao)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Chamado", str(erro), parent=self.root)

    def _comentar_chamado(self):
        registro = self._registro_selecionado()
        if not registro:
            return
        comentario = simpledialog.askstring("Chamado", "Comentário:", parent=self.root)
        if comentario:
            try:
                adicionar_comentario(registro["id"], comentario, SESSAO.usuario, interno=False)
                self.abrir_secao(self.secao)
            except (ValueError, PermissionError) as erro:
                messagebox.showerror("Chamado", str(erro), parent=self.root)

    def _heartbeat(self):
        ativo = self._registro_selecionado()
        if not ativo:
            return
        self._formulario("Registrar heartbeat do agente", (
            ("cpu_percentual", "CPU %", "texto", ()), ("memoria_percentual", "Memória %", "texto", ()),
            ("disco_percentual", "Disco %", "texto", ()), ("espaco_livre_gb", "Espaço livre GB", "texto", ()),
            ("uptime_segundos", "Uptime em segundos", "texto", ()), ("latencia_ms", "Latência ms", "texto", ()),
            ("agente_versao", "Versão do agente", "texto", ()), ("endereco_ip", "IP atual", "texto", ()),
        ), lambda d: registrar_heartbeat(ativo["id"], d, SESSAO.usuario))

    def _manutencao(self):
        ativo = self._registro_selecionado()
        if not ativo:
            return
        self._formulario("Iniciar manutenção", (
            ("problema", "Problema", "texto", ()), ("previsao", "Previsão", "texto", ()),
        ), lambda d: iniciar_manutencao(ativo["id"], d["problema"], SESSAO.usuario, previsao=d["previsao"]))

    def _concluir_manutencao(self):
        manutencao = self._registro_selecionado()
        if not manutencao:
            return
        self._formulario("Concluir manutenção", (
            ("diagnostico", "Diagnóstico e serviço", "texto", ()), ("custo", "Custo", "texto", ()),
        ), lambda d: concluir_manutencao(manutencao["id"], d["diagnostico"], SESSAO.usuario, custo=d["custo"]))

    def _autorizar_segmento(self):
        segmento = self._registro_selecionado()
        if not segmento:
            return
        justificativa = simpledialog.askstring("Autorizar descoberta", "Justificativa e escopo da autorização:", parent=self.root)
        if justificativa:
            try:
                autorizar_segmento_rede(segmento["id"], justificativa, SESSAO.usuario)
                self.abrir_secao("segmentos")
            except (ValueError, PermissionError) as erro:
                messagebox.showerror("Rede", str(erro), parent=self.root)

    def _novo_dispositivo(self):
        segmento = self._registro_selecionado()
        if not segmento:
            return
        self._formulario("Registrar dispositivo observado", (
            ("endereco_ip", "Endereço IP", "texto", ()), ("endereco_mac", "Endereço MAC", "texto", ()),
            ("hostname", "Hostname", "texto", ()), ("fabricante", "Fabricante", "texto", ()),
            ("tipo_estimado", "Tipo estimado", "texto", ()), ("status", "Status", "opcoes", ("Novo", "Online", "Offline", "Desconhecido")),
            ("origem", "Origem", "opcoes", ("Agente", "SNMP", "Importação", "Conector autorizado")),
        ), lambda d: registrar_dispositivo_descoberto(segmento["id"], d, SESSAO.usuario))

    def _atribuir_licenca(self):
        licenca = self._registro_selecionado()
        if not licenca:
            return
        self._formulario("Atribuir licença", (
            ("usuario_id", "Usuário", "opcoes", [("", "Não definido")] + self._usuarios()),
            ("ativo_id", "Ativo", "opcoes", [("", "Não definido")] + self._ativos()),
            ("identificador", "Identificador externo", "texto", ()),
        ), lambda d: atribuir_licenca(licenca["id"], SESSAO.usuario, usuario_id=d["usuario_id"] or None, ativo_id=d["ativo_id"] or None, identificador=d["identificador"] or None))

    def _evento_monitor(self):
        monitor = self._registro_selecionado()
        if not monitor:
            return
        self._formulario("Registrar evento de monitoramento", (
            ("status", "Status", "opcoes", ("Operacional", "Aviso", "Crítico", "Indisponível", "Sem dados")),
            ("valor", "Valor", "texto", ()), ("mensagem", "Mensagem", "texto", ()),
        ), lambda d: registrar_evento_monitoramento(monitor["id"], d["status"], SESSAO.usuario, valor=d["valor"], mensagem=d["mensagem"]))

    def _decidir_mudanca(self, decisao):
        mudanca = self._registro_selecionado()
        if not mudanca:
            return
        observacao = simpledialog.askstring("Mudança", "Justificativa da decisão:", parent=self.root) or "Decisão registrada na interface."
        try:
            decidir_mudanca(mudanca["id"], decisao, SESSAO.usuario, observacao)
            self.abrir_secao("mudancas")
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Mudança", str(erro), parent=self.root)

    def _resolver_alerta(self):
        alerta = self._registro_selecionado()
        if not alerta:
            return
        try:
            resolver_alerta(alerta["id"], SESSAO.usuario)
            self.abrir_secao("alertas")
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Alerta", str(erro), parent=self.root)

    def _acesso_remoto(self):
        ativo = self._registro_selecionado()
        if ativo:
            self._acesso_remoto_registro(ativo)

    def _acesso_remoto_registro(self, ativo):
        if not tem_permissao_tecnologia(SESSAO.usuario, "acessar_remotamente"):
            messagebox.showerror("Acesso remoto", "Seu perfil não possui permissão para iniciar sessões remotas.", parent=self.root)
            return
        provedor = ativo.get("remote_provider") or simpledialog.askstring("Acesso remoto", "Provedor: AnyDesk, TeamViewer ou RustDesk", parent=self.root)
        if not provedor:
            return
        justificativa = simpledialog.askstring("Acesso remoto", "Justificativa operacional:", parent=self.root)
        if not justificativa:
            return
        confirmado = messagebox.askyesno(
            "Consentimento e auditoria",
            "Confirma que o acesso foi autorizado, possui consentimento aplicável e será auditado?",
            parent=self.root,
        )
        if not confirmado:
            return
        try:
            sessao = solicitar_acesso_remoto(ativo["id"], provedor, justificativa, SESSAO.usuario, consentimento=True)
            if messagebox.askyesno("Acesso remoto", f"Sessão #{sessao['acesso_id']} registrada. Abrir {provedor} agora?", parent=self.root):
                webbrowser.open(sessao["destino"])
            resultado = simpledialog.askstring("Encerrar sessão", "Ao concluir, registre o resultado do atendimento:", parent=self.root)
            if resultado is not None:
                encerrar_acesso_remoto(sessao["acesso_id"], resultado, SESSAO.usuario)
            if self.container.winfo_exists():
                self.abrir_secao("acessos")
        except (ValueError, PermissionError, OSError) as erro:
            messagebox.showerror("Acesso remoto", str(erro), parent=self.root)

    def _mostrar_analise(self):
        try:
            resultado = analisar_tecnologia(SESSAO.usuario)
            texto = "ANÁLISE OPERACIONAL DE TECNOLOGIA\n\n" + "\n\n".join(f"• {x}" for x in resultado["pontos_atencao"])
            messagebox.showinfo("Data Intelligence · Tecnologia", texto, parent=self.root)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Tecnologia", str(erro), parent=self.root)

    def _relatorios(self):
        self._cabecalho("Relatórios de Tecnologia", "Exporte dados operacionais para auditoria, gestão e análise.", acoes=False)
        grade = GradeResponsiva(self.conteudo, max_colunas=3, largura_minima=270, gap=10, bg=CORES["bg"])
        grade.pack(fill="x")
        for tipo, titulo, detalhe in (
            ("chamados", "Service Desk", "Chamados, prioridade, SLA, solicitante e atendimento."),
            ("ativos", "Ativos / CMDB", "Patrimônio, responsável, saúde e conectividade."),
            ("licencas", "Licenças", "Contratação, utilização, custo e vencimento."),
            ("sistemas", "Sistemas", "Criticidade, ambiente, status, responsável e SLA."),
            ("alertas", "Alertas", "Ocorrências operacionais e tratamento."),
            ("auditoria", "Auditoria", "Ações, recursos, usuários e evidências."),
        ):
            card = criar_card(grade)
            tk.Label(card, text=titulo, font=FONTES["subtitulo"], fg=CORES["text"], bg=CORES["card"]).pack(anchor="w", padx=16, pady=(16, 5))
            tk.Label(card, text=detalhe, font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["card"], wraplength=260, justify="left").pack(anchor="w", padx=16, pady=(0, 12))
            criar_botao(card, "EXPORTAR", lambda alvo=tipo: self._exportar(alvo), tipo="secundario", compacto=True).pack(anchor="w", padx=14, pady=(0, 14))
            grade.adicionar(card)

    def _exportar(self, tipo):
        formato = simpledialog.askstring("Relatório", "Formato: csv, json ou html", parent=self.root) or "csv"
        destino = filedialog.asksaveasfilename(parent=self.root, defaultextension=f".{formato.lower()}", filetypes=((formato.upper(), f"*.{formato.lower()}"),))
        if not destino:
            return
        try:
            caminho = gerar_relatorio_tecnologia(tipo, formato, destino, SESSAO.usuario)
            messagebox.showinfo("Relatório", f"Relatório gerado em:\n{caminho}", parent=self.root)
        except (ValueError, PermissionError, OSError) as erro:
            messagebox.showerror("Relatório", str(erro), parent=self.root)
