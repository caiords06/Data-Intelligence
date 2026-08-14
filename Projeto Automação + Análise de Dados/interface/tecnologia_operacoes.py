"""Workspace especializado de Tecnologia e Serviços 3.0.1."""

from __future__ import annotations

import webbrowser
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

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


class TecnologiaOperacoesMixin:
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
        tk.Label(esquerda, text="Precisa de ajuda?", font=("Inter", 20, "bold"), fg=CORES["text"], bg=CORES["card"]).pack(anchor="w")
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
            tk.Label(linha_item, text=icone, font=("Inter", 9, "bold"), fg=CORES["primary"], bg=CORES["primary_soft"], width=3, pady=4).pack(side="left")
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
            tk.Label(bloco, text=rotulo.upper(), font=("Inter", 9, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w")
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
            tk.Label(bloco, text=rotulo.upper(), font=("Inter", 9, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w")
            combo = ttk.Combobox(bloco, values=valores, state="readonly", style="Dark.TCombobox")
            combo.current(0 if chave == "categoria" else 1)
            combo.pack(fill="x", pady=(4, 0), ipady=5)
            entradas[chave] = combo
        bloco_desc = tk.Frame(corpo, bg=CORES["card"])
        bloco_desc.grid(row=2, column=0, columnspan=2, sticky="ew", pady=6)
        tk.Label(bloco_desc, text="DESCRIÇÃO / SINTOMAS", font=("Inter", 9, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w")
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
        tk.Label(topo, text="SEGMENTO ATIVO", font=("Inter", 9, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(side="left")
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
            tk.Label(bloco, text=titulo.upper(), font=("Inter", 8, "bold"), fg=CORES["text_muted"], bg=CORES["card_secundario"]).pack(anchor="w", padx=11, pady=(8, 2))
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
                from services.servidor_cliente import testar_servidor
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

        criar_botao(botoes, "COPIAR", copiar, tipo="secundario", compacto=True).pack(side="left")
        criar_botao(botoes, "FECHAR", janela.destroy, compacto=True).pack(side="right")

