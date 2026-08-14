"""Workspace especializado de Tecnologia e Serviços 3.0.1."""

from __future__ import annotations

import webbrowser
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from auth.sessao import SESSAO
from interface.armazenamento_servidor import escolher_destino_gerado, mensagem_arquivo_gerado
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


class TecnologiaAcoesMixin:
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
            tk.Label(linha, text=rotulo.upper(), font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["bg"], width=29, anchor="w").pack(side="left")
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
        formato = (simpledialog.askstring("Relatório", "Formato: csv, json ou html", parent=self.root) or "csv").lower()
        nome = f"tecnologia_{tipo}.{formato}"
        destino, remoto = escolher_destino_gerado(
            parent=self.root, nome_sugerido=nome, titulo="Gerar relatório de Tecnologia",
            defaultextension=f".{formato}", filetypes=((formato.upper(), f"*.{formato}"),),
        )
        if not destino:
            return
        try:
            resultado = gerar_relatorio_tecnologia(tipo, formato, destino, SESSAO.usuario)
            messagebox.showinfo("Relatório", mensagem_arquivo_gerado(resultado, remoto=remoto, nome=nome), parent=self.root)
        except (ValueError, PermissionError, OSError) as erro:
            messagebox.showerror("Relatório", str(erro), parent=self.root)

