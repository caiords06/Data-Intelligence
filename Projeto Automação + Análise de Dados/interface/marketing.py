"""Growth Studio — workspace especializado de Marketing V10.3.0."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from auth.sessao import SESSAO
from services.contexto import tem_permissao
from services.departamentos.marketing import (
    analisar_marketing,
    criar_automacao,
    criar_campanha,
    criar_canal,
    criar_contato,
    criar_conteudo,
    criar_empresa_crm,
    criar_lead,
    listar_automacoes,
    listar_campanhas,
    listar_canais,
    listar_conteudos,
    listar_contatos,
    listar_empresas_crm,
    listar_leads,
    registrar_metricas,
    resumo_marketing,
)
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_estado_vazio,
    criar_metrica,
    criar_titulo_secao,
    preparar_janela_secundaria,
)
from interface.navegacao_modulos import criar_sidebar_modulo
from interface.tema import CORES, FONTES, LAYOUT, configurar_estilos_ttk

COR_MARKETING = "#C45AA8"

GRUPOS_MENU = (
    ("MARKETING", (("visao", "📊", "Visão geral"),)),
    ("CRESCIMENTO", (
        ("campanhas", "📣", "Campanhas"),
        ("leads", "🎯", "Leads"),
        ("crm", "◎", "CRM e contatos"),
        ("canais", "⌁", "Canais"),
        ("calendario", "📅", "Calendário"),
        ("conteudo", "▤", "Conteúdo"),
    )),
    ("AUTOMAÇÃO E DADOS", (
        ("automacao", "⚙", "Automações"),
        ("atribuicao", "⇄", "Atribuição"),
        ("relatorios", "▥", "Relatórios"),
    )),
)
ROTULOS = {chave: titulo for _grupo, itens in GRUPOS_MENU for chave, _icone, titulo in itens}


def _moeda(centavos) -> str:
    valor = int(centavos or 0) / 100
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _combo(parent, var, valores):
    w = ttk.Combobox(parent, textvariable=var, values=valores, state="readonly", style="App.TCombobox")
    w.pack(fill="x", ipady=3)
    return w


class TelaMarketing:
    def __init__(self, root, navegacao, secao="visao"):
        if not tem_permissao(SESSAO.usuario, "marketing", "ler"):
            raise PermissionError("Seu perfil não possui acesso ao Marketing.")
        self.root = root
        self.navegacao = navegacao
        self.secao = secao if secao in ROTULOS else "visao"
        self.container = tk.Frame(root, bg=CORES["bg"])
        self.container.pack(fill="both", expand=True)
        self._criar_interface()

    def _criar_interface(self):
        configurar_estilos_ttk(self.root)
        criar_sidebar_modulo(
            self.container, self.navegacao, modulo="marketing", titulo="MARKETING",
            ativo=self.secao, grupos_menu=GRUPOS_MENU, grupos_recolhiveis=True,
        )
        viewport = AreaRolavel(self.container)
        viewport.pack(side="left", fill="both", expand=True, padx=LAYOUT["conteudo_padx"], pady=(22, 20))
        self.conteudo = viewport.conteudo
        render = {
            "visao": self._visao,
            "campanhas": self._campanhas,
            "leads": self._leads,
            "crm": self._crm,
            "canais": self._canais,
            "calendario": self._calendario,
            "conteudo": self._conteudo,
            "automacao": self._automacoes,
            "atribuicao": self._atribuicao,
            "relatorios": self._relatorios,
        }
        render.get(self.secao, self._visao)()

    def _cabecalho(self, titulo, subtitulo, *, acao=None):
        criar_cabecalho(
            self.conteudo, titulo, subtitulo,
            breadcrumb=f"MÓDULOS / MARKETING / {titulo.upper()}", etiqueta="GROWTH STUDIO 3.0",
            acao=acao,
        )

    def _acoes_visao(self, parent):
        bloco = tk.Frame(parent, bg=CORES["bg"])
        criar_botao(bloco, "+ CAMPANHA", self._nova_campanha, compacto=True).pack(side="right")
        criar_botao(bloco, "+ LEAD", self._novo_lead, tipo="secundario", compacto=True).pack(side="right", padx=(0, 8))
        return bloco

    def _visao(self):
        self._cabecalho(
            "Marketing e crescimento",
            "Campanhas, aquisição, conteúdo e conversão conectados ao CRM corporativo.",
            acao=self._acoes_visao,
        )
        try:
            r = resumo_marketing(SESSAO.usuario)
            analise = analisar_marketing(SESSAO.usuario)
        except (ValueError, PermissionError, ConnectionError) as erro:
            criar_estado_vazio(self.conteudo, "⚠", "Marketing indisponível", str(erro), cor=CORES["warning"]).pack(fill="x")
            return
        grade = GradeResponsiva(self.conteudo, max_colunas=4, largura_minima=190, gap=10, bg=CORES["bg"])
        grade.pack(fill="x", pady=(0, 16))
        metricas = (
            ("Investimento", _moeda(r["investimento_centavos"]), "◎"),
            ("Leads", r["leads"], "🎯"),
            ("MQLs", r["mqls"], "◇"),
            ("Conversões", r["conversoes"], "✓"),
            ("CPL", _moeda(r["cpl_centavos"]), "$"),
            ("CAC", _moeda(r["cac_centavos"]), "$"),
            ("Receita atribuída", _moeda(r["receita_centavos"]), "↗"),
            ("ROAS", f"{r['roas']:.2f}x", "📊"),
        )
        for titulo, valor, icone in metricas:
            grade.adicionar(criar_metrica(grade, titulo, valor, icone=icone, cor=COR_MARKETING))

        linha = tk.Frame(self.conteudo, bg=CORES["bg"])
        linha.pack(fill="both", expand=True)
        linha.grid_columnconfigure(0, weight=3, uniform="growth")
        linha.grid_columnconfigure(1, weight=2, uniform="growth")
        funil = criar_card(linha); funil.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        criar_titulo_secao(funil, "Funil de aquisição", "Do lead até a conversão, sem cadastros duplicados.")
        total = max(1, int(r["leads"] or 0))
        for titulo, valor in (("Leads", r["leads"]), ("MQL", r["mqls"]), ("Conversões", r["conversoes"])):
            faixa = tk.Frame(funil, bg=CORES["card"]); faixa.pack(fill="x", padx=18, pady=6)
            tk.Label(faixa, text=titulo, bg=CORES["card"], fg=CORES["text_sec"], font=FONTES["texto_pequeno"]).pack(side="left")
            tk.Label(faixa, text=str(valor), bg=CORES["card"], fg=CORES["text"], font=FONTES["destaque"]).pack(side="right")
            barra = tk.Frame(funil, bg=CORES["border_soft"], height=7); barra.pack(fill="x", padx=18, pady=(0, 4))
            tk.Frame(barra, bg=COR_MARKETING, height=7, width=max(6, int(360 * min(1, int(valor or 0)/total)))).place(x=0, y=0)
        tk.Frame(funil, bg=CORES["card"], height=12).pack()

        alertas = criar_card(linha); alertas.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        criar_titulo_secao(alertas, "O que precisa de atenção", "Insights simples e acionáveis do módulo.")
        itens = analise.get("alertas") or ["Nenhum alerta crítico de Marketing no momento."]
        for item in itens[:5]:
            tk.Label(alertas, text=f"⚠  {item}" if analise.get("alertas") else f"✓  {item}", bg=CORES["card"],
                     fg=CORES["warning"] if analise.get("alertas") else CORES["success"], font=FONTES["texto_pequeno"],
                     justify="left", wraplength=330).pack(anchor="w", padx=18, pady=7)

    def _campanhas(self):
        self._cabecalho("Campanhas", "Planeje verba, objetivo, público, canal e desempenho no mesmo lugar.",
                        acao=lambda p: self._botao_acao(p, "+ NOVA CAMPANHA", self._nova_campanha))
        dados = listar_campanhas(SESSAO.usuario)
        self._tabela(
            dados,
            (("nome","Campanha",220),("canal_nome","Canal",120),("objetivo","Objetivo",180),("status","Status",110),
             ("orcamento_centavos","Orçamento",120),("investimento_centavos","Investimento",120)),
            moedas={"orcamento_centavos","investimento_centavos"}, vazio=("📣","Nenhuma campanha","Crie a primeira campanha do Growth Studio."),
        )

    def _leads(self):
        self._cabecalho("Leads e qualificação", "Score, origem, campanha e estágio de qualificação compartilhados com o CRM.",
                        acao=lambda p: self._acoes_leads(p))
        dados = listar_leads(SESSAO.usuario)
        self._tabela(dados, (("contato_nome","Contato",190),("empresa_nome","Empresa",180),("origem","Origem",120),
                             ("campanha_nome","Campanha",170),("score","Score",70),("temperatura","Temperatura",100),("status","Status",110)),
                     vazio=("🎯","Nenhum lead","Cadastre contatos e transforme aquisição em pipeline mensurável."))

    def _acoes_leads(self, parent):
        bloco=tk.Frame(parent,bg=CORES["bg"]);
        criar_botao(bloco,"ENVIAR MQL → COMERCIAL",self._enviar_mql,tipo="sucesso",compacto=True).pack(side="right")
        criar_botao(bloco,"+ NOVO LEAD",self._novo_lead,compacto=True).pack(side="right",padx=(0,8))
        return bloco

    def _enviar_mql(self):
        from tkinter import simpledialog, messagebox
        from services.orquestracao import converter_lead_em_oportunidade
        candidatos=[x for x in listar_leads(SESSAO.usuario,limite=500) if x.get("status") in {"MQL","SQL"}]
        if not candidatos:
            messagebox.showinfo("Marketing → Comercial","Não há MQL/SQL disponível para encaminhamento.",parent=self.root); return
        resumo="\n".join(f"#{x['id']} · {x.get('contato_nome') or x.get('empresa_nome') or 'Lead'} · score {x.get('score',0)}" for x in candidatos[:20])
        lead_id=simpledialog.askinteger("Enviar ao Comercial",f"Informe o ID do lead qualificado:\n\n{resumo}",parent=self.root)
        if not lead_id: return
        try:
            resultado=converter_lead_em_oportunidade(lead_id,{},SESSAO.usuario)
            texto=(f"Oportunidade #{resultado['oportunidade_id']} criada e vinculada ao mesmo CRM." if resultado.get("criada")
                   else f"O lead já possui a oportunidade #{resultado['oportunidade_id']}.")
            messagebox.showinfo("Marketing → Comercial",texto,parent=self.root); self.abrir_secao("leads")
        except Exception as exc: messagebox.showerror("Marketing → Comercial",str(exc),parent=self.root)

    def _crm(self):
        self._cabecalho("CRM e contatos", "Base compartilhada de empresas e pessoas para Marketing e o futuro Comercial especializado.",
                        acao=lambda p: self._acoes_crm(p))
        empresas = listar_empresas_crm(SESSAO.usuario)
        contatos = listar_contatos(SESSAO.usuario)
        criar_titulo_secao(self.conteudo, "Empresas", "Contas organizacionais conhecidas pelo CRM.")
        if empresas:
            self._tabela(empresas, (("nome","Empresa",230),("segmento","Segmento",140),("porte","Porte",100),("cidade","Cidade",130),("estado","UF",70),("status","Status",90)))
        else:
            criar_estado_vazio(self.conteudo,"◎","Nenhuma empresa CRM","Cadastre uma conta para associar contatos e leads.",cor=COR_MARKETING).pack(fill="x",pady=(0,14))
        criar_titulo_secao(self.conteudo, "Contatos", "Pessoas vinculadas a empresas, com origem e responsável.")
        if contatos:
            self._tabela(contatos, (("nome","Contato",210),("empresa_nome","Empresa",190),("cargo","Cargo",140),("email","E-mail",220),("origem","Origem",110)))
        else:
            criar_estado_vazio(self.conteudo,"◇","Nenhum contato","Cadastre o primeiro contato compartilhado do CRM.",cor=COR_MARKETING).pack(fill="x")

    def _acoes_crm(self, parent):
        bloco=tk.Frame(parent,bg=CORES["bg"]); criar_botao(bloco,"+ CONTATO",self._novo_contato,compacto=True).pack(side="right"); criar_botao(bloco,"+ EMPRESA",self._nova_empresa_crm,tipo="secundario",compacto=True).pack(side="right",padx=(0,8)); return bloco

    def _canais(self):
        self._cabecalho("Canais", "Catálogo corporativo de mídia paga, orgânico, eventos, parceiros e relacionamento.",
                        acao=lambda p: self._botao_acao(p, "+ NOVO CANAL", self._novo_canal))
        self._tabela(listar_canais(SESSAO.usuario), (("nome","Canal",220),("tipo","Tipo",150),("custo_mensal_centavos","Custo mensal",130),("status","Status",100)),
                     moedas={"custo_mensal_centavos"}, vazio=("⌁","Nenhum canal","Cadastre os canais usados pela empresa."))

    def _calendario(self):
        self._cabecalho("Calendário editorial", "Conteúdos organizados por data de publicação e etapa produtiva.",
                        acao=lambda p: self._botao_acao(p, "+ CONTEÚDO", self._novo_conteudo))
        dados = listar_conteudos(SESSAO.usuario)
        self._tabela(dados, (("data_publicacao","Publicação",110),("titulo","Conteúdo",250),("formato","Formato",100),("canal","Canal",120),
                             ("campanha_nome","Campanha",170),("etapa","Etapa",110)),
                     vazio=("📅","Calendário vazio","Planeje o primeiro conteúdo e uma data de publicação."))

    def _conteudo(self):
        self._cabecalho("Estúdio de conteúdo", "Pauta, produção, revisão e publicação conectadas às campanhas.",
                        acao=lambda p: self._botao_acao(p, "+ NOVO CONTEÚDO", self._novo_conteudo))
        dados = listar_conteudos(SESSAO.usuario)
        grade = GradeResponsiva(self.conteudo, max_colunas=3, largura_minima=280, gap=10, bg=CORES["bg"]); grade.pack(fill="both", expand=True)
        if not dados:
            criar_estado_vazio(self.conteudo, "▤", "Nenhum conteúdo", "Organize pauta, formato, canal e publicação sem depender de planilhas.", cor=COR_MARKETING).pack(fill="x")
            return
        for item in dados:
            card = criar_card(grade); grade.adicionar(card)
            tk.Frame(card, bg=COR_MARKETING, height=3).pack(fill="x")
            tk.Label(card, text=item.get("etapa") or "Pauta", bg=CORES["card"], fg=COR_MARKETING, font=FONTES["micro"]).pack(anchor="e", padx=14, pady=(10,0))
            tk.Label(card, text=item.get("titulo") or "Conteúdo", bg=CORES["card"], fg=CORES["text"], font=FONTES["subtitulo"], wraplength=270, justify="left").pack(anchor="w", padx=16, pady=(2,8))
            detalhe = " · ".join(x for x in (item.get("formato"), item.get("canal"), item.get("data_publicacao")) if x)
            tk.Label(card, text=detalhe or "Sem publicação definida", bg=CORES["card"], fg=CORES["text_sec"], font=FONTES["micro"], wraplength=270).pack(anchor="w", padx=16, pady=(0,16))

    def _automacoes(self):
        self._cabecalho("Automações de Marketing", "Regras transparentes de gatilho e ação; nenhuma automação sensível fica escondida.",
                        acao=lambda p: self._botao_acao(p, "+ AUTOMAÇÃO", self._nova_automacao))
        self._tabela(listar_automacoes(SESSAO.usuario), (("nome","Automação",220),("gatilho","Gatilho",220),("acao","Ação",300),("ativo","Ativa",70)),
                     vazio=("⚙","Nenhuma automação","Cadastre regras para reduzir tarefas repetitivas do time."))

    def _atribuicao(self):
        self._cabecalho("Atribuição e performance", "Registre métricas por período e relacione investimento, leads e receita à campanha correta.")
        campanhas = listar_campanhas(SESSAO.usuario)
        if not campanhas:
            criar_estado_vazio(self.conteudo, "⇄", "Sem campanhas para atribuição", "Crie uma campanha antes de registrar métricas.", cor=COR_MARKETING).pack(fill="x")
            return
        card = criar_card(self.conteudo); card.pack(fill="x")
        criar_titulo_secao(card, "Registrar fechamento de período", "Use dados consolidados do canal ou da plataforma de mídia.")
        self._form_metricas_inline(card, campanhas)

    def _relatorios(self):
        self._cabecalho("Relatórios de Marketing", "Resumo executivo calculado diretamente sobre campanhas, CRM e métricas.")
        r = resumo_marketing(SESSAO.usuario)
        card = criar_card(self.conteudo); card.pack(fill="x")
        criar_titulo_secao(card, "Resumo atual", "Indicadores preparados para exportação e Analytics corporativo.")
        linhas = (
            ("Campanhas", r["campanhas"]), ("Campanhas ativas", r["campanhas_ativas"]), ("Leads", r["leads"]),
            ("MQLs", r["mqls"]), ("Conversões", r["conversoes"]), ("Investimento", _moeda(r["investimento_centavos"])),
            ("Receita atribuída", _moeda(r["receita_centavos"])), ("ROAS", f"{r['roas']:.2f}x"),
        )
        for nome, valor in linhas:
            linha=tk.Frame(card,bg=CORES["card"]); linha.pack(fill="x",padx=18,pady=6)
            tk.Label(linha,text=nome,bg=CORES["card"],fg=CORES["text_sec"],font=FONTES["texto_pequeno"]).pack(side="left")
            tk.Label(linha,text=str(valor),bg=CORES["card"],fg=CORES["text"],font=FONTES["destaque"]).pack(side="right")

    def _botao_acao(self, parent, texto, comando):
        bloco=tk.Frame(parent,bg=CORES["bg"]); criar_botao(bloco,texto,comando,compacto=True).pack(side="right"); return bloco

    def _tabela(self, dados, colunas, *, moedas=None, vazio=None):
        if not dados:
            icone,titulo,texto=vazio or ("◇","Nenhum registro","Não há dados para exibir.")
            criar_estado_vazio(self.conteudo,icone,titulo,texto,cor=COR_MARKETING).pack(fill="x")
            return
        moedas=moedas or set(); card=criar_card(self.conteudo); card.pack(fill="both",expand=True)
        area=tk.Frame(card,bg=CORES["card"]); area.pack(fill="both",expand=True,padx=16,pady=16)
        nomes=[c[0] for c in colunas]
        tabela=ttk.Treeview(area,columns=nomes,show="headings",style="App.Treeview")
        for chave,titulo,largura in colunas:
            tabela.heading(chave,text=titulo); tabela.column(chave,width=largura,minwidth=max(65,largura//2),stretch=True)
        for item in dados:
            vals=[]
            for chave,_,_ in colunas:
                valor=item.get(chave)
                if chave in moedas: valor=_moeda(valor)
                elif chave=="ativo": valor="Sim" if bool(valor) else "Não"
                vals.append("—" if valor in (None,"") else valor)
            tabela.insert("","end",values=vals)
        sy=ttk.Scrollbar(area,orient="vertical",command=tabela.yview,style="App.Vertical.TScrollbar")
        sx=ttk.Scrollbar(area,orient="horizontal",command=tabela.xview,style="App.Horizontal.TScrollbar")
        tabela.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        tabela.grid(row=0,column=0,sticky="nsew"); sy.grid(row=0,column=1,sticky="ns"); sx.grid(row=1,column=0,sticky="ew")
        area.grid_rowconfigure(0,weight=1,minsize=280); area.grid_columnconfigure(0,weight=1)

    def _campo(self, parent, rotulo, var, *, valores=None):
        tk.Label(parent,text=rotulo.upper(),bg=CORES["bg"],fg=CORES["text_sec"],font=("Inter",8,"bold")).pack(anchor="w",pady=(9,4))
        if valores is not None: return _combo(parent,var,valores)
        w=tk.Entry(parent,textvariable=var,bg=CORES["input"],fg=CORES["text"],insertbackground=COR_MARKETING,relief="flat")
        w.pack(fill="x",ipady=8); return w

    def _dialogo(self, titulo, largura=620, altura=680):
        j=tk.Toplevel(self.root); j.title(titulo); j.configure(bg=CORES["bg"]); preparar_janela_secundaria(j,self.root,largura,altura,minimo=(520,460),modal=True)
        area=AreaRolavel(j); area.pack(fill="both",expand=True,padx=24,pady=20); return j,area.conteudo

    def _nova_campanha(self):
        j,a=self._dialogo("Nova campanha"); canais=listar_canais(SESSAO.usuario)
        vars={k:tk.StringVar() for k in ("nome","objetivo","publico","orcamento","investimento","inicio","fim")}
        canal=tk.StringVar(); status=tk.StringVar(value="Planejada")
        self._campo(a,"Nome",vars["nome"]); self._campo(a,"Objetivo",vars["objetivo"]); self._campo(a,"Público",vars["publico"])
        mapa={f"{x['nome']} · {x['tipo']}":x["id"] for x in canais}; self._campo(a,"Canal",canal,valores=list(mapa))
        self._campo(a,"Orçamento",vars["orcamento"]); self._campo(a,"Investimento inicial",vars["investimento"])
        self._campo(a,"Início",vars["inicio"]); self._campo(a,"Fim",vars["fim"]); self._campo(a,"Status",status,valores=sorted(("Planejada","Em produção","Ativa","Pausada","Concluída")))
        def salvar():
            try: criar_campanha({**{k:v.get() for k,v in vars.items()},"canal_id":mapa.get(canal.get()),"status":status.get()},SESSAO.usuario)
            except (ValueError,PermissionError) as e: messagebox.showerror("Campanha",str(e),parent=j); return
            j.destroy(); self._reabrir("campanhas")
        criar_botao(a,"CRIAR CAMPANHA",salvar).pack(anchor="e",pady=18)

    def _novo_canal(self):
        j,a=self._dialogo("Novo canal",560,520); nome=tk.StringVar(); tipo=tk.StringVar(value="Mídia paga"); custo=tk.StringVar()
        self._campo(a,"Nome",nome); self._campo(a,"Tipo",tipo,valores=("Mídia paga","Orgânico","E-mail","Evento","Parceiro","Social","Outro")); self._campo(a,"Custo mensal",custo)
        def salvar():
            try: criar_canal({"nome":nome.get(),"tipo":tipo.get(),"custo_mensal":custo.get()},SESSAO.usuario)
            except (ValueError,PermissionError) as e: messagebox.showerror("Canal",str(e),parent=j); return
            j.destroy(); self._reabrir("canais")
        criar_botao(a,"SALVAR CANAL",salvar).pack(anchor="e",pady=18)

    def _nova_empresa_crm(self):
        j,a=self._dialogo("Nova empresa CRM",600,650); campos={k:tk.StringVar() for k in ("nome","nome_fantasia","cnpj","segmento","porte","site","cidade","estado")}
        for rotulo,chave in (("Nome","nome"),("Nome fantasia","nome_fantasia"),("CNPJ","cnpj"),("Segmento","segmento"),("Porte","porte"),("Site","site"),("Cidade","cidade"),("Estado / UF","estado")): self._campo(a,rotulo,campos[chave])
        def salvar():
            try: criar_empresa_crm({k:v.get() for k,v in campos.items()},SESSAO.usuario)
            except (ValueError,PermissionError) as e: messagebox.showerror("CRM",str(e),parent=j); return
            j.destroy(); self._reabrir("crm")
        criar_botao(a,"CRIAR EMPRESA",salvar).pack(anchor="e",pady=18)

    def _novo_contato(self):
        j,a=self._dialogo("Novo contato CRM",600,650); empresas=listar_empresas_crm(SESSAO.usuario); mapa={x["nome"]:x["id"] for x in empresas}; empresa=tk.StringVar()
        campos={k:tk.StringVar() for k in ("nome","cargo","email","telefone","linkedin","origem")}
        self._campo(a,"Empresa",empresa,valores=[""]+list(mapa))
        for rotulo,chave in (("Nome","nome"),("Cargo","cargo"),("E-mail","email"),("Telefone","telefone"),("LinkedIn","linkedin"),("Origem","origem")): self._campo(a,rotulo,campos[chave])
        def salvar():
            try: criar_contato({**{k:v.get() for k,v in campos.items()},"crm_empresa_id":mapa.get(empresa.get())},SESSAO.usuario)
            except (ValueError,PermissionError) as e: messagebox.showerror("CRM",str(e),parent=j); return
            j.destroy(); self._reabrir("crm")
        criar_botao(a,"CRIAR CONTATO",salvar).pack(anchor="e",pady=18)

    def _novo_lead(self):
        j,a=self._dialogo("Novo lead",620,720)
        contatos=listar_contatos(SESSAO.usuario); empresas=listar_empresas_crm(SESSAO.usuario); campanhas=listar_campanhas(SESSAO.usuario)
        contato=tk.StringVar(); empresa=tk.StringVar(); campanha=tk.StringVar(); origem=tk.StringVar(); score=tk.StringVar(value="0"); status=tk.StringVar(value="Novo")
        map_cont={x["nome"]:x["id"] for x in contatos}; map_emp={x["nome"]:x["id"] for x in empresas}; map_camp={x["nome"]:x["id"] for x in campanhas}
        if not contatos:
            tk.Label(a,text="DICA: cadastre um contato CRM antes ou crie um lead sem contato para classificar depois.",bg=CORES["bg"],fg=CORES["text_muted"],font=FONTES["micro"],wraplength=480,justify="left").pack(anchor="w",pady=(0,8))
        self._campo(a,"Contato",contato,valores=[""]+list(map_cont)); self._campo(a,"Empresa CRM",empresa,valores=[""]+list(map_emp)); self._campo(a,"Campanha",campanha,valores=[""]+list(map_camp))
        self._campo(a,"Origem",origem); self._campo(a,"Score (0-100)",score); self._campo(a,"Status",status,valores=("Novo","Em nutrição","MQL","SQL","Convertido","Descartado"))
        def salvar():
            try: criar_lead({"contato_id":map_cont.get(contato.get()),"crm_empresa_id":map_emp.get(empresa.get()),"campanha_id":map_camp.get(campanha.get()),"origem":origem.get(),"score":score.get(),"status":status.get()},SESSAO.usuario)
            except (ValueError,PermissionError) as e: messagebox.showerror("Lead",str(e),parent=j); return
            j.destroy(); self._reabrir("leads")
        criar_botao(a,"CRIAR LEAD",salvar).pack(anchor="e",pady=18)

    def _novo_conteudo(self):
        j,a=self._dialogo("Novo conteúdo",600,680); campanhas=listar_campanhas(SESSAO.usuario); mapa={x["nome"]:x["id"] for x in campanhas}
        titulo=tk.StringVar(); formato=tk.StringVar(value="Post"); canal=tk.StringVar(); etapa=tk.StringVar(value="Pauta"); data=tk.StringVar(); campanha=tk.StringVar(); obs=tk.StringVar()
        self._campo(a,"Título",titulo); self._campo(a,"Formato",formato,valores=("Post","Vídeo","E-mail","Landing page","Artigo","Evento","Peça")); self._campo(a,"Canal",canal)
        self._campo(a,"Etapa",etapa,valores=("Pauta","Produção","Revisão","Aprovado","Publicado")); self._campo(a,"Data de publicação",data); self._campo(a,"Campanha",campanha,valores=[""]+list(mapa)); self._campo(a,"Observações",obs)
        def salvar():
            try: criar_conteudo({"titulo":titulo.get(),"formato":formato.get(),"canal":canal.get(),"etapa":etapa.get(),"data_publicacao":data.get(),"campanha_id":mapa.get(campanha.get()),"observacoes":obs.get()},SESSAO.usuario)
            except (ValueError,PermissionError) as e: messagebox.showerror("Conteúdo",str(e),parent=j); return
            j.destroy(); self._reabrir("conteudo")
        criar_botao(a,"SALVAR CONTEÚDO",salvar).pack(anchor="e",pady=18)

    def _nova_automacao(self):
        j,a=self._dialogo("Nova automação",580,570); nome=tk.StringVar(); gatilho=tk.StringVar(); acao=tk.StringVar()
        self._campo(a,"Nome",nome); self._campo(a,"Gatilho",gatilho); self._campo(a,"Ação",acao)
        def salvar():
            try: criar_automacao({"nome":nome.get(),"gatilho":gatilho.get(),"acao":acao.get()},SESSAO.usuario)
            except (ValueError,PermissionError) as e: messagebox.showerror("Automação",str(e),parent=j); return
            j.destroy(); self._reabrir("automacao")
        criar_botao(a,"CRIAR AUTOMAÇÃO",salvar).pack(anchor="e",pady=18)

    def _form_metricas_inline(self, card, campanhas):
        area=tk.Frame(card,bg=CORES["card"]); area.pack(fill="x",padx=18,pady=(0,18)); mapa={x["nome"]:x["id"] for x in campanhas}
        campanha=tk.StringVar(value=next(iter(mapa))); referencia=tk.StringVar(); vars={k:tk.StringVar(value="0") for k in ("impressoes","cliques","leads","mqls","conversoes","investimento","receita")}
        tk.Label(area,text="CAMPANHA",bg=CORES["card"],fg=CORES["text_sec"],font=("Inter",8,"bold")).pack(anchor="w",pady=(4,4)); _combo(area,campanha,list(mapa))
        for rotulo,chave in (("Referência (AAAA-MM)","referencia"),("Impressões","impressoes"),("Cliques","cliques"),("Leads","leads"),("MQLs","mqls"),("Conversões","conversoes"),("Investimento","investimento"),("Receita","receita")):
            v=referencia if chave=="referencia" else vars[chave]
            tk.Label(area,text=rotulo.upper(),bg=CORES["card"],fg=CORES["text_sec"],font=("Inter",8,"bold")).pack(anchor="w",pady=(8,4))
            tk.Entry(area,textvariable=v,bg=CORES["input"],fg=CORES["text"],insertbackground=COR_MARKETING,relief="flat").pack(fill="x",ipady=7)
        def salvar():
            try: registrar_metricas(mapa[campanha.get()],referencia.get(),{k:v.get() for k,v in vars.items()},SESSAO.usuario)
            except (ValueError,PermissionError) as e: messagebox.showerror("Métricas",str(e),parent=self.root); return
            messagebox.showinfo("Métricas","Métricas registradas com sucesso.",parent=self.root); self._reabrir("atribuicao")
        criar_botao(area,"REGISTRAR MÉTRICAS",salvar).pack(anchor="e",pady=(14,0))

    def _reabrir(self, secao):
        callback=self.navegacao.get("secao_modulo")
        if callable(callback): callback("marketing",secao)
