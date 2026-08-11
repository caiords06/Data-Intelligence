"""Domínio especializado de Estoque 2.0.

O saldo deixa de ser um número editável e passa a ser consequência de
operações e de um razão imutável de movimentações. Valores monetários são
armazenados em centavos e quantidades continuam decimais para suportar
unidades fracionárias.
"""

from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS est_unidades_medida (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            casas_decimais INTEGER NOT NULL DEFAULT 0 CHECK (casas_decimais BETWEEN 0 AND 6),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        );

        CREATE TABLE IF NOT EXISTS est_categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            categoria_pai_id INTEGER,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (categoria_pai_id) REFERENCES est_categorias(id)
        );

        CREATE TABLE IF NOT EXISTS est_fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            documento TEXT,
            email TEXT,
            telefone TEXT,
            prazo_medio_dias INTEGER NOT NULL DEFAULT 0 CHECK (prazo_medio_dias >= 0),
            avaliacao REAL NOT NULL DEFAULT 0 CHECK (avaliacao BETWEEN 0 AND 10),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, documento),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        );

        CREATE TABLE IF NOT EXISTS est_depositos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Depósito',
            endereco TEXT,
            capacidade REAL NOT NULL DEFAULT 0 CHECK (capacidade >= 0),
            responsavel_id INTEGER,
            permite_negativo INTEGER NOT NULL DEFAULT 0 CHECK (permite_negativo IN (0, 1)),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, filial_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS est_localizacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deposito_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            corredor TEXT,
            prateleira TEXT,
            nivel TEXT,
            posicao TEXT,
            capacidade REAL NOT NULL DEFAULT 0 CHECK (capacidade >= 0),
            bloqueada INTEGER NOT NULL DEFAULT 0 CHECK (bloqueada IN (0, 1)),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (deposito_id, codigo),
            FOREIGN KEY (deposito_id) REFERENCES est_depositos(id)
        );

        CREATE TABLE IF NOT EXISTS est_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            peso REAL NOT NULL DEFAULT 0 CHECK (peso >= 0),
            dimensoes TEXT,
            foto_caminho TEXT,
            fornecedor_principal_id INTEGER,
            estoque_minimo REAL NOT NULL DEFAULT 0 CHECK (estoque_minimo >= 0),
            estoque_maximo REAL NOT NULL DEFAULT 0 CHECK (estoque_maximo >= 0),
            ponto_reposicao REAL NOT NULL DEFAULT 0 CHECK (ponto_reposicao >= 0),
            estoque_seguranca REAL NOT NULL DEFAULT 0 CHECK (estoque_seguranca >= 0),
            consumo_medio_dia REAL NOT NULL DEFAULT 0 CHECK (consumo_medio_dia >= 0),
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo),
            UNIQUE (empresa_id, sku),
            UNIQUE (empresa_id, codigo_barras),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (categoria_id) REFERENCES est_categorias(id),
            FOREIGN KEY (unidade_id) REFERENCES est_unidades_medida(id),
            FOREIGN KEY (fornecedor_principal_id) REFERENCES est_fornecedores(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_est_itens_busca
            ON est_itens (empresa_id, status, nome, codigo);

        CREATE TABLE IF NOT EXISTS est_lotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            fornecedor_id INTEGER,
            numero TEXT NOT NULL,
            fabricante TEXT,
            fabricacao TEXT,
            validade TEXT,
            quantidade_original REAL NOT NULL DEFAULT 0 CHECK (quantidade_original >= 0),
            status TEXT NOT NULL DEFAULT 'Disponível',
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, item_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (fornecedor_id) REFERENCES est_fornecedores(id)
        );

        CREATE TABLE IF NOT EXISTS est_seriais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero_serie),
            UNIQUE (empresa_id, patrimonio),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (lote_id) REFERENCES est_lotes(id),
            FOREIGN KEY (deposito_id) REFERENCES est_depositos(id),
            FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id)
        );

        CREATE TABLE IF NOT EXISTS est_saldos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            item_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            localizacao_id INTEGER,
            lote_id INTEGER,
            quantidade_fisica REAL NOT NULL DEFAULT 0,
            quantidade_reservada REAL NOT NULL DEFAULT 0 CHECK (quantidade_reservada >= 0),
            quantidade_bloqueada REAL NOT NULL DEFAULT 0 CHECK (quantidade_bloqueada >= 0),
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (item_id, deposito_id, localizacao_id, lote_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (deposito_id) REFERENCES est_depositos(id),
            FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id),
            FOREIGN KEY (lote_id) REFERENCES est_lotes(id)
        );
        CREATE INDEX IF NOT EXISTS idx_est_saldos_escopo
            ON est_saldos (empresa_id, filial_id, item_id, deposito_id);

        CREATE TABLE IF NOT EXISTS est_operacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (deposito_origem_id) REFERENCES est_depositos(id),
            FOREIGN KEY (deposito_destino_id) REFERENCES est_depositos(id),
            FOREIGN KEY (localizacao_origem_id) REFERENCES est_localizacoes(id),
            FOREIGN KEY (localizacao_destino_id) REFERENCES est_localizacoes(id),
            FOREIGN KEY (fornecedor_id) REFERENCES est_fornecedores(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (solicitante_id) REFERENCES usuarios(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id),
            FOREIGN KEY (documento_id) REFERENCES documentos(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (confirmado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_est_operacoes_escopo
            ON est_operacoes (empresa_id, filial_id, tipo, status, criado_em DESC);

        CREATE TABLE IF NOT EXISTS est_operacao_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operacao_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantidade_solicitada REAL NOT NULL CHECK (quantidade_solicitada > 0),
            quantidade_conferida REAL NOT NULL DEFAULT 0 CHECK (quantidade_conferida >= 0),
            custo_unitario_centavos INTEGER NOT NULL DEFAULT 0 CHECK (custo_unitario_centavos >= 0),
            lote_id INTEGER,
            lote_numero TEXT,
            fabricacao TEXT,
            validade TEXT,
            seriais_json TEXT NOT NULL DEFAULT '[]',
            divergencia_motivo TEXT,
            observacao TEXT,
            FOREIGN KEY (operacao_id) REFERENCES est_operacoes(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (lote_id) REFERENCES est_lotes(id)
        );

        CREATE TABLE IF NOT EXISTS est_movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            operacao_id INTEGER,
            item_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            localizacao_id INTEGER,
            lote_id INTEGER,
            tipo TEXT NOT NULL,
            quantidade REAL NOT NULL CHECK (quantidade != 0),
            custo_unitario_centavos INTEGER NOT NULL DEFAULT 0,
            saldo_anterior REAL NOT NULL,
            saldo_posterior REAL NOT NULL,
            centro_custo_id INTEGER,
            departamento_id INTEGER,
            motivo TEXT,
            documento TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (operacao_id) REFERENCES est_operacoes(id),
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (deposito_id) REFERENCES est_depositos(id),
            FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id),
            FOREIGN KEY (lote_id) REFERENCES est_lotes(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_est_movimentacoes_razao
            ON est_movimentacoes (empresa_id, item_id, criado_em DESC);

        CREATE TRIGGER IF NOT EXISTS trg_est_movimentacoes_sem_update
        BEFORE UPDATE ON est_movimentacoes BEGIN
            SELECT RAISE(ABORT, 'o razão de estoque é imutável');
        END;
        CREATE TRIGGER IF NOT EXISTS trg_est_movimentacoes_sem_delete
        BEFORE DELETE ON est_movimentacoes BEGIN
            SELECT RAISE(ABORT, 'o razão de estoque é imutável');
        END;

        CREATE TABLE IF NOT EXISTS est_reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            localizacao_id INTEGER,
            lote_id INTEGER,
            quantidade REAL NOT NULL CHECK (quantidade > 0),
            quantidade_atendida REAL NOT NULL DEFAULT 0 CHECK (quantidade_atendida >= 0),
            solicitante_id INTEGER,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            finalidade TEXT NOT NULL,
            origem_modulo TEXT,
            origem_recurso_id INTEGER,
            expira_em TEXT,
            status TEXT NOT NULL DEFAULT 'Ativa',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (deposito_id) REFERENCES est_depositos(id),
            FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id),
            FOREIGN KEY (lote_id) REFERENCES est_lotes(id),
            FOREIGN KEY (solicitante_id) REFERENCES usuarios(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS est_inventarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (deposito_id) REFERENCES est_depositos(id),
            FOREIGN KEY (categoria_id) REFERENCES est_categorias(id),
            FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS est_inventario_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventario_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            localizacao_id INTEGER,
            lote_id INTEGER,
            quantidade_sistema REAL NOT NULL,
            primeira_contagem REAL,
            segunda_contagem REAL,
            quantidade_final REAL,
            divergencia REAL NOT NULL DEFAULT 0,
            motivo_divergencia TEXT,
            contado_por INTEGER,
            recontado_por INTEGER,
            contado_em TEXT,
            recontado_em TEXT,
            UNIQUE (inventario_id, item_id, localizacao_id, lote_id),
            FOREIGN KEY (inventario_id) REFERENCES est_inventarios(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (localizacao_id) REFERENCES est_localizacoes(id),
            FOREIGN KEY (lote_id) REFERENCES est_lotes(id),
            FOREIGN KEY (contado_por) REFERENCES usuarios(id),
            FOREIGN KEY (recontado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS est_solicitacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            solicitante_id INTEGER,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            item_id INTEGER NOT NULL,
            quantidade REAL NOT NULL CHECK (quantidade > 0),
            justificativa TEXT NOT NULL,
            prioridade TEXT NOT NULL DEFAULT 'Normal',
            status TEXT NOT NULL DEFAULT 'Solicitada',
            aprovacao_id INTEGER,
            reserva_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (solicitante_id) REFERENCES usuarios(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id),
            FOREIGN KEY (reserva_id) REFERENCES est_reservas(id)
        );

        CREATE TABLE IF NOT EXISTS est_ocorrencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            numero TEXT NOT NULL,
            tipo TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            lote_id INTEGER,
            serial_id INTEGER,
            quantidade REAL NOT NULL CHECK (quantidade > 0),
            motivo TEXT NOT NULL,
            destino TEXT,
            foto_caminho TEXT,
            status TEXT NOT NULL DEFAULT 'Aberta',
            aprovacao_id INTEGER,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (deposito_id) REFERENCES est_depositos(id),
            FOREIGN KEY (lote_id) REFERENCES est_lotes(id),
            FOREIGN KEY (serial_id) REFERENCES est_seriais(id),
            FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS est_reposicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            item_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            saldo_disponivel REAL NOT NULL,
            consumo_medio_dia REAL NOT NULL,
            cobertura_dias REAL,
            quantidade_sugerida REAL NOT NULL CHECK (quantidade_sugerida > 0),
            justificativa TEXT,
            status TEXT NOT NULL DEFAULT 'Sugerida',
            solicitacao_compra_id INTEGER,
            tarefa_id INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (deposito_id) REFERENCES est_depositos(id),
            FOREIGN KEY (solicitacao_compra_id) REFERENCES solicitacoes_compra(id),
            FOREIGN KEY (tarefa_id) REFERENCES tarefas(id)
        );

        CREATE TABLE IF NOT EXISTS est_alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            resolvido_em TEXT,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (deposito_id) REFERENCES est_depositos(id),
            FOREIGN KEY (lote_id) REFERENCES est_lotes(id),
            FOREIGN KEY (operacao_id) REFERENCES est_operacoes(id),
            FOREIGN KEY (resolvido_por) REFERENCES usuarios(id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_est_alertas_chave
            ON est_alertas (
                empresa_id, tipo, IFNULL(item_id, 0),
                IFNULL(deposito_id, 0), IFNULL(lote_id, 0)
            );

        CREATE TABLE IF NOT EXISTS est_custos_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            operacao_id INTEGER,
            custo_anterior_centavos INTEGER NOT NULL,
            custo_novo_centavos INTEGER NOT NULL,
            quantidade_entrada REAL NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (item_id) REFERENCES est_itens(id),
            FOREIGN KEY (operacao_id) REFERENCES est_operacoes(id)
        );

        CREATE TABLE IF NOT EXISTS est_permissoes_acoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            permitido INTEGER NOT NULL DEFAULT 0 CHECK (permitido IN (0, 1)),
            atualizado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (usuario_id, empresa_id, acao),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS est_usuarios_depositos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            deposito_id INTEGER NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (usuario_id, deposito_id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (deposito_id) REFERENCES est_depositos(id)
        );

        CREATE TABLE IF NOT EXISTS est_relatorios_agendados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        """
    )
