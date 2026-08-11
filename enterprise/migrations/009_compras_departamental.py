"""Domínio especializado de Compras e Suprimentos 2.0.

O processo preserva uma cadeia única entre necessidade, solicitação,
aprovação, cotação, negociação, pedido, recebimento, estoque e
financeiro. Valores monetários são armazenados em centavos e a trilha de
histórico é imutável.
"""

from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS cmp_categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            categoria_pai_id INTEGER,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (categoria_pai_id) REFERENCES cmp_categorias(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            razao_social TEXT NOT NULL,
            nome_fantasia TEXT,
            cnpj_cpf TEXT,
            inscricao_estadual TEXT,
            inscricao_municipal TEXT,
            endereco TEXT,
            cidade TEXT,
            uf TEXT,
            telefone TEXT,
            email TEXT,
            site TEXT,
            categorias TEXT,
            dados_bancarios TEXT,
            pix TEXT,
            status_homologacao TEXT NOT NULL DEFAULT 'Em análise',
            restricoes TEXT,
            score REAL NOT NULL DEFAULT 0 CHECK (score BETWEEN 0 AND 10),
            prazo_medio_dias REAL NOT NULL DEFAULT 0 CHECK (prazo_medio_dias >= 0),
            taxa_atraso REAL NOT NULL DEFAULT 0 CHECK (taxa_atraso BETWEEN 0 AND 100),
            estoque_fornecedor_id INTEGER,
            financeiro_parte_id INTEGER,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo),
            UNIQUE (empresa_id, cnpj_cpf),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (estoque_fornecedor_id) REFERENCES est_fornecedores(id),
            FOREIGN KEY (financeiro_parte_id) REFERENCES fin_partes(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cmp_fornecedores_busca
            ON cmp_fornecedores (empresa_id, status_homologacao, razao_social);

        CREATE TABLE IF NOT EXISTS cmp_fornecedor_contatos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fornecedor_id INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Comercial',
            nome TEXT NOT NULL,
            cargo TEXT,
            email TEXT,
            telefone TEXT,
            principal INTEGER NOT NULL DEFAULT 0 CHECK (principal IN (0, 1)),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_fornecedor_documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fornecedor_id INTEGER NOT NULL,
            documento_id INTEGER,
            tipo TEXT NOT NULL,
            numero TEXT,
            emissao TEXT,
            validade TEXT,
            status TEXT NOT NULL DEFAULT 'Pendente',
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id),
            FOREIGN KEY (documento_id) REFERENCES documentos(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_fornecedor_avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            fornecedor_id INTEGER NOT NULL,
            pedido_id INTEGER,
            recebimento_id INTEGER,
            preco REAL NOT NULL CHECK (preco BETWEEN 0 AND 10),
            prazo REAL NOT NULL CHECK (prazo BETWEEN 0 AND 10),
            qualidade REAL NOT NULL CHECK (qualidade BETWEEN 0 AND 10),
            atendimento REAL NOT NULL CHECK (atendimento BETWEEN 0 AND 10),
            conformidade REAL NOT NULL CHECK (conformidade BETWEEN 0 AND 10),
            score REAL NOT NULL CHECK (score BETWEEN 0 AND 10),
            comentario TEXT,
            avaliado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id),
            FOREIGN KEY (pedido_id) REFERENCES cmp_pedidos(id),
            FOREIGN KEY (recebimento_id) REFERENCES cmp_recebimentos(id),
            FOREIGN KEY (avaliado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_solicitacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Produto',
            titulo TEXT NOT NULL,
            justificativa TEXT NOT NULL,
            prioridade TEXT NOT NULL DEFAULT 'Normal',
            necessario_em TEXT,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            solicitante_id INTEGER NOT NULL,
            gestor_id INTEGER,
            comprador_id INTEGER,
            valor_estimado_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_estimado_centavos >= 0),
            valor_aprovado_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_aprovado_centavos >= 0),
            status TEXT NOT NULL DEFAULT 'Rascunho',
            etapa TEXT NOT NULL DEFAULT 'Necessidade',
            aprovacao_id INTEGER,
            origem_modulo TEXT,
            origem_recurso_tipo TEXT,
            origem_recurso_id INTEGER,
            recorrente INTEGER NOT NULL DEFAULT 0 CHECK (recorrente IN (0, 1)),
            recorrencia TEXT,
            proxima_recorrencia TEXT,
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (solicitante_id) REFERENCES usuarios(id),
            FOREIGN KEY (gestor_id) REFERENCES usuarios(id),
            FOREIGN KEY (comprador_id) REFERENCES usuarios(id),
            FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cmp_solicitacoes_fila
            ON cmp_solicitacoes (empresa_id, filial_id, status, prioridade, criado_em DESC);

        CREATE TABLE IF NOT EXISTS cmp_solicitacao_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            solicitacao_id INTEGER NOT NULL,
            estoque_item_id INTEGER,
            catalogo_item_id INTEGER,
            categoria_id INTEGER,
            descricao TEXT NOT NULL,
            especificacao TEXT,
            marca_sugerida TEXT,
            modelo_sugerido TEXT,
            quantidade REAL NOT NULL CHECK (quantidade > 0),
            unidade TEXT NOT NULL DEFAULT 'UN',
            valor_estimado_unitario_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_estimado_unitario_centavos >= 0),
            valor_estimado_total_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_estimado_total_centavos >= 0),
            quantidade_aprovada REAL,
            observacao TEXT,
            FOREIGN KEY (solicitacao_id) REFERENCES cmp_solicitacoes(id),
            FOREIGN KEY (estoque_item_id) REFERENCES est_itens(id),
            FOREIGN KEY (catalogo_item_id) REFERENCES cmp_catalogo(id),
            FOREIGN KEY (categoria_id) REFERENCES cmp_categorias(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_regras_aprovacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            valor_minimo_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_minimo_centavos >= 0),
            valor_maximo_centavos INTEGER CHECK (valor_maximo_centavos IS NULL OR valor_maximo_centavos >= valor_minimo_centavos),
            prioridade TEXT,
            departamento_id INTEGER,
            exige_financeiro INTEGER NOT NULL DEFAULT 0 CHECK (exige_financeiro IN (0, 1)),
            exige_diretor INTEGER NOT NULL DEFAULT 0 CHECK (exige_diretor IN (0, 1)),
            nivel INTEGER NOT NULL DEFAULT 1 CHECK (nivel > 0),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_cotacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            solicitacao_id INTEGER NOT NULL,
            comprador_id INTEGER NOT NULL,
            resposta_ate TEXT,
            condicoes_desejadas TEXT,
            status TEXT NOT NULL DEFAULT 'Em andamento',
            fornecedor_selecionado_id INTEGER,
            motivo_escolha TEXT,
            valor_referencia_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_referencia_centavos >= 0),
            valor_selecionado_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_selecionado_centavos >= 0),
            saving_centavos INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            encerrado_em TEXT,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (solicitacao_id) REFERENCES cmp_solicitacoes(id),
            FOREIGN KEY (comprador_id) REFERENCES usuarios(id),
            FOREIGN KEY (fornecedor_selecionado_id) REFERENCES cmp_fornecedores(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_cotacao_fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cotacao_id INTEGER NOT NULL,
            fornecedor_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Convidado',
            proposta_em TEXT,
            validade_proposta TEXT,
            prazo_entrega_dias INTEGER NOT NULL DEFAULT 0 CHECK (prazo_entrega_dias >= 0),
            frete_centavos INTEGER NOT NULL DEFAULT 0 CHECK (frete_centavos >= 0),
            impostos_centavos INTEGER NOT NULL DEFAULT 0 CHECK (impostos_centavos >= 0),
            desconto_centavos INTEGER NOT NULL DEFAULT 0 CHECK (desconto_centavos >= 0),
            valor_total_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_total_centavos >= 0),
            forma_pagamento TEXT,
            parcelamento TEXT,
            garantia TEXT,
            condicoes_comerciais TEXT,
            score_preco REAL NOT NULL DEFAULT 0,
            score_prazo REAL NOT NULL DEFAULT 0,
            score_qualidade REAL NOT NULL DEFAULT 0,
            score_total REAL NOT NULL DEFAULT 0,
            selecionado INTEGER NOT NULL DEFAULT 0 CHECK (selecionado IN (0, 1)),
            UNIQUE (cotacao_id, fornecedor_id),
            FOREIGN KEY (cotacao_id) REFERENCES cmp_cotacoes(id),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_cotacao_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cotacao_fornecedor_id INTEGER NOT NULL,
            solicitacao_item_id INTEGER NOT NULL,
            quantidade REAL NOT NULL CHECK (quantidade > 0),
            valor_unitario_centavos INTEGER NOT NULL CHECK (valor_unitario_centavos >= 0),
            valor_total_centavos INTEGER NOT NULL CHECK (valor_total_centavos >= 0),
            marca TEXT,
            modelo TEXT,
            observacao TEXT,
            FOREIGN KEY (cotacao_fornecedor_id) REFERENCES cmp_cotacao_fornecedores(id),
            FOREIGN KEY (solicitacao_item_id) REFERENCES cmp_solicitacao_itens(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_negociacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cotacao_fornecedor_id INTEGER NOT NULL,
            rodada INTEGER NOT NULL DEFAULT 1 CHECK (rodada > 0),
            proposta_anterior_centavos INTEGER NOT NULL DEFAULT 0 CHECK (proposta_anterior_centavos >= 0),
            proposta_nova_centavos INTEGER NOT NULL DEFAULT 0 CHECK (proposta_nova_centavos >= 0),
            desconto_obtido_centavos INTEGER NOT NULL DEFAULT 0,
            prazo_anterior_dias INTEGER,
            prazo_novo_dias INTEGER,
            condicoes TEXT,
            observacao TEXT,
            responsavel_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cotacao_fornecedor_id) REFERENCES cmp_cotacao_fornecedores(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            solicitacao_id INTEGER,
            cotacao_id INTEGER,
            fornecedor_id INTEGER NOT NULL,
            comprador_id INTEGER NOT NULL,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            entrega_endereco TEXT,
            entrega_contato TEXT,
            previsao_entrega TEXT,
            condicao_pagamento TEXT,
            vencimento TEXT,
            parcelas INTEGER NOT NULL DEFAULT 1 CHECK (parcelas > 0),
            subtotal_centavos INTEGER NOT NULL DEFAULT 0 CHECK (subtotal_centavos >= 0),
            frete_centavos INTEGER NOT NULL DEFAULT 0 CHECK (frete_centavos >= 0),
            impostos_centavos INTEGER NOT NULL DEFAULT 0 CHECK (impostos_centavos >= 0),
            desconto_centavos INTEGER NOT NULL DEFAULT 0 CHECK (desconto_centavos >= 0),
            valor_total_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_total_centavos >= 0),
            status TEXT NOT NULL DEFAULT 'Rascunho',
            aprovacao_id INTEGER,
            enviado_em TEXT,
            confirmado_em TEXT,
            encerrado_em TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (solicitacao_id) REFERENCES cmp_solicitacoes(id),
            FOREIGN KEY (cotacao_id) REFERENCES cmp_cotacoes(id),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id),
            FOREIGN KEY (comprador_id) REFERENCES usuarios(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_cmp_pedidos_entrega
            ON cmp_pedidos (empresa_id, filial_id, status, previsao_entrega);

        CREATE TABLE IF NOT EXISTS cmp_pedido_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            solicitacao_item_id INTEGER,
            estoque_item_id INTEGER,
            descricao TEXT NOT NULL,
            quantidade REAL NOT NULL CHECK (quantidade > 0),
            quantidade_recebida REAL NOT NULL DEFAULT 0 CHECK (quantidade_recebida >= 0),
            unidade TEXT NOT NULL DEFAULT 'UN',
            valor_unitario_centavos INTEGER NOT NULL CHECK (valor_unitario_centavos >= 0),
            valor_total_centavos INTEGER NOT NULL CHECK (valor_total_centavos >= 0),
            FOREIGN KEY (pedido_id) REFERENCES cmp_pedidos(id),
            FOREIGN KEY (solicitacao_item_id) REFERENCES cmp_solicitacao_itens(id),
            FOREIGN KEY (estoque_item_id) REFERENCES est_itens(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_recebimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            pedido_id INTEGER NOT NULL,
            fornecedor_id INTEGER NOT NULL,
            deposito_id INTEGER,
            localizacao_id INTEGER,
            nota_fiscal TEXT,
            chave_nfe TEXT,
            documento_valor_centavos INTEGER NOT NULL DEFAULT 0 CHECK (documento_valor_centavos >= 0),
            recebido_em TEXT NOT NULL,
            recebido_por INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Em conferência',
            possui_divergencia INTEGER NOT NULL DEFAULT 0 CHECK (possui_divergencia IN (0, 1)),
            estoque_operacao_id INTEGER,
            financeiro_lancamento_id INTEGER,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (pedido_id) REFERENCES cmp_pedidos(id),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id),
            FOREIGN KEY (deposito_id) REFERENCES est_depositos(id),
            FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id),
            FOREIGN KEY (recebido_por) REFERENCES usuarios(id),
            FOREIGN KEY (estoque_operacao_id) REFERENCES est_operacoes(id),
            FOREIGN KEY (financeiro_lancamento_id) REFERENCES fin_lancamentos(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_recebimento_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recebimento_id INTEGER NOT NULL,
            pedido_item_id INTEGER NOT NULL,
            quantidade_recebida REAL NOT NULL CHECK (quantidade_recebida >= 0),
            quantidade_aceita REAL NOT NULL CHECK (quantidade_aceita >= 0),
            quantidade_recusada REAL NOT NULL CHECK (quantidade_recusada >= 0),
            custo_unitario_centavos INTEGER NOT NULL DEFAULT 0 CHECK (custo_unitario_centavos >= 0),
            lote_numero TEXT,
            fabricacao TEXT,
            validade TEXT,
            seriais_json TEXT NOT NULL DEFAULT '[]',
            motivo_recusa TEXT,
            FOREIGN KEY (recebimento_id) REFERENCES cmp_recebimentos(id),
            FOREIGN KEY (pedido_item_id) REFERENCES cmp_pedido_itens(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_divergencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            recebimento_id INTEGER NOT NULL,
            pedido_item_id INTEGER,
            tipo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            severidade TEXT NOT NULL DEFAULT 'Média',
            status TEXT NOT NULL DEFAULT 'Aberta',
            responsavel_id INTEGER,
            resolucao TEXT,
            resolvida_em TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (recebimento_id) REFERENCES cmp_recebimentos(id),
            FOREIGN KEY (pedido_item_id) REFERENCES cmp_pedido_itens(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_contratos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            fornecedor_id INTEGER NOT NULL,
            objeto TEXT NOT NULL,
            responsavel_id INTEGER,
            departamento_id INTEGER,
            inicio TEXT NOT NULL,
            termino TEXT NOT NULL,
            valor_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_centavos >= 0),
            periodicidade TEXT,
            indice_reajuste TEXT,
            percentual_reajuste REAL NOT NULL DEFAULT 0,
            renovacao_automatica INTEGER NOT NULL DEFAULT 0 CHECK (renovacao_automatica IN (0, 1)),
            prazo_cancelamento_dias INTEGER NOT NULL DEFAULT 0 CHECK (prazo_cancelamento_dias >= 0),
            status TEXT NOT NULL DEFAULT 'Ativo',
            documento_id INTEGER,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (documento_id) REFERENCES documentos(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_contrato_aditivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contrato_id INTEGER NOT NULL,
            numero TEXT NOT NULL,
            tipo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            valor_anterior_centavos INTEGER NOT NULL DEFAULT 0,
            valor_novo_centavos INTEGER NOT NULL DEFAULT 0,
            termino_anterior TEXT,
            termino_novo TEXT,
            documento_id INTEGER,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contrato_id) REFERENCES cmp_contratos(id),
            FOREIGN KEY (documento_id) REFERENCES documentos(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            fornecedor_id INTEGER NOT NULL,
            estoque_item_id INTEGER,
            categoria_id INTEGER,
            codigo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            especificacao TEXT,
            unidade TEXT NOT NULL DEFAULT 'UN',
            preco_centavos INTEGER NOT NULL DEFAULT 0 CHECK (preco_centavos >= 0),
            prazo_dias INTEGER NOT NULL DEFAULT 0 CHECK (prazo_dias >= 0),
            validade_preco TEXT,
            homologado INTEGER NOT NULL DEFAULT 1 CHECK (homologado IN (0, 1)),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id),
            FOREIGN KEY (estoque_item_id) REFERENCES est_itens(id),
            FOREIGN KEY (categoria_id) REFERENCES cmp_categorias(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_comentarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            comentario TEXT NOT NULL,
            interno INTEGER NOT NULL DEFAULT 1 CHECK (interno IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_anexos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            documento_id INTEGER NOT NULL,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (documento_id) REFERENCES documentos(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            tipo TEXT NOT NULL,
            severidade TEXT NOT NULL DEFAULT 'Aviso',
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            recurso_tipo TEXT,
            recurso_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Aberto',
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolvido_em TEXT,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_cmp_alertas_chave
            ON cmp_alertas (
                empresa_id, COALESCE(filial_id, -1), tipo,
                COALESCE(recurso_tipo, ''), COALESCE(recurso_id, -1)
            );

        CREATE TABLE IF NOT EXISTS cmp_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER,
            acao TEXT NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER,
            antes_json TEXT,
            depois_json TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE TRIGGER IF NOT EXISTS trg_cmp_historico_sem_update
        BEFORE UPDATE ON cmp_historico
        BEGIN
            SELECT RAISE(ABORT, 'O histórico de Compras é imutável');
        END;

        CREATE TRIGGER IF NOT EXISTS trg_cmp_historico_sem_delete
        BEFORE DELETE ON cmp_historico
        BEGIN
            SELECT RAISE(ABORT, 'O histórico de Compras é imutável');
        END;

        CREATE TABLE IF NOT EXISTS cmp_permissoes_acoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            permitido INTEGER NOT NULL CHECK (permitido IN (0, 1)),
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (usuario_id, empresa_id, acao),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_relatorios_agendados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            formato TEXT NOT NULL DEFAULT 'PDF',
            frequencia TEXT NOT NULL,
            proxima_execucao TEXT,
            destinatarios TEXT,
            filtros_json TEXT NOT NULL DEFAULT '{}',
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS cmp_filtros_salvos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            secao TEXT NOT NULL,
            nome TEXT NOT NULL,
            filtros_json TEXT NOT NULL DEFAULT '{}',
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, usuario_id, secao, nome),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );
        """
    )

    empresas = conexao.execute("SELECT id FROM empresas WHERE ativo=1").fetchall()
    for empresa in empresas:
        empresa_id = int(empresa["id"])
        categorias = (
            ("INF", "Informática"), ("ESC", "Material de escritório"),
            ("LIM", "Limpeza"), ("ALI", "Alimentação"),
            ("SER", "Serviços"), ("SOF", "Software"),
            ("MAN", "Manutenção"), ("CON", "Consultoria"),
        )
        for codigo, nome in categorias:
            conexao.execute(
                "INSERT OR IGNORE INTO cmp_categorias (empresa_id,codigo,nome) VALUES (?,?,?)",
                (empresa_id, codigo, nome),
            )
        regras = (
            ("Supervisor", 0, 100_000, 1, 0, 0),
            ("Gerência", 100_001, 1_000_000, 2, 0, 0),
            ("Diretoria", 1_000_001, 5_000_000, 3, 1, 0),
            ("Diretoria e Financeiro", 5_000_001, None, 4, 1, 1),
        )
        for nome, minimo, maximo, nivel, diretor, financeiro in regras:
            existente = conexao.execute(
                "SELECT id FROM cmp_regras_aprovacao WHERE empresa_id=? AND nome=?",
                (empresa_id, nome),
            ).fetchone()
            if existente is None:
                conexao.execute(
                    """INSERT INTO cmp_regras_aprovacao (
                        empresa_id,nome,valor_minimo_centavos,valor_maximo_centavos,
                        nivel,exige_diretor,exige_financeiro
                    ) VALUES (?,?,?,?,?,?,?)""",
                    (empresa_id, nome, minimo, maximo, nivel, diretor, financeiro),
                )
