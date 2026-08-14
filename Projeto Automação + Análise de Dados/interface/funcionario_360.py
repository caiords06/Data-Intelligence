"""Janela do Funcionário 360° com visões contextuais e dados compostos."""
from __future__ import annotations

from io import BytesIO
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from auth.sessao import SESSAO
from interface.componentes import criar_botao, preparar_janela_secundaria
from interface.tema import CORES, FONTES
from services.funcionario_360 import (
    carregar_avatar, obter_funcionario_360, obter_meu_funcionario_360, registrar_avatar,
    registrar_feedback, registrar_ocorrencia,
)
from services.departamentos.rh import (
    adicionar_dependente, atualizar_colaborador, iniciar_desligamento,
    solicitar_ferias_ausencia, vincular_equipamento,
)

try:
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover
    Image = ImageTk = None

ROTULOS = {
    "identidade": "Identidade", "dados_pessoais": "Dados pessoais", "profissional": "Profissional",
    "contatos": "Contatos", "linha_tempo": "Linha do tempo", "documentos": "Documentos e assinaturas",
    "jornada": "Férias, ausências e jornada", "beneficios": "Benefícios", "remuneracao": "Folha e contracheques",
    "equipamentos": "Equipamentos", "acessos": "Sistemas e acessos", "treinamentos": "Treinamentos e certificados",
    "desempenho": "Desempenho, feedbacks e PDI", "tarefas": "Tarefas", "chamados": "Chamados de TI",
    "solicitacoes": "Solicitações", "ocorrencias": "Ocorrências", "custos": "Custos vinculados", "auditoria": "Auditoria",
}


def _texto(valor) -> str:
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, bool):
        return "Sim" if valor else "Não"
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, default=str)
    return str(valor)


def _renderizar_lista(parent, itens: list) -> None:
    if not itens:
        tk.Label(parent, text="Nenhum registro nesta seção.", bg=CORES["card"], fg=CORES["text_muted"], font=FONTES["texto"]).pack(anchor="w", padx=16, pady=16)
        return
    chaves = []
    for item in itens:
        if isinstance(item, dict):
            for chave, valor in item.items():
                if chave.endswith("_json") or isinstance(valor, (dict, list, bytes)):
                    continue
                if chave not in chaves:
                    chaves.append(chave)
                if len(chaves) >= 7:
                    break
        if len(chaves) >= 7:
            break
    if not chaves:
        tk.Label(parent, text="\n".join(_texto(x) for x in itens), bg=CORES["card"], fg=CORES["text"], justify="left").pack(anchor="w", padx=16, pady=12)
        return
    tabela = ttk.Treeview(parent, columns=chaves, show="headings", style="Dark.Treeview", height=min(14, max(4, len(itens))))
    for chave in chaves:
        tabela.heading(chave, text=chave.replace("_", " ").upper())
        tabela.column(chave, width=145, minwidth=85, anchor="w")
    for item in itens:
        tabela.insert("", "end", values=[_texto(item.get(chave)) for chave in chaves])
    barra = ttk.Scrollbar(parent, orient="horizontal", command=tabela.xview, style="Dark.Horizontal.TScrollbar")
    tabela.configure(xscrollcommand=barra.set); tabela.pack(fill="both", expand=True, padx=12, pady=(12, 0)); barra.pack(fill="x", padx=12, pady=(0, 12))


def _renderizar_secao(parent, valor) -> None:
    if isinstance(valor, list):
        _renderizar_lista(parent, valor); return
    if isinstance(valor, dict):
        simples = {k: v for k, v in valor.items() if not isinstance(v, (dict, list))}
        compostos = {k: v for k, v in valor.items() if isinstance(v, (dict, list))}
        for chave, item in simples.items():
            linha = tk.Frame(parent, bg=CORES["card_secundario"]); linha.pack(fill="x", padx=12, pady=3)
            tk.Label(linha, text=chave.replace("_centavos", "").replace("_", " ").upper(), width=27, anchor="w",
                     bg=CORES["card_secundario"], fg=CORES["text_sec"], font=("Inter", 8, "bold")).pack(side="left", padx=10, pady=8)
            tk.Label(linha, text=_texto(item), anchor="w", bg=CORES["card_secundario"], fg=CORES["text"],
                     font=FONTES["texto"], wraplength=680, justify="left").pack(side="left", fill="x", expand=True, padx=(0, 10))
        for chave, item in compostos.items():
            quadro = tk.LabelFrame(parent, text=chave.replace("_", " ").upper(), bg=CORES["card"], fg=CORES["text_sec"], bd=1)
            quadro.pack(fill="both", expand=True, padx=12, pady=7); _renderizar_secao(quadro, item)
        return
    tk.Label(parent, text=_texto(valor), bg=CORES["card"], fg=CORES["text"], font=FONTES["texto"]).pack(anchor="w", padx=16, pady=16)


class JanelaFuncionario360:
    def __init__(self, root, colaborador_id: int, *, visao: str | None = None):
        self.root = root; self.colaborador_id = int(colaborador_id); self.visao = visao; self._foto = None
        self.janela = tk.Toplevel(root); self.janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(self.janela, root, 1160, 780, minimo=(900, 600))
        self._carregar()

    def _carregar(self):
        try:
            self.dados = obter_funcionario_360(self.colaborador_id, SESSAO.usuario, visao=self.visao)
        except (ValueError, PermissionError) as erro:
            messagebox.showerror("Funcionário 360°", str(erro), parent=self.janela); self.janela.destroy(); return
        identidade = self.dados["secoes"].get("identidade", {})
        self.janela.title(f"Funcionário 360° · {identidade.get('nome') or self.colaborador_id}")
        for filho in self.janela.winfo_children():
            filho.destroy()
        topo = tk.Frame(self.janela, bg=CORES["card"]); topo.pack(fill="x", padx=18, pady=18)
        info = tk.Frame(topo, bg=CORES["card"]); info.pack(side="left", fill="both", expand=True, padx=18, pady=18)
        tk.Label(info, text=identidade.get("nome") or "Colaborador", bg=CORES["card"], fg=CORES["text"], font=FONTES["titulo"]).pack(anchor="w")
        tk.Label(info, text=f"{identidade.get('matricula') or 'Sem matrícula'}  ·  Visão {self.dados['visao'].replace('_', ' ').title()}",
                 bg=CORES["card"], fg=CORES["purple"], font=FONTES["texto"]).pack(anchor="w", pady=(4, 0))
        tk.Label(
            info,
            text="Identidade, vínculo, documentos, jornada, ativos, acessos e histórico em um só perfil.",
            bg=CORES["card"], fg=CORES["text_sec"], font=FONTES["micro"],
        ).pack(anchor="w", pady=(8, 0))
        if not self.dados.get("somente_leitura"):
            botao_acao = tk.Menubutton(
                info, text="+  AÇÃO", font=FONTES["destaque"], bg=CORES["primary"],
                fg=CORES["on_primary"], activebackground=CORES["primary_hover"],
                activeforeground=CORES["on_primary"], relief="flat", bd=0, cursor="hand2", padx=16, pady=8,
            )
            menu = tk.Menu(botao_acao, tearoff=False, bg=CORES["card"], fg=CORES["text"], activebackground=CORES["primary_soft"])
            menu.add_command(label="Editar dados profissionais", command=self._editar_dados)
            menu.add_command(label="Adicionar dependente", command=self._adicionar_dependente)
            menu.add_command(label="Solicitar férias ou ausência", command=self._solicitar_ausencia)
            menu.add_command(label="Vincular equipamento", command=self._vincular_equipamento)
            menu.add_separator()
            menu.add_command(label="Registrar feedback", command=self._registrar_feedback)
            menu.add_command(label="Registrar ocorrência", command=self._registrar_ocorrencia)
            menu.add_separator()
            menu.add_command(label="Iniciar desligamento", command=self._iniciar_desligamento)
            botao_acao.configure(menu=menu); botao_acao.pack(anchor="w", pady=(13, 0))

        # A foto fica explicitamente à direita do nome e possui uma ação sempre
        # visível. O estado sem imagem usa iniciais, não um ícone ambíguo.
        acoes = tk.Frame(topo, bg=CORES["card"]); acoes.pack(side="right", padx=18, pady=12)
        iniciais = "".join(
            parte[:1] for parte in str(identidade.get("nome") or "Colaborador").split()[:2]
        ).upper() or "CO"
        tk.Label(acoes, text="FOTO DO COLABORADOR", bg=CORES["card"], fg=CORES["primary"], font=("Inter", 8, "bold")).pack()
        self.avatar = tk.Label(
            acoes, text=iniciais, width=12, height=5,
            bg=CORES["primary_soft"], fg=CORES["purple"],
            font=("Inter", 24, "bold"), bd=0,
        )
        self.avatar.pack(pady=(5, 7)); self._carregar_avatar()
        criar_botao(acoes, "ADICIONAR / ALTERAR FOTO", self._alterar_foto, tipo="secundario", compacto=True).pack(fill="x", pady=(0, 10))
        tk.Label(acoes, text="VISÃO", bg=CORES["card"], fg=CORES["text_sec"], font=("Inter", 8, "bold")).pack(anchor="e")
        combo = ttk.Combobox(acoes, state="readonly", width=18, values=self.dados["visoes_disponiveis"], style="Dark.TCombobox")
        combo.set(self.dados["visao"]); combo.pack(pady=(3, 0))
        combo.bind("<<ComboboxSelected>>", lambda _e: self._trocar_visao(combo.get()))
        abas = ttk.Notebook(self.janela, style="Dark.TNotebook"); abas.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        for chave, valor in self.dados["secoes"].items():
            aba = tk.Frame(abas, bg=CORES["card"]); abas.add(aba, text=ROTULOS.get(chave, chave.replace("_", " ").title()))
            _renderizar_secao(aba, valor)

    def _trocar_visao(self, visao: str):
        self.visao = visao; self._carregar()

    def _alterar_foto(self):
        caminho = filedialog.askopenfilename(
            parent=self.janela, title="Selecionar foto", filetypes=(("Imagens", "*.jpg *.jpeg *.png *.webp *.gif"),),
        )
        if not caminho:
            return
        try:
            registrar_avatar(self.colaborador_id, caminho, SESSAO.usuario); self._carregar()
        except (ValueError, PermissionError, FileNotFoundError) as erro:
            messagebox.showerror("Funcionário 360°", str(erro), parent=self.janela)

    def _carregar_avatar(self):
        if Image is None or ImageTk is None:
            return
        try:
            bruto, _meta = carregar_avatar(self.colaborador_id, SESSAO.usuario, miniatura=True)
            imagem = Image.open(BytesIO(bruto)); imagem.thumbnail((112, 112)); self._foto = ImageTk.PhotoImage(imagem)
            self.avatar.configure(image=self._foto, text="", width=112, height=112)
        except (ValueError, PermissionError, FileNotFoundError, OSError):
            return

    def _formulario_acao(self, titulo: str, campos: tuple, callback, *, inicial=None):
        janela = tk.Toplevel(self.janela); janela.configure(bg=CORES["bg"])
        preparar_janela_secundaria(janela, self.janela, 590, min(650, 220 + len(campos) * 64), minimo=(520, 360))
        tk.Label(janela, text=titulo, font=FONTES["titulo"], fg=CORES["text"], bg=CORES["bg"]).pack(anchor="w", padx=22, pady=(20, 10))
        corpo = tk.Frame(janela, bg=CORES["bg"]); corpo.pack(fill="both", expand=True, padx=22)
        variaveis = {}
        for chave, rotulo, tipo, opcoes in campos:
            linha = tk.Frame(corpo, bg=CORES["bg"]); linha.pack(fill="x", pady=5)
            tk.Label(linha, text=rotulo.upper(), font=FONTES["micro"], fg=CORES["text_sec"], bg=CORES["bg"], width=24, anchor="w").pack(side="left")
            valor = (inicial or {}).get(chave)
            if tipo == "bool":
                var = tk.BooleanVar(value=bool(valor)); widget = tk.Checkbutton(linha, variable=var, text="Sim", bg=CORES["bg"], fg=CORES["text"], selectcolor=CORES["input"])
            elif tipo == "combo":
                var = tk.StringVar(value=str(valor or opcoes[0])); widget = ttk.Combobox(linha, textvariable=var, values=opcoes, state="readonly", style="App.TCombobox")
            else:
                var = tk.StringVar(value="" if valor is None else str(valor)); widget = tk.Entry(linha, textvariable=var, font=FONTES["texto"], bg=CORES["input"], fg=CORES["text"], insertbackground=CORES["primary"], relief="flat")
            widget.pack(side="left", fill="x", expand=True, ipady=6 if tipo == "texto" else 0); variaveis[chave] = var
        status = tk.Label(janela, text="", font=FONTES["micro"], fg=CORES["danger"], bg=CORES["bg"]); status.pack(anchor="w", padx=22)
        def salvar():
            try:
                callback({chave: var.get() for chave, var in variaveis.items()}); janela.destroy(); self._carregar()
            except (PermissionError, ValueError, RuntimeError) as erro:
                status.configure(text=str(erro))
        criar_botao(janela, "SALVAR", salvar).pack(anchor="e", padx=22, pady=18)

    def _editar_dados(self):
        profissional = self.dados["secoes"].get("profissional", {}); contatos = self.dados["secoes"].get("contatos", {}); identidade = self.dados["secoes"].get("identidade", {})
        inicial = {"nome_completo": identidade.get("nome"), "cargo_texto": profissional.get("cargo_texto"), "email_corporativo": contatos.get("email_corporativo"), "telefone": contatos.get("telefone"), "tipo_contrato": profissional.get("tipo_contrato"), "modalidade": profissional.get("modalidade")}
        campos = (("nome_completo", "Nome completo", "texto", ()), ("cargo_texto", "Cargo", "texto", ()), ("email_corporativo", "E-mail corporativo", "texto", ()), ("telefone", "Telefone", "texto", ()), ("tipo_contrato", "Contrato", "texto", ()), ("modalidade", "Modalidade", "combo", ("Presencial", "Híbrido", "Remoto")))
        self._formulario_acao("Editar dados profissionais", campos, lambda d: atualizar_colaborador(self.colaborador_id, d, SESSAO.usuario), inicial=inicial)

    def _adicionar_dependente(self):
        campos = (("nome", "Nome", "texto", ()), ("parentesco", "Parentesco", "texto", ()), ("nascimento", "Nascimento (AAAA-MM-DD)", "texto", ()), ("cpf", "CPF", "texto", ()), ("dependente_ir", "Dependente de IR", "bool", ()))
        self._formulario_acao("Adicionar dependente", campos, lambda d: adicionar_dependente(self.colaborador_id, d, SESSAO.usuario))

    def _solicitar_ausencia(self):
        campos = (("tipo", "Tipo", "combo", ("Férias", "Ausência", "Afastamento", "Licença")), ("inicio", "Início (AAAA-MM-DD)", "texto", ()), ("fim", "Fim (AAAA-MM-DD)", "texto", ()), ("motivo", "Motivo", "texto", ()))
        self._formulario_acao("Solicitar férias ou ausência", campos, lambda d: solicitar_ferias_ausencia({**d, "colaborador_id": self.colaborador_id}, SESSAO.usuario))

    def _vincular_equipamento(self):
        campos = (("patrimonio", "Patrimônio", "texto", ()), ("descricao", "Descrição", "texto", ()), ("entregue_em", "Entregue em (AAAA-MM-DD)", "texto", ()))
        self._formulario_acao("Vincular equipamento", campos, lambda d: vincular_equipamento(self.colaborador_id, d, SESSAO.usuario))

    def _registrar_feedback(self):
        campos = (("tipo", "Tipo", "combo", ("Feedback", "Reconhecimento", "Desenvolvimento")), ("titulo", "Título", "texto", ()), ("conteudo", "Conteúdo", "texto", ()), ("visibilidade", "Visibilidade", "combo", ("RH_Gestor", "RH", "Colaborador")))
        self._formulario_acao("Registrar feedback", campos, lambda d: registrar_feedback(self.colaborador_id, d, SESSAO.usuario))

    def _registrar_ocorrencia(self):
        campos = (("categoria", "Categoria", "texto", ()), ("titulo", "Título", "texto", ()), ("descricao", "Descrição", "texto", ()), ("severidade", "Severidade", "combo", ("Baixa", "Média", "Alta", "Crítica")), ("confidencial", "Confidencial", "bool", ()))
        self._formulario_acao("Registrar ocorrência", campos, lambda d: registrar_ocorrencia(self.colaborador_id, d, SESSAO.usuario))

    def _iniciar_desligamento(self):
        campos = (("tipo", "Tipo", "combo", ("Sem justa causa", "Pedido de demissão", "Justa causa", "Acordo")), ("motivo", "Motivo", "texto", ()), ("data_prevista", "Data prevista (AAAA-MM-DD)", "texto", ()))
        self._formulario_acao("Iniciar desligamento", campos, lambda d: iniciar_desligamento(self.colaborador_id, d, SESSAO.usuario))


def abrir_funcionario_360(root, colaborador_id: int, *, visao: str | None = None):
    return JanelaFuncionario360(root, int(colaborador_id), visao=visao)


def abrir_meu_funcionario_360(root):
    try:
        dados = obter_meu_funcionario_360(SESSAO.usuario)
    except (ValueError, PermissionError) as erro:
        messagebox.showerror("Meu perfil 360°", str(erro), parent=root); return None
    return JanelaFuncionario360(root, int(dados["colaborador_id"]), visao="meu_perfil")


__all__ = ("JanelaFuncionario360", "abrir_funcionario_360", "abrir_meu_funcionario_360")
