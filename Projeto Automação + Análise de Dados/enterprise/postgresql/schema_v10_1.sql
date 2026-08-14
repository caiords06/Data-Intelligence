-- Data Intelligence V10.1 — baseline PostgreSQL gerado do schema SQLite canônico V10.0.
-- Não editar manualmente sem atualizar scripts/gerar_schema_postgresql.py.
BEGIN;
SET TIME ZONE 'UTC';

CREATE TABLE aprovacoes (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                solicitante_id INTEGER NOT NULL,
                responsavel_id INTEGER,
                modulo TEXT NOT NULL,
                recurso_tipo TEXT NOT NULL,
                recurso_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                valor DOUBLE PRECISION NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Pendente'
                    CHECK (status IN ('Pendente', 'Aprovado', 'Rejeitado', 'Alteração solicitada')),
                observacao TEXT,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
                decidido_em TEXT, valor_centavos INTEGER NOT NULL DEFAULT 0, excluido_em TEXT, excluido_por INTEGER
            );

CREATE TABLE arquivos_corporativos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            modulo TEXT,
            categoria TEXT NOT NULL DEFAULT 'arquivo',
            nome TEXT NOT NULL,
            caminho_relativo TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT,
            origem TEXT NOT NULL DEFAULT 'local',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            excluido_em TEXT
        );

CREATE TABLE atividades (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                modulo TEXT NOT NULL,
                acao TEXT NOT NULL,
                descricao TEXT NOT NULL,
                recurso_tipo TEXT,
                recurso_id INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
            );

CREATE TABLE ativos_ti (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                patrimonio TEXT NOT NULL,
                nome TEXT NOT NULL,
                tipo TEXT,
                status TEXT NOT NULL DEFAULT 'Disponível',
                responsavel TEXT,
                endereco_ip TEXT,
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), filial_id INTEGER, estado_registro TEXT NOT NULL DEFAULT 'Ativo', arquivado_em TEXT, arquivado_por INTEGER, atualizado_em TEXT,
                UNIQUE (empresa_id, patrimonio)
            );

CREATE TABLE auditoria (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER,
                alvo_usuario_id INTEGER,
                acao TEXT NOT NULL,
                detalhes TEXT,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
            , empresa_id INTEGER, filial_id INTEGER, modulo TEXT, entidade TEXT, entidade_id INTEGER, dados_antes TEXT, dados_depois TEXT, operacao_id TEXT, versao_aplicacao TEXT, maquina TEXT);

CREATE TABLE backups (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER,
            usuario_id INTEGER,
            arquivo TEXT NOT NULL,
            hash_sha256 TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Válido',
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE backups_empresariais (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER,
            filial_id INTEGER,
            tipo TEXT NOT NULL DEFAULT 'Completo',
            arquivo_relativo TEXT NOT NULL,
            manifesto_relativo TEXT,
            tamanho_bytes INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            restaurado_em TEXT
        );

CREATE TABLE campanhas_marketing (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                canal TEXT NOT NULL,
                investimento DOUBLE PRECISION NOT NULL DEFAULT 0,
                leads INTEGER NOT NULL DEFAULT 0,
                conversoes INTEGER NOT NULL DEFAULT 0,
                receita DOUBLE PRECISION NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Planejada',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), filial_id INTEGER, estado_registro TEXT NOT NULL DEFAULT 'Ativo', arquivado_em TEXT, arquivado_por INTEGER, atualizado_em TEXT, investimento_centavos INTEGER NOT NULL DEFAULT 0, receita_centavos INTEGER NOT NULL DEFAULT 0
            );

CREATE TABLE centros_custo (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                departamento_id INTEGER,
                nome TEXT NOT NULL,
                codigo TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
                UNIQUE (empresa_id, codigo)
            );

CREATE TABLE chamados_ti (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                categoria TEXT,
                prioridade TEXT NOT NULL DEFAULT 'Média',
                status TEXT NOT NULL DEFAULT 'Aberto',
                responsavel TEXT,
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), filial_id INTEGER, estado_registro TEXT NOT NULL DEFAULT 'Ativo', arquivado_em TEXT, arquivado_por INTEGER, atualizado_em TEXT
            );

CREATE TABLE cmp_alertas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            tipo TEXT NOT NULL,
            severidade TEXT NOT NULL DEFAULT 'Aviso',
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            recurso_tipo TEXT,
            recurso_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Aberto',
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            resolvido_em TEXT
        );

CREATE TABLE cmp_anexos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            documento_id INTEGER NOT NULL,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE cmp_aprovacoes_solicitacao (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            solicitacao_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            perfil_aprovador TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (status IN ('Pendente','Aprovado','Rejeitado','Alteração solicitada')),
            aprovador_id INTEGER,
            comentario TEXT,
            decidido_em TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (solicitacao_id, ordem)
        );

CREATE TABLE cmp_catalogo (
            id SERIAL PRIMARY KEY,
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
            UNIQUE (empresa_id, codigo)
        );

CREATE TABLE cmp_categorias (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            categoria_pai_id INTEGER,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, codigo)
        );

CREATE TABLE cmp_comentarios (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            comentario TEXT NOT NULL,
            interno INTEGER NOT NULL DEFAULT 1 CHECK (interno IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE cmp_contrato_aditivos (
            id SERIAL PRIMARY KEY,
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
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE cmp_contratos (
            id SERIAL PRIMARY KEY,
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
            percentual_reajuste DOUBLE PRECISION NOT NULL DEFAULT 0,
            renovacao_automatica INTEGER NOT NULL DEFAULT 0 CHECK (renovacao_automatica IN (0, 1)),
            prazo_cancelamento_dias INTEGER NOT NULL DEFAULT 0 CHECK (prazo_cancelamento_dias >= 0),
            status TEXT NOT NULL DEFAULT 'Ativo',
            documento_id INTEGER,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE cmp_cotacao_fornecedores (
            id SERIAL PRIMARY KEY,
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
            score_preco DOUBLE PRECISION NOT NULL DEFAULT 0,
            score_prazo DOUBLE PRECISION NOT NULL DEFAULT 0,
            score_qualidade DOUBLE PRECISION NOT NULL DEFAULT 0,
            score_total DOUBLE PRECISION NOT NULL DEFAULT 0,
            selecionado INTEGER NOT NULL DEFAULT 0 CHECK (selecionado IN (0, 1)),
            UNIQUE (cotacao_id, fornecedor_id)
        );

CREATE TABLE cmp_cotacao_itens (
            id SERIAL PRIMARY KEY,
            cotacao_fornecedor_id INTEGER NOT NULL,
            solicitacao_item_id INTEGER NOT NULL,
            quantidade DOUBLE PRECISION NOT NULL CHECK (quantidade > 0),
            valor_unitario_centavos INTEGER NOT NULL CHECK (valor_unitario_centavos >= 0),
            valor_total_centavos INTEGER NOT NULL CHECK (valor_total_centavos >= 0),
            marca TEXT,
            modelo TEXT,
            observacao TEXT
        );

CREATE TABLE cmp_cotacoes (
            id SERIAL PRIMARY KEY,
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
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            encerrado_em TEXT,
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE cmp_divergencias (
            id SERIAL PRIMARY KEY,
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
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE cmp_filtros_salvos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            secao TEXT NOT NULL,
            nome TEXT NOT NULL,
            filtros_json TEXT NOT NULL DEFAULT '{}',
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, usuario_id, secao, nome)
        );

CREATE TABLE cmp_fornecedor_avaliacoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            fornecedor_id INTEGER NOT NULL,
            pedido_id INTEGER,
            recebimento_id INTEGER,
            preco DOUBLE PRECISION NOT NULL CHECK (preco BETWEEN 0 AND 10),
            prazo DOUBLE PRECISION NOT NULL CHECK (prazo BETWEEN 0 AND 10),
            qualidade DOUBLE PRECISION NOT NULL CHECK (qualidade BETWEEN 0 AND 10),
            atendimento DOUBLE PRECISION NOT NULL CHECK (atendimento BETWEEN 0 AND 10),
            conformidade DOUBLE PRECISION NOT NULL CHECK (conformidade BETWEEN 0 AND 10),
            score DOUBLE PRECISION NOT NULL CHECK (score BETWEEN 0 AND 10),
            comentario TEXT,
            avaliado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE cmp_fornecedor_contatos (
            id SERIAL PRIMARY KEY,
            fornecedor_id INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Comercial',
            nome TEXT NOT NULL,
            cargo TEXT,
            email TEXT,
            telefone TEXT,
            principal INTEGER NOT NULL DEFAULT 0 CHECK (principal IN (0, 1)),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
        );

CREATE TABLE cmp_fornecedor_documentos (
            id SERIAL PRIMARY KEY,
            fornecedor_id INTEGER NOT NULL,
            documento_id INTEGER,
            tipo TEXT NOT NULL,
            numero TEXT,
            emissao TEXT,
            validade TEXT,
            status TEXT NOT NULL DEFAULT 'Pendente',
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE cmp_fornecedores (
            id SERIAL PRIMARY KEY,
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
            score DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (score BETWEEN 0 AND 10),
            prazo_medio_dias DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (prazo_medio_dias >= 0),
            taxa_atraso DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (taxa_atraso BETWEEN 0 AND 100),
            estoque_fornecedor_id INTEGER,
            financeiro_parte_id INTEGER,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, codigo),
            UNIQUE (empresa_id, cnpj_cpf)
        );

CREATE TABLE cmp_historico (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER,
            acao TEXT NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER,
            antes_json TEXT,
            depois_json TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE cmp_negociacoes (
            id SERIAL PRIMARY KEY,
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
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE cmp_pedido_itens (
            id SERIAL PRIMARY KEY,
            pedido_id INTEGER NOT NULL,
            solicitacao_item_id INTEGER,
            estoque_item_id INTEGER,
            descricao TEXT NOT NULL,
            quantidade DOUBLE PRECISION NOT NULL CHECK (quantidade > 0),
            quantidade_recebida DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (quantidade_recebida >= 0),
            unidade TEXT NOT NULL DEFAULT 'UN',
            valor_unitario_centavos INTEGER NOT NULL CHECK (valor_unitario_centavos >= 0),
            valor_total_centavos INTEGER NOT NULL CHECK (valor_total_centavos >= 0)
        );

CREATE TABLE cmp_pedidos (
            id SERIAL PRIMARY KEY,
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
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE cmp_permissoes_acoes (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            permitido INTEGER NOT NULL CHECK (permitido IN (0, 1)),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (usuario_id, empresa_id, acao)
        );

CREATE TABLE cmp_recebimento_itens (
            id SERIAL PRIMARY KEY,
            recebimento_id INTEGER NOT NULL,
            pedido_item_id INTEGER NOT NULL,
            quantidade_recebida DOUBLE PRECISION NOT NULL CHECK (quantidade_recebida >= 0),
            quantidade_aceita DOUBLE PRECISION NOT NULL CHECK (quantidade_aceita >= 0),
            quantidade_recusada DOUBLE PRECISION NOT NULL CHECK (quantidade_recusada >= 0),
            custo_unitario_centavos INTEGER NOT NULL DEFAULT 0 CHECK (custo_unitario_centavos >= 0),
            lote_numero TEXT,
            fabricacao TEXT,
            validade TEXT,
            seriais_json TEXT NOT NULL DEFAULT '[]',
            motivo_recusa TEXT
        );

CREATE TABLE cmp_recebimentos (
            id SERIAL PRIMARY KEY,
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
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE cmp_regras_aprovacao (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            valor_minimo_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_minimo_centavos >= 0),
            valor_maximo_centavos INTEGER CHECK (valor_maximo_centavos IS NULL OR valor_maximo_centavos >= valor_minimo_centavos),
            prioridade TEXT,
            departamento_id INTEGER,
            exige_financeiro INTEGER NOT NULL DEFAULT 0 CHECK (exige_financeiro IN (0, 1)),
            exige_diretor INTEGER NOT NULL DEFAULT 0 CHECK (exige_diretor IN (0, 1)),
            nivel INTEGER NOT NULL DEFAULT 1 CHECK (nivel > 0),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))
        );

CREATE TABLE cmp_relatorios_agendados (
            id SERIAL PRIMARY KEY,
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
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE cmp_solicitacao_itens (
            id SERIAL PRIMARY KEY,
            solicitacao_id INTEGER NOT NULL,
            estoque_item_id INTEGER,
            catalogo_item_id INTEGER,
            categoria_id INTEGER,
            descricao TEXT NOT NULL,
            especificacao TEXT,
            marca_sugerida TEXT,
            modelo_sugerido TEXT,
            quantidade DOUBLE PRECISION NOT NULL CHECK (quantidade > 0),
            unidade TEXT NOT NULL DEFAULT 'UN',
            valor_estimado_unitario_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_estimado_unitario_centavos >= 0),
            valor_estimado_total_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_estimado_total_centavos >= 0),
            quantidade_aprovada DOUBLE PRECISION,
            observacao TEXT
        );

CREATE TABLE cmp_solicitacoes (
            id SERIAL PRIMARY KEY,
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
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE colaboradores (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                departamento_id INTEGER,
                centro_custo_id INTEGER,
                nome TEXT NOT NULL,
                email TEXT,
                cargo TEXT NOT NULL,
                salario DOUBLE PRECISION NOT NULL DEFAULT 0,
                admissao TEXT,
                desligamento TEXT,
                status TEXT NOT NULL DEFAULT 'Ativo',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), estado_registro TEXT NOT NULL DEFAULT 'Ativo', arquivado_em TEXT, arquivado_por INTEGER, atualizado_em TEXT, salario_centavos INTEGER NOT NULL DEFAULT 0
            );

CREATE TABLE conjuntos_dados (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            descricao TEXT,
            origem TEXT NOT NULL,
            nome_original TEXT NOT NULL,
            caminho_relativo TEXT NOT NULL,
            extensao TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL DEFAULT 0,
            total_registros INTEGER NOT NULL DEFAULT 0,
            total_colunas INTEGER NOT NULL DEFAULT 0,
            categoria TEXT NOT NULL DEFAULT 'automatica',
            data_inicial TEXT,
            data_final TEXT,
            status TEXT NOT NULL DEFAULT 'Pronto',
            hash_sha256 TEXT NOT NULL,
            versao INTEGER NOT NULL DEFAULT 1,
            tags TEXT NOT NULL DEFAULT '',
            responsavel_id INTEGER,
            estado_registro TEXT NOT NULL DEFAULT 'Ativo'
                CHECK (estado_registro IN ('Ativo', 'Arquivado', 'Lixeira')),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, filial_id, hash_sha256, estado_registro)
        );

CREATE TABLE contratos_juridicos (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                parte TEXT NOT NULL,
                valor DOUBLE PRECISION NOT NULL DEFAULT 0,
                risco TEXT NOT NULL DEFAULT 'Baixo',
                vencimento TEXT,
                status TEXT NOT NULL DEFAULT 'Elaboração',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), filial_id INTEGER, estado_registro TEXT NOT NULL DEFAULT 'Ativo', arquivado_em TEXT, arquivado_por INTEGER, atualizado_em TEXT, valor_centavos INTEGER NOT NULL DEFAULT 0
            );

CREATE TABLE correio_anexos (
            id SERIAL PRIMARY KEY,
            mensagem_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            arquivo_relativo TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL DEFAULT 0,
            sha256 TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE correio_destinatarios (
            id SERIAL PRIMARY KEY,
            mensagem_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'PARA' CHECK (tipo IN ('PARA','CC','CCO')),
            lida_em TEXT,
            arquivada INTEGER NOT NULL DEFAULT 0 CHECK (arquivada IN (0,1)),
            excluida INTEGER NOT NULL DEFAULT 0 CHECK (excluida IN (0,1)),
            estrela INTEGER NOT NULL DEFAULT 0 CHECK (estrela IN (0,1)),
            UNIQUE (mensagem_id, usuario_id, tipo)
        );

CREATE TABLE correio_mensagens (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            remetente_id INTEGER NOT NULL,
            assunto TEXT NOT NULL,
            corpo TEXT NOT NULL,
            modulo_origem TEXT,
            resposta_de_id INTEGER,
            encaminhada_de_id INTEGER,
            rascunho INTEGER NOT NULL DEFAULT 0 CHECK (rascunho IN (0,1)),
            excluida_remetente INTEGER NOT NULL DEFAULT 0 CHECK (excluida_remetente IN (0,1)),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            enviado_em TEXT
        );

CREATE TABLE departamentos (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                codigo TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
                UNIQUE (empresa_id, codigo)
            );

CREATE TABLE documentos (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                modulo TEXT NOT NULL,
                titulo TEXT NOT NULL,
                tipo TEXT,
                caminho_relativo TEXT NOT NULL,
                hash_sha256 TEXT,
                classificacao TEXT NOT NULL DEFAULT 'Interno',
                status TEXT NOT NULL DEFAULT 'Ativo',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), atualizado_em TEXT NOT NULL DEFAULT '', estado_registro TEXT NOT NULL DEFAULT 'Ativo'
            );

CREATE TABLE empresas (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                cnpj TEXT,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
            );

CREATE TABLE est_alertas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            tipo TEXT NOT NULL,
            severidade TEXT NOT NULL DEFAULT 'Aviso',
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            item_id INTEGER,
            deposito_id INTEGER,
            lote_id INTEGER,
            operacao_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Aberto',
            resolvido_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            resolvido_em TEXT
        );

CREATE TABLE est_categorias (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            categoria_pai_id INTEGER,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, codigo)
        );

CREATE TABLE est_custos_historico (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            operacao_id INTEGER,
            custo_anterior_centavos INTEGER NOT NULL,
            custo_novo_centavos INTEGER NOT NULL,
            quantidade_entrada DOUBLE PRECISION NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE est_depositos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Depósito',
            endereco TEXT,
            capacidade DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (capacidade >= 0),
            responsavel_id INTEGER,
            permite_negativo INTEGER NOT NULL DEFAULT 0 CHECK (permite_negativo IN (0, 1)),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, filial_id, codigo)
        );

CREATE TABLE est_fornecedores (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            documento TEXT,
            email TEXT,
            telefone TEXT,
            prazo_medio_dias INTEGER NOT NULL DEFAULT 0 CHECK (prazo_medio_dias >= 0),
            avaliacao DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (avaliacao BETWEEN 0 AND 10),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, documento)
        );

CREATE TABLE est_inventario_itens (
            id SERIAL PRIMARY KEY,
            inventario_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            localizacao_id INTEGER,
            lote_id INTEGER,
            quantidade_sistema DOUBLE PRECISION NOT NULL,
            primeira_contagem DOUBLE PRECISION,
            segunda_contagem DOUBLE PRECISION,
            quantidade_final DOUBLE PRECISION,
            divergencia DOUBLE PRECISION NOT NULL DEFAULT 0,
            motivo_divergencia TEXT,
            contado_por INTEGER,
            recontado_por INTEGER,
            contado_em TEXT,
            recontado_em TEXT,
            UNIQUE (inventario_id, item_id, localizacao_id, lote_id)
        );

CREATE TABLE est_inventarios (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            deposito_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            descricao TEXT,
            categoria_id INTEGER,
            contagem_cega INTEGER NOT NULL DEFAULT 1 CHECK (contagem_cega IN (0, 1)),
            status TEXT NOT NULL DEFAULT 'Criado',
            etapa TEXT NOT NULL DEFAULT 'Preparação',
            aprovacao_id INTEGER,
            responsavel_id INTEGER,
            previsto_inicio TEXT,
            iniciado_em TEXT,
            finalizado_em TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE est_itens (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            sku TEXT,
            codigo_barras TEXT,
            qr_code TEXT,
            nome TEXT NOT NULL,
            descricao TEXT,
            categoria_id INTEGER,
            subcategoria TEXT,
            marca TEXT,
            fabricante TEXT,
            modelo TEXT,
            unidade_id INTEGER,
            peso DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (peso >= 0),
            dimensoes TEXT,
            foto_caminho TEXT,
            fornecedor_principal_id INTEGER,
            estoque_minimo DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
            estoque_maximo DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (estoque_maximo >= 0),
            ponto_reposicao DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (ponto_reposicao >= 0),
            estoque_seguranca DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (estoque_seguranca >= 0),
            consumo_medio_dia DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (consumo_medio_dia >= 0),
            lead_time_dias INTEGER NOT NULL DEFAULT 0 CHECK (lead_time_dias >= 0),
            custo_medio_centavos INTEGER NOT NULL DEFAULT 0 CHECK (custo_medio_centavos >= 0),
            ultimo_custo_centavos INTEGER NOT NULL DEFAULT 0 CHECK (ultimo_custo_centavos >= 0),
            preco_referencia_centavos INTEGER NOT NULL DEFAULT 0 CHECK (preco_referencia_centavos >= 0),
            metodo_custeio TEXT NOT NULL DEFAULT 'Custo médio',
            controla_lote INTEGER NOT NULL DEFAULT 0 CHECK (controla_lote IN (0, 1)),
            controla_validade INTEGER NOT NULL DEFAULT 0 CHECK (controla_validade IN (0, 1)),
            controla_serie INTEGER NOT NULL DEFAULT 0 CHECK (controla_serie IN (0, 1)),
            eh_patrimonio INTEGER NOT NULL DEFAULT 0 CHECK (eh_patrimonio IN (0, 1)),
            status TEXT NOT NULL DEFAULT 'Ativo',
            origem_legado_id INTEGER,
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, codigo),
            UNIQUE (empresa_id, sku),
            UNIQUE (empresa_id, codigo_barras)
        );

CREATE TABLE est_localizacoes (
            id SERIAL PRIMARY KEY,
            deposito_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            corredor TEXT,
            prateleira TEXT,
            nivel TEXT,
            posicao TEXT,
            capacidade DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (capacidade >= 0),
            bloqueada INTEGER NOT NULL DEFAULT 0 CHECK (bloqueada IN (0, 1)),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (deposito_id, codigo)
        );

CREATE TABLE est_lotes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            fornecedor_id INTEGER,
            numero TEXT NOT NULL,
            fabricante TEXT,
            fabricacao TEXT,
            validade TEXT,
            quantidade_original DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (quantidade_original >= 0),
            status TEXT NOT NULL DEFAULT 'Disponível',
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, item_id, numero)
        );

CREATE TABLE est_movimentacoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            operacao_id INTEGER,
            item_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            localizacao_id INTEGER,
            lote_id INTEGER,
            tipo TEXT NOT NULL,
            quantidade DOUBLE PRECISION NOT NULL CHECK (quantidade != 0),
            custo_unitario_centavos INTEGER NOT NULL DEFAULT 0,
            saldo_anterior DOUBLE PRECISION NOT NULL,
            saldo_posterior DOUBLE PRECISION NOT NULL,
            centro_custo_id INTEGER,
            departamento_id INTEGER,
            motivo TEXT,
            documento TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE est_ocorrencias (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            tipo TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            lote_id INTEGER,
            serial_id INTEGER,
            quantidade DOUBLE PRECISION NOT NULL CHECK (quantidade > 0),
            motivo TEXT NOT NULL,
            destino TEXT,
            foto_caminho TEXT,
            status TEXT NOT NULL DEFAULT 'Aberta',
            aprovacao_id INTEGER,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE est_operacao_itens (
            id SERIAL PRIMARY KEY,
            operacao_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantidade_solicitada DOUBLE PRECISION NOT NULL CHECK (quantidade_solicitada > 0),
            quantidade_conferida DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (quantidade_conferida >= 0),
            custo_unitario_centavos INTEGER NOT NULL DEFAULT 0 CHECK (custo_unitario_centavos >= 0),
            lote_id INTEGER,
            lote_numero TEXT,
            fabricacao TEXT,
            validade TEXT,
            seriais_json TEXT NOT NULL DEFAULT '[]',
            divergencia_motivo TEXT,
            observacao TEXT
        );

CREATE TABLE est_operacoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            tipo TEXT NOT NULL,
            etapa TEXT NOT NULL DEFAULT 'Rascunho',
            status TEXT NOT NULL DEFAULT 'Rascunho',
            deposito_origem_id INTEGER,
            deposito_destino_id INTEGER,
            localizacao_origem_id INTEGER,
            localizacao_destino_id INTEGER,
            fornecedor_id INTEGER,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            solicitante_id INTEGER,
            responsavel_id INTEGER,
            aprovacao_id INTEGER,
            documento_numero TEXT,
            documento_id INTEGER,
            motivo TEXT,
            observacao TEXT,
            origem_modulo TEXT,
            origem_recurso_tipo TEXT,
            origem_recurso_id INTEGER,
            valor_total_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_total_centavos >= 0),
            prevista_em TEXT,
            iniciada_em TEXT,
            confirmada_em TEXT,
            recebida_em TEXT,
            cancelada_em TEXT,
            criado_por INTEGER,
            confirmado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE est_permissoes_acoes (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            permitido INTEGER NOT NULL DEFAULT 0 CHECK (permitido IN (0, 1)),
            atualizado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (usuario_id, empresa_id, acao)
        );

CREATE TABLE est_relatorios_agendados (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            tipo TEXT NOT NULL,
            formato TEXT NOT NULL,
            filtros_json TEXT NOT NULL DEFAULT '{}',
            frequencia TEXT NOT NULL,
            horario TEXT NOT NULL,
            destinatarios TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE est_reposicoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            item_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            saldo_disponivel DOUBLE PRECISION NOT NULL,
            consumo_medio_dia DOUBLE PRECISION NOT NULL,
            cobertura_dias DOUBLE PRECISION,
            quantidade_sugerida DOUBLE PRECISION NOT NULL CHECK (quantidade_sugerida > 0),
            justificativa TEXT,
            status TEXT NOT NULL DEFAULT 'Sugerida',
            solicitacao_compra_id INTEGER,
            tarefa_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE est_reservas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            localizacao_id INTEGER,
            lote_id INTEGER,
            quantidade DOUBLE PRECISION NOT NULL CHECK (quantidade > 0),
            quantidade_atendida DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (quantidade_atendida >= 0),
            solicitante_id INTEGER,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            finalidade TEXT NOT NULL,
            origem_modulo TEXT,
            origem_recurso_id INTEGER,
            expira_em TEXT,
            status TEXT NOT NULL DEFAULT 'Ativa',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE est_saldos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            item_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            localizacao_id INTEGER,
            lote_id INTEGER,
            quantidade_fisica DOUBLE PRECISION NOT NULL DEFAULT 0,
            quantidade_reservada DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (quantidade_reservada >= 0),
            quantidade_bloqueada DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (quantidade_bloqueada >= 0),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (item_id, deposito_id, localizacao_id, lote_id)
        );

CREATE TABLE est_seriais (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            lote_id INTEGER,
            numero_serie TEXT NOT NULL,
            patrimonio TEXT,
            condicao TEXT NOT NULL DEFAULT 'Novo',
            status TEXT NOT NULL DEFAULT 'Disponível',
            deposito_id INTEGER,
            localizacao_id INTEGER,
            colaborador_id INTEGER,
            garantia_ate TEXT,
            data_compra TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero_serie),
            UNIQUE (empresa_id, patrimonio)
        );

CREATE TABLE est_solicitacoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            solicitante_id INTEGER,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            item_id INTEGER NOT NULL,
            quantidade DOUBLE PRECISION NOT NULL CHECK (quantidade > 0),
            justificativa TEXT NOT NULL,
            prioridade TEXT NOT NULL DEFAULT 'Normal',
            status TEXT NOT NULL DEFAULT 'Solicitada',
            aprovacao_id INTEGER,
            reserva_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE est_unidades_medida (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            casas_decimais INTEGER NOT NULL DEFAULT 0 CHECK (casas_decimais BETWEEN 0 AND 6),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, codigo)
        );

CREATE TABLE est_usuarios_depositos (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (usuario_id, deposito_id)
        );

CREATE TABLE filiais (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                codigo TEXT NOT NULL,
                cidade TEXT,
                estado TEXT,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
                UNIQUE (empresa_id, codigo)
            );

CREATE TABLE fin_anexos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            lancamento_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            caminho_relativo TEXT NOT NULL,
            hash_sha256 TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE fin_aprovacoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            lancamento_id INTEGER NOT NULL,
            nivel INTEGER NOT NULL,
            perfil_aprovador TEXT NOT NULL,
            aprovador_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (status IN ('Pendente', 'Aprovado', 'Rejeitado', 'Alteração solicitada')),
            comentario TEXT,
            decidido_em TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (lancamento_id, nivel)
        );

CREATE TABLE fin_baixas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            lancamento_id INTEGER NOT NULL,
            conta_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            principal_centavos INTEGER NOT NULL CHECK (principal_centavos > 0),
            juros_centavos INTEGER NOT NULL DEFAULT 0 CHECK (juros_centavos >= 0),
            multa_centavos INTEGER NOT NULL DEFAULT 0 CHECK (multa_centavos >= 0),
            desconto_centavos INTEGER NOT NULL DEFAULT 0 CHECK (desconto_centavos >= 0),
            forma_pagamento TEXT,
            referencia TEXT,
            estornada INTEGER NOT NULL DEFAULT 0 CHECK (estornada IN (0, 1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE fin_cartoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            conta_id INTEGER,
            nome TEXT NOT NULL,
            final TEXT NOT NULL,
            limite_centavos INTEGER NOT NULL DEFAULT 0,
            responsavel_id INTEGER,
            centro_custo_id INTEGER,
            fechamento_dia INTEGER CHECK (fechamento_dia BETWEEN 1 AND 31),
            vencimento_dia INTEGER CHECK (vencimento_dia BETWEEN 1 AND 31),
            status TEXT NOT NULL DEFAULT 'Ativo'
                CHECK (status IN ('Ativo', 'Bloqueado', 'Cancelado')),
            UNIQUE (empresa_id, final)
        );

CREATE TABLE fin_categorias (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            natureza TEXT NOT NULL
                CHECK (natureza IN ('Receita', 'Despesa', 'Ambos')),
            plano_conta_id INTEGER,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, nome)
        );

CREATE TABLE fin_contas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            banco TEXT,
            agencia TEXT,
            numero TEXT,
            tipo TEXT NOT NULL DEFAULT 'Conta corrente'
                CHECK (tipo IN (
                    'Conta corrente', 'Poupança', 'Investimento',
                    'Caixa físico', 'Carteira digital'
                )),
            saldo_inicial_centavos INTEGER NOT NULL DEFAULT 0,
            data_saldo_inicial TEXT,
            responsavel_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Ativa'
                CHECK (status IN ('Ativa', 'Bloqueada', 'Encerrada')),
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, filial_id, nome)
        );

CREATE TABLE fin_extrato_itens (
            id SERIAL PRIMARY KEY,
            extrato_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            descricao TEXT NOT NULL,
            documento TEXT,
            valor_centavos INTEGER NOT NULL,
            identificador_banco TEXT,
            status TEXT NOT NULL DEFAULT 'Sem correspondência'
                CHECK (status IN (
                    'Sem correspondência', 'Sugerido', 'Conciliado',
                    'Divergente', 'Duplicidade', 'Ignorado'
                )),
            lancamento_id INTEGER,
            score INTEGER NOT NULL DEFAULT 0 CHECK (score BETWEEN 0 AND 100),
            conciliado_por INTEGER,
            conciliado_em TEXT,
            UNIQUE (extrato_id, identificador_banco)
        );

CREATE TABLE fin_extratos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            conta_id INTEGER NOT NULL,
            arquivo_nome TEXT NOT NULL,
            arquivo_hash TEXT NOT NULL,
            formato TEXT NOT NULL CHECK (formato IN ('OFX', 'CSV', 'XLSX')),
            importado_por INTEGER,
            importado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, conta_id, arquivo_hash)
        );

CREATE TABLE fin_lancamentos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            projeto_id INTEGER,
            conta_id INTEGER,
            conta_destino_id INTEGER,
            plano_conta_id INTEGER,
            categoria_id INTEGER,
            parte_id INTEGER,
            natureza TEXT NOT NULL CHECK (natureza IN (
                'Receita', 'Despesa', 'Transferência', 'Ajuste',
                'Conta a pagar', 'Conta a receber', 'Reembolso'
            )),
            descricao TEXT NOT NULL,
            competencia TEXT NOT NULL,
            vencimento TEXT,
            liquidacao TEXT,
            valor_original_centavos INTEGER NOT NULL
                CHECK (valor_original_centavos >= 0),
            valor_liquidado_centavos INTEGER NOT NULL DEFAULT 0
                CHECK (valor_liquidado_centavos >= 0),
            juros_centavos INTEGER NOT NULL DEFAULT 0 CHECK (juros_centavos >= 0),
            multa_centavos INTEGER NOT NULL DEFAULT 0 CHECK (multa_centavos >= 0),
            desconto_centavos INTEGER NOT NULL DEFAULT 0 CHECK (desconto_centavos >= 0),
            status TEXT NOT NULL DEFAULT 'Rascunho',
            forma_pagamento TEXT,
            documento_numero TEXT,
            nota_fiscal TEXT,
            observacoes TEXT,
            tags TEXT,
            parcela_atual INTEGER NOT NULL DEFAULT 1 CHECK (parcela_atual > 0),
            total_parcelas INTEGER NOT NULL DEFAULT 1 CHECK (total_parcelas > 0),
            grupo_parcelamento TEXT,
            recorrencia_id INTEGER,
            origem_modulo TEXT,
            origem_recurso_tipo TEXT,
            origem_recurso_id INTEGER,
            contabilizado INTEGER NOT NULL DEFAULT 0 CHECK (contabilizado IN (0, 1)),
            conciliado INTEGER NOT NULL DEFAULT 0 CHECK (conciliado IN (0, 1)),
            cancelado_em TEXT,
            cancelado_por INTEGER,
            motivo_cancelamento TEXT,
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE fin_orcamentos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            projeto_id INTEGER,
            categoria_id INTEGER,
            ano INTEGER NOT NULL CHECK (ano BETWEEN 2000 AND 2200),
            mes INTEGER NOT NULL CHECK (mes BETWEEN 1 AND 12),
            planejado_centavos INTEGER NOT NULL CHECK (planejado_centavos >= 0),
            limite_alerta_percentual INTEGER NOT NULL DEFAULT 85
                CHECK (limite_alerta_percentual BETWEEN 1 AND 100),
            status TEXT NOT NULL DEFAULT 'Planejado'
                CHECK (status IN ('Planejado', 'Aprovado', 'Revisão', 'Encerrado')),
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (
                empresa_id, filial_id, departamento_id, centro_custo_id,
                projeto_id, categoria_id, ano, mes
            )
        );

CREATE TABLE fin_partes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            tipo TEXT NOT NULL DEFAULT 'Ambos'
                CHECK (tipo IN ('Cliente', 'Fornecedor', 'Ambos')),
            nome TEXT NOT NULL,
            documento TEXT,
            email TEXT,
            telefone TEXT,
            banco TEXT,
            chave_pix TEXT,
            status TEXT NOT NULL DEFAULT 'Ativo'
                CHECK (status IN ('Ativo', 'Inativo', 'Bloqueado')),
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, documento)
        );

CREATE TABLE fin_permissoes_acoes (
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            permitido INTEGER NOT NULL DEFAULT 0 CHECK (permitido IN (0, 1)),
            atualizado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            PRIMARY KEY (usuario_id, empresa_id, acao)
        );

CREATE TABLE fin_plano_contas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            natureza TEXT NOT NULL
                CHECK (natureza IN ('Receita', 'Despesa', 'Neutra')),
            grupo_dre TEXT NOT NULL,
            conta_pai_id INTEGER,
            aceita_lancamento INTEGER NOT NULL DEFAULT 1
                CHECK (aceita_lancamento IN (0, 1)),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, codigo)
        );

CREATE TABLE fin_projetos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Ativo'
                CHECK (status IN ('Ativo', 'Concluído', 'Cancelado')),
            UNIQUE (empresa_id, codigo)
        );

CREATE TABLE fin_recorrencias (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            descricao TEXT NOT NULL,
            periodicidade TEXT NOT NULL DEFAULT 'Mensal'
                CHECK (periodicidade IN ('Semanal', 'Mensal', 'Trimestral', 'Anual')),
            inicio TEXT NOT NULL,
            fim TEXT,
            proxima_geracao TEXT,
            modelo_json TEXT NOT NULL DEFAULT '{}',
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE fin_regras_aprovacao (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            valor_minimo_centavos INTEGER NOT NULL DEFAULT 0,
            valor_maximo_centavos INTEGER,
            nivel INTEGER NOT NULL DEFAULT 1 CHECK (nivel > 0),
            perfil_aprovador TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, nome, nivel)
        );

CREATE TABLE fin_relatorios_agendados (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            filtros_json TEXT NOT NULL DEFAULT '{}',
            formato TEXT NOT NULL DEFAULT 'PDF'
                CHECK (formato IN ('PDF', 'Excel', 'CSV', 'HTML')),
            destinatarios TEXT,
            frequencia TEXT NOT NULL DEFAULT 'Manual',
            proxima_execucao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE historico_alteracoes (
            id SERIAL PRIMARY KEY,
            operacao_id TEXT NOT NULL,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER,
            modulo TEXT NOT NULL,
            entidade TEXT NOT NULL,
            entidade_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            dados_antes TEXT,
            dados_depois TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE integracoes (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                provedor TEXT NOT NULL,
                nome TEXT NOT NULL,
                referencia_credencial TEXT,
                configuracao_json TEXT NOT NULL DEFAULT '{}',
                ativo INTEGER NOT NULL DEFAULT 0 CHECK (ativo IN (0, 1)),
                ultima_sincronizacao TEXT,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), atualizado_em TEXT NOT NULL DEFAULT '',
                UNIQUE (empresa_id, provedor, nome)
            );

CREATE TABLE itens_estoque (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                codigo TEXT NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT,
                quantidade DOUBLE PRECISION NOT NULL DEFAULT 0,
                estoque_minimo DOUBLE PRECISION NOT NULL DEFAULT 0,
                custo DOUBLE PRECISION NOT NULL DEFAULT 0,
                localizacao TEXT,
                status TEXT NOT NULL DEFAULT 'Ativo',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), estado_registro TEXT NOT NULL DEFAULT 'Ativo', arquivado_em TEXT, arquivado_por INTEGER, atualizado_em TEXT, custo_centavos INTEGER NOT NULL DEFAULT 0,
                UNIQUE (empresa_id, filial_id, codigo)
            );

CREATE TABLE jobs (
            id SERIAL PRIMARY KEY,
            codigo TEXT NOT NULL UNIQUE,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (status IN (
                    'Pendente', 'Executando', 'Concluído',
                    'Falhou', 'Cancelamento solicitado', 'Cancelado'
                )),
            progresso INTEGER NOT NULL DEFAULT 0
                CHECK (progresso BETWEEN 0 AND 100),
            mensagem TEXT,
            resultado_json TEXT,
            erro TEXT,
            cancelamento_solicitado INTEGER NOT NULL DEFAULT 0
                CHECK (cancelamento_solicitado IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            iniciado_em TEXT,
            concluido_em TEXT
        );

CREATE TABLE lancamentos_financeiros (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                centro_custo_id INTEGER,
                tipo TEXT NOT NULL CHECK (tipo IN ('Receita', 'Despesa')),
                descricao TEXT NOT NULL,
                categoria TEXT,
                valor DOUBLE PRECISION NOT NULL CHECK (valor >= 0),
                vencimento TEXT,
                status TEXT NOT NULL DEFAULT 'Pendente',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), filial_id INTEGER, estado_registro TEXT NOT NULL DEFAULT 'Ativo', arquivado_em TEXT, arquivado_por INTEGER, atualizado_em TEXT, valor_centavos INTEGER NOT NULL DEFAULT 0
            );

CREATE TABLE mensagem_anexos (
            id SERIAL PRIMARY KEY,
            mensagem_id INTEGER NOT NULL,
            nome_original TEXT NOT NULL,
            caminho_relativo TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL,
            hash_sha256 TEXT NOT NULL,
            mime_type TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE mensagem_destinatarios (
            mensagem_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Para'
                CHECK (tipo IN ('Para', 'Cc', 'Cco')),
            lida INTEGER NOT NULL DEFAULT 0 CHECK (lida IN (0, 1)),
            lida_em TEXT,
            arquivada INTEGER NOT NULL DEFAULT 0 CHECK (arquivada IN (0, 1)),
            excluida INTEGER NOT NULL DEFAULT 0 CHECK (excluida IN (0, 1)),
            PRIMARY KEY (mensagem_id, usuario_id, tipo)
        );

CREATE TABLE mensagens (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            remetente_id INTEGER NOT NULL,
            assunto TEXT NOT NULL,
            corpo TEXT NOT NULL,
            prioridade TEXT NOT NULL DEFAULT 'Normal'
                CHECK (prioridade IN ('Baixa', 'Normal', 'Alta', 'Urgente')),
            status TEXT NOT NULL DEFAULT 'Enviada'
                CHECK (status IN ('Rascunho', 'Enviada', 'Cancelada')),
            resposta_de_id INTEGER,
            conversa_id TEXT NOT NULL,
            enviada_em TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE migracoes_sistema (
                chave TEXT PRIMARY KEY,
                aplicada_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
            );

CREATE TABLE movimentos_estoque (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                item_id INTEGER NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('Entrada', 'Saída', 'Ajuste')),
                quantidade DOUBLE PRECISION NOT NULL CHECK (quantidade > 0),
                observacao TEXT,
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
            );

CREATE TABLE nonces_agente (
            agent_id TEXT NOT NULL,
            nonce TEXT NOT NULL,
            usado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            PRIMARY KEY (agent_id, nonce)
        );

CREATE TABLE nos_plataforma (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            identificador TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK (tipo IN ('Servidor', 'Central', 'Agente')),
            versao TEXT,
            sistema TEXT,
            endereco_ip TEXT,
            chave_publica TEXT,
            token_hash TEXT,
            segredo_ref TEXT,
            status TEXT NOT NULL DEFAULT 'Pendente'
                CHECK (status IN ('Pendente', 'Ativo', 'Bloqueado', 'Revogado', 'Offline')),
            ultimo_heartbeat TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE notificacoes (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                modulo TEXT NOT NULL,
                titulo TEXT NOT NULL,
                mensagem TEXT NOT NULL,
                nivel TEXT NOT NULL DEFAULT 'info'
                    CHECK (nivel IN ('info', 'sucesso', 'aviso', 'critico')),
                lida INTEGER NOT NULL DEFAULT 0 CHECK (lida IN (0, 1)),
                recurso_tipo TEXT,
                recurso_id INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
            );

CREATE TABLE oportunidades_comerciais (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                cliente TEXT NOT NULL,
                etapa TEXT NOT NULL DEFAULT 'Novo',
                valor DOUBLE PRECISION NOT NULL DEFAULT 0,
                responsavel TEXT,
                status TEXT NOT NULL DEFAULT 'Aberto',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), filial_id INTEGER, estado_registro TEXT NOT NULL DEFAULT 'Ativo', arquivado_em TEXT, arquivado_por INTEGER, atualizado_em TEXT, valor_centavos INTEGER NOT NULL DEFAULT 0
            );

CREATE TABLE permissoes_modulos (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL,
                empresa_id INTEGER NOT NULL,
                modulo TEXT NOT NULL,
                pode_ler INTEGER NOT NULL DEFAULT 0 CHECK (pode_ler IN (0, 1)),
                pode_escrever INTEGER NOT NULL DEFAULT 0 CHECK (pode_escrever IN (0, 1)),
                pode_aprovar INTEGER NOT NULL DEFAULT 0 CHECK (pode_aprovar IN (0, 1)),
                atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
                UNIQUE (usuario_id, empresa_id, modulo)
            );

CREATE TABLE recursos_departamentais (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            modulo TEXT NOT NULL,
            recurso TEXT NOT NULL,
            identificacao TEXT NOT NULL,
            descricao TEXT,
            responsavel TEXT,
            status TEXT NOT NULL DEFAULT 'Pendente',
            prioridade TEXT NOT NULL DEFAULT 'Média',
            valor_centavos INTEGER NOT NULL DEFAULT 0
                CHECK (valor_centavos >= 0),
            data_referencia TEXT,
            dados_json TEXT NOT NULL DEFAULT '{}',
            estado_registro TEXT NOT NULL DEFAULT 'Ativo'
                CHECK (estado_registro IN ('Ativo', 'Arquivado', 'Lixeira')),
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            arquivado_em TEXT,
            arquivado_por INTEGER
        );

CREATE TABLE "relatorios_corporativos" (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                modulo TEXT NOT NULL DEFAULT 'analytics',
                titulo TEXT NOT NULL,
                descricao TEXT,
                formato TEXT NOT NULL DEFAULT 'HTML'
                    CHECK (formato IN ('HTML','CSV','JSON','XLSX','PDF')),
                filtros_json TEXT NOT NULL DEFAULT '{}',
                arquivo TEXT,
                status TEXT NOT NULL DEFAULT 'Rascunho',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
                atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
            );

CREATE TABLE rh_admissoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL UNIQUE,
            etapa_atual INTEGER NOT NULL DEFAULT 1 CHECK (etapa_atual BETWEEN 1 AND 8),
            status TEXT NOT NULL DEFAULT 'Em preparação',
            checklist_json TEXT NOT NULL DEFAULT '{}',
            beneficios_json TEXT NOT NULL DEFAULT '[]',
            onboarding_json TEXT NOT NULL DEFAULT '{}',
            assinatura_status TEXT NOT NULL DEFAULT 'Pendente',
            responsavel_id INTEGER,
            previsao_conclusao TEXT,
            concluido_em TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE rh_avaliacoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL,
            avaliador_id INTEGER,
            ciclo TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Gestor',
            nota DOUBLE PRECISION,
            competencias_json TEXT NOT NULL DEFAULT '{}',
            feedback TEXT,
            status TEXT NOT NULL DEFAULT 'Planejada',
            realizada_em TEXT
        );

CREATE TABLE rh_beneficios (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            fornecedor TEXT,
            custo_empresa_centavos INTEGER NOT NULL DEFAULT 0 CHECK (custo_empresa_centavos >= 0),
            desconto_colaborador_centavos INTEGER NOT NULL DEFAULT 0 CHECK (desconto_colaborador_centavos >= 0),
            elegibilidade TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, nome)
        );

CREATE TABLE rh_candidatos (
            id SERIAL PRIMARY KEY,
            vaga_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            email TEXT,
            telefone TEXT,
            curriculo_caminho TEXT,
            etapa TEXT NOT NULL DEFAULT 'Inscrição',
            nota DOUBLE PRECISION,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE rh_cargos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            departamento_id INTEGER,
            codigo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            nivel TEXT,
            descricao TEXT,
            responsabilidades TEXT,
            competencias TEXT,
            salario_minimo_centavos INTEGER NOT NULL DEFAULT 0 CHECK (salario_minimo_centavos >= 0),
            salario_referencia_centavos INTEGER NOT NULL DEFAULT 0 CHECK (salario_referencia_centavos >= 0),
            salario_maximo_centavos INTEGER NOT NULL DEFAULT 0 CHECK (salario_maximo_centavos >= 0),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, codigo)
        );

CREATE TABLE rh_colaborador_beneficios (
            id SERIAL PRIMARY KEY,
            colaborador_id INTEGER NOT NULL,
            beneficio_id INTEGER NOT NULL,
            inicio TEXT NOT NULL,
            fim TEXT,
            status TEXT NOT NULL DEFAULT 'Ativo',
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (colaborador_id, beneficio_id, inicio)
        );

CREATE TABLE rh_colaboradores (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            cargo_id INTEGER,
            gestor_id INTEGER,
            usuario_id INTEGER,
            matricula TEXT NOT NULL,
            nome_completo TEXT NOT NULL,
            nome_social TEXT,
            cpf TEXT,
            rg TEXT,
            nascimento TEXT,
            estado_civil TEXT,
            nacionalidade TEXT,
            endereco TEXT,
            telefone TEXT,
            email_pessoal TEXT,
            email_corporativo TEXT,
            contato_emergencia TEXT,
            cargo_texto TEXT NOT NULL,
            tipo_contrato TEXT NOT NULL DEFAULT 'CLT',
            modalidade TEXT NOT NULL DEFAULT 'Presencial',
            jornada_semanal DOUBLE PRECISION NOT NULL DEFAULT 44,
            admissao TEXT NOT NULL,
            experiencia_fim TEXT,
            salario_centavos INTEGER NOT NULL DEFAULT 0 CHECK (salario_centavos >= 0),
            banco TEXT,
            agencia TEXT,
            conta TEXT,
            chave_pix TEXT,
            status TEXT NOT NULL DEFAULT 'Pré-admissão',
            etapa_jornada TEXT NOT NULL DEFAULT 'Pré-admissão',
            foto_caminho TEXT,
            desligamento TEXT,
            motivo_desligamento TEXT,
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            origem_legado_id INTEGER,
            UNIQUE (empresa_id, matricula),
            UNIQUE (empresa_id, cpf)
        );

CREATE TABLE rh_contracheques (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            folha_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            caminho TEXT NOT NULL,
            hash_sha256 TEXT NOT NULL,
            gerado_por INTEGER,
            gerado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (folha_id, colaborador_id)
        );

CREATE TABLE rh_dependentes (
            id SERIAL PRIMARY KEY,
            colaborador_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            parentesco TEXT NOT NULL,
            nascimento TEXT,
            cpf TEXT,
            dependente_ir INTEGER NOT NULL DEFAULT 0 CHECK (dependente_ir IN (0, 1))
        );

CREATE TABLE rh_desligamentos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            motivo TEXT NOT NULL,
            data_prevista TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Em preparação',
            checklist_json TEXT NOT NULL DEFAULT '{}',
            entrevista_saida TEXT,
            concluido_em TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE rh_documentos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER,
            categoria TEXT NOT NULL,
            titulo TEXT NOT NULL,
            caminho TEXT NOT NULL,
            hash_sha256 TEXT NOT NULL,
            versao INTEGER NOT NULL DEFAULT 1,
            classificacao TEXT NOT NULL DEFAULT 'Confidencial',
            validade TEXT,
            assinatura_status TEXT NOT NULL DEFAULT 'Não aplicável',
            status TEXT NOT NULL DEFAULT 'Ativo',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE rh_equipamentos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL,
            patrimonio TEXT NOT NULL,
            descricao TEXT NOT NULL,
            origem_modulo TEXT,
            origem_recurso_id INTEGER,
            entregue_em TEXT NOT NULL,
            devolvido_em TEXT,
            termo_documento_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Em uso',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, patrimonio, entregue_em)
        );

CREATE TABLE rh_eventos_folha (
            id SERIAL PRIMARY KEY,
            folha_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            natureza TEXT NOT NULL CHECK (natureza IN ('Provento', 'Desconto', 'Encargo')),
            valor_centavos INTEGER NOT NULL CHECK (valor_centavos >= 0),
            origem TEXT NOT NULL DEFAULT 'Manual',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE rh_ferias_ausencias (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            inicio TEXT NOT NULL,
            fim TEXT NOT NULL,
            dias DOUBLE PRECISION NOT NULL CHECK (dias > 0),
            periodo_aquisitivo_inicio TEXT,
            periodo_aquisitivo_fim TEXT,
            saldo_antes DOUBLE PRECISION NOT NULL DEFAULT 30,
            saldo_depois DOUBLE PRECISION NOT NULL DEFAULT 30,
            abono_dias DOUBLE PRECISION NOT NULL DEFAULT 0,
            motivo TEXT,
            anexo_caminho TEXT,
            status TEXT NOT NULL DEFAULT 'Solicitado',
            aprovacao_id INTEGER,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE rh_folhas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            competencia TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Aberta',
            total_proventos_centavos INTEGER NOT NULL DEFAULT 0,
            total_descontos_centavos INTEGER NOT NULL DEFAULT 0,
            total_liquido_centavos INTEGER NOT NULL DEFAULT 0,
            encargos_centavos INTEGER NOT NULL DEFAULT 0,
            fechada_por INTEGER,
            fechada_em TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, filial_id, competencia)
        );

CREATE TABLE rh_historico_profissional (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            vigencia TEXT NOT NULL,
            dados_antes TEXT,
            dados_depois TEXT,
            observacao TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE rh_inscricoes_treinamento (
            id SERIAL PRIMARY KEY,
            treinamento_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            inscrito_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            concluido_em TEXT,
            nota DOUBLE PRECISION,
            certificado_caminho TEXT,
            status TEXT NOT NULL DEFAULT 'Inscrito',
            UNIQUE (treinamento_id, colaborador_id)
        );

CREATE TABLE rh_pdis (
            id SERIAL PRIMARY KEY,
            colaborador_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            objetivo TEXT NOT NULL,
            acoes_json TEXT NOT NULL DEFAULT '[]',
            inicio TEXT NOT NULL,
            prazo TEXT,
            progresso INTEGER NOT NULL DEFAULT 0 CHECK (progresso BETWEEN 0 AND 100),
            status TEXT NOT NULL DEFAULT 'Ativo'
        );

CREATE TABLE rh_permissoes_acoes (
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            permitido INTEGER NOT NULL CHECK (permitido IN (0, 1)),
            atualizado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            PRIMARY KEY (usuario_id, empresa_id, acao)
        );

CREATE TABLE rh_pontos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            entrada TEXT,
            intervalo_inicio TEXT,
            intervalo_fim TEXT,
            saida TEXT,
            minutos_trabalhados INTEGER NOT NULL DEFAULT 0,
            minutos_extras INTEGER NOT NULL DEFAULT 0,
            minutos_atraso INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Registrado',
            justificativa TEXT,
            aprovado_por INTEGER,
            UNIQUE (colaborador_id, data)
        );

CREATE TABLE rh_relatorios_agendados (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            tipo TEXT NOT NULL,
            formato TEXT NOT NULL,
            frequencia TEXT NOT NULL,
            destinatarios TEXT,
            filtros_json TEXT NOT NULL DEFAULT '{}',
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE rh_solicitacoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT,
            status TEXT NOT NULL DEFAULT 'Aberta',
            aprovacao_id INTEGER,
            responsavel_id INTEGER,
            resposta TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE rh_treinamentos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Interno',
            carga_horaria DOUBLE PRECISION NOT NULL DEFAULT 0,
            validade_meses INTEGER,
            obrigatorio INTEGER NOT NULL DEFAULT 0 CHECK (obrigatorio IN (0, 1)),
            custo_centavos INTEGER NOT NULL DEFAULT 0,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, titulo)
        );

CREATE TABLE rh_vagas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            departamento_id INTEGER,
            cargo_id INTEGER,
            titulo TEXT NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 1 CHECK (quantidade > 0),
            motivo TEXT,
            status TEXT NOT NULL DEFAULT 'Rascunho',
            aprovacao_id INTEGER,
            responsavel_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE solicitacoes_administrativas (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                centro_custo_id INTEGER,
                titulo TEXT NOT NULL,
                categoria TEXT NOT NULL,
                solicitante TEXT,
                valor DOUBLE PRECISION NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Pendente',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), filial_id INTEGER, estado_registro TEXT NOT NULL DEFAULT 'Ativo', arquivado_em TEXT, arquivado_por INTEGER, atualizado_em TEXT, valor_centavos INTEGER NOT NULL DEFAULT 0
            );

CREATE TABLE solicitacoes_compra (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                centro_custo_id INTEGER,
                item TEXT NOT NULL,
                quantidade DOUBLE PRECISION NOT NULL DEFAULT 1,
                fornecedor TEXT,
                valor_estimado DOUBLE PRECISION NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Pendente',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), filial_id INTEGER, estado_registro TEXT NOT NULL DEFAULT 'Ativo', arquivado_em TEXT, arquivado_por INTEGER, atualizado_em TEXT, valor_estimado_centavos INTEGER NOT NULL DEFAULT 0
            );

CREATE TABLE tarefas (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                modulo TEXT NOT NULL,
                titulo TEXT NOT NULL,
                descricao TEXT,
                responsavel_id INTEGER,
                prioridade TEXT NOT NULL DEFAULT 'Média',
                vencimento TEXT,
                status TEXT NOT NULL DEFAULT 'Pendente',
                recurso_tipo TEXT,
                recurso_id INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), atualizado_em TEXT NOT NULL DEFAULT '', estado_registro TEXT NOT NULL DEFAULT 'Ativo'
            );

CREATE TABLE ti_acessos_remotos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            ativo_id INTEGER NOT NULL,
            chamado_id INTEGER,
            tecnico_id INTEGER NOT NULL,
            provedor TEXT NOT NULL,
            identificador_destino TEXT NOT NULL,
            justificativa TEXT NOT NULL,
            consentimento_confirmado INTEGER NOT NULL DEFAULT 0 CHECK (consentimento_confirmado IN (0, 1)),
            status TEXT NOT NULL DEFAULT 'Solicitada',
            iniciado_em TEXT,
            encerrado_em TEXT,
            duracao_segundos INTEGER CHECK (duracao_segundos IS NULL OR duracao_segundos >= 0),
            resultado TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE ti_agente_nonces (
            agente_id INTEGER NOT NULL,
            nonce TEXT NOT NULL,
            recebido_em INTEGER NOT NULL,
            PRIMARY KEY (agente_id, nonce)
        );

CREATE TABLE ti_agentes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            ativo_id INTEGER NOT NULL,
            agent_id TEXT NOT NULL UNIQUE,
            token_hash TEXT NOT NULL,
            patrimonio TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Provisionado'
                CHECK (status IN ('Provisionado','Online','Degradado','Revogado')),
            ultimo_ip TEXT,
            ultima_versao TEXT,
            ultimo_heartbeat TEXT,
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            UNIQUE (ativo_id)
        );

CREATE TABLE ti_alertas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            mensagem TEXT NOT NULL,
            severidade TEXT NOT NULL DEFAULT 'Aviso',
            recurso_tipo TEXT,
            recurso_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Aberto',
            responsavel_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            reconhecido_em TEXT,
            resolvido_em TEXT,
            UNIQUE (empresa_id, tipo, recurso_tipo, recurso_id, status)
        );

CREATE TABLE ti_ativos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            patrimonio TEXT NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Computador',
            fabricante TEXT,
            modelo TEXT,
            numero_serie TEXT,
            hostname TEXT,
            endereco_ip TEXT,
            endereco_mac TEXT,
            sistema_operacional TEXT,
            processador TEXT,
            memoria_gb DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (memoria_gb >= 0),
            armazenamento_gb DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (armazenamento_gb >= 0),
            usuario_responsavel_id INTEGER,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            localizacao TEXT,
            status TEXT NOT NULL DEFAULT 'Disponível',
            estado_conectividade TEXT NOT NULL DEFAULT 'Desconhecido',
            saude_percentual DOUBLE PRECISION CHECK (saude_percentual IS NULL OR saude_percentual BETWEEN 0 AND 100),
            criticidade TEXT NOT NULL DEFAULT 'Média',
            comprado_em TEXT,
            garantia_ate TEXT,
            valor_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_centavos >= 0),
            fornecedor_id INTEGER,
            estoque_item_id INTEGER,
            agente_versao TEXT,
            ultimo_contato TEXT,
            remote_provider TEXT,
            remote_id TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), agent_id TEXT, fqdn TEXT, versao_sistema TEXT, arquitetura TEXT, usuario_sessao TEXT, remote_alias TEXT, remote_status TEXT, remote_versao TEXT,
            UNIQUE (empresa_id, patrimonio),
            UNIQUE (empresa_id, numero_serie)
        );

CREATE TABLE ti_chamado_comentarios (
            id SERIAL PRIMARY KEY,
            chamado_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            comentario TEXT NOT NULL,
            interno INTEGER NOT NULL DEFAULT 0 CHECK (interno IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE ti_chamados (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            categoria TEXT,
            subcategoria TEXT,
            prioridade TEXT NOT NULL DEFAULT 'Média',
            impacto TEXT NOT NULL DEFAULT 'Individual',
            urgencia TEXT NOT NULL DEFAULT 'Normal',
            status TEXT NOT NULL DEFAULT 'Novo',
            solicitante_id INTEGER NOT NULL,
            tecnico_id INTEGER,
            equipe TEXT,
            departamento_id INTEGER,
            ativo_id INTEGER,
            sistema_id INTEGER,
            sla_atendimento_minutos INTEGER NOT NULL DEFAULT 240 CHECK (sla_atendimento_minutos > 0),
            sla_solucao_minutos INTEGER NOT NULL DEFAULT 1440 CHECK (sla_solucao_minutos > 0),
            sla_inicia_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            primeira_resposta_em TEXT,
            resolvido_em TEXT,
            causa TEXT,
            solucao TEXT,
            satisfacao INTEGER CHECK (satisfacao IS NULL OR satisfacao BETWEEN 1 AND 5),
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE ti_conhecimento (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            categoria TEXT,
            resumo TEXT,
            conteudo TEXT NOT NULL,
            palavras_chave TEXT,
            status TEXT NOT NULL DEFAULT 'Rascunho',
            autor_id INTEGER NOT NULL,
            publicado_em TEXT,
            visualizacoes INTEGER NOT NULL DEFAULT 0 CHECK (visualizacoes >= 0),
            util_sim INTEGER NOT NULL DEFAULT 0 CHECK (util_sim >= 0),
            util_nao INTEGER NOT NULL DEFAULT 0 CHECK (util_nao >= 0),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE ti_contratos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            titulo TEXT NOT NULL,
            fornecedor_id INTEGER,
            tipo TEXT,
            inicio_em TEXT,
            termino_em TEXT,
            valor_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_centavos >= 0),
            periodicidade TEXT,
            sla TEXT,
            renovacao_automatica INTEGER NOT NULL DEFAULT 0 CHECK (renovacao_automatica IN (0, 1)),
            responsavel_id INTEGER,
            documento_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Ativo',
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE ti_dispositivos_rede (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            segmento_id INTEGER NOT NULL,
            ativo_id INTEGER,
            endereco_ip TEXT NOT NULL,
            endereco_mac TEXT,
            hostname TEXT,
            fabricante TEXT,
            tipo_estimado TEXT,
            status TEXT NOT NULL DEFAULT 'Novo',
            primeira_deteccao TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            ultima_deteccao TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            origem TEXT NOT NULL DEFAULT 'Agente',
            investigado_por INTEGER, ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)), ultimo_ping_ms DOUBLE PRECISION, observacao TEXT,
            UNIQUE (segmento_id, endereco_ip)
        );

CREATE TABLE ti_emprestimos (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            ativo_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            manutencao_id INTEGER,
            motivo TEXT,
            entregue_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            previsto_devolucao TEXT,
            devolvido_em TEXT,
            status TEXT NOT NULL DEFAULT 'Ativo',
            criado_por INTEGER
        );

CREATE TABLE ti_eventos_monitoramento (
            id SERIAL PRIMARY KEY,
            monitor_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            valor DOUBLE PRECISION,
            mensagem TEXT,
            coletado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE ti_historico (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER,
            acao TEXT NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER,
            antes_json TEXT,
            depois_json TEXT,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE ti_incidentes_seguranca (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            severidade TEXT NOT NULL DEFAULT 'Média',
            ativo_id INTEGER,
            sistema_id INTEGER,
            descricao TEXT NOT NULL,
            contencao TEXT,
            responsavel_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Aberto',
            detectado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            encerrado_em TEXT,
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE ti_licenca_atribuicoes (
            id SERIAL PRIMARY KEY,
            licenca_id INTEGER NOT NULL,
            usuario_id INTEGER,
            ativo_id INTEGER,
            identificador TEXT,
            atribuido_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            revogado_em TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            CHECK (usuario_id IS NOT NULL OR ativo_id IS NOT NULL OR identificador IS NOT NULL)
        );

CREATE TABLE ti_licencas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            fornecedor_id INTEGER,
            tipo TEXT NOT NULL DEFAULT 'Assinatura',
            quantidade_contratada INTEGER NOT NULL DEFAULT 1 CHECK (quantidade_contratada > 0),
            custo_centavos INTEGER NOT NULL DEFAULT 0 CHECK (custo_centavos >= 0),
            periodicidade TEXT NOT NULL DEFAULT 'Mensal',
            inicio_em TEXT,
            vencimento_em TEXT,
            renovacao_automatica INTEGER NOT NULL DEFAULT 0 CHECK (renovacao_automatica IN (0, 1)),
            centro_custo_id INTEGER,
            financeiro_recorrencia_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Ativa',
            criado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE ti_manutencoes (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            ativo_id INTEGER NOT NULL,
            chamado_id INTEGER,
            problema TEXT NOT NULL,
            diagnostico TEXT,
            fornecedor_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Triagem',
            inicio_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            previsao_em TEXT,
            concluido_em TEXT,
            custo_centavos INTEGER NOT NULL DEFAULT 0 CHECK (custo_centavos >= 0),
            criado_por INTEGER
        );

CREATE TABLE ti_monitores (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            ativo_id INTEGER,
            sistema_id INTEGER,
            alvo TEXT,
            intervalo_segundos INTEGER NOT NULL DEFAULT 60 CHECK (intervalo_segundos >= 30),
            limite_aviso DOUBLE PRECISION,
            limite_critico DOUBLE PRECISION,
            status TEXT NOT NULL DEFAULT 'Sem dados',
            ultimo_valor DOUBLE PRECISION,
            ultima_verificacao TEXT,
            habilitado INTEGER NOT NULL DEFAULT 1 CHECK (habilitado IN (0, 1)),
            criado_por INTEGER
        );

CREATE TABLE ti_mudancas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            motivo TEXT,
            risco TEXT NOT NULL DEFAULT 'Médio',
            impacto TEXT,
            plano_execucao TEXT NOT NULL,
            plano_rollback TEXT NOT NULL,
            janela_inicio TEXT,
            janela_fim TEXT,
            responsavel_id INTEGER NOT NULL,
            aprovacao_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Solicitada',
            resultado TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            concluido_em TEXT,
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE ti_permissoes_acoes (
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            permitido INTEGER NOT NULL DEFAULT 0 CHECK (permitido IN (0, 1)),
            atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            PRIMARY KEY (usuario_id, empresa_id, acao)
        );

CREATE TABLE ti_problema_chamados (
            problema_id INTEGER NOT NULL,
            chamado_id INTEGER NOT NULL,
            PRIMARY KEY (problema_id, chamado_id)
        );

CREATE TABLE ti_problemas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            impacto TEXT,
            causa_raiz TEXT,
            workaround TEXT,
            solucao_definitiva TEXT,
            responsavel_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Investigando',
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            concluido_em TEXT,
            UNIQUE (empresa_id, numero)
        );

CREATE TABLE "ti_segmentos_rede" (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                nome TEXT NOT NULL,
                cidr TEXT NOT NULL,
                vlan TEXT,
                gateway TEXT,
                dns TEXT,
                departamento_id INTEGER,
                autorizado INTEGER NOT NULL DEFAULT 0 CHECK (autorizado IN (0, 1)),
                justificativa_autorizacao TEXT,
                autorizado_por INTEGER,
                autorizado_em TEXT,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                firewall_status TEXT,
                firewall_regra TEXT,
                ultima_varredura_em TEXT,
                ultima_varredura_total INTEGER NOT NULL DEFAULT 0,
                ultima_varredura_online INTEGER NOT NULL DEFAULT 0
            );

CREATE TABLE ti_sistema_dependencias (
            id SERIAL PRIMARY KEY,
            sistema_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            nome TEXT NOT NULL,
            ativo_id INTEGER,
            sistema_dependencia_id INTEGER,
            criticidade TEXT NOT NULL DEFAULT 'Média'
        );

CREATE TABLE ti_sistemas (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            descricao TEXT,
            ambiente TEXT NOT NULL DEFAULT 'Produção',
            criticidade TEXT NOT NULL DEFAULT 'Média',
            status TEXT NOT NULL DEFAULT 'Operacional',
            versao TEXT,
            url TEXT,
            servidor_ativo_id INTEGER,
            fornecedor_id INTEGER,
            responsavel_ti_id INTEGER,
            responsavel_negocio_id INTEGER,
            sla_disponibilidade DOUBLE PRECISION NOT NULL DEFAULT 99.0 CHECK (sla_disponibilidade BETWEEN 0 AND 100),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            UNIQUE (empresa_id, nome, ambiente)
        );

CREATE TABLE ti_telemetria (
            id SERIAL PRIMARY KEY,
            ativo_id INTEGER NOT NULL,
            cpu_percentual DOUBLE PRECISION CHECK (cpu_percentual IS NULL OR cpu_percentual BETWEEN 0 AND 100),
            memoria_percentual DOUBLE PRECISION CHECK (memoria_percentual IS NULL OR memoria_percentual BETWEEN 0 AND 100),
            disco_percentual DOUBLE PRECISION CHECK (disco_percentual IS NULL OR disco_percentual BETWEEN 0 AND 100),
            espaco_livre_gb DOUBLE PRECISION CHECK (espaco_livre_gb IS NULL OR espaco_livre_gb >= 0),
            uptime_segundos INTEGER CHECK (uptime_segundos IS NULL OR uptime_segundos >= 0),
            latencia_ms DOUBLE PRECISION CHECK (latencia_ms IS NULL OR latencia_ms >= 0),
            agente_versao TEXT,
            coletado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE tokens_api (
            id SERIAL PRIMARY KEY,
            empresa_id INTEGER NOT NULL,
            usuario_id INTEGER,
            no_id INTEGER,
            nome TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            escopos TEXT NOT NULL DEFAULT '[]',
            expira_em TEXT,
            revogado_em TEXT,
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
        );

CREATE TABLE usuarios (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                usuario TEXT NOT NULL,
                senha_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                perfil TEXT NOT NULL DEFAULT 'usuario'
                    CHECK (perfil IN ('admin', 'usuario')),
                perfil_acesso TEXT NOT NULL DEFAULT 'analista',
                email_corporativo TEXT,
                sessao_epoch INTEGER NOT NULL DEFAULT 0,
                ativo INTEGER NOT NULL DEFAULT 1
                    CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
                ultimo_login TEXT,
                tentativas_falhas INTEGER NOT NULL DEFAULT 0,
                bloqueado_ate TEXT,
                senha_alterada_em TEXT
            , mfa_habilitado INTEGER NOT NULL DEFAULT 0, mfa_secret_ref TEXT);

CREATE TABLE usuarios_empresas (
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
            PRIMARY KEY (usuario_id, empresa_id)
        );

CREATE TABLE workflows (
                id SERIAL PRIMARY KEY,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                nome TEXT NOT NULL,
                evento_modulo TEXT NOT NULL,
                evento_tipo TEXT NOT NULL,
                condicoes_json TEXT NOT NULL DEFAULT '{}',
                acoes_json TEXT NOT NULL DEFAULT '[]',
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), atualizado_em TEXT NOT NULL DEFAULT ''
            );

-- Índices
CREATE INDEX idx_aprovacoes_empresa_status
                ON aprovacoes (empresa_id, status, criado_em DESC);
CREATE INDEX idx_atividades_empresa_data
                ON atividades (empresa_id, criado_em DESC);
CREATE INDEX idx_atividades_escopo_v82 ON atividades (empresa_id, filial_id, id DESC);
CREATE INDEX idx_ativos_ti_escopo_estado ON ativos_ti (empresa_id, filial_id, estado_registro, id DESC);
CREATE INDEX idx_campanhas_marketing_escopo_estado ON campanhas_marketing (empresa_id, filial_id, estado_registro, id DESC);
CREATE INDEX idx_chamados_ti_escopo_estado ON chamados_ti (empresa_id, filial_id, estado_registro, id DESC);
CREATE UNIQUE INDEX idx_cmp_alertas_chave
            ON cmp_alertas (
                empresa_id, COALESCE(filial_id, -1), tipo,
                COALESCE(recurso_tipo, ''), COALESCE(recurso_id, -1)
            );
CREATE INDEX idx_cmp_aprov_solicitacao_status
            ON cmp_aprovacoes_solicitacao(empresa_id, filial_id, solicitacao_id, status, ordem);
CREATE INDEX idx_cmp_fornecedores_busca
            ON cmp_fornecedores (empresa_id, status_homologacao, razao_social);
CREATE INDEX idx_cmp_pedidos_entrega
            ON cmp_pedidos (empresa_id, filial_id, status, previsao_entrega);
CREATE INDEX idx_cmp_solicitacoes_fila
            ON cmp_solicitacoes (empresa_id, filial_id, status, prioridade, criado_em DESC);
CREATE INDEX idx_colaboradores_escopo_estado ON colaboradores (empresa_id, filial_id, estado_registro, id DESC);
CREATE INDEX idx_conjuntos_dados_escopo
            ON conjuntos_dados (
                empresa_id, filial_id, estado_registro, atualizado_em DESC
            );
CREATE INDEX idx_contratos_juridicos_escopo_estado ON contratos_juridicos (empresa_id, filial_id, estado_registro, id DESC);
CREATE INDEX idx_correio_destinatario_caixa
            ON correio_destinatarios(usuario_id, excluida, arquivada, mensagem_id);
CREATE INDEX idx_correio_remetente
            ON correio_mensagens(remetente_id, excluida_remetente, id);
CREATE INDEX idx_destinatarios_usuario_caixa
            ON mensagem_destinatarios (usuario_id, excluida, arquivada, lida);
CREATE UNIQUE INDEX idx_est_alertas_chave
            ON est_alertas (
                empresa_id, tipo, COALESCE(item_id, 0),
                COALESCE(deposito_id, 0), COALESCE(lote_id, 0)
            );
CREATE INDEX idx_est_itens_busca
            ON est_itens (empresa_id, status, nome, codigo);
CREATE INDEX idx_est_movimentacoes_razao
            ON est_movimentacoes (empresa_id, item_id, criado_em DESC);
CREATE INDEX idx_est_operacoes_escopo
            ON est_operacoes (empresa_id, filial_id, tipo, status, criado_em DESC);
CREATE INDEX idx_est_saldos_escopo
            ON est_saldos (empresa_id, filial_id, item_id, deposito_id);
CREATE INDEX idx_estoque_empresa_codigo
                ON itens_estoque (empresa_id, codigo);
CREATE INDEX idx_fin_lancamentos_escopo
            ON fin_lancamentos (
                empresa_id, filial_id, status, competencia DESC, id DESC
            );
CREATE INDEX idx_fin_lancamentos_vencimento
            ON fin_lancamentos (empresa_id, filial_id, vencimento, status);
CREATE INDEX idx_financeiro_empresa_vencimento
                ON lancamentos_financeiros (empresa_id, vencimento);
CREATE INDEX idx_historico_alteracoes_recurso
            ON historico_alteracoes (
                empresa_id, modulo, entidade, entidade_id, criado_em DESC
            );
CREATE INDEX idx_itens_estoque_escopo_estado ON itens_estoque (empresa_id, filial_id, estado_registro, id DESC);
CREATE INDEX idx_jobs_empresa_status
            ON jobs (empresa_id, status, criado_em DESC);
CREATE INDEX idx_lancamentos_financeiros_escopo_estado ON lancamentos_financeiros (empresa_id, filial_id, estado_registro, id DESC);
CREATE INDEX idx_mensagens_empresa_data
            ON mensagens (empresa_id, criado_em DESC);
CREATE INDEX idx_movimentos_estoque_escopo_v82 ON movimentos_estoque (empresa_id, filial_id, id DESC);
CREATE INDEX idx_nonces_agente_data
            ON nonces_agente (usado_em);
CREATE INDEX idx_notificacoes_escopo_v82 ON notificacoes (empresa_id, filial_id, id DESC);
CREATE INDEX idx_notificacoes_usuario_lida
                ON notificacoes (usuario_id, lida, criado_em DESC);
CREATE INDEX idx_oportunidades_comerciais_escopo_estado ON oportunidades_comerciais (empresa_id, filial_id, estado_registro, id DESC);
CREATE INDEX idx_recursos_departamentais_escopo
            ON recursos_departamentais (
                empresa_id, filial_id, modulo, recurso,
                estado_registro, atualizado_em DESC
            );
CREATE INDEX idx_recursos_departamentais_status
            ON recursos_departamentais (
                empresa_id, filial_id, modulo, status
            );
CREATE INDEX idx_relatorios_corporativos_escopo
                ON relatorios_corporativos (
                    empresa_id, filial_id, modulo, criado_em DESC
                );
CREATE INDEX idx_rh_colaboradores_escopo
            ON rh_colaboradores (empresa_id, filial_id, status, nome_completo);
CREATE INDEX idx_solicitacoes_administrativas_escopo_estado ON solicitacoes_administrativas (empresa_id, filial_id, estado_registro, id DESC);
CREATE INDEX idx_solicitacoes_compra_escopo_estado ON solicitacoes_compra (empresa_id, filial_id, estado_registro, id DESC);
CREATE INDEX idx_ti_agente_nonces_tempo
            ON ti_agente_nonces (recebido_em);
CREATE INDEX idx_ti_agentes_escopo
            ON ti_agentes (empresa_id, filial_id, ativo, status);
CREATE INDEX idx_ti_ativos_agent_id ON ti_ativos (empresa_id, agent_id);
CREATE INDEX idx_ti_ativos_contexto
            ON ti_ativos (empresa_id, filial_id, status, estado_conectividade, ativo);
CREATE INDEX idx_ti_chamados_fila
            ON ti_chamados (empresa_id, filial_id, status, prioridade, criado_em DESC);
CREATE INDEX idx_ti_dispositivos_rede_ativos ON ti_dispositivos_rede (segmento_id, ativo, ultima_deteccao DESC);
CREATE INDEX idx_ti_historico_recurso
            ON ti_historico (empresa_id, recurso_tipo, recurso_id, criado_em DESC);
CREATE INDEX idx_ti_segmentos_escopo_ativo
            ON ti_segmentos_rede (empresa_id, filial_id, ativo, nome);
CREATE INDEX idx_ti_telemetria_ativo
            ON ti_telemetria (ativo_id, coletado_em DESC);
CREATE UNIQUE INDEX uq_ti_segmentos_empresa_filial_cidr
            ON ti_segmentos_rede (empresa_id, COALESCE(filial_id, 0), cidr);
CREATE UNIQUE INDEX ux_usuarios_email_corporativo
           ON usuarios(LOWER(email_corporativo))
           WHERE email_corporativo IS NOT NULL AND TRIM(email_corporativo)<>'';
CREATE UNIQUE INDEX IF NOT EXISTS ux_usuarios_usuario_ci ON usuarios (LOWER(usuario));

-- Foreign keys do schema canônico.
ALTER TABLE aprovacoes ADD CONSTRAINT fk_aprovacoes_0 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE aprovacoes ADD CONSTRAINT fk_aprovacoes_1 FOREIGN KEY (solicitante_id) REFERENCES usuarios(id);
ALTER TABLE aprovacoes ADD CONSTRAINT fk_aprovacoes_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE aprovacoes ADD CONSTRAINT fk_aprovacoes_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE arquivos_corporativos ADD CONSTRAINT fk_arquivos_corporativos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE arquivos_corporativos ADD CONSTRAINT fk_arquivos_corporativos_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE arquivos_corporativos ADD CONSTRAINT fk_arquivos_corporativos_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE atividades ADD CONSTRAINT fk_atividades_0 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE atividades ADD CONSTRAINT fk_atividades_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE atividades ADD CONSTRAINT fk_atividades_2 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE ativos_ti ADD CONSTRAINT fk_ativos_ti_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE ativos_ti ADD CONSTRAINT fk_ativos_ti_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE backups ADD CONSTRAINT fk_backups_0 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE backups ADD CONSTRAINT fk_backups_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE backups_empresariais ADD CONSTRAINT fk_backups_empresariais_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE backups_empresariais ADD CONSTRAINT fk_backups_empresariais_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE backups_empresariais ADD CONSTRAINT fk_backups_empresariais_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE campanhas_marketing ADD CONSTRAINT fk_campanhas_marketing_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE campanhas_marketing ADD CONSTRAINT fk_campanhas_marketing_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE centros_custo ADD CONSTRAINT fk_centros_custo_0 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE centros_custo ADD CONSTRAINT fk_centros_custo_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE chamados_ti ADD CONSTRAINT fk_chamados_ti_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE chamados_ti ADD CONSTRAINT fk_chamados_ti_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_alertas ADD CONSTRAINT fk_cmp_alertas_0 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE cmp_alertas ADD CONSTRAINT fk_cmp_alertas_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_anexos ADD CONSTRAINT fk_cmp_anexos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE cmp_anexos ADD CONSTRAINT fk_cmp_anexos_1 FOREIGN KEY (documento_id) REFERENCES documentos(id);
ALTER TABLE cmp_anexos ADD CONSTRAINT fk_cmp_anexos_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_aprovacoes_solicitacao ADD CONSTRAINT fk_cmp_aprovacoes_solicitacao_0 FOREIGN KEY (aprovador_id) REFERENCES usuarios(id);
ALTER TABLE cmp_aprovacoes_solicitacao ADD CONSTRAINT fk_cmp_aprovacoes_solicitacao_1 FOREIGN KEY (solicitacao_id) REFERENCES cmp_solicitacoes(id);
ALTER TABLE cmp_aprovacoes_solicitacao ADD CONSTRAINT fk_cmp_aprovacoes_solicitacao_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE cmp_aprovacoes_solicitacao ADD CONSTRAINT fk_cmp_aprovacoes_solicitacao_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_catalogo ADD CONSTRAINT fk_cmp_catalogo_0 FOREIGN KEY (categoria_id) REFERENCES cmp_categorias(id);
ALTER TABLE cmp_catalogo ADD CONSTRAINT fk_cmp_catalogo_1 FOREIGN KEY (estoque_item_id) REFERENCES est_itens(id);
ALTER TABLE cmp_catalogo ADD CONSTRAINT fk_cmp_catalogo_2 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE cmp_catalogo ADD CONSTRAINT fk_cmp_catalogo_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_categorias ADD CONSTRAINT fk_cmp_categorias_0 FOREIGN KEY (categoria_pai_id) REFERENCES cmp_categorias(id);
ALTER TABLE cmp_categorias ADD CONSTRAINT fk_cmp_categorias_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_comentarios ADD CONSTRAINT fk_cmp_comentarios_0 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE cmp_comentarios ADD CONSTRAINT fk_cmp_comentarios_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_contrato_aditivos ADD CONSTRAINT fk_cmp_contrato_aditivos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE cmp_contrato_aditivos ADD CONSTRAINT fk_cmp_contrato_aditivos_1 FOREIGN KEY (documento_id) REFERENCES documentos(id);
ALTER TABLE cmp_contrato_aditivos ADD CONSTRAINT fk_cmp_contrato_aditivos_2 FOREIGN KEY (contrato_id) REFERENCES cmp_contratos(id);
ALTER TABLE cmp_contratos ADD CONSTRAINT fk_cmp_contratos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE cmp_contratos ADD CONSTRAINT fk_cmp_contratos_1 FOREIGN KEY (documento_id) REFERENCES documentos(id);
ALTER TABLE cmp_contratos ADD CONSTRAINT fk_cmp_contratos_2 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE cmp_contratos ADD CONSTRAINT fk_cmp_contratos_3 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE cmp_contratos ADD CONSTRAINT fk_cmp_contratos_4 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE cmp_contratos ADD CONSTRAINT fk_cmp_contratos_5 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE cmp_contratos ADD CONSTRAINT fk_cmp_contratos_6 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_cotacao_fornecedores ADD CONSTRAINT fk_cmp_cotacao_fornecedores_0 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE cmp_cotacao_fornecedores ADD CONSTRAINT fk_cmp_cotacao_fornecedores_1 FOREIGN KEY (cotacao_id) REFERENCES cmp_cotacoes(id);
ALTER TABLE cmp_cotacao_itens ADD CONSTRAINT fk_cmp_cotacao_itens_0 FOREIGN KEY (solicitacao_item_id) REFERENCES cmp_solicitacao_itens(id);
ALTER TABLE cmp_cotacao_itens ADD CONSTRAINT fk_cmp_cotacao_itens_1 FOREIGN KEY (cotacao_fornecedor_id) REFERENCES cmp_cotacao_fornecedores(id);
ALTER TABLE cmp_cotacoes ADD CONSTRAINT fk_cmp_cotacoes_0 FOREIGN KEY (fornecedor_selecionado_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE cmp_cotacoes ADD CONSTRAINT fk_cmp_cotacoes_1 FOREIGN KEY (comprador_id) REFERENCES usuarios(id);
ALTER TABLE cmp_cotacoes ADD CONSTRAINT fk_cmp_cotacoes_2 FOREIGN KEY (solicitacao_id) REFERENCES cmp_solicitacoes(id);
ALTER TABLE cmp_cotacoes ADD CONSTRAINT fk_cmp_cotacoes_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE cmp_cotacoes ADD CONSTRAINT fk_cmp_cotacoes_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_divergencias ADD CONSTRAINT fk_cmp_divergencias_0 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE cmp_divergencias ADD CONSTRAINT fk_cmp_divergencias_1 FOREIGN KEY (pedido_item_id) REFERENCES cmp_pedido_itens(id);
ALTER TABLE cmp_divergencias ADD CONSTRAINT fk_cmp_divergencias_2 FOREIGN KEY (recebimento_id) REFERENCES cmp_recebimentos(id);
ALTER TABLE cmp_divergencias ADD CONSTRAINT fk_cmp_divergencias_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE cmp_divergencias ADD CONSTRAINT fk_cmp_divergencias_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_filtros_salvos ADD CONSTRAINT fk_cmp_filtros_salvos_0 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE cmp_filtros_salvos ADD CONSTRAINT fk_cmp_filtros_salvos_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_fornecedor_avaliacoes ADD CONSTRAINT fk_cmp_fornecedor_avaliacoes_0 FOREIGN KEY (avaliado_por) REFERENCES usuarios(id);
ALTER TABLE cmp_fornecedor_avaliacoes ADD CONSTRAINT fk_cmp_fornecedor_avaliacoes_1 FOREIGN KEY (recebimento_id) REFERENCES cmp_recebimentos(id);
ALTER TABLE cmp_fornecedor_avaliacoes ADD CONSTRAINT fk_cmp_fornecedor_avaliacoes_2 FOREIGN KEY (pedido_id) REFERENCES cmp_pedidos(id);
ALTER TABLE cmp_fornecedor_avaliacoes ADD CONSTRAINT fk_cmp_fornecedor_avaliacoes_3 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE cmp_fornecedor_avaliacoes ADD CONSTRAINT fk_cmp_fornecedor_avaliacoes_4 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE cmp_fornecedor_avaliacoes ADD CONSTRAINT fk_cmp_fornecedor_avaliacoes_5 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_fornecedor_contatos ADD CONSTRAINT fk_cmp_fornecedor_contatos_0 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE cmp_fornecedor_documentos ADD CONSTRAINT fk_cmp_fornecedor_documentos_0 FOREIGN KEY (documento_id) REFERENCES documentos(id);
ALTER TABLE cmp_fornecedor_documentos ADD CONSTRAINT fk_cmp_fornecedor_documentos_1 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE cmp_fornecedores ADD CONSTRAINT fk_cmp_fornecedores_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE cmp_fornecedores ADD CONSTRAINT fk_cmp_fornecedores_1 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE cmp_fornecedores ADD CONSTRAINT fk_cmp_fornecedores_2 FOREIGN KEY (financeiro_parte_id) REFERENCES fin_partes(id);
ALTER TABLE cmp_fornecedores ADD CONSTRAINT fk_cmp_fornecedores_3 FOREIGN KEY (estoque_fornecedor_id) REFERENCES est_fornecedores(id);
ALTER TABLE cmp_fornecedores ADD CONSTRAINT fk_cmp_fornecedores_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_historico ADD CONSTRAINT fk_cmp_historico_0 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE cmp_historico ADD CONSTRAINT fk_cmp_historico_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE cmp_historico ADD CONSTRAINT fk_cmp_historico_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_negociacoes ADD CONSTRAINT fk_cmp_negociacoes_0 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE cmp_negociacoes ADD CONSTRAINT fk_cmp_negociacoes_1 FOREIGN KEY (cotacao_fornecedor_id) REFERENCES cmp_cotacao_fornecedores(id);
ALTER TABLE cmp_pedido_itens ADD CONSTRAINT fk_cmp_pedido_itens_0 FOREIGN KEY (estoque_item_id) REFERENCES est_itens(id);
ALTER TABLE cmp_pedido_itens ADD CONSTRAINT fk_cmp_pedido_itens_1 FOREIGN KEY (solicitacao_item_id) REFERENCES cmp_solicitacao_itens(id);
ALTER TABLE cmp_pedido_itens ADD CONSTRAINT fk_cmp_pedido_itens_2 FOREIGN KEY (pedido_id) REFERENCES cmp_pedidos(id);
ALTER TABLE cmp_pedidos ADD CONSTRAINT fk_cmp_pedidos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE cmp_pedidos ADD CONSTRAINT fk_cmp_pedidos_1 FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id);
ALTER TABLE cmp_pedidos ADD CONSTRAINT fk_cmp_pedidos_2 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE cmp_pedidos ADD CONSTRAINT fk_cmp_pedidos_3 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE cmp_pedidos ADD CONSTRAINT fk_cmp_pedidos_4 FOREIGN KEY (comprador_id) REFERENCES usuarios(id);
ALTER TABLE cmp_pedidos ADD CONSTRAINT fk_cmp_pedidos_5 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE cmp_pedidos ADD CONSTRAINT fk_cmp_pedidos_6 FOREIGN KEY (cotacao_id) REFERENCES cmp_cotacoes(id);
ALTER TABLE cmp_pedidos ADD CONSTRAINT fk_cmp_pedidos_7 FOREIGN KEY (solicitacao_id) REFERENCES cmp_solicitacoes(id);
ALTER TABLE cmp_pedidos ADD CONSTRAINT fk_cmp_pedidos_8 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE cmp_pedidos ADD CONSTRAINT fk_cmp_pedidos_9 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_permissoes_acoes ADD CONSTRAINT fk_cmp_permissoes_acoes_0 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_permissoes_acoes ADD CONSTRAINT fk_cmp_permissoes_acoes_1 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE cmp_recebimento_itens ADD CONSTRAINT fk_cmp_recebimento_itens_0 FOREIGN KEY (pedido_item_id) REFERENCES cmp_pedido_itens(id);
ALTER TABLE cmp_recebimento_itens ADD CONSTRAINT fk_cmp_recebimento_itens_1 FOREIGN KEY (recebimento_id) REFERENCES cmp_recebimentos(id);
ALTER TABLE cmp_recebimentos ADD CONSTRAINT fk_cmp_recebimentos_0 FOREIGN KEY (financeiro_lancamento_id) REFERENCES fin_lancamentos(id);
ALTER TABLE cmp_recebimentos ADD CONSTRAINT fk_cmp_recebimentos_1 FOREIGN KEY (estoque_operacao_id) REFERENCES est_operacoes(id);
ALTER TABLE cmp_recebimentos ADD CONSTRAINT fk_cmp_recebimentos_2 FOREIGN KEY (recebido_por) REFERENCES usuarios(id);
ALTER TABLE cmp_recebimentos ADD CONSTRAINT fk_cmp_recebimentos_3 FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id);
ALTER TABLE cmp_recebimentos ADD CONSTRAINT fk_cmp_recebimentos_4 FOREIGN KEY (deposito_id) REFERENCES est_depositos(id);
ALTER TABLE cmp_recebimentos ADD CONSTRAINT fk_cmp_recebimentos_5 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE cmp_recebimentos ADD CONSTRAINT fk_cmp_recebimentos_6 FOREIGN KEY (pedido_id) REFERENCES cmp_pedidos(id);
ALTER TABLE cmp_recebimentos ADD CONSTRAINT fk_cmp_recebimentos_7 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE cmp_recebimentos ADD CONSTRAINT fk_cmp_recebimentos_8 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_regras_aprovacao ADD CONSTRAINT fk_cmp_regras_aprovacao_0 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE cmp_regras_aprovacao ADD CONSTRAINT fk_cmp_regras_aprovacao_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_relatorios_agendados ADD CONSTRAINT fk_cmp_relatorios_agendados_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE cmp_relatorios_agendados ADD CONSTRAINT fk_cmp_relatorios_agendados_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE cmp_relatorios_agendados ADD CONSTRAINT fk_cmp_relatorios_agendados_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE cmp_solicitacao_itens ADD CONSTRAINT fk_cmp_solicitacao_itens_0 FOREIGN KEY (categoria_id) REFERENCES cmp_categorias(id);
ALTER TABLE cmp_solicitacao_itens ADD CONSTRAINT fk_cmp_solicitacao_itens_1 FOREIGN KEY (catalogo_item_id) REFERENCES cmp_catalogo(id);
ALTER TABLE cmp_solicitacao_itens ADD CONSTRAINT fk_cmp_solicitacao_itens_2 FOREIGN KEY (estoque_item_id) REFERENCES est_itens(id);
ALTER TABLE cmp_solicitacao_itens ADD CONSTRAINT fk_cmp_solicitacao_itens_3 FOREIGN KEY (solicitacao_id) REFERENCES cmp_solicitacoes(id);
ALTER TABLE cmp_solicitacoes ADD CONSTRAINT fk_cmp_solicitacoes_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE cmp_solicitacoes ADD CONSTRAINT fk_cmp_solicitacoes_1 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE cmp_solicitacoes ADD CONSTRAINT fk_cmp_solicitacoes_2 FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id);
ALTER TABLE cmp_solicitacoes ADD CONSTRAINT fk_cmp_solicitacoes_3 FOREIGN KEY (comprador_id) REFERENCES usuarios(id);
ALTER TABLE cmp_solicitacoes ADD CONSTRAINT fk_cmp_solicitacoes_4 FOREIGN KEY (gestor_id) REFERENCES usuarios(id);
ALTER TABLE cmp_solicitacoes ADD CONSTRAINT fk_cmp_solicitacoes_5 FOREIGN KEY (solicitante_id) REFERENCES usuarios(id);
ALTER TABLE cmp_solicitacoes ADD CONSTRAINT fk_cmp_solicitacoes_6 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE cmp_solicitacoes ADD CONSTRAINT fk_cmp_solicitacoes_7 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE cmp_solicitacoes ADD CONSTRAINT fk_cmp_solicitacoes_8 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE cmp_solicitacoes ADD CONSTRAINT fk_cmp_solicitacoes_9 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE colaboradores ADD CONSTRAINT fk_colaboradores_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE colaboradores ADD CONSTRAINT fk_colaboradores_1 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE colaboradores ADD CONSTRAINT fk_colaboradores_2 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE colaboradores ADD CONSTRAINT fk_colaboradores_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE colaboradores ADD CONSTRAINT fk_colaboradores_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE conjuntos_dados ADD CONSTRAINT fk_conjuntos_dados_0 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE conjuntos_dados ADD CONSTRAINT fk_conjuntos_dados_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE conjuntos_dados ADD CONSTRAINT fk_conjuntos_dados_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE contratos_juridicos ADD CONSTRAINT fk_contratos_juridicos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE contratos_juridicos ADD CONSTRAINT fk_contratos_juridicos_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE correio_anexos ADD CONSTRAINT fk_correio_anexos_0 FOREIGN KEY (mensagem_id) REFERENCES correio_mensagens(id);
ALTER TABLE correio_destinatarios ADD CONSTRAINT fk_correio_destinatarios_0 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE correio_destinatarios ADD CONSTRAINT fk_correio_destinatarios_1 FOREIGN KEY (mensagem_id) REFERENCES correio_mensagens(id);
ALTER TABLE correio_mensagens ADD CONSTRAINT fk_correio_mensagens_0 FOREIGN KEY (encaminhada_de_id) REFERENCES correio_mensagens(id);
ALTER TABLE correio_mensagens ADD CONSTRAINT fk_correio_mensagens_1 FOREIGN KEY (resposta_de_id) REFERENCES correio_mensagens(id);
ALTER TABLE correio_mensagens ADD CONSTRAINT fk_correio_mensagens_2 FOREIGN KEY (remetente_id) REFERENCES usuarios(id);
ALTER TABLE correio_mensagens ADD CONSTRAINT fk_correio_mensagens_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE correio_mensagens ADD CONSTRAINT fk_correio_mensagens_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE departamentos ADD CONSTRAINT fk_departamentos_0 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE documentos ADD CONSTRAINT fk_documentos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE documentos ADD CONSTRAINT fk_documentos_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE documentos ADD CONSTRAINT fk_documentos_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_alertas ADD CONSTRAINT fk_est_alertas_0 FOREIGN KEY (resolvido_por) REFERENCES usuarios(id);
ALTER TABLE est_alertas ADD CONSTRAINT fk_est_alertas_1 FOREIGN KEY (operacao_id) REFERENCES est_operacoes(id);
ALTER TABLE est_alertas ADD CONSTRAINT fk_est_alertas_2 FOREIGN KEY (lote_id) REFERENCES est_lotes(id);
ALTER TABLE est_alertas ADD CONSTRAINT fk_est_alertas_3 FOREIGN KEY (deposito_id) REFERENCES est_depositos(id);
ALTER TABLE est_alertas ADD CONSTRAINT fk_est_alertas_4 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_alertas ADD CONSTRAINT fk_est_alertas_5 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE est_alertas ADD CONSTRAINT fk_est_alertas_6 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_categorias ADD CONSTRAINT fk_est_categorias_0 FOREIGN KEY (categoria_pai_id) REFERENCES est_categorias(id);
ALTER TABLE est_categorias ADD CONSTRAINT fk_est_categorias_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_custos_historico ADD CONSTRAINT fk_est_custos_historico_0 FOREIGN KEY (operacao_id) REFERENCES est_operacoes(id);
ALTER TABLE est_custos_historico ADD CONSTRAINT fk_est_custos_historico_1 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_custos_historico ADD CONSTRAINT fk_est_custos_historico_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_depositos ADD CONSTRAINT fk_est_depositos_0 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE est_depositos ADD CONSTRAINT fk_est_depositos_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE est_depositos ADD CONSTRAINT fk_est_depositos_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_fornecedores ADD CONSTRAINT fk_est_fornecedores_0 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_inventario_itens ADD CONSTRAINT fk_est_inventario_itens_0 FOREIGN KEY (recontado_por) REFERENCES usuarios(id);
ALTER TABLE est_inventario_itens ADD CONSTRAINT fk_est_inventario_itens_1 FOREIGN KEY (contado_por) REFERENCES usuarios(id);
ALTER TABLE est_inventario_itens ADD CONSTRAINT fk_est_inventario_itens_2 FOREIGN KEY (lote_id) REFERENCES est_lotes(id);
ALTER TABLE est_inventario_itens ADD CONSTRAINT fk_est_inventario_itens_3 FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id);
ALTER TABLE est_inventario_itens ADD CONSTRAINT fk_est_inventario_itens_4 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_inventario_itens ADD CONSTRAINT fk_est_inventario_itens_5 FOREIGN KEY (inventario_id) REFERENCES est_inventarios(id);
ALTER TABLE est_inventarios ADD CONSTRAINT fk_est_inventarios_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE est_inventarios ADD CONSTRAINT fk_est_inventarios_1 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE est_inventarios ADD CONSTRAINT fk_est_inventarios_2 FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id);
ALTER TABLE est_inventarios ADD CONSTRAINT fk_est_inventarios_3 FOREIGN KEY (categoria_id) REFERENCES est_categorias(id);
ALTER TABLE est_inventarios ADD CONSTRAINT fk_est_inventarios_4 FOREIGN KEY (deposito_id) REFERENCES est_depositos(id);
ALTER TABLE est_inventarios ADD CONSTRAINT fk_est_inventarios_5 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE est_inventarios ADD CONSTRAINT fk_est_inventarios_6 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_itens ADD CONSTRAINT fk_est_itens_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE est_itens ADD CONSTRAINT fk_est_itens_1 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE est_itens ADD CONSTRAINT fk_est_itens_2 FOREIGN KEY (fornecedor_principal_id) REFERENCES est_fornecedores(id);
ALTER TABLE est_itens ADD CONSTRAINT fk_est_itens_3 FOREIGN KEY (unidade_id) REFERENCES est_unidades_medida(id);
ALTER TABLE est_itens ADD CONSTRAINT fk_est_itens_4 FOREIGN KEY (categoria_id) REFERENCES est_categorias(id);
ALTER TABLE est_itens ADD CONSTRAINT fk_est_itens_5 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_localizacoes ADD CONSTRAINT fk_est_localizacoes_0 FOREIGN KEY (deposito_id) REFERENCES est_depositos(id);
ALTER TABLE est_lotes ADD CONSTRAINT fk_est_lotes_0 FOREIGN KEY (fornecedor_id) REFERENCES est_fornecedores(id);
ALTER TABLE est_lotes ADD CONSTRAINT fk_est_lotes_1 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_lotes ADD CONSTRAINT fk_est_lotes_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_movimentacoes ADD CONSTRAINT fk_est_movimentacoes_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE est_movimentacoes ADD CONSTRAINT fk_est_movimentacoes_1 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE est_movimentacoes ADD CONSTRAINT fk_est_movimentacoes_2 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE est_movimentacoes ADD CONSTRAINT fk_est_movimentacoes_3 FOREIGN KEY (lote_id) REFERENCES est_lotes(id);
ALTER TABLE est_movimentacoes ADD CONSTRAINT fk_est_movimentacoes_4 FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id);
ALTER TABLE est_movimentacoes ADD CONSTRAINT fk_est_movimentacoes_5 FOREIGN KEY (deposito_id) REFERENCES est_depositos(id);
ALTER TABLE est_movimentacoes ADD CONSTRAINT fk_est_movimentacoes_6 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_movimentacoes ADD CONSTRAINT fk_est_movimentacoes_7 FOREIGN KEY (operacao_id) REFERENCES est_operacoes(id);
ALTER TABLE est_movimentacoes ADD CONSTRAINT fk_est_movimentacoes_8 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE est_movimentacoes ADD CONSTRAINT fk_est_movimentacoes_9 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_ocorrencias ADD CONSTRAINT fk_est_ocorrencias_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE est_ocorrencias ADD CONSTRAINT fk_est_ocorrencias_1 FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id);
ALTER TABLE est_ocorrencias ADD CONSTRAINT fk_est_ocorrencias_2 FOREIGN KEY (serial_id) REFERENCES est_seriais(id);
ALTER TABLE est_ocorrencias ADD CONSTRAINT fk_est_ocorrencias_3 FOREIGN KEY (lote_id) REFERENCES est_lotes(id);
ALTER TABLE est_ocorrencias ADD CONSTRAINT fk_est_ocorrencias_4 FOREIGN KEY (deposito_id) REFERENCES est_depositos(id);
ALTER TABLE est_ocorrencias ADD CONSTRAINT fk_est_ocorrencias_5 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_ocorrencias ADD CONSTRAINT fk_est_ocorrencias_6 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE est_ocorrencias ADD CONSTRAINT fk_est_ocorrencias_7 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_operacao_itens ADD CONSTRAINT fk_est_operacao_itens_0 FOREIGN KEY (lote_id) REFERENCES est_lotes(id);
ALTER TABLE est_operacao_itens ADD CONSTRAINT fk_est_operacao_itens_1 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_operacao_itens ADD CONSTRAINT fk_est_operacao_itens_2 FOREIGN KEY (operacao_id) REFERENCES est_operacoes(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_0 FOREIGN KEY (confirmado_por) REFERENCES usuarios(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_1 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_2 FOREIGN KEY (documento_id) REFERENCES documentos(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_3 FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_4 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_5 FOREIGN KEY (solicitante_id) REFERENCES usuarios(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_6 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_7 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_8 FOREIGN KEY (fornecedor_id) REFERENCES est_fornecedores(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_9 FOREIGN KEY (localizacao_destino_id) REFERENCES est_localizacoes(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_10 FOREIGN KEY (localizacao_origem_id) REFERENCES est_localizacoes(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_11 FOREIGN KEY (deposito_destino_id) REFERENCES est_depositos(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_12 FOREIGN KEY (deposito_origem_id) REFERENCES est_depositos(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_13 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_14 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_permissoes_acoes ADD CONSTRAINT fk_est_permissoes_acoes_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE est_permissoes_acoes ADD CONSTRAINT fk_est_permissoes_acoes_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_permissoes_acoes ADD CONSTRAINT fk_est_permissoes_acoes_2 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE est_relatorios_agendados ADD CONSTRAINT fk_est_relatorios_agendados_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE est_relatorios_agendados ADD CONSTRAINT fk_est_relatorios_agendados_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE est_relatorios_agendados ADD CONSTRAINT fk_est_relatorios_agendados_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_reposicoes ADD CONSTRAINT fk_est_reposicoes_0 FOREIGN KEY (tarefa_id) REFERENCES tarefas(id);
ALTER TABLE est_reposicoes ADD CONSTRAINT fk_est_reposicoes_1 FOREIGN KEY (solicitacao_compra_id) REFERENCES solicitacoes_compra(id);
ALTER TABLE est_reposicoes ADD CONSTRAINT fk_est_reposicoes_2 FOREIGN KEY (deposito_id) REFERENCES est_depositos(id);
ALTER TABLE est_reposicoes ADD CONSTRAINT fk_est_reposicoes_3 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_reposicoes ADD CONSTRAINT fk_est_reposicoes_4 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE est_reposicoes ADD CONSTRAINT fk_est_reposicoes_5 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_reservas ADD CONSTRAINT fk_est_reservas_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE est_reservas ADD CONSTRAINT fk_est_reservas_1 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE est_reservas ADD CONSTRAINT fk_est_reservas_2 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE est_reservas ADD CONSTRAINT fk_est_reservas_3 FOREIGN KEY (solicitante_id) REFERENCES usuarios(id);
ALTER TABLE est_reservas ADD CONSTRAINT fk_est_reservas_4 FOREIGN KEY (lote_id) REFERENCES est_lotes(id);
ALTER TABLE est_reservas ADD CONSTRAINT fk_est_reservas_5 FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id);
ALTER TABLE est_reservas ADD CONSTRAINT fk_est_reservas_6 FOREIGN KEY (deposito_id) REFERENCES est_depositos(id);
ALTER TABLE est_reservas ADD CONSTRAINT fk_est_reservas_7 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_reservas ADD CONSTRAINT fk_est_reservas_8 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE est_reservas ADD CONSTRAINT fk_est_reservas_9 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_saldos ADD CONSTRAINT fk_est_saldos_0 FOREIGN KEY (lote_id) REFERENCES est_lotes(id);
ALTER TABLE est_saldos ADD CONSTRAINT fk_est_saldos_1 FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id);
ALTER TABLE est_saldos ADD CONSTRAINT fk_est_saldos_2 FOREIGN KEY (deposito_id) REFERENCES est_depositos(id);
ALTER TABLE est_saldos ADD CONSTRAINT fk_est_saldos_3 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_saldos ADD CONSTRAINT fk_est_saldos_4 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE est_saldos ADD CONSTRAINT fk_est_saldos_5 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_seriais ADD CONSTRAINT fk_est_seriais_0 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE est_seriais ADD CONSTRAINT fk_est_seriais_1 FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id);
ALTER TABLE est_seriais ADD CONSTRAINT fk_est_seriais_2 FOREIGN KEY (deposito_id) REFERENCES est_depositos(id);
ALTER TABLE est_seriais ADD CONSTRAINT fk_est_seriais_3 FOREIGN KEY (lote_id) REFERENCES est_lotes(id);
ALTER TABLE est_seriais ADD CONSTRAINT fk_est_seriais_4 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_seriais ADD CONSTRAINT fk_est_seriais_5 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_solicitacoes ADD CONSTRAINT fk_est_solicitacoes_0 FOREIGN KEY (reserva_id) REFERENCES est_reservas(id);
ALTER TABLE est_solicitacoes ADD CONSTRAINT fk_est_solicitacoes_1 FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id);
ALTER TABLE est_solicitacoes ADD CONSTRAINT fk_est_solicitacoes_2 FOREIGN KEY (item_id) REFERENCES est_itens(id);
ALTER TABLE est_solicitacoes ADD CONSTRAINT fk_est_solicitacoes_3 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE est_solicitacoes ADD CONSTRAINT fk_est_solicitacoes_4 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE est_solicitacoes ADD CONSTRAINT fk_est_solicitacoes_5 FOREIGN KEY (solicitante_id) REFERENCES usuarios(id);
ALTER TABLE est_solicitacoes ADD CONSTRAINT fk_est_solicitacoes_6 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE est_solicitacoes ADD CONSTRAINT fk_est_solicitacoes_7 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_unidades_medida ADD CONSTRAINT fk_est_unidades_medida_0 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE est_usuarios_depositos ADD CONSTRAINT fk_est_usuarios_depositos_0 FOREIGN KEY (deposito_id) REFERENCES est_depositos(id);
ALTER TABLE est_usuarios_depositos ADD CONSTRAINT fk_est_usuarios_depositos_1 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE filiais ADD CONSTRAINT fk_filiais_0 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_anexos ADD CONSTRAINT fk_fin_anexos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE fin_anexos ADD CONSTRAINT fk_fin_anexos_1 FOREIGN KEY (lancamento_id) REFERENCES fin_lancamentos(id);
ALTER TABLE fin_anexos ADD CONSTRAINT fk_fin_anexos_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_aprovacoes ADD CONSTRAINT fk_fin_aprovacoes_0 FOREIGN KEY (aprovador_id) REFERENCES usuarios(id);
ALTER TABLE fin_aprovacoes ADD CONSTRAINT fk_fin_aprovacoes_1 FOREIGN KEY (lancamento_id) REFERENCES fin_lancamentos(id);
ALTER TABLE fin_aprovacoes ADD CONSTRAINT fk_fin_aprovacoes_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE fin_aprovacoes ADD CONSTRAINT fk_fin_aprovacoes_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_baixas ADD CONSTRAINT fk_fin_baixas_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE fin_baixas ADD CONSTRAINT fk_fin_baixas_1 FOREIGN KEY (conta_id) REFERENCES fin_contas(id);
ALTER TABLE fin_baixas ADD CONSTRAINT fk_fin_baixas_2 FOREIGN KEY (lancamento_id) REFERENCES fin_lancamentos(id);
ALTER TABLE fin_baixas ADD CONSTRAINT fk_fin_baixas_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE fin_baixas ADD CONSTRAINT fk_fin_baixas_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_cartoes ADD CONSTRAINT fk_fin_cartoes_0 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE fin_cartoes ADD CONSTRAINT fk_fin_cartoes_1 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE fin_cartoes ADD CONSTRAINT fk_fin_cartoes_2 FOREIGN KEY (conta_id) REFERENCES fin_contas(id);
ALTER TABLE fin_cartoes ADD CONSTRAINT fk_fin_cartoes_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE fin_cartoes ADD CONSTRAINT fk_fin_cartoes_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_categorias ADD CONSTRAINT fk_fin_categorias_0 FOREIGN KEY (plano_conta_id) REFERENCES fin_plano_contas(id);
ALTER TABLE fin_categorias ADD CONSTRAINT fk_fin_categorias_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_contas ADD CONSTRAINT fk_fin_contas_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE fin_contas ADD CONSTRAINT fk_fin_contas_1 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE fin_contas ADD CONSTRAINT fk_fin_contas_2 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE fin_contas ADD CONSTRAINT fk_fin_contas_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE fin_contas ADD CONSTRAINT fk_fin_contas_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_extrato_itens ADD CONSTRAINT fk_fin_extrato_itens_0 FOREIGN KEY (conciliado_por) REFERENCES usuarios(id);
ALTER TABLE fin_extrato_itens ADD CONSTRAINT fk_fin_extrato_itens_1 FOREIGN KEY (lancamento_id) REFERENCES fin_lancamentos(id);
ALTER TABLE fin_extrato_itens ADD CONSTRAINT fk_fin_extrato_itens_2 FOREIGN KEY (extrato_id) REFERENCES fin_extratos(id);
ALTER TABLE fin_extratos ADD CONSTRAINT fk_fin_extratos_0 FOREIGN KEY (importado_por) REFERENCES usuarios(id);
ALTER TABLE fin_extratos ADD CONSTRAINT fk_fin_extratos_1 FOREIGN KEY (conta_id) REFERENCES fin_contas(id);
ALTER TABLE fin_extratos ADD CONSTRAINT fk_fin_extratos_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE fin_extratos ADD CONSTRAINT fk_fin_extratos_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_1 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_2 FOREIGN KEY (cancelado_por) REFERENCES usuarios(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_3 FOREIGN KEY (parte_id) REFERENCES fin_partes(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_4 FOREIGN KEY (categoria_id) REFERENCES fin_categorias(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_5 FOREIGN KEY (plano_conta_id) REFERENCES fin_plano_contas(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_6 FOREIGN KEY (conta_destino_id) REFERENCES fin_contas(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_7 FOREIGN KEY (conta_id) REFERENCES fin_contas(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_8 FOREIGN KEY (projeto_id) REFERENCES fin_projetos(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_9 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_10 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_11 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_12 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_orcamentos ADD CONSTRAINT fk_fin_orcamentos_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE fin_orcamentos ADD CONSTRAINT fk_fin_orcamentos_1 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE fin_orcamentos ADD CONSTRAINT fk_fin_orcamentos_2 FOREIGN KEY (categoria_id) REFERENCES fin_categorias(id);
ALTER TABLE fin_orcamentos ADD CONSTRAINT fk_fin_orcamentos_3 FOREIGN KEY (projeto_id) REFERENCES fin_projetos(id);
ALTER TABLE fin_orcamentos ADD CONSTRAINT fk_fin_orcamentos_4 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE fin_orcamentos ADD CONSTRAINT fk_fin_orcamentos_5 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE fin_orcamentos ADD CONSTRAINT fk_fin_orcamentos_6 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE fin_orcamentos ADD CONSTRAINT fk_fin_orcamentos_7 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_partes ADD CONSTRAINT fk_fin_partes_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE fin_partes ADD CONSTRAINT fk_fin_partes_1 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE fin_partes ADD CONSTRAINT fk_fin_partes_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE fin_partes ADD CONSTRAINT fk_fin_partes_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_permissoes_acoes ADD CONSTRAINT fk_fin_permissoes_acoes_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE fin_permissoes_acoes ADD CONSTRAINT fk_fin_permissoes_acoes_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_permissoes_acoes ADD CONSTRAINT fk_fin_permissoes_acoes_2 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE fin_plano_contas ADD CONSTRAINT fk_fin_plano_contas_0 FOREIGN KEY (conta_pai_id) REFERENCES fin_plano_contas(id);
ALTER TABLE fin_plano_contas ADD CONSTRAINT fk_fin_plano_contas_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_projetos ADD CONSTRAINT fk_fin_projetos_0 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE fin_projetos ADD CONSTRAINT fk_fin_projetos_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_recorrencias ADD CONSTRAINT fk_fin_recorrencias_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE fin_recorrencias ADD CONSTRAINT fk_fin_recorrencias_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE fin_recorrencias ADD CONSTRAINT fk_fin_recorrencias_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_regras_aprovacao ADD CONSTRAINT fk_fin_regras_aprovacao_0 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE fin_relatorios_agendados ADD CONSTRAINT fk_fin_relatorios_agendados_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE fin_relatorios_agendados ADD CONSTRAINT fk_fin_relatorios_agendados_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE fin_relatorios_agendados ADD CONSTRAINT fk_fin_relatorios_agendados_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE historico_alteracoes ADD CONSTRAINT fk_historico_alteracoes_0 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE historico_alteracoes ADD CONSTRAINT fk_historico_alteracoes_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE historico_alteracoes ADD CONSTRAINT fk_historico_alteracoes_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE integracoes ADD CONSTRAINT fk_integracoes_0 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE integracoes ADD CONSTRAINT fk_integracoes_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE itens_estoque ADD CONSTRAINT fk_itens_estoque_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE itens_estoque ADD CONSTRAINT fk_itens_estoque_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE itens_estoque ADD CONSTRAINT fk_itens_estoque_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE jobs ADD CONSTRAINT fk_jobs_0 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE jobs ADD CONSTRAINT fk_jobs_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE jobs ADD CONSTRAINT fk_jobs_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE lancamentos_financeiros ADD CONSTRAINT fk_lancamentos_financeiros_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE lancamentos_financeiros ADD CONSTRAINT fk_lancamentos_financeiros_1 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE lancamentos_financeiros ADD CONSTRAINT fk_lancamentos_financeiros_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE mensagem_anexos ADD CONSTRAINT fk_mensagem_anexos_0 FOREIGN KEY (mensagem_id) REFERENCES mensagens(id);
ALTER TABLE mensagem_destinatarios ADD CONSTRAINT fk_mensagem_destinatarios_0 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE mensagem_destinatarios ADD CONSTRAINT fk_mensagem_destinatarios_1 FOREIGN KEY (mensagem_id) REFERENCES mensagens(id);
ALTER TABLE mensagens ADD CONSTRAINT fk_mensagens_0 FOREIGN KEY (resposta_de_id) REFERENCES mensagens(id);
ALTER TABLE mensagens ADD CONSTRAINT fk_mensagens_1 FOREIGN KEY (remetente_id) REFERENCES usuarios(id);
ALTER TABLE mensagens ADD CONSTRAINT fk_mensagens_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE mensagens ADD CONSTRAINT fk_mensagens_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE movimentos_estoque ADD CONSTRAINT fk_movimentos_estoque_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE movimentos_estoque ADD CONSTRAINT fk_movimentos_estoque_1 FOREIGN KEY (item_id) REFERENCES itens_estoque(id);
ALTER TABLE movimentos_estoque ADD CONSTRAINT fk_movimentos_estoque_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE movimentos_estoque ADD CONSTRAINT fk_movimentos_estoque_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE nos_plataforma ADD CONSTRAINT fk_nos_plataforma_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE nos_plataforma ADD CONSTRAINT fk_nos_plataforma_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE nos_plataforma ADD CONSTRAINT fk_nos_plataforma_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE notificacoes ADD CONSTRAINT fk_notificacoes_0 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE notificacoes ADD CONSTRAINT fk_notificacoes_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE notificacoes ADD CONSTRAINT fk_notificacoes_2 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE oportunidades_comerciais ADD CONSTRAINT fk_oportunidades_comerciais_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE oportunidades_comerciais ADD CONSTRAINT fk_oportunidades_comerciais_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE permissoes_modulos ADD CONSTRAINT fk_permissoes_modulos_0 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE permissoes_modulos ADD CONSTRAINT fk_permissoes_modulos_1 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE recursos_departamentais ADD CONSTRAINT fk_recursos_departamentais_0 FOREIGN KEY (arquivado_por) REFERENCES usuarios(id);
ALTER TABLE recursos_departamentais ADD CONSTRAINT fk_recursos_departamentais_1 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE recursos_departamentais ADD CONSTRAINT fk_recursos_departamentais_2 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE recursos_departamentais ADD CONSTRAINT fk_recursos_departamentais_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE recursos_departamentais ADD CONSTRAINT fk_recursos_departamentais_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE relatorios_corporativos ADD CONSTRAINT fk_relatorios_corporativos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE relatorios_corporativos ADD CONSTRAINT fk_relatorios_corporativos_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE relatorios_corporativos ADD CONSTRAINT fk_relatorios_corporativos_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_admissoes ADD CONSTRAINT fk_rh_admissoes_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE rh_admissoes ADD CONSTRAINT fk_rh_admissoes_1 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE rh_admissoes ADD CONSTRAINT fk_rh_admissoes_2 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_admissoes ADD CONSTRAINT fk_rh_admissoes_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_admissoes ADD CONSTRAINT fk_rh_admissoes_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_avaliacoes ADD CONSTRAINT fk_rh_avaliacoes_0 FOREIGN KEY (avaliador_id) REFERENCES usuarios(id);
ALTER TABLE rh_avaliacoes ADD CONSTRAINT fk_rh_avaliacoes_1 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_avaliacoes ADD CONSTRAINT fk_rh_avaliacoes_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_avaliacoes ADD CONSTRAINT fk_rh_avaliacoes_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_beneficios ADD CONSTRAINT fk_rh_beneficios_0 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_candidatos ADD CONSTRAINT fk_rh_candidatos_0 FOREIGN KEY (vaga_id) REFERENCES rh_vagas(id);
ALTER TABLE rh_cargos ADD CONSTRAINT fk_rh_cargos_0 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE rh_cargos ADD CONSTRAINT fk_rh_cargos_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_colaborador_beneficios ADD CONSTRAINT fk_rh_colaborador_beneficios_0 FOREIGN KEY (beneficio_id) REFERENCES rh_beneficios(id);
ALTER TABLE rh_colaborador_beneficios ADD CONSTRAINT fk_rh_colaborador_beneficios_1 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_colaboradores ADD CONSTRAINT fk_rh_colaboradores_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE rh_colaboradores ADD CONSTRAINT fk_rh_colaboradores_1 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE rh_colaboradores ADD CONSTRAINT fk_rh_colaboradores_2 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE rh_colaboradores ADD CONSTRAINT fk_rh_colaboradores_3 FOREIGN KEY (gestor_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_colaboradores ADD CONSTRAINT fk_rh_colaboradores_4 FOREIGN KEY (cargo_id) REFERENCES rh_cargos(id);
ALTER TABLE rh_colaboradores ADD CONSTRAINT fk_rh_colaboradores_5 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE rh_colaboradores ADD CONSTRAINT fk_rh_colaboradores_6 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE rh_colaboradores ADD CONSTRAINT fk_rh_colaboradores_7 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_colaboradores ADD CONSTRAINT fk_rh_colaboradores_8 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_contracheques ADD CONSTRAINT fk_rh_contracheques_0 FOREIGN KEY (gerado_por) REFERENCES usuarios(id);
ALTER TABLE rh_contracheques ADD CONSTRAINT fk_rh_contracheques_1 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_contracheques ADD CONSTRAINT fk_rh_contracheques_2 FOREIGN KEY (folha_id) REFERENCES rh_folhas(id);
ALTER TABLE rh_contracheques ADD CONSTRAINT fk_rh_contracheques_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_contracheques ADD CONSTRAINT fk_rh_contracheques_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_dependentes ADD CONSTRAINT fk_rh_dependentes_0 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_desligamentos ADD CONSTRAINT fk_rh_desligamentos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE rh_desligamentos ADD CONSTRAINT fk_rh_desligamentos_1 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_desligamentos ADD CONSTRAINT fk_rh_desligamentos_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_desligamentos ADD CONSTRAINT fk_rh_desligamentos_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_documentos ADD CONSTRAINT fk_rh_documentos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE rh_documentos ADD CONSTRAINT fk_rh_documentos_1 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_documentos ADD CONSTRAINT fk_rh_documentos_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_documentos ADD CONSTRAINT fk_rh_documentos_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_equipamentos ADD CONSTRAINT fk_rh_equipamentos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE rh_equipamentos ADD CONSTRAINT fk_rh_equipamentos_1 FOREIGN KEY (termo_documento_id) REFERENCES rh_documentos(id);
ALTER TABLE rh_equipamentos ADD CONSTRAINT fk_rh_equipamentos_2 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_equipamentos ADD CONSTRAINT fk_rh_equipamentos_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_equipamentos ADD CONSTRAINT fk_rh_equipamentos_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_eventos_folha ADD CONSTRAINT fk_rh_eventos_folha_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE rh_eventos_folha ADD CONSTRAINT fk_rh_eventos_folha_1 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_eventos_folha ADD CONSTRAINT fk_rh_eventos_folha_2 FOREIGN KEY (folha_id) REFERENCES rh_folhas(id);
ALTER TABLE rh_ferias_ausencias ADD CONSTRAINT fk_rh_ferias_ausencias_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE rh_ferias_ausencias ADD CONSTRAINT fk_rh_ferias_ausencias_1 FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id);
ALTER TABLE rh_ferias_ausencias ADD CONSTRAINT fk_rh_ferias_ausencias_2 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_ferias_ausencias ADD CONSTRAINT fk_rh_ferias_ausencias_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_ferias_ausencias ADD CONSTRAINT fk_rh_ferias_ausencias_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_folhas ADD CONSTRAINT fk_rh_folhas_0 FOREIGN KEY (fechada_por) REFERENCES usuarios(id);
ALTER TABLE rh_folhas ADD CONSTRAINT fk_rh_folhas_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_folhas ADD CONSTRAINT fk_rh_folhas_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_historico_profissional ADD CONSTRAINT fk_rh_historico_profissional_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE rh_historico_profissional ADD CONSTRAINT fk_rh_historico_profissional_1 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_historico_profissional ADD CONSTRAINT fk_rh_historico_profissional_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_historico_profissional ADD CONSTRAINT fk_rh_historico_profissional_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_inscricoes_treinamento ADD CONSTRAINT fk_rh_inscricoes_treinamento_0 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_inscricoes_treinamento ADD CONSTRAINT fk_rh_inscricoes_treinamento_1 FOREIGN KEY (treinamento_id) REFERENCES rh_treinamentos(id);
ALTER TABLE rh_pdis ADD CONSTRAINT fk_rh_pdis_0 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_permissoes_acoes ADD CONSTRAINT fk_rh_permissoes_acoes_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE rh_permissoes_acoes ADD CONSTRAINT fk_rh_permissoes_acoes_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_permissoes_acoes ADD CONSTRAINT fk_rh_permissoes_acoes_2 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE rh_pontos ADD CONSTRAINT fk_rh_pontos_0 FOREIGN KEY (aprovado_por) REFERENCES usuarios(id);
ALTER TABLE rh_pontos ADD CONSTRAINT fk_rh_pontos_1 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_pontos ADD CONSTRAINT fk_rh_pontos_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_pontos ADD CONSTRAINT fk_rh_pontos_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_relatorios_agendados ADD CONSTRAINT fk_rh_relatorios_agendados_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE rh_relatorios_agendados ADD CONSTRAINT fk_rh_relatorios_agendados_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_relatorios_agendados ADD CONSTRAINT fk_rh_relatorios_agendados_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_solicitacoes ADD CONSTRAINT fk_rh_solicitacoes_0 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE rh_solicitacoes ADD CONSTRAINT fk_rh_solicitacoes_1 FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id);
ALTER TABLE rh_solicitacoes ADD CONSTRAINT fk_rh_solicitacoes_2 FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id);
ALTER TABLE rh_solicitacoes ADD CONSTRAINT fk_rh_solicitacoes_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_solicitacoes ADD CONSTRAINT fk_rh_solicitacoes_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_treinamentos ADD CONSTRAINT fk_rh_treinamentos_0 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE rh_vagas ADD CONSTRAINT fk_rh_vagas_0 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE rh_vagas ADD CONSTRAINT fk_rh_vagas_1 FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id);
ALTER TABLE rh_vagas ADD CONSTRAINT fk_rh_vagas_2 FOREIGN KEY (cargo_id) REFERENCES rh_cargos(id);
ALTER TABLE rh_vagas ADD CONSTRAINT fk_rh_vagas_3 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE rh_vagas ADD CONSTRAINT fk_rh_vagas_4 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE rh_vagas ADD CONSTRAINT fk_rh_vagas_5 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE solicitacoes_administrativas ADD CONSTRAINT fk_solicitacoes_administrativas_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE solicitacoes_administrativas ADD CONSTRAINT fk_solicitacoes_administrativas_1 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE solicitacoes_administrativas ADD CONSTRAINT fk_solicitacoes_administrativas_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE solicitacoes_compra ADD CONSTRAINT fk_solicitacoes_compra_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE solicitacoes_compra ADD CONSTRAINT fk_solicitacoes_compra_1 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE solicitacoes_compra ADD CONSTRAINT fk_solicitacoes_compra_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE tarefas ADD CONSTRAINT fk_tarefas_0 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE tarefas ADD CONSTRAINT fk_tarefas_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE tarefas ADD CONSTRAINT fk_tarefas_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_acessos_remotos ADD CONSTRAINT fk_ti_acessos_remotos_0 FOREIGN KEY (tecnico_id) REFERENCES usuarios(id);
ALTER TABLE ti_acessos_remotos ADD CONSTRAINT fk_ti_acessos_remotos_1 FOREIGN KEY (chamado_id) REFERENCES ti_chamados(id);
ALTER TABLE ti_acessos_remotos ADD CONSTRAINT fk_ti_acessos_remotos_2 FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE ti_acessos_remotos ADD CONSTRAINT fk_ti_acessos_remotos_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_acessos_remotos ADD CONSTRAINT fk_ti_acessos_remotos_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_agente_nonces ADD CONSTRAINT fk_ti_agente_nonces_0 FOREIGN KEY (agente_id) REFERENCES ti_agentes(id);
ALTER TABLE ti_agentes ADD CONSTRAINT fk_ti_agentes_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE ti_agentes ADD CONSTRAINT fk_ti_agentes_1 FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE ti_agentes ADD CONSTRAINT fk_ti_agentes_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_agentes ADD CONSTRAINT fk_ti_agentes_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_alertas ADD CONSTRAINT fk_ti_alertas_0 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE ti_alertas ADD CONSTRAINT fk_ti_alertas_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_alertas ADD CONSTRAINT fk_ti_alertas_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_ativos ADD CONSTRAINT fk_ti_ativos_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE ti_ativos ADD CONSTRAINT fk_ti_ativos_1 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE ti_ativos ADD CONSTRAINT fk_ti_ativos_2 FOREIGN KEY (estoque_item_id) REFERENCES est_itens(id);
ALTER TABLE ti_ativos ADD CONSTRAINT fk_ti_ativos_3 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE ti_ativos ADD CONSTRAINT fk_ti_ativos_4 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE ti_ativos ADD CONSTRAINT fk_ti_ativos_5 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE ti_ativos ADD CONSTRAINT fk_ti_ativos_6 FOREIGN KEY (usuario_responsavel_id) REFERENCES usuarios(id);
ALTER TABLE ti_ativos ADD CONSTRAINT fk_ti_ativos_7 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_ativos ADD CONSTRAINT fk_ti_ativos_8 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_chamado_comentarios ADD CONSTRAINT fk_ti_chamado_comentarios_0 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE ti_chamado_comentarios ADD CONSTRAINT fk_ti_chamado_comentarios_1 FOREIGN KEY (chamado_id) REFERENCES ti_chamados(id);
ALTER TABLE ti_chamados ADD CONSTRAINT fk_ti_chamados_0 FOREIGN KEY (atualizado_por) REFERENCES usuarios(id);
ALTER TABLE ti_chamados ADD CONSTRAINT fk_ti_chamados_1 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE ti_chamados ADD CONSTRAINT fk_ti_chamados_2 FOREIGN KEY (sistema_id) REFERENCES ti_sistemas(id);
ALTER TABLE ti_chamados ADD CONSTRAINT fk_ti_chamados_3 FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE ti_chamados ADD CONSTRAINT fk_ti_chamados_4 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE ti_chamados ADD CONSTRAINT fk_ti_chamados_5 FOREIGN KEY (tecnico_id) REFERENCES usuarios(id);
ALTER TABLE ti_chamados ADD CONSTRAINT fk_ti_chamados_6 FOREIGN KEY (solicitante_id) REFERENCES usuarios(id);
ALTER TABLE ti_chamados ADD CONSTRAINT fk_ti_chamados_7 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_chamados ADD CONSTRAINT fk_ti_chamados_8 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_conhecimento ADD CONSTRAINT fk_ti_conhecimento_0 FOREIGN KEY (autor_id) REFERENCES usuarios(id);
ALTER TABLE ti_conhecimento ADD CONSTRAINT fk_ti_conhecimento_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_contratos ADD CONSTRAINT fk_ti_contratos_0 FOREIGN KEY (documento_id) REFERENCES documentos(id);
ALTER TABLE ti_contratos ADD CONSTRAINT fk_ti_contratos_1 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE ti_contratos ADD CONSTRAINT fk_ti_contratos_2 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE ti_contratos ADD CONSTRAINT fk_ti_contratos_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_contratos ADD CONSTRAINT fk_ti_contratos_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_dispositivos_rede ADD CONSTRAINT fk_ti_dispositivos_rede_0 FOREIGN KEY (investigado_por) REFERENCES usuarios(id);
ALTER TABLE ti_dispositivos_rede ADD CONSTRAINT fk_ti_dispositivos_rede_1 FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE ti_dispositivos_rede ADD CONSTRAINT fk_ti_dispositivos_rede_2 FOREIGN KEY (segmento_id) REFERENCES ti_segmentos_rede(id);
ALTER TABLE ti_dispositivos_rede ADD CONSTRAINT fk_ti_dispositivos_rede_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_dispositivos_rede ADD CONSTRAINT fk_ti_dispositivos_rede_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_emprestimos ADD CONSTRAINT fk_ti_emprestimos_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE ti_emprestimos ADD CONSTRAINT fk_ti_emprestimos_1 FOREIGN KEY (manutencao_id) REFERENCES ti_manutencoes(id);
ALTER TABLE ti_emprestimos ADD CONSTRAINT fk_ti_emprestimos_2 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE ti_emprestimos ADD CONSTRAINT fk_ti_emprestimos_3 FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE ti_emprestimos ADD CONSTRAINT fk_ti_emprestimos_4 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_emprestimos ADD CONSTRAINT fk_ti_emprestimos_5 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_eventos_monitoramento ADD CONSTRAINT fk_ti_eventos_monitoramento_0 FOREIGN KEY (monitor_id) REFERENCES ti_monitores(id);
ALTER TABLE ti_historico ADD CONSTRAINT fk_ti_historico_0 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE ti_historico ADD CONSTRAINT fk_ti_historico_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_historico ADD CONSTRAINT fk_ti_historico_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_incidentes_seguranca ADD CONSTRAINT fk_ti_incidentes_seguranca_0 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE ti_incidentes_seguranca ADD CONSTRAINT fk_ti_incidentes_seguranca_1 FOREIGN KEY (sistema_id) REFERENCES ti_sistemas(id);
ALTER TABLE ti_incidentes_seguranca ADD CONSTRAINT fk_ti_incidentes_seguranca_2 FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE ti_incidentes_seguranca ADD CONSTRAINT fk_ti_incidentes_seguranca_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_incidentes_seguranca ADD CONSTRAINT fk_ti_incidentes_seguranca_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_licenca_atribuicoes ADD CONSTRAINT fk_ti_licenca_atribuicoes_0 FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE ti_licenca_atribuicoes ADD CONSTRAINT fk_ti_licenca_atribuicoes_1 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE ti_licenca_atribuicoes ADD CONSTRAINT fk_ti_licenca_atribuicoes_2 FOREIGN KEY (licenca_id) REFERENCES ti_licencas(id);
ALTER TABLE ti_licencas ADD CONSTRAINT fk_ti_licencas_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE ti_licencas ADD CONSTRAINT fk_ti_licencas_1 FOREIGN KEY (financeiro_recorrencia_id) REFERENCES fin_recorrencias(id);
ALTER TABLE ti_licencas ADD CONSTRAINT fk_ti_licencas_2 FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id);
ALTER TABLE ti_licencas ADD CONSTRAINT fk_ti_licencas_3 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE ti_licencas ADD CONSTRAINT fk_ti_licencas_4 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_licencas ADD CONSTRAINT fk_ti_licencas_5 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_manutencoes ADD CONSTRAINT fk_ti_manutencoes_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE ti_manutencoes ADD CONSTRAINT fk_ti_manutencoes_1 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE ti_manutencoes ADD CONSTRAINT fk_ti_manutencoes_2 FOREIGN KEY (chamado_id) REFERENCES ti_chamados(id);
ALTER TABLE ti_manutencoes ADD CONSTRAINT fk_ti_manutencoes_3 FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE ti_manutencoes ADD CONSTRAINT fk_ti_manutencoes_4 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_manutencoes ADD CONSTRAINT fk_ti_manutencoes_5 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_monitores ADD CONSTRAINT fk_ti_monitores_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE ti_monitores ADD CONSTRAINT fk_ti_monitores_1 FOREIGN KEY (sistema_id) REFERENCES ti_sistemas(id);
ALTER TABLE ti_monitores ADD CONSTRAINT fk_ti_monitores_2 FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE ti_monitores ADD CONSTRAINT fk_ti_monitores_3 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_monitores ADD CONSTRAINT fk_ti_monitores_4 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_mudancas ADD CONSTRAINT fk_ti_mudancas_0 FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id);
ALTER TABLE ti_mudancas ADD CONSTRAINT fk_ti_mudancas_1 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE ti_mudancas ADD CONSTRAINT fk_ti_mudancas_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_mudancas ADD CONSTRAINT fk_ti_mudancas_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_permissoes_acoes ADD CONSTRAINT fk_ti_permissoes_acoes_0 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_permissoes_acoes ADD CONSTRAINT fk_ti_permissoes_acoes_1 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE ti_problema_chamados ADD CONSTRAINT fk_ti_problema_chamados_0 FOREIGN KEY (chamado_id) REFERENCES ti_chamados(id);
ALTER TABLE ti_problema_chamados ADD CONSTRAINT fk_ti_problema_chamados_1 FOREIGN KEY (problema_id) REFERENCES ti_problemas(id);
ALTER TABLE ti_problemas ADD CONSTRAINT fk_ti_problemas_0 FOREIGN KEY (responsavel_id) REFERENCES usuarios(id);
ALTER TABLE ti_problemas ADD CONSTRAINT fk_ti_problemas_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_problemas ADD CONSTRAINT fk_ti_problemas_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_segmentos_rede ADD CONSTRAINT fk_ti_segmentos_rede_0 FOREIGN KEY (autorizado_por) REFERENCES usuarios(id);
ALTER TABLE ti_segmentos_rede ADD CONSTRAINT fk_ti_segmentos_rede_1 FOREIGN KEY (departamento_id) REFERENCES departamentos(id);
ALTER TABLE ti_segmentos_rede ADD CONSTRAINT fk_ti_segmentos_rede_2 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_segmentos_rede ADD CONSTRAINT fk_ti_segmentos_rede_3 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_sistema_dependencias ADD CONSTRAINT fk_ti_sistema_dependencias_0 FOREIGN KEY (sistema_dependencia_id) REFERENCES ti_sistemas(id);
ALTER TABLE ti_sistema_dependencias ADD CONSTRAINT fk_ti_sistema_dependencias_1 FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE ti_sistema_dependencias ADD CONSTRAINT fk_ti_sistema_dependencias_2 FOREIGN KEY (sistema_id) REFERENCES ti_sistemas(id);
ALTER TABLE ti_sistemas ADD CONSTRAINT fk_ti_sistemas_0 FOREIGN KEY (responsavel_negocio_id) REFERENCES usuarios(id);
ALTER TABLE ti_sistemas ADD CONSTRAINT fk_ti_sistemas_1 FOREIGN KEY (responsavel_ti_id) REFERENCES usuarios(id);
ALTER TABLE ti_sistemas ADD CONSTRAINT fk_ti_sistemas_2 FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id);
ALTER TABLE ti_sistemas ADD CONSTRAINT fk_ti_sistemas_3 FOREIGN KEY (servidor_ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE ti_sistemas ADD CONSTRAINT fk_ti_sistemas_4 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE ti_sistemas ADD CONSTRAINT fk_ti_sistemas_5 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE ti_telemetria ADD CONSTRAINT fk_ti_telemetria_0 FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id);
ALTER TABLE tokens_api ADD CONSTRAINT fk_tokens_api_0 FOREIGN KEY (no_id) REFERENCES nos_plataforma(id);
ALTER TABLE tokens_api ADD CONSTRAINT fk_tokens_api_1 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE tokens_api ADD CONSTRAINT fk_tokens_api_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE usuarios_empresas ADD CONSTRAINT fk_usuarios_empresas_0 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE usuarios_empresas ADD CONSTRAINT fk_usuarios_empresas_1 FOREIGN KEY (empresa_id) REFERENCES empresas(id);
ALTER TABLE usuarios_empresas ADD CONSTRAINT fk_usuarios_empresas_2 FOREIGN KEY (usuario_id) REFERENCES usuarios(id);
ALTER TABLE workflows ADD CONSTRAINT fk_workflows_0 FOREIGN KEY (criado_por) REFERENCES usuarios(id);
ALTER TABLE workflows ADD CONSTRAINT fk_workflows_1 FOREIGN KEY (filial_id) REFERENCES filiais(id);
ALTER TABLE workflows ADD CONSTRAINT fk_workflows_2 FOREIGN KEY (empresa_id) REFERENCES empresas(id);

-- Integridade empresa/filial: FK composta em vez de triggers SQLite.
CREATE UNIQUE INDEX IF NOT EXISTS ux_filiais_id_empresa ON filiais(id, empresa_id);
ALTER TABLE aprovacoes ADD CONSTRAINT fk_aprovacoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE aprovacoes VALIDATE CONSTRAINT fk_aprovacoes_filial_empresa;
ALTER TABLE arquivos_corporativos ADD CONSTRAINT fk_arquivos_corporativos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE arquivos_corporativos VALIDATE CONSTRAINT fk_arquivos_corporativos_filial_empresa;
ALTER TABLE atividades ADD CONSTRAINT fk_atividades_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE atividades VALIDATE CONSTRAINT fk_atividades_filial_empresa;
ALTER TABLE ativos_ti ADD CONSTRAINT fk_ativos_ti_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ativos_ti VALIDATE CONSTRAINT fk_ativos_ti_filial_empresa;
ALTER TABLE auditoria ADD CONSTRAINT fk_auditoria_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE auditoria VALIDATE CONSTRAINT fk_auditoria_filial_empresa;
ALTER TABLE backups_empresariais ADD CONSTRAINT fk_backups_empresariais_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE backups_empresariais VALIDATE CONSTRAINT fk_backups_empresariais_filial_empresa;
ALTER TABLE campanhas_marketing ADD CONSTRAINT fk_campanhas_marketing_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE campanhas_marketing VALIDATE CONSTRAINT fk_campanhas_marketing_filial_empresa;
ALTER TABLE chamados_ti ADD CONSTRAINT fk_chamados_ti_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE chamados_ti VALIDATE CONSTRAINT fk_chamados_ti_filial_empresa;
ALTER TABLE cmp_alertas ADD CONSTRAINT fk_cmp_alertas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE cmp_alertas VALIDATE CONSTRAINT fk_cmp_alertas_filial_empresa;
ALTER TABLE cmp_aprovacoes_solicitacao ADD CONSTRAINT fk_cmp_aprovacoes_solicitacao_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE cmp_aprovacoes_solicitacao VALIDATE CONSTRAINT fk_cmp_aprovacoes_solicitacao_filial_empresa;
ALTER TABLE cmp_contratos ADD CONSTRAINT fk_cmp_contratos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE cmp_contratos VALIDATE CONSTRAINT fk_cmp_contratos_filial_empresa;
ALTER TABLE cmp_cotacoes ADD CONSTRAINT fk_cmp_cotacoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE cmp_cotacoes VALIDATE CONSTRAINT fk_cmp_cotacoes_filial_empresa;
ALTER TABLE cmp_divergencias ADD CONSTRAINT fk_cmp_divergencias_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE cmp_divergencias VALIDATE CONSTRAINT fk_cmp_divergencias_filial_empresa;
ALTER TABLE cmp_fornecedor_avaliacoes ADD CONSTRAINT fk_cmp_fornecedor_avaliacoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE cmp_fornecedor_avaliacoes VALIDATE CONSTRAINT fk_cmp_fornecedor_avaliacoes_filial_empresa;
ALTER TABLE cmp_historico ADD CONSTRAINT fk_cmp_historico_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE cmp_historico VALIDATE CONSTRAINT fk_cmp_historico_filial_empresa;
ALTER TABLE cmp_pedidos ADD CONSTRAINT fk_cmp_pedidos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE cmp_pedidos VALIDATE CONSTRAINT fk_cmp_pedidos_filial_empresa;
ALTER TABLE cmp_recebimentos ADD CONSTRAINT fk_cmp_recebimentos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE cmp_recebimentos VALIDATE CONSTRAINT fk_cmp_recebimentos_filial_empresa;
ALTER TABLE cmp_relatorios_agendados ADD CONSTRAINT fk_cmp_relatorios_agendados_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE cmp_relatorios_agendados VALIDATE CONSTRAINT fk_cmp_relatorios_agendados_filial_empresa;
ALTER TABLE cmp_solicitacoes ADD CONSTRAINT fk_cmp_solicitacoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE cmp_solicitacoes VALIDATE CONSTRAINT fk_cmp_solicitacoes_filial_empresa;
ALTER TABLE colaboradores ADD CONSTRAINT fk_colaboradores_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE colaboradores VALIDATE CONSTRAINT fk_colaboradores_filial_empresa;
ALTER TABLE conjuntos_dados ADD CONSTRAINT fk_conjuntos_dados_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE conjuntos_dados VALIDATE CONSTRAINT fk_conjuntos_dados_filial_empresa;
ALTER TABLE contratos_juridicos ADD CONSTRAINT fk_contratos_juridicos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE contratos_juridicos VALIDATE CONSTRAINT fk_contratos_juridicos_filial_empresa;
ALTER TABLE correio_mensagens ADD CONSTRAINT fk_correio_mensagens_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE correio_mensagens VALIDATE CONSTRAINT fk_correio_mensagens_filial_empresa;
ALTER TABLE documentos ADD CONSTRAINT fk_documentos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE documentos VALIDATE CONSTRAINT fk_documentos_filial_empresa;
ALTER TABLE est_alertas ADD CONSTRAINT fk_est_alertas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE est_alertas VALIDATE CONSTRAINT fk_est_alertas_filial_empresa;
ALTER TABLE est_depositos ADD CONSTRAINT fk_est_depositos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE est_depositos VALIDATE CONSTRAINT fk_est_depositos_filial_empresa;
ALTER TABLE est_inventarios ADD CONSTRAINT fk_est_inventarios_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE est_inventarios VALIDATE CONSTRAINT fk_est_inventarios_filial_empresa;
ALTER TABLE est_movimentacoes ADD CONSTRAINT fk_est_movimentacoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE est_movimentacoes VALIDATE CONSTRAINT fk_est_movimentacoes_filial_empresa;
ALTER TABLE est_ocorrencias ADD CONSTRAINT fk_est_ocorrencias_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE est_ocorrencias VALIDATE CONSTRAINT fk_est_ocorrencias_filial_empresa;
ALTER TABLE est_operacoes ADD CONSTRAINT fk_est_operacoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE est_operacoes VALIDATE CONSTRAINT fk_est_operacoes_filial_empresa;
ALTER TABLE est_relatorios_agendados ADD CONSTRAINT fk_est_relatorios_agendados_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE est_relatorios_agendados VALIDATE CONSTRAINT fk_est_relatorios_agendados_filial_empresa;
ALTER TABLE est_reposicoes ADD CONSTRAINT fk_est_reposicoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE est_reposicoes VALIDATE CONSTRAINT fk_est_reposicoes_filial_empresa;
ALTER TABLE est_reservas ADD CONSTRAINT fk_est_reservas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE est_reservas VALIDATE CONSTRAINT fk_est_reservas_filial_empresa;
ALTER TABLE est_saldos ADD CONSTRAINT fk_est_saldos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE est_saldos VALIDATE CONSTRAINT fk_est_saldos_filial_empresa;
ALTER TABLE est_solicitacoes ADD CONSTRAINT fk_est_solicitacoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE est_solicitacoes VALIDATE CONSTRAINT fk_est_solicitacoes_filial_empresa;
ALTER TABLE fin_aprovacoes ADD CONSTRAINT fk_fin_aprovacoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE fin_aprovacoes VALIDATE CONSTRAINT fk_fin_aprovacoes_filial_empresa;
ALTER TABLE fin_baixas ADD CONSTRAINT fk_fin_baixas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE fin_baixas VALIDATE CONSTRAINT fk_fin_baixas_filial_empresa;
ALTER TABLE fin_cartoes ADD CONSTRAINT fk_fin_cartoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE fin_cartoes VALIDATE CONSTRAINT fk_fin_cartoes_filial_empresa;
ALTER TABLE fin_contas ADD CONSTRAINT fk_fin_contas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE fin_contas VALIDATE CONSTRAINT fk_fin_contas_filial_empresa;
ALTER TABLE fin_extratos ADD CONSTRAINT fk_fin_extratos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE fin_extratos VALIDATE CONSTRAINT fk_fin_extratos_filial_empresa;
ALTER TABLE fin_lancamentos ADD CONSTRAINT fk_fin_lancamentos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE fin_lancamentos VALIDATE CONSTRAINT fk_fin_lancamentos_filial_empresa;
ALTER TABLE fin_orcamentos ADD CONSTRAINT fk_fin_orcamentos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE fin_orcamentos VALIDATE CONSTRAINT fk_fin_orcamentos_filial_empresa;
ALTER TABLE fin_partes ADD CONSTRAINT fk_fin_partes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE fin_partes VALIDATE CONSTRAINT fk_fin_partes_filial_empresa;
ALTER TABLE fin_projetos ADD CONSTRAINT fk_fin_projetos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE fin_projetos VALIDATE CONSTRAINT fk_fin_projetos_filial_empresa;
ALTER TABLE fin_recorrencias ADD CONSTRAINT fk_fin_recorrencias_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE fin_recorrencias VALIDATE CONSTRAINT fk_fin_recorrencias_filial_empresa;
ALTER TABLE fin_relatorios_agendados ADD CONSTRAINT fk_fin_relatorios_agendados_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE fin_relatorios_agendados VALIDATE CONSTRAINT fk_fin_relatorios_agendados_filial_empresa;
ALTER TABLE historico_alteracoes ADD CONSTRAINT fk_historico_alteracoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE historico_alteracoes VALIDATE CONSTRAINT fk_historico_alteracoes_filial_empresa;
ALTER TABLE integracoes ADD CONSTRAINT fk_integracoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE integracoes VALIDATE CONSTRAINT fk_integracoes_filial_empresa;
ALTER TABLE itens_estoque ADD CONSTRAINT fk_itens_estoque_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE itens_estoque VALIDATE CONSTRAINT fk_itens_estoque_filial_empresa;
ALTER TABLE jobs ADD CONSTRAINT fk_jobs_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE jobs VALIDATE CONSTRAINT fk_jobs_filial_empresa;
ALTER TABLE lancamentos_financeiros ADD CONSTRAINT fk_lancamentos_financeiros_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE lancamentos_financeiros VALIDATE CONSTRAINT fk_lancamentos_financeiros_filial_empresa;
ALTER TABLE mensagens ADD CONSTRAINT fk_mensagens_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE mensagens VALIDATE CONSTRAINT fk_mensagens_filial_empresa;
ALTER TABLE movimentos_estoque ADD CONSTRAINT fk_movimentos_estoque_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE movimentos_estoque VALIDATE CONSTRAINT fk_movimentos_estoque_filial_empresa;
ALTER TABLE nos_plataforma ADD CONSTRAINT fk_nos_plataforma_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE nos_plataforma VALIDATE CONSTRAINT fk_nos_plataforma_filial_empresa;
ALTER TABLE notificacoes ADD CONSTRAINT fk_notificacoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE notificacoes VALIDATE CONSTRAINT fk_notificacoes_filial_empresa;
ALTER TABLE oportunidades_comerciais ADD CONSTRAINT fk_oportunidades_comerciais_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE oportunidades_comerciais VALIDATE CONSTRAINT fk_oportunidades_comerciais_filial_empresa;
ALTER TABLE recursos_departamentais ADD CONSTRAINT fk_recursos_departamentais_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE recursos_departamentais VALIDATE CONSTRAINT fk_recursos_departamentais_filial_empresa;
ALTER TABLE relatorios_corporativos ADD CONSTRAINT fk_relatorios_corporativos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE relatorios_corporativos VALIDATE CONSTRAINT fk_relatorios_corporativos_filial_empresa;
ALTER TABLE rh_admissoes ADD CONSTRAINT fk_rh_admissoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_admissoes VALIDATE CONSTRAINT fk_rh_admissoes_filial_empresa;
ALTER TABLE rh_avaliacoes ADD CONSTRAINT fk_rh_avaliacoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_avaliacoes VALIDATE CONSTRAINT fk_rh_avaliacoes_filial_empresa;
ALTER TABLE rh_colaboradores ADD CONSTRAINT fk_rh_colaboradores_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_colaboradores VALIDATE CONSTRAINT fk_rh_colaboradores_filial_empresa;
ALTER TABLE rh_contracheques ADD CONSTRAINT fk_rh_contracheques_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_contracheques VALIDATE CONSTRAINT fk_rh_contracheques_filial_empresa;
ALTER TABLE rh_desligamentos ADD CONSTRAINT fk_rh_desligamentos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_desligamentos VALIDATE CONSTRAINT fk_rh_desligamentos_filial_empresa;
ALTER TABLE rh_documentos ADD CONSTRAINT fk_rh_documentos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_documentos VALIDATE CONSTRAINT fk_rh_documentos_filial_empresa;
ALTER TABLE rh_equipamentos ADD CONSTRAINT fk_rh_equipamentos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_equipamentos VALIDATE CONSTRAINT fk_rh_equipamentos_filial_empresa;
ALTER TABLE rh_ferias_ausencias ADD CONSTRAINT fk_rh_ferias_ausencias_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_ferias_ausencias VALIDATE CONSTRAINT fk_rh_ferias_ausencias_filial_empresa;
ALTER TABLE rh_folhas ADD CONSTRAINT fk_rh_folhas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_folhas VALIDATE CONSTRAINT fk_rh_folhas_filial_empresa;
ALTER TABLE rh_historico_profissional ADD CONSTRAINT fk_rh_historico_profissional_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_historico_profissional VALIDATE CONSTRAINT fk_rh_historico_profissional_filial_empresa;
ALTER TABLE rh_pontos ADD CONSTRAINT fk_rh_pontos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_pontos VALIDATE CONSTRAINT fk_rh_pontos_filial_empresa;
ALTER TABLE rh_relatorios_agendados ADD CONSTRAINT fk_rh_relatorios_agendados_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_relatorios_agendados VALIDATE CONSTRAINT fk_rh_relatorios_agendados_filial_empresa;
ALTER TABLE rh_solicitacoes ADD CONSTRAINT fk_rh_solicitacoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_solicitacoes VALIDATE CONSTRAINT fk_rh_solicitacoes_filial_empresa;
ALTER TABLE rh_vagas ADD CONSTRAINT fk_rh_vagas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE rh_vagas VALIDATE CONSTRAINT fk_rh_vagas_filial_empresa;
ALTER TABLE solicitacoes_administrativas ADD CONSTRAINT fk_solicitacoes_administrativas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE solicitacoes_administrativas VALIDATE CONSTRAINT fk_solicitacoes_administrativas_filial_empresa;
ALTER TABLE solicitacoes_compra ADD CONSTRAINT fk_solicitacoes_compra_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE solicitacoes_compra VALIDATE CONSTRAINT fk_solicitacoes_compra_filial_empresa;
ALTER TABLE tarefas ADD CONSTRAINT fk_tarefas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE tarefas VALIDATE CONSTRAINT fk_tarefas_filial_empresa;
ALTER TABLE ti_acessos_remotos ADD CONSTRAINT fk_ti_acessos_remotos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_acessos_remotos VALIDATE CONSTRAINT fk_ti_acessos_remotos_filial_empresa;
ALTER TABLE ti_agentes ADD CONSTRAINT fk_ti_agentes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_agentes VALIDATE CONSTRAINT fk_ti_agentes_filial_empresa;
ALTER TABLE ti_alertas ADD CONSTRAINT fk_ti_alertas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_alertas VALIDATE CONSTRAINT fk_ti_alertas_filial_empresa;
ALTER TABLE ti_ativos ADD CONSTRAINT fk_ti_ativos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_ativos VALIDATE CONSTRAINT fk_ti_ativos_filial_empresa;
ALTER TABLE ti_chamados ADD CONSTRAINT fk_ti_chamados_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_chamados VALIDATE CONSTRAINT fk_ti_chamados_filial_empresa;
ALTER TABLE ti_contratos ADD CONSTRAINT fk_ti_contratos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_contratos VALIDATE CONSTRAINT fk_ti_contratos_filial_empresa;
ALTER TABLE ti_dispositivos_rede ADD CONSTRAINT fk_ti_dispositivos_rede_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_dispositivos_rede VALIDATE CONSTRAINT fk_ti_dispositivos_rede_filial_empresa;
ALTER TABLE ti_emprestimos ADD CONSTRAINT fk_ti_emprestimos_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_emprestimos VALIDATE CONSTRAINT fk_ti_emprestimos_filial_empresa;
ALTER TABLE ti_historico ADD CONSTRAINT fk_ti_historico_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_historico VALIDATE CONSTRAINT fk_ti_historico_filial_empresa;
ALTER TABLE ti_incidentes_seguranca ADD CONSTRAINT fk_ti_incidentes_seguranca_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_incidentes_seguranca VALIDATE CONSTRAINT fk_ti_incidentes_seguranca_filial_empresa;
ALTER TABLE ti_licencas ADD CONSTRAINT fk_ti_licencas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_licencas VALIDATE CONSTRAINT fk_ti_licencas_filial_empresa;
ALTER TABLE ti_manutencoes ADD CONSTRAINT fk_ti_manutencoes_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_manutencoes VALIDATE CONSTRAINT fk_ti_manutencoes_filial_empresa;
ALTER TABLE ti_monitores ADD CONSTRAINT fk_ti_monitores_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_monitores VALIDATE CONSTRAINT fk_ti_monitores_filial_empresa;
ALTER TABLE ti_mudancas ADD CONSTRAINT fk_ti_mudancas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_mudancas VALIDATE CONSTRAINT fk_ti_mudancas_filial_empresa;
ALTER TABLE ti_problemas ADD CONSTRAINT fk_ti_problemas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_problemas VALIDATE CONSTRAINT fk_ti_problemas_filial_empresa;
ALTER TABLE ti_segmentos_rede ADD CONSTRAINT fk_ti_segmentos_rede_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_segmentos_rede VALIDATE CONSTRAINT fk_ti_segmentos_rede_filial_empresa;
ALTER TABLE ti_sistemas ADD CONSTRAINT fk_ti_sistemas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE ti_sistemas VALIDATE CONSTRAINT fk_ti_sistemas_filial_empresa;
ALTER TABLE usuarios_empresas ADD CONSTRAINT fk_usuarios_empresas_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE usuarios_empresas VALIDATE CONSTRAINT fk_usuarios_empresas_filial_empresa;
ALTER TABLE workflows ADD CONSTRAINT fk_workflows_filial_empresa FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id) NOT VALID;
ALTER TABLE workflows VALIDATE CONSTRAINT fk_workflows_filial_empresa;

-- Compatibilidade centavos/valor para aprovações.
CREATE OR REPLACE FUNCTION di_aprovacoes_sync_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF COALESCE(NEW.valor_centavos, 0) = 0 AND ABS(COALESCE(NEW.valor, 0)) > 0 THEN NEW.valor_centavos := ROUND(COALESCE(NEW.valor,0) * 100);
  ELSIF COALESCE(NEW.valor_centavos, 0) <> 0 THEN NEW.valor := NEW.valor_centavos / 100.0; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_aprovacoes_valor_insert BEFORE INSERT ON aprovacoes FOR EACH ROW EXECUTE FUNCTION di_aprovacoes_sync_insert();
CREATE OR REPLACE FUNCTION di_aprovacoes_sync_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.valor IS DISTINCT FROM OLD.valor THEN NEW.valor_centavos := ROUND(COALESCE(NEW.valor,0)*100); END IF;
  IF NEW.valor_centavos IS DISTINCT FROM OLD.valor_centavos THEN NEW.valor := COALESCE(NEW.valor_centavos,0)/100.0; END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_aprovacoes_valor_update BEFORE UPDATE OF valor, valor_centavos ON aprovacoes FOR EACH ROW EXECUTE FUNCTION di_aprovacoes_sync_update();


-- Persistência central que não existia no baseline V10.1 original.
CREATE TABLE IF NOT EXISTS historico_analises (
    id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    empresa_id INTEGER REFERENCES empresas(id),
    filial_id INTEGER,
    categoria TEXT NOT NULL,
    fonte TEXT NOT NULL,
    quantidade_arquivos INTEGER NOT NULL,
    total_registros INTEGER NOT NULL,
    total_colunas INTEGER NOT NULL,
    score_qualidade DOUBLE PRECISION,
    nivel_qualidade TEXT,
    status TEXT NOT NULL DEFAULT 'concluida',
    resumo_json TEXT NOT NULL,
    estado_registro TEXT NOT NULL DEFAULT 'Ativo',
    excluido_em TEXT,
    excluido_por INTEGER REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    FOREIGN KEY (filial_id, empresa_id) REFERENCES filiais(id, empresa_id)
);
CREATE INDEX IF NOT EXISTS idx_historico_analises_escopo
    ON historico_analises (empresa_id, filial_id, usuario_id, estado_registro, id DESC);

CREATE TABLE IF NOT EXISTS preferencias_usuarios (
    usuario_id INTEGER PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
    preferencias_json TEXT NOT NULL,
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);

-- O baseline já incorpora as migrations SQLite 001..019.
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_001_v6_estabilizacao') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_002_v8_recursos_departamentais') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_003_v8_1_integridade') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_004_v8_2_estabilizacao') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_005_financeiro_departamental') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_006_rh_departamental') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_007_rh_2_0_complementos') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_008_estoque_departamental') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_009_compras_departamental') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_010_tecnologia_departamental') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_011_tecnologia_operacoes_rede') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_012_segmentos_rede_multifilial') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_013_agentes_ti_api') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_014_colaboracao_email_sessoes') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_015_aprovacoes_compras') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_016_relatorios_formatos') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_017_consistencia_monetaria_aprovacoes') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_018_caminhos_rh_portaveis') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('enterprise_019_compatibilidade_v9_legada') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('v5_1_perfis_departamentais') ON CONFLICT (chave) DO NOTHING;
INSERT INTO migracoes_sistema (chave) VALUES ('postgresql_baseline_v10_1') ON CONFLICT (chave) DO NOTHING;
COMMIT;
