"""Formulários e ações do módulo empresarial V9.8."""
from interface.modulo_empresarial_shared import *

class ModuloEmpresarialFormulariosMixin:
    def abrir_formulario(self, registro_id=None):
        registro = None
        if registro_id is not None:
            try:
                registro = obter_registro(self.modulo, registro_id, SESSAO.usuario)
            except (PermissionError, ValueError) as erro:
                messagebox.showerror("Editar registro", str(erro), parent=self.root)
                return
        titulo_formulario = (
            f"Editar · {self.configuracao['nome']}"
            if registro is not None
            else self.configuracao["titulo_registro"]
        )
        janela = tk.Toplevel(self.root)
        janela.title(titulo_formulario)
        preparar_janela_secundaria(
            janela, self.root, 700, 520, minimo=(620, 480)
        )
        janela.configure(bg=CORES["bg"])
        tk.Label(
            janela,
            text=titulo_formulario,
            font=("Inter", 18, "bold"),
            fg=CORES["text"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=28, pady=(24, 4))
        tk.Label(
            janela,
            text="Preencha somente informações necessárias e autorizadas.",
            font=("Inter", 9),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        ).pack(anchor="w", padx=28, pady=(0, 15))

        formulario = criar_card(janela)
        formulario.pack(fill="both", expand=True, padx=28)
        formulario.grid_columnconfigure(0, weight=1)
        formulario.grid_columnconfigure(1, weight=1)
        self.form_vars = {}
        self.form_maps = {}
        for indice, (nome, rotulo, tipo, obrigatorio) in enumerate(
            self.configuracao["campos"]
        ):
            grupo = tk.Frame(formulario, bg=CORES["card"])
            grupo.grid(
                row=indice // 2,
                column=indice % 2,
                sticky="ew",
                padx=(18, 9) if indice % 2 == 0 else (9, 18),
                pady=(14, 0),
            )
            tk.Label(
                grupo,
                text=f"{rotulo.upper()}{'  *' if obrigatorio else ''}",
                font=("Inter", 8, "bold"),
                fg=CORES["text_sec"],
                bg=CORES["card"],
            ).pack(anchor="w", pady=(0, 5))
            variavel = tk.StringVar()
            self.form_vars[nome] = variavel
            valores = None
            if isinstance(tipo, tuple):
                valores = list(tipo)
            elif tipo == "departamento":
                registros = [item for item in listar_departamentos() if item["ativo"]]
                self.form_maps[nome] = {item["nome"]: item["id"] for item in registros}
                valores = list(self.form_maps[nome])
            elif tipo == "centro_custo":
                registros = [item for item in listar_centros_custo() if item["ativo"]]
                self.form_maps[nome] = {
                    f'{item["codigo"]} · {item["nome"]}': item["id"]
                    for item in registros
                }
                valores = list(self.form_maps[nome])
            if valores is not None:
                campo = ttk.Combobox(
                    grupo,
                    textvariable=variavel,
                    values=valores,
                    state="readonly",
                    style="Dark.TCombobox",
                )
                if valores:
                    variavel.set(valores[0])
            else:
                campo = tk.Entry(
                    grupo,
                    textvariable=variavel,
                    font=("Inter", 10),
                    bg=CORES["input"],
                    fg=CORES["text"],
                    insertbackground=CORES["primary"],
                    relief="flat",
                    bd=0,
                )
            campo.pack(fill="x", ipady=7)
            if registro is not None:
                valor_atual = registro.get(nome)
                if nome in self.form_maps:
                    valor_atual = next(
                        (
                            rotulo
                            for rotulo, identificador in self.form_maps[nome].items()
                            if identificador == valor_atual
                        ),
                        "",
                    )
                variavel.set("" if valor_atual is None else str(valor_atual))

        rodape = tk.Frame(janela, bg=CORES["bg"])
        rodape.pack(fill="x", padx=28, pady=20)
        self.form_status = tk.Label(
            rodape,
            text="* Campos obrigatórios",
            font=("Inter", 8),
            fg=CORES["text_sec"],
            bg=CORES["bg"],
        )
        self.form_status.pack(side="left")
        criar_botao(
            rodape,
            "CANCELAR",
            janela.destroy,
            tipo="secundario",
        ).pack(side="right")
        criar_botao(
            rodape,
            "SALVAR ALTERAÇÕES" if registro is not None else "SALVAR REGISTRO",
            lambda: self._salvar_formulario(janela, registro_id),
        ).pack(side="right", padx=(0, 8))

    def _salvar_formulario(self, janela, registro_id=None):
        dados = {}
        for nome, variavel in self.form_vars.items():
            valor = variavel.get()
            if nome in self.form_maps:
                valor = self.form_maps[nome].get(valor)
            dados[nome] = valor
        try:
            if registro_id is None:
                criar_registro(self.modulo, dados, SESSAO.usuario)
            else:
                atualizar_registro(
                    self.modulo,
                    registro_id,
                    dados,
                    SESSAO.usuario,
                )
        except (PermissionError, ValueError) as erro:
            self.form_status.configure(text=str(erro), fg=CORES["danger"])
            return
        janela.destroy()
        self.carregar()
        mensagem = (
            "Registro criado com sucesso."
            if registro_id is None
            else "Registro atualizado com sucesso."
        )
        self.status.configure(text=mensagem, fg=CORES["success"])

    def editar_selecionado(self):
        registro_id = self._id_selecionado()
        if registro_id is None:
            return
        self.abrir_formulario(registro_id)

    def mudar_estado_selecionado(self, estado):
        registro_id = self._id_selecionado()
        if registro_id is None:
            return
        verbos = {
            "Ativo": "restaurar",
            "Arquivado": "arquivar",
            "Lixeira": "enviar à lixeira",
        }
        if not messagebox.askyesno(
            "Confirmar alteração",
            f"Deseja {verbos[estado]} o registro selecionado?",
            parent=self.root,
        ):
            return
        try:
            alterar_estado_registro(
                self.modulo,
                registro_id,
                estado,
                SESSAO.usuario,
            )
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Registro", str(erro), parent=self.root)
            return
        self.carregar()
        self.status.configure(
            text=f"Registro alterado para {estado}.",
            fg=CORES["success"],
        )

    def abrir_movimentacao(self):
        selecao = self.tabela.selection()
        if not selecao:
            messagebox.showwarning(
                "Movimentar estoque",
                "Selecione um item na tabela.",
                parent=self.root,
            )
            return
        item_id = int(selecao[0])
        tipo = simpledialog.askstring(
            "Movimentar estoque",
            "Informe Entrada, Saída ou Ajuste:",
            parent=self.root,
        )
        if not tipo:
            return
        mapa = {"entrada": "Entrada", "saida": "Saída", "saída": "Saída", "ajuste": "Ajuste"}
        tipo = mapa.get(tipo.strip().lower())
        quantidade = simpledialog.askstring(
            "Movimentar estoque",
            "Quantidade:",
            parent=self.root,
        )
        if not tipo or not quantidade:
            messagebox.showerror("Movimentar estoque", "Operação inválida.", parent=self.root)
            return
        try:
            movimentar_estoque(item_id, tipo, quantidade, SESSAO.usuario)
        except (PermissionError, ValueError) as erro:
            messagebox.showerror("Movimentar estoque", str(erro), parent=self.root)
            return
        self.carregar()

    @staticmethod
    def _formatar_valor(valor, formato):
        # Consultas sem registros podem retornar None
        if valor is None or valor == "":
            numero = 0.0
        else:
            try:
                numero = float(valor)
            except (TypeError, ValueError):
                return "—"

        if formato == "moeda":
            texto = (
                f"{numero:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
            return f"R$ {texto}"

        if formato == "decimal":
            return (
                f"{numero:,.1f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        return f"{int(numero):,}".replace(",", ".")

    @classmethod
    def _formatar_celula(cls, chave, valor):
        if valor is None or valor == "":
            return "—"
        if chave in {"salario", "valor", "valor_estimado", "investimento", "receita"}:
            return cls._formatar_valor(valor, "moeda")
        if chave in {"quantidade", "estoque_minimo"}:
            return cls._formatar_valor(valor, "decimal")
        return str(valor)
