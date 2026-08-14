"""Workspace especializado do departamento Financeiro."""

from __future__ import annotations

import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

from auth.sessao import SESSAO
from interface.armazenamento_servidor import mensagem_arquivo_gerado
from services.contexto import tem_permissao
from services.departamentos.financeiro import (
    NATUREZAS,
    STATUS_ABERTOS,
    STATUS_TERMINAIS,
    analisar_financeiro,
    agendar_relatorio,
    anexar_documento,
    atualizar_lancamento,
    atualizar_status_vencidos,
    calcular_dre,
    cancelar_lancamento,
    conciliar_item,
    contabilizar_lancamento,
    criar_categoria,
    criar_conta,
    criar_lancamento,
    criar_parte,
    decidir_aprovacao,
    estornar_lancamento,
    gerar_alertas_financeiros,
    gerar_recorrencias_pendentes,
    gerar_relatorio_financeiro,
    importar_extrato,
    listar_aprovacoes_financeiras,
    listar_auditoria_financeira,
    listar_cartoes,
    listar_catalogos,
    listar_conciliacoes,
    listar_contas_com_saldo,
    listar_lancamentos,
    listar_orcamentos,
    listar_recorrencias,
    listar_relatorios_agendados,
    obter_lancamento,
    projetar_fluxo_caixa,
    registrar_baixa,
    resumo_financeiro,
    salvar_cartao,
    salvar_orcamento,
    salvar_plano_conta,
    submeter_aprovacao,
    tem_permissao_financeira,
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
from interface.navegacao_modulos import criar_sidebar_modulo
from interface.tema import (
    CORES,
    FONTES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


COR_FINANCEIRO = "#34D079"

GRUPOS_MENU = (
    ("FINANCEIRO", (("visao", "⌂", "Visão geral"),)),
    ("OPERAÇÕES", (
        ("lancamentos", "≡", "Lançamentos"),
        ("pagar", "↓", "Contas a pagar"),
        ("receber", "↑", "Contas a receber"),
        ("reembolsos", "$", "Reembolsos"),
        ("transferencias", "⇄", "Transferências"),
        ("recorrencias", "↻", "Recorrências"),
    )),
    ("TESOURARIA", (
        ("fluxo", "≋", "Fluxo de caixa"),
        ("bancos", "▣", "Bancos e contas"),
        ("conciliacao", "✓", "Conciliação"),
        ("cartoes", "▭", "Cartões corporativos"),
    )),
    ("PLANEJAMENTO", (
        ("orcamento", "▥", "Orçamento"),
        ("projecoes", "↗", "Projeções"),
        ("centros_custo", "◇", "Centros de custo"),
    )),
    ("GESTÃO", (
        ("dre", "▤", "DRE"),
        ("relatorios", "↥", "Relatórios"),
        ("aprovacoes_fin", "✓", "Aprovações"),
        ("auditoria_fin", "◎", "Auditoria"),
    )),
    ("CADASTROS", (
        ("plano_contas", "#", "Plano de contas"),
        ("categorias", "◈", "Categorias"),
        ("partes", "◉", "Clientes e fornecedores"),
    )),
)


ROTULOS = {
    chave: titulo
    for _grupo, itens in GRUPOS_MENU
    for chave, _icone, titulo in itens
}


def _moeda(centavos) -> str:
    valor = int(centavos or 0) / 100
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _data_br(valor) -> str:
    texto = str(valor or "")[:10]
    partes = texto.split("-")
    return "/".join(reversed(partes)) if len(partes) == 3 else texto


class FinanceiroDialogosMixin:
    def _menu_novo(self):
        janela = tk.Toplevel(self.root)
        janela.title("Novo registro financeiro")
        preparar_janela_secundaria(janela, self.root, 620, 520, minimo=(560, 470))
        janela.configure(bg=CORES["bg"])
        tk.Label(janela, text="Novo registro", font=FONTES["titulo_grande"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", padx=25, pady=(22, 5))
        tk.Label(janela, text="Selecione a operação financeira que deseja iniciar.", font=FONTES["texto"], fg=CORES["text_sec"], bg=CORES["bg"]).pack(anchor="w", padx=25, pady=(0, 15))
        grade = tk.Frame(janela, bg=CORES["bg"])
        grade.pack(fill="both", expand=True, padx=25)
        opcoes = (
            ("+ Receita", "Receita"), ("− Despesa", "Despesa"), ("⇄ Transferência", "Transferência"),
            ("$ Conta a pagar", "Conta a pagar"), ("$ Conta a receber", "Conta a receber"),
            ("↻ Lançamento recorrente", "recorrente"), ("↑ Importar movimentações", "importar"),
        )
        for indice, (texto, destino) in enumerate(opcoes):
            if destino == "importar":
                comando = self._importar_extrato
            elif destino == "recorrente":
                comando = lambda: self._form_lancamento(
                    "Conta a pagar", recorrente=True,
                )
            else:
                comando = lambda natureza=destino: self._form_lancamento(natureza)
            botao = criar_botao(grade, texto.upper(), lambda c=comando: (janela.destroy(), c()), tipo="secundario")
            botao.grid(row=indice // 2, column=indice % 2, sticky="ew", padx=5, pady=5)
            grade.grid_columnconfigure(indice % 2, weight=1)


    def _form_lancamento(self, natureza=None, *, recorrente=False, registro_id=None):
        catalogos = listar_catalogos(SESSAO.usuario)
        registro = obter_lancamento(registro_id, SESSAO.usuario) if registro_id else None
        opcoes = {
            "natureza": {item: item for item in sorted(NATUREZAS)},
            "categoria_id": {f"{item['nome']} · {item['natureza']}": item["id"] for item in catalogos["categorias"]},
            "plano_conta_id": {f"{item['codigo']} · {item['nome']}": item["id"] for item in catalogos["plano_contas"]},
            "centro_custo_id": {f"{item['codigo']} · {item['nome']}": item["id"] for item in catalogos["centros_custo"]},
            "departamento_id": {f"{item['codigo']} · {item['nome']}": item["id"] for item in catalogos["departamentos"]},
            "projeto_id": {f"{item['codigo']} · {item['nome']}": item["id"] for item in catalogos["projetos"]},
            "conta_id": {item["nome"]: item["id"] for item in catalogos["contas"]},
            "conta_destino_id": {item["nome"]: item["id"] for item in catalogos["contas"]},
            "parte_id": {f"{item['nome']} · {item['tipo']}": item["id"] for item in catalogos["partes"]},
        }
        padroes = {
            "natureza": natureza or (registro["natureza"] if registro else "Despesa"),
            "descricao": registro["descricao"] if registro else "",
            "valor": str(int(registro["valor_original_centavos"]) / 100).replace(".", ",") if registro else "",
            "competencia": _data_br(registro["competencia"]) if registro else _data_br(date.today().isoformat()),
            "vencimento": _data_br(registro["vencimento"]) if registro else "",
            "forma_pagamento": registro.get("forma_pagamento") if registro else "",
            "documento_numero": registro.get("documento_numero") if registro else "",
            "nota_fiscal": registro.get("nota_fiscal") if registro else "",
            "observacoes": registro.get("observacoes") if registro else "",
            "tags": registro.get("tags") if registro else "",
            "parcelas": "1",
            "recorrente": recorrente,
            "periodicidade": "Mensal",
            "recorrencia_fim": "",
        }
        if registro:
            for chave in ("categoria_id", "plano_conta_id", "centro_custo_id", "departamento_id", "projeto_id", "conta_id", "conta_destino_id", "parte_id"):
                valor = registro.get(chave)
                padroes[chave] = next((rotulo for rotulo, ident in opcoes[chave].items() if ident == valor), "")
        campos = (
            ("natureza", "Tipo", "combo"), ("descricao", "Descrição", "texto"),
            ("valor", "Valor", "texto"), ("competencia", "Competência", "texto"),
            ("vencimento", "Vencimento", "texto"), ("parte_id", "Cliente / fornecedor", "combo"),
            ("categoria_id", "Categoria", "combo"), ("plano_conta_id", "Plano de contas", "combo"),
            ("departamento_id", "Departamento", "combo"), ("centro_custo_id", "Centro de custo", "combo"),
            ("projeto_id", "Projeto", "combo"),
            ("conta_id", "Conta de origem / liquidação", "combo"), ("conta_destino_id", "Conta de destino", "combo"),
            ("forma_pagamento", "Forma de pagamento", "texto"), ("documento_numero", "Número do documento", "texto"),
            ("nota_fiscal", "Nota fiscal", "texto"), ("tags", "Tags", "texto"),
            ("parcelas", "Quantidade de parcelas", "texto"), ("periodicidade", "Periodicidade", "combo", ("Semanal", "Mensal", "Trimestral", "Anual")),
            ("recorrencia_fim", "Repetir até", "texto"), ("recorrente", "Lançamento recorrente", "bool"),
            ("observacoes", "Observações", "texto"),
        )
        def salvar(valores):
            for chave, mapa in opcoes.items():
                valores[chave] = mapa.get(valores.get(chave))
            if registro_id:
                atualizar_lancamento(registro_id, valores, SESSAO.usuario)
            else:
                criar_lancamento(valores, SESSAO.usuario)
        self._modal_formulario("Editar lançamento" if registro_id else "Novo lançamento", campos, padroes, opcoes, salvar)


    def _form_baixa(self, lancamento_id):
        catalogos = listar_catalogos(SESSAO.usuario)
        contas = {item["nome"]: item["id"] for item in catalogos["contas"]}
        item = obter_lancamento(lancamento_id, SESSAO.usuario)
        saldo = (int(item["valor_original_centavos"]) - int(item["valor_liquidado_centavos"])) / 100
        campos = (("valor", "Valor principal", "texto"), ("data", "Data da baixa", "texto"), ("conta_id", "Conta", "combo"), ("juros", "Juros", "texto"), ("multa", "Multa", "texto"), ("desconto", "Desconto", "texto"), ("forma_pagamento", "Forma de pagamento", "texto"), ("referencia", "Referência", "texto"))
        padroes = {"valor": str(saldo).replace(".", ","), "data": _data_br(date.today().isoformat()), "juros": "0", "multa": "0", "desconto": "0"}
        def salvar(valores):
            valores["conta_id"] = contas.get(valores.get("conta_id"))
            registrar_baixa(lancamento_id, valores, SESSAO.usuario)
        self._modal_formulario("Registrar pagamento / recebimento", campos, padroes, {"conta_id": contas}, salvar)


    def _form_conta(self):
        campos = (("nome", "Nome da conta", "texto"), ("banco", "Banco / instituição", "texto"), ("agencia", "Agência", "texto"), ("numero", "Número", "texto"), ("tipo", "Tipo", "combo", ("Conta corrente", "Poupança", "Investimento", "Caixa físico", "Carteira digital")), ("saldo_inicial", "Saldo inicial", "texto"), ("data_saldo_inicial", "Data do saldo", "texto"))
        self._modal_formulario("Nova conta financeira", campos, {"tipo": "Conta corrente", "saldo_inicial": "0", "data_saldo_inicial": _data_br(date.today().isoformat())}, {}, lambda valores: criar_conta(valores, SESSAO.usuario))


    def _form_orcamento(self):
        catalogos = listar_catalogos(SESSAO.usuario)
        opcoes = {
            "centro_custo_id": {f"{i['codigo']} · {i['nome']}": i["id"] for i in catalogos["centros_custo"]},
            "categoria_id": {i["nome"]: i["id"] for i in catalogos["categorias"]},
        }
        campos = (("ano", "Ano", "texto"), ("mes", "Mês", "texto"), ("centro_custo_id", "Centro de custo", "combo"), ("categoria_id", "Categoria", "combo"), ("planejado", "Valor planejado", "texto"), ("limite_alerta_percentual", "Alertar em %", "texto"), ("status", "Status", "combo", ("Planejado", "Aprovado", "Revisão", "Encerrado")))
        def salvar(valores):
            for chave, mapa in opcoes.items():
                valores[chave] = mapa.get(valores.get(chave))
            salvar_orcamento(valores, SESSAO.usuario)
        self._modal_formulario("Novo orçamento", campos, {"ano": str(date.today().year), "mes": str(date.today().month), "limite_alerta_percentual": "85", "status": "Planejado"}, opcoes, salvar)


    def _form_plano(self):
        campos = (("codigo", "Código", "texto"), ("nome", "Nome", "texto"), ("natureza", "Natureza", "combo", ("Receita", "Despesa", "Neutra")), ("grupo_dre", "Grupo DRE", "combo", ("Receita bruta", "Deduções", "Custos", "Despesas operacionais", "Resultado financeiro", "Não operacional")))
        self._modal_formulario("Nova conta contábil", campos, {"natureza": "Despesa", "grupo_dre": "Despesas operacionais"}, {}, lambda valores: salvar_plano_conta(valores, SESSAO.usuario))


    def _form_categoria(self):
        planos = {f"{i['codigo']} · {i['nome']}": i["id"] for i in listar_catalogos(SESSAO.usuario)["plano_contas"]}
        campos = (("nome", "Nome", "texto"), ("natureza", "Natureza", "combo", ("Receita", "Despesa", "Ambos")), ("plano_conta_id", "Conta contábil", "combo"))
        def salvar(valores):
            valores["plano_conta_id"] = planos.get(valores.get("plano_conta_id"))
            criar_categoria(valores, SESSAO.usuario)
        self._modal_formulario("Nova categoria", campos, {"natureza": "Despesa"}, {"plano_conta_id": planos}, salvar)


    def _form_parte(self):
        campos = (("nome", "Nome / razão social", "texto"), ("tipo", "Tipo", "combo", ("Cliente", "Fornecedor", "Ambos")), ("documento", "CPF / CNPJ", "texto"), ("email", "E-mail", "texto"), ("telefone", "Telefone", "texto"), ("banco", "Banco", "texto"), ("chave_pix", "Chave PIX", "texto"))
        self._modal_formulario("Novo cliente ou fornecedor", campos, {"tipo": "Ambos"}, {}, lambda valores: criar_parte(valores, SESSAO.usuario))


    def _form_cartao(self):
        catalogos = listar_catalogos(SESSAO.usuario)
        contas = {i["nome"]: i["id"] for i in catalogos["contas"]}
        centros = {f"{i['codigo']} · {i['nome']}": i["id"] for i in catalogos["centros_custo"]}
        campos = (("nome", "Nome do cartão", "texto"), ("final", "Quatro últimos dígitos", "texto"), ("limite", "Limite", "texto"), ("conta_id", "Conta vinculada", "combo"), ("centro_custo_id", "Centro de custo", "combo"), ("fechamento_dia", "Dia do fechamento", "texto"), ("vencimento_dia", "Dia do vencimento", "texto"))
        def salvar(valores):
            valores["conta_id"] = contas.get(valores.get("conta_id"))
            valores["centro_custo_id"] = centros.get(valores.get("centro_custo_id"))
            salvar_cartao(valores, SESSAO.usuario)
        self._modal_formulario("Novo cartão corporativo", campos, {"limite": "0", "fechamento_dia": "1", "vencimento_dia": "10"}, {"conta_id": contas, "centro_custo_id": centros}, salvar)


    def _form_agendamento_relatorio(self):
        campos = (
            ("nome", "Nome do agendamento", "texto"),
            ("tipo", "Relatório", "combo", ("Contas a pagar", "Contas a receber", "Fluxo de caixa", "DRE", "Orçamento x realizado", "Auditoria financeira")),
            ("formato", "Formato", "combo", ("PDF", "Excel", "CSV", "HTML")),
            ("frequencia", "Frequência", "combo", ("Diário", "Semanal", "Mensal", "Trimestral", "Manual")),
            ("proxima_execucao", "Próxima execução", "texto"),
            ("destinatarios", "Destinatários", "texto"),
        )
        self._modal_formulario(
            "Agendar relatório",
            campos,
            {"tipo": "DRE", "formato": "PDF", "frequencia": "Mensal", "proxima_execucao": _data_br(date.today().isoformat())},
            {},
            lambda valores: agendar_relatorio(valores, SESSAO.usuario),
        )


    def _modal_formulario(self, titulo, campos, padroes, mapas, salvar):
        janela = tk.Toplevel(self.root)
        janela.title(titulo)
        preparar_janela_secundaria(janela, self.root, 900, 700, minimo=(720, 570))
        janela.configure(bg=CORES["bg"])
        tk.Label(janela, text=titulo, font=FONTES["titulo_grande"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", padx=26, pady=(22, 4))
        tk.Label(janela, text="Dados salvos no contexto empresarial atual, com permissões e auditoria.", font=FONTES["texto_pequeno"], fg=CORES["text_sec"], bg=CORES["bg"]).pack(anchor="w", padx=26, pady=(0, 14))
        viewport = AreaRolavel(janela)
        viewport.pack(fill="both", expand=True, padx=26)
        formulario = criar_card(viewport.conteudo)
        formulario.pack(fill="both", expand=True)
        formulario.grid_columnconfigure(0, weight=1)
        formulario.grid_columnconfigure(1, weight=1)
        variaveis = {}
        for indice, definicao in enumerate(campos):
            chave, rotulo, tipo, *config = definicao
            grupo = tk.Frame(formulario, bg=CORES["card"])
            grupo.grid(row=indice // 2, column=indice % 2, sticky="ew", padx=(17, 8) if indice % 2 == 0 else (8, 17), pady=(13, 0))
            tk.Label(grupo, text=rotulo.upper(), font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["card"]).pack(anchor="w", pady=(0, 5))
            if tipo == "bool":
                var = tk.BooleanVar(value=bool(padroes.get(chave)))
                widget = tk.Checkbutton(grupo, variable=var, text="Sim", font=FONTES["texto"], fg=CORES["text"], bg=CORES["card"], activebackground=CORES["card"], selectcolor=CORES["input"])
            else:
                var = tk.StringVar(value=str(padroes.get(chave) or ""))
                mapa = mapas.get(chave, {})
                valores = (("", *tuple(mapa.keys())) if mapa else (config[0] if config else ()))
                if tipo == "combo":
                    widget = ttk.Combobox(grupo, textvariable=var, values=valores, state="readonly", style="Dark.TCombobox")
                    if not var.get() and valores and not mapa:
                        var.set(valores[0])
                else:
                    widget = tk.Entry(grupo, textvariable=var, font=FONTES["texto"], bg=CORES["input"], fg=CORES["text"], insertbackground=CORES["primary"], relief="flat", bd=0)
            variaveis[chave] = var
            widget.pack(fill="x", ipady=7)
        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=26, pady=18)
        status = tk.Label(rodape, text="", font=FONTES["micro"], fg=CORES["danger_muted"], bg=CORES["bg"])
        status.pack(side="left")
        def confirmar():
            dados = {chave: var.get() for chave, var in variaveis.items()}
            try:
                salvar(dados)
            except (ValueError, PermissionError, RuntimeError) as erro:
                status.configure(text=str(erro))
                return
            janela.destroy()
            messagebox.showinfo("Financeiro", "Operação concluída e registrada na auditoria.", parent=self.root)
            self.abrir_secao(self.secao)
        criar_botao(rodape, "SALVAR", confirmar, tipo="sucesso").pack(side="right")
        criar_botao(rodape, "CANCELAR", janela.destroy, tipo="secundario").pack(side="right", padx=(0, 8))


    def _importar_extrato(self):
        contas = listar_contas_com_saldo(SESSAO.usuario)
        if not contas:
            messagebox.showinfo("Importar extrato", "Cadastre uma conta bancária antes de importar o extrato.", parent=self.root)
            self._form_conta()
            return
        conta_id = self._escolher_conta_importacao(contas)
        if not conta_id:
            return
        caminho = filedialog.askopenfilename(parent=self.root, title="Selecionar extrato", filetypes=(("Extratos", "*.ofx *.csv *.xlsx *.xls"), ("Todos", "*.*")))
        if not caminho:
            return
        try:
            resultado = importar_extrato(conta_id, caminho, SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Importar extrato", str(erro), parent=self.root)
            return
        messagebox.showinfo("Importar extrato", f"{resultado['itens']} movimentação(ões) importada(s).\nRevise as sugestões na Conciliação.", parent=self.root)
        self.abrir_secao("conciliacao")


    def _escolher_conta_importacao(self, contas):
        janela = tk.Toplevel(self.root)
        janela.title("Conta do extrato")
        preparar_janela_secundaria(janela, self.root, 560, 260, minimo=(500, 240))
        janela.configure(bg=CORES["bg"])
        tk.Label(
            janela, text="Selecione a conta do extrato",
            font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"],
        ).pack(anchor="w", padx=24, pady=(22, 6))
        tk.Label(
            janela,
            text="A conta correta é necessária para calcular o saldo e registrar a conciliação.",
            font=FONTES["texto_pequeno"], fg=CORES["text_sec"], bg=CORES["bg"],
            wraplength=500, justify="left",
        ).pack(anchor="w", padx=24, pady=(0, 14))
        mapa = {
            f"{item['nome']}  ·  {_moeda(item['saldo_centavos'])}": item["id"]
            for item in contas
        }
        variavel = tk.StringVar(value=next(iter(mapa)))
        ttk.Combobox(
            janela, textvariable=variavel, values=tuple(mapa),
            state="readonly", style="Dark.TCombobox",
        ).pack(fill="x", padx=24)
        resultado = {"id": None}

        def confirmar():
            resultado["id"] = mapa.get(variavel.get())
            janela.destroy()

        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=24, pady=18)
        criar_botao(rodape, "CONTINUAR", confirmar, compacto=True).pack(side="right")
        criar_botao(rodape, "CANCELAR", janela.destroy, tipo="secundario", compacto=True).pack(side="right", padx=(0, 7))
        janela.wait_window()
        return resultado["id"]


    def _anexar(self, lancamento_id):
        caminho = filedialog.askopenfilename(parent=self.root, title="Anexar documento")
        if not caminho:
            return
        try:
            anexar_documento(lancamento_id, caminho, SESSAO.usuario)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Anexo", str(erro), parent=self.root)
            return
        messagebox.showinfo("Anexo", "Documento copiado para o repositório protegido.", parent=self.root)


    def _gerar_relatorio(self, tipo, formato):
        try:
            resultado = gerar_relatorio_financeiro(tipo, formato, SESSAO.usuario)
        except (ValueError, PermissionError, RuntimeError) as erro:
            messagebox.showerror("Relatório", str(erro), parent=self.root)
            return
        remoto = isinstance(resultado, dict) and resultado.get("armazenamento") == "servidor_corporativo"
        nome = resultado.get("nome", f"financeiro.{formato.lower()}") if isinstance(resultado, dict) else str(resultado)
        messagebox.showinfo(
            "Relatório concluído",
            mensagem_arquivo_gerado(resultado, remoto=remoto, nome=nome),
            parent=self.root,
        )


    def _mostrar_analise(self):
        analise = analisar_financeiro(SESSAO.usuario)
        janela = tk.Toplevel(self.root)
        janela.title("Analista financeiro interno")
        preparar_janela_secundaria(janela, self.root, 820, 650, minimo=(700, 560))
        janela.configure(bg=CORES["bg"])
        tk.Label(janela, text="Analista financeiro interno", font=FONTES["titulo_grande"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", padx=26, pady=(22, 4))
        tk.Label(janela, text="Diagnóstico determinístico do contexto autorizado. Nenhuma decisão sensível é executada automaticamente.", font=FONTES["texto_pequeno"], fg=CORES["text_sec"], bg=CORES["bg"], wraplength=740, justify="left").pack(anchor="w", padx=26, pady=(0, 14))
        texto = tk.Text(janela, bg=CORES["card"], fg=CORES["text"], relief="flat", bd=0, font=FONTES["texto"], wrap="word", padx=18, pady=18)
        texto.pack(fill="both", expand=True, padx=26)
        resumo = analise["resumo"]
        texto.insert("end", "RESUMO EXECUTIVO\n", "titulo")
        texto.insert("end", f"Receitas liquidadas: {_moeda(resumo['receitas_centavos'])}\nDespesas liquidadas: {_moeda(resumo['despesas_centavos'])}\nResultado: {_moeda(resumo['resultado_centavos'])}\nSaldo consolidado: {_moeda(resumo['saldo_centavos'])}\n\n")
        texto.insert("end", "PONTOS DE ATENÇÃO\n", "titulo")
        for item in analise["alertas"]:
            texto.insert("end", f"• {item}\n")
        texto.insert("end", "\nRECOMENDAÇÕES\n", "titulo")
        for item in analise["recomendacoes"]:
            texto.insert("end", f"• {item}\n")
        texto.insert("end", "\nQUESTÕES PARA A GESTÃO\n", "titulo")
        for indice, item in enumerate(analise["questoes_gestao"], 1):
            texto.insert("end", f"{indice}. {item}\n")
        texto.tag_configure("titulo", foreground=COR_FINANCEIRO, font=("Inter", 10, "bold"), spacing1=6, spacing3=5)
        texto.configure(state="disabled")
        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=26, pady=18)
        criar_botao(rodape, "GERAR ALERTAS", lambda: gerar_alertas_financeiros(SESSAO.usuario), tipo="secundario", compacto=True).pack(side="left")
        criar_botao(rodape, "ABRIR ANALYTICS COMPLETO", lambda: (janela.destroy(), self.navegacao["analisar_modulo"]("financeiro")), compacto=True).pack(side="left", padx=7)
        criar_botao(rodape, "FECHAR", janela.destroy, tipo="secundario", compacto=True).pack(side="right")


    def _form_simples_valor(self, titulo, rotulo):
        janela = tk.Toplevel(self.root)
        janela.title(titulo)
        preparar_janela_secundaria(janela, self.root, 520, 230, minimo=(460, 210))
        janela.configure(bg=CORES["bg"])
        tk.Label(janela, text=titulo, font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", padx=24, pady=(22, 12))
        tk.Label(janela, text=rotulo.upper(), font=("Inter", 8, "bold"), fg=CORES["text_sec"], bg=CORES["bg"]).pack(anchor="w", padx=24)
        var = tk.StringVar()
        entrada = tk.Entry(janela, textvariable=var, font=FONTES["texto"], bg=CORES["input"], fg=CORES["text"], insertbackground=CORES["primary"], relief="flat", bd=0)
        entrada.pack(fill="x", padx=24, pady=(5, 15), ipady=8)
        resultado = {"valor": None}
        def confirmar():
            resultado["valor"] = var.get().strip()
            janela.destroy()
        criar_botao(janela, "CONFIRMAR", confirmar, compacto=True).pack(anchor="e", padx=24)
        entrada.focus_set()
        janela.wait_window()
        return resultado["valor"]

