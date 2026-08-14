"""Central funcional de tarefas, documentos, automações e governança V8."""

from __future__ import annotations
from core.versao import VERSAO_INTERFACE

import json
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from auth.autenticacao import obter_usuarios
from auth.sessao import SESSAO
from interface.armazenamento_servidor import mensagem_arquivo_gerado
from services.catalogo import MODULOS
from services.ferramentas import (
    arquivar_documento,
    arquivar_tarefa,
    atualizar_status_tarefa,
    criar_tarefa,
    gerar_relatorio,
    listar_auditoria,
    listar_documentos,
    listar_relatorios,
    listar_tarefas,
    obter_arquivo_relatorio,
    registrar_documento,
    registrar_uso_ferramenta,
    verificar_documento,
)
from services.integracoes import (
    PROVEDORES_SUPORTADOS,
    definir_integracao_ativa,
    listar_integracoes,
    registrar_integracao,
)
from services.workflows import (
    criar_workflow,
    definir_workflow_ativo,
    listar_workflows,
)
from interface.componentes import (
    AreaRolavel,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_estado_vazio,
    criar_sidebar,
    preparar_janela_secundaria,
)
from interface.tema import (
    CORES,
    FONTES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


FERRAMENTAS = {
    "tarefas": {
        "titulo": "Central de tarefas",
        "subtitulo": "Acompanhe responsabilidades, prioridades e vencimentos do contexto atual.",
        "icone": "✓",
        "admin": False,
    },
    "documentos": {
        "titulo": "Central de documentos",
        "subtitulo": "Registre arquivos corporativos com classificação e verificação de integridade.",
        "icone": "▤",
        "admin": False,
    },
    "workflows": {
        "titulo": "Workflow Builder",
        "subtitulo": "Crie regras seguras para notificações e automações internas.",
        "icone": "↻",
        "admin": True,
    },
    "integracoes": {
        "titulo": "Integration Hub",
        "subtitulo": "Cadastre conectores sem armazenar segredos diretamente no banco.",
        "icone": "∞",
        "admin": True,
    },
    "relatorios": {
        "titulo": "Central de relatórios",
        "subtitulo": "Gere saídas HTML, CSV ou JSON a partir dos dados operacionais autorizados.",
        "icone": "▥",
        "admin": False,
    },
    "auditoria": {
        "titulo": "Auditoria empresarial",
        "subtitulo": "Consulte a trilha de alterações por usuário, módulo e entidade.",
        "icone": "◉",
        "admin": True,
    },
}


class TelaFerramentaCorporativa:
    def __init__(self, root, navegacao, ferramenta):
        if ferramenta not in FERRAMENTAS:
            raise ValueError("Ferramenta corporativa desconhecida.")
        self.root = root
        self.navegacao = navegacao
        self.ferramenta = ferramenta
        self.config = FERRAMENTAS[ferramenta]
        if self.config["admin"] and not SESSAO.eh_admin():
            raise PermissionError("Esta ferramenta é restrita a administradores.")
        self.registros: list[dict] = []
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        registrar_uso_ferramenta(ferramenta, SESSAO.usuario)
        self.criar_interface()

    def criar_interface(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar(
            self.container,
            self.navegacao,
            # Esta tela não representa a Visão geral. Como as ferramentas
            # corporativas ainda não possuem item próprio no menu global,
            # deixamos a sidebar sem destaque falso.
            ativo="",
            rodape_texto="Voltar à central",
            rodape_comando=self.navegacao.get("inicio"),
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(
            side="left",
            fill="both",
            expand=True,
            padx=LAYOUT["conteudo_padx"],
            pady=(23, 21),
        )
        conteudo = viewport.conteudo

        def acoes(area):
            bloco = tk.Frame(area, bg=CORES["bg"])
            criar_botao(
                bloco,
                "ATUALIZAR",
                self.carregar,
                tipo="secundario",
                compacto=True,
            ).pack(side="right")
            if self.ferramenta != "auditoria":
                criar_botao(
                    bloco,
                    "+  NOVO",
                    self.novo,
                    compacto=True,
                ).pack(side="right", padx=(0, 8))
            return bloco
        criar_cabecalho(
            conteudo,
            self.config["titulo"],
            self.config["subtitulo"],
            acao=acoes,
            breadcrumb=f"CENTRAL DA APLICAÇÃO  /  {self.config['titulo'].upper()}",
            etiqueta=f"FUNCIONAL {VERSAO_INTERFACE}",
        )
        self._criar_tabela(conteudo)
        self.carregar()

    def _definicoes_colunas(self):
        mapas = {
            "tarefas": (
                ("titulo", "TAREFA", 260),
                ("modulo", "MÓDULO", 110),
                ("responsavel", "RESPONSÁVEL", 150),
                ("prioridade", "PRIORIDADE", 95),
                ("status", "STATUS", 115),
                ("vencimento", "VENCIMENTO", 110),
            ),
            "documentos": (
                ("titulo", "DOCUMENTO", 260),
                ("modulo", "MÓDULO", 115),
                ("tipo", "TIPO", 85),
                ("classificacao", "CLASSIFICAÇÃO", 120),
                ("autor", "AUTOR", 150),
                ("criado", "REGISTRO", 135),
            ),
            "workflows": (
                ("nome", "WORKFLOW", 280),
                ("modulo", "MÓDULO", 120),
                ("evento", "EVENTO", 180),
                ("acoes", "AÇÕES", 180),
                ("status", "STATUS", 100),
            ),
            "integracoes": (
                ("nome", "INTEGRAÇÃO", 280),
                ("provedor", "PROVEDOR", 150),
                ("credencial", "REFERÊNCIA SEGURA", 240),
                ("sincronizacao", "ÚLTIMA SINCRONIZAÇÃO", 170),
                ("status", "STATUS", 100),
            ),
            "relatorios": (
                ("titulo", "RELATÓRIO", 300),
                ("modulo", "MÓDULO", 140),
                ("formato", "FORMATO", 100),
                ("status", "STATUS", 110),
                ("arquivo", "ARQUIVO", 320),
                ("criado", "GERADO EM", 145),
            ),
            "auditoria": (
                ("operacao", "OPERAÇÃO", 170),
                ("usuario", "USUÁRIO", 150),
                ("modulo", "MÓDULO", 120),
                ("entidade", "ENTIDADE", 190),
                ("acao", "AÇÃO", 120),
                ("criado", "DATA/HORA", 145),
            ),
        }
        return mapas[self.ferramenta]

    def _criar_tabela(self, parent):
        painel = criar_card(parent)
        painel.pack(fill="both", expand=True)
        topo = tk.Frame(painel, bg=CORES["card"])
        topo.pack(fill="x", padx=16, pady=(14, 10))
        tk.Label(
            topo,
            text="REGISTROS DO CONTEXTO ATUAL",
            font=("Inter", 9, "bold"),
            fg=CORES["primary"],
            bg=CORES["card"],
        ).pack(side="left")
        self.label_total = tk.Label(
            topo,
            text="0 registro(s)",
            font=FONTES["micro"],
            fg=CORES["text_sec"],
            bg=CORES["card"],
        )
        self.label_total.pack(side="right")
        area = tk.Frame(painel, bg=CORES["card"])
        area.pack(fill="both", expand=True, padx=16)
        definicoes = self._definicoes_colunas()
        colunas = tuple(item[0] for item in definicoes)
        self.tabela = ttk.Treeview(
            area,
            columns=colunas,
            show="headings",
            style="Dark.Treeview",
        )
        for chave, titulo, largura in definicoes:
            self.tabela.heading(chave, text=titulo)
            self.tabela.column(
                chave,
                width=largura,
                minwidth=75,
                anchor="w",
                stretch=chave in {"titulo", "nome", "arquivo", "entidade"},
            )
        barra = ttk.Scrollbar(
            area,
            orient="vertical",
            command=self.tabela.yview,
            style="Dark.Vertical.TScrollbar",
        )
        barra_horizontal = ttk.Scrollbar(
            area,
            orient="horizontal",
            command=self.tabela.xview,
            style="Dark.Horizontal.TScrollbar",
        )
        self.tabela.configure(
            yscrollcommand=barra.set,
            xscrollcommand=barra_horizontal.set,
        )
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra.grid(row=0, column=1, sticky="ns")
        barra_horizontal.grid(row=1, column=0, sticky="ew")
        area.grid_rowconfigure(0, weight=1, minsize=280)
        area.grid_columnconfigure(0, weight=1)
        self.tabela.bind("<<TreeviewSelect>>", self._atualizar_acoes)
        self.estado_vazio = criar_estado_vazio(
            area,
            self.config["icone"],
            "Nenhum registro encontrado",
            "Use Novo para iniciar ou aguarde eventos da plataforma.",
        )
        adicionar_divisorias_treeview(self.tabela, sobreposicao=self.estado_vazio)
        rodape = tk.Frame(painel, bg=CORES["card"])
        rodape.pack(fill="x", padx=16, pady=14)
        self.botao_primario = criar_botao(
            rodape,
            self._rotulo_acao_primaria(),
            self.acao_primaria,
            tipo="secundario",
            compacto=True,
        )
        self.botao_primario.pack(side="left")
        self.botao_secundario = criar_botao(
            rodape,
            self._rotulo_acao_secundaria(),
            self.acao_secundaria,
            tipo="perigo" if self.ferramenta in {"tarefas", "documentos"} else "secundario",
            compacto=True,
        )
        self.botao_secundario.pack(side="left", padx=(7, 0))
        if self.ferramenta == "auditoria":
            self.botao_primario.pack_forget()
            self.botao_secundario.pack_forget()
        self._atualizar_acoes()

    def _rotulo_acao_primaria(self):
        return {
            "tarefas": "CONCLUIR",
            "documentos": "VERIFICAR INTEGRIDADE",
            "workflows": "ATIVAR / PAUSAR",
            "integracoes": "ATIVAR / PAUSAR",
            "relatorios": "VER LOCAL",
            "auditoria": "",
        }[self.ferramenta]

    def _rotulo_acao_secundaria(self):
        return {
            "tarefas": "ARQUIVAR",
            "documentos": "ARQUIVAR",
            "workflows": "RECARREGAR",
            "integracoes": "RECARREGAR",
            "relatorios": "RECARREGAR",
            "auditoria": "",
        }[self.ferramenta]

    def _id_selecionado(self):
        selecao = self.tabela.selection()
        return int(selecao[0]) if selecao else None

    def _registro_selecionado(self):
        identificador = self._id_selecionado()
        return next((item for item in self.registros if item["id"] == identificador), None)

    def _atualizar_acoes(self, _evento=None):
        estado = "normal" if self._id_selecionado() is not None else "disabled"
        if self.ferramenta != "auditoria":
            self.botao_primario.configure(state=estado)
            self.botao_secundario.configure(state=estado)

    def carregar(self):
        try:
            if self.ferramenta == "tarefas":
                self.registros = listar_tarefas(SESSAO.usuario)
            elif self.ferramenta == "documentos":
                self.registros = listar_documentos(SESSAO.usuario)
            elif self.ferramenta == "workflows":
                self.registros = listar_workflows(SESSAO.usuario)
            elif self.ferramenta == "integracoes":
                self.registros = listar_integracoes(SESSAO.usuario)
            elif self.ferramenta == "relatorios":
                self.registros = listar_relatorios(SESSAO.usuario)
            else:
                self.registros = listar_auditoria(SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Carregar ferramenta", str(erro), parent=self.root)
            self.registros = []
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for registro in self.registros:
            self.tabela.insert(
                "",
                tk.END,
                iid=str(registro["id"]),
                values=self._valores_linha(registro),
            )
        if self.registros:
            self.estado_vazio.place_forget()
        else:
            self.estado_vazio.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.estado_vazio.lift()
        self.label_total.configure(text=f"{len(self.registros)} registro(s)")
        self._atualizar_acoes()

    def _valores_linha(self, item):
        if self.ferramenta == "tarefas":
            return (
                item["titulo"],
                MODULOS.get(item["modulo"], {}).get("nome", item["modulo"]),
                item.get("responsavel_nome") or "Não atribuído",
                item["prioridade"],
                item["status"],
                item.get("vencimento") or "—",
            )
        if self.ferramenta == "documentos":
            return (
                item["titulo"],
                MODULOS.get(item["modulo"], {}).get("nome", item["modulo"]),
                str(item.get("tipo") or "").upper(),
                item["classificacao"],
                item.get("autor_nome") or "Sistema",
                str(item["criado_em"])[:19],
            )
        if self.ferramenta == "workflows":
            acoes = ", ".join(acao.get("tipo", "") for acao in item["acoes"])
            return (
                item["nome"],
                MODULOS.get(item["evento_modulo"], {}).get("nome", item["evento_modulo"]),
                item["evento_tipo"],
                acoes,
                "Ativo" if item["ativo"] else "Pausado",
            )
        if self.ferramenta == "integracoes":
            return (
                item["nome"],
                item["provedor"].upper(),
                item.get("referencia_credencial") or "Não configurada",
                item.get("ultima_sincronizacao") or "—",
                "Ativa" if item["ativo"] else "Inativa",
            )
        if self.ferramenta == "relatorios":
            return (
                item["titulo"],
                MODULOS.get(item["modulo"], {}).get("nome", item["modulo"]),
                item["formato"],
                item["status"],
                item.get("arquivo") or "—",
                str(item["criado_em"])[:19],
            )
        return (
            item.get("operacao_id") or f"AUD-{item['id']}",
            item.get("usuario_nome") or "Sistema",
            item.get("modulo") or "Core",
            item.get("entidade") or "—",
            item.get("acao") or "—",
            str(item.get("criado_em") or "")[:19],
        )

    def novo(self):
        metodos = {
            "tarefas": self._nova_tarefa,
            "documentos": self._novo_documento,
            "workflows": self._novo_workflow,
            "integracoes": self._nova_integracao,
            "relatorios": self._novo_relatorio,
        }
        metodos[self.ferramenta]()

    def _dialogo(self, titulo, campos, ao_salvar):
        janela = tk.Toplevel(self.root)
        janela.title(titulo)
        preparar_janela_secundaria(
            janela, self.root, 690, 500, minimo=(610, 430)
        )
        janela.configure(bg=CORES["bg"])
        tk.Label(
            janela,
            text=titulo,
            font=FONTES["titulo_grande"],
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=26, pady=(22, 5))
        card = criar_card(janela)
        card.pack(fill="both", expand=True, padx=26, pady=(8, 0))
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=1)
        variaveis = {}
        for indice, (chave, rotulo, valores, padrao) in enumerate(campos):
            grupo = tk.Frame(card, bg=CORES["card"])
            grupo.grid(
                row=indice // 2,
                column=indice % 2,
                sticky="ew",
                padx=(17, 8) if indice % 2 == 0 else (8, 17),
                pady=(14, 0),
            )
            tk.Label(
                grupo,
                text=rotulo.upper(),
                font=("Inter", 8, "bold"),
                fg=CORES["text_sec"],
                bg=CORES["card"],
            ).pack(anchor="w", pady=(0, 5))
            variavel = tk.StringVar(value=str(padrao or ""))
            variaveis[chave] = variavel
            if valores:
                campo = ttk.Combobox(
                    grupo,
                    textvariable=variavel,
                    values=valores,
                    state="readonly",
                    style="Dark.TCombobox",
                )
                if not variavel.get() and valores:
                    variavel.set(valores[0])
            else:
                campo = tk.Entry(
                    grupo,
                    textvariable=variavel,
                    font=FONTES["texto"],
                    bg=CORES["input"],
                    fg=CORES["text"],
                    insertbackground=CORES["primary"],
                    relief="flat",
                    bd=0,
                )
            campo.pack(fill="x", ipady=7)
        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=26, pady=18)
        status = tk.Label(
            rodape,
            text="",
            font=FONTES["micro"],
            fg=CORES["danger"],
            bg=CORES["bg"],
        )
        status.pack(side="left")

        def salvar():
            dados = {chave: var.get() for chave, var in variaveis.items()}
            try:
                ao_salvar(dados)
            except (
                PermissionError,
                ValueError,
                OSError,
                json.JSONDecodeError,
            ) as erro:
                status.configure(text=str(erro))
                return
            janela.destroy()
            self.carregar()

        criar_botao(rodape, "SALVAR", salvar).pack(side="right")
        criar_botao(
            rodape,
            "CANCELAR",
            janela.destroy,
            tipo="secundario",
        ).pack(side="right", padx=(0, 8))

    def _modulos_autorizados(self):
        from services.contexto import listar_modulos_permitidos

        return tuple(
            MODULOS[chave]["nome"]
            for chave in listar_modulos_permitidos(SESSAO.usuario)
            if chave in MODULOS and chave != "analytics"
        )

    @staticmethod
    def _codigo_modulo(rotulo):
        return next(
            (chave for chave, item in MODULOS.items() if item["nome"] == rotulo),
            str(rotulo).lower(),
        )

    def _nova_tarefa(self):
        usuarios = [item for item in obter_usuarios(SESSAO.usuario) if item["ativo"]]
        nomes = ("Não atribuído", *(item["nome"] for item in usuarios))

        def salvar(dados):
            responsavel = next(
                (item["id"] for item in usuarios if item["nome"] == dados["responsavel"]),
                None,
            )
            criar_tarefa(
                {
                    "titulo": dados["titulo"],
                    "descricao": dados["descricao"],
                    "modulo": self._codigo_modulo(dados["modulo"]),
                    "responsavel_id": responsavel,
                    "prioridade": dados["prioridade"],
                    "vencimento": dados["vencimento"],
                },
                SESSAO.usuario,
            )

        self._dialogo(
            "Nova tarefa",
            (
                ("titulo", "Título *", None, ""),
                ("modulo", "Módulo", self._modulos_autorizados(), ""),
                ("descricao", "Descrição", None, ""),
                ("responsavel", "Responsável", nomes, nomes[0]),
                ("prioridade", "Prioridade", ("Baixa", "Média", "Alta", "Crítica"), "Média"),
                ("vencimento", "Vencimento", None, ""),
            ),
            salvar,
        )

    def _novo_documento(self):
        caminho = filedialog.askopenfilename(title="Selecionar documento corporativo")
        if not caminho:
            return
        self._dialogo(
            "Registrar documento",
            (
                ("titulo", "Título", None, ""),
                ("modulo", "Módulo", self._modulos_autorizados(), ""),
                ("classificacao", "Classificação", ("Público", "Interno", "Confidencial", "Restrito"), "Interno"),
                ("arquivo", "Arquivo selecionado", None, caminho),
            ),
            lambda dados: registrar_documento(
                caminho,
                dados["titulo"],
                self._codigo_modulo(dados["modulo"]),
                dados["classificacao"],
                SESSAO.usuario,
            ),
        )

    def _novo_workflow(self):
        modulos = tuple(MODULOS[chave]["nome"] for chave in MODULOS)

        def salvar(dados):
            criar_workflow(
                dados["nome"],
                self._codigo_modulo(dados["modulo"]),
                dados["evento"],
                {"todos": []},
                [
                    {
                        "tipo": "notificar",
                        "titulo": dados["titulo_alerta"] or dados["nome"],
                        "mensagem": dados["mensagem"],
                        "nivel": dados["nivel"],
                    }
                ],
                SESSAO.usuario,
            )

        self._dialogo(
            "Novo workflow de notificação",
            (
                ("nome", "Nome *", None, ""),
                ("modulo", "Módulo", modulos, ""),
                ("evento", "Evento", ("registro_criado", "registro_atualizado", "movimentacao"), "registro_criado"),
                ("nivel", "Nível", ("info", "sucesso", "aviso", "critico"), "info"),
                ("titulo_alerta", "Título do alerta", None, ""),
                ("mensagem", "Mensagem", None, "Evento processado automaticamente."),
            ),
            salvar,
        )

    def _nova_integracao(self):
        def salvar(dados):
            configuracao = json.loads(dados["configuracao"] or "{}")
            registrar_integracao(
                dados["provedor"],
                dados["nome"],
                dados["credencial"],
                configuracao,
                SESSAO.usuario,
            )

        self._dialogo(
            "Nova integração",
            (
                ("nome", "Nome *", None, ""),
                ("provedor", "Provedor", tuple(sorted(PROVEDORES_SUPORTADOS)), "google"),
                ("credencial", "Referência no cofre", None, ""),
                ("configuracao", "Configuração JSON sem segredos", None, "{}"),
            ),
            salvar,
        )

    def _novo_relatorio(self):
        def salvar(dados):
            resultado = gerar_relatorio(
                dados["titulo"],
                self._codigo_modulo(dados["modulo"]),
                dados["formato"],
                SESSAO.usuario,
            )
            remoto = isinstance(resultado, dict) and resultado.get("armazenamento") == "servidor_corporativo"
            nome = resultado.get("nome", "relatorio") if isinstance(resultado, dict) else "relatorio"
            registros = resultado.get("registros") if isinstance(resultado, dict) else None
            detalhe = mensagem_arquivo_gerado(resultado, remoto=remoto, nome=nome)
            if registros is not None:
                detalhe = f"{registros} registro(s) exportado(s).\n\n{detalhe}"
            messagebox.showinfo("Relatório concluído", detalhe, parent=self.root)

        self._dialogo(
            "Gerar relatório",
            (
                ("titulo", "Título *", None, ""),
                ("modulo", "Módulo", self._modulos_autorizados(), ""),
                ("formato", "Formato", ("HTML", "CSV", "JSON"), "HTML"),
            ),
            salvar,
        )

    def acao_primaria(self):
        registro = self._registro_selecionado()
        if registro is None:
            return
        try:
            if self.ferramenta == "tarefas":
                atualizar_status_tarefa(registro["id"], "Concluída", SESSAO.usuario)
            elif self.ferramenta == "documentos":
                resultado = verificar_documento(registro["id"], SESSAO.usuario)
                messagebox.showinfo(
                    "Integridade do documento",
                    "Documento íntegro e disponível."
                    if resultado["integro"]
                    else "O arquivo está ausente ou teve seu conteúdo alterado.",
                    parent=self.root,
                )
            elif self.ferramenta == "workflows":
                definir_workflow_ativo(registro["id"], not bool(registro["ativo"]), SESSAO.usuario)
            elif self.ferramenta == "integracoes":
                definir_integracao_ativa(registro["id"], not bool(registro["ativo"]), SESSAO.usuario)
            elif self.ferramenta == "relatorios":
                caminho = obter_arquivo_relatorio(
                    registro["id"],
                    SESSAO.usuario,
                )
                if not webbrowser.open(Path(caminho).as_uri()):
                    messagebox.showinfo(
                        "Arquivo do relatório",
                        caminho,
                        parent=self.root,
                    )
        except (PermissionError, ValueError, OSError, webbrowser.Error) as erro:
            messagebox.showerror("Executar ação", str(erro), parent=self.root)
        self.carregar()

    def acao_secundaria(self):
        registro = self._registro_selecionado()
        if registro is None:
            return
        try:
            if self.ferramenta == "tarefas":
                arquivar_tarefa(registro["id"], SESSAO.usuario)
            elif self.ferramenta == "documentos":
                arquivar_documento(registro["id"], SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Executar ação", str(erro), parent=self.root)
        self.carregar()
