"""Domínio financeiro especializado e auditável.

A migração preserva ``lancamentos_financeiros`` como legado e copia seu
conteúdo para o novo livro. A partir desta versão, a interface financeira usa
exclusivamente as tabelas ``fin_*``.
"""

from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS fin_partes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, documento),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS fin_contas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, filial_id, nome),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS fin_plano_contas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (conta_pai_id) REFERENCES fin_plano_contas(id)
        );

        CREATE TABLE IF NOT EXISTS fin_categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            natureza TEXT NOT NULL
                CHECK (natureza IN ('Receita', 'Despesa', 'Ambos')),
            plano_conta_id INTEGER,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, nome),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (plano_conta_id) REFERENCES fin_plano_contas(id)
        );

        CREATE TABLE IF NOT EXISTS fin_projetos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Ativo'
                CHECK (status IN ('Ativo', 'Concluído', 'Cancelado')),
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id)
        );

        CREATE TABLE IF NOT EXISTS fin_lancamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (projeto_id) REFERENCES fin_projetos(id),
            FOREIGN KEY (conta_id) REFERENCES fin_contas(id),
            FOREIGN KEY (conta_destino_id) REFERENCES fin_contas(id),
            FOREIGN KEY (plano_conta_id) REFERENCES fin_plano_contas(id),
            FOREIGN KEY (categoria_id) REFERENCES fin_categorias(id),
            FOREIGN KEY (parte_id) REFERENCES fin_partes(id),
            FOREIGN KEY (cancelado_por) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );

        CREATE INDEX IF NOT EXISTS idx_fin_lancamentos_escopo
            ON fin_lancamentos (
                empresa_id, filial_id, status, competencia DESC, id DESC
            );
        CREATE INDEX IF NOT EXISTS idx_fin_lancamentos_vencimento
            ON fin_lancamentos (empresa_id, filial_id, vencimento, status);

        CREATE TABLE IF NOT EXISTS fin_baixas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (lancamento_id) REFERENCES fin_lancamentos(id),
            FOREIGN KEY (conta_id) REFERENCES fin_contas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS fin_recorrencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS fin_orcamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (
                empresa_id, filial_id, departamento_id, centro_custo_id,
                projeto_id, categoria_id, ano, mes
            ),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (projeto_id) REFERENCES fin_projetos(id),
            FOREIGN KEY (categoria_id) REFERENCES fin_categorias(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS fin_extratos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            conta_id INTEGER NOT NULL,
            arquivo_nome TEXT NOT NULL,
            arquivo_hash TEXT NOT NULL,
            formato TEXT NOT NULL CHECK (formato IN ('OFX', 'CSV', 'XLSX')),
            importado_por INTEGER,
            importado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, conta_id, arquivo_hash),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (conta_id) REFERENCES fin_contas(id),
            FOREIGN KEY (importado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS fin_extrato_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            UNIQUE (extrato_id, identificador_banco),
            FOREIGN KEY (extrato_id) REFERENCES fin_extratos(id) ON DELETE CASCADE,
            FOREIGN KEY (lancamento_id) REFERENCES fin_lancamentos(id),
            FOREIGN KEY (conciliado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS fin_regras_aprovacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            valor_minimo_centavos INTEGER NOT NULL DEFAULT 0,
            valor_maximo_centavos INTEGER,
            nivel INTEGER NOT NULL DEFAULT 1 CHECK (nivel > 0),
            perfil_aprovador TEXT NOT NULL,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, nome, nivel),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        );

        CREATE TABLE IF NOT EXISTS fin_aprovacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (lancamento_id, nivel),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (lancamento_id) REFERENCES fin_lancamentos(id),
            FOREIGN KEY (aprovador_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS fin_anexos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            lancamento_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            caminho_relativo TEXT NOT NULL,
            hash_sha256 TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (lancamento_id) REFERENCES fin_lancamentos(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS fin_cartoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            UNIQUE (empresa_id, final),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (conta_id) REFERENCES fin_contas(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id)
        );

        CREATE TABLE IF NOT EXISTS fin_relatorios_agendados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS fin_permissoes_acoes (
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            permitido INTEGER NOT NULL DEFAULT 0 CHECK (permitido IN (0, 1)),
            atualizado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (usuario_id, empresa_id, acao),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        """
    )

    # Catálogo mínimo para a DRE e classificação. ``INSERT OR IGNORE``
    # também atende empresas já existentes sem duplicar o plano.
    planos = (
        ("1", "Receitas", "Receita", "Receita bruta", 0),
        ("1.1", "Vendas", "Receita", "Receita bruta", 1),
        ("1.2", "Serviços", "Receita", "Receita bruta", 1),
        ("1.3", "Receitas financeiras", "Receita", "Resultado financeiro", 1),
        ("2", "Deduções", "Despesa", "Deduções", 0),
        ("2.1", "Impostos sobre vendas", "Despesa", "Deduções", 1),
        ("3", "Custos", "Despesa", "Custos", 0),
        ("3.1", "Mercadorias e produção", "Despesa", "Custos", 1),
        ("4", "Despesas operacionais", "Despesa", "Despesas operacionais", 0),
        ("4.1", "Administrativo", "Despesa", "Despesas operacionais", 1),
        ("4.2", "Marketing", "Despesa", "Despesas operacionais", 1),
        ("4.3", "Tecnologia", "Despesa", "Despesas operacionais", 1),
        ("4.4", "Recursos Humanos", "Despesa", "Despesas operacionais", 1),
        ("5", "Resultado financeiro", "Despesa", "Resultado financeiro", 0),
        ("5.1", "Juros e tarifas", "Despesa", "Resultado financeiro", 1),
        ("9.1", "Transferências internas", "Neutra", "Não operacional", 1),
    )
    empresas = conexao.execute("SELECT id FROM empresas").fetchall()
    for empresa in empresas:
        empresa_id = int(empresa["id"])
        for codigo, nome, natureza, grupo, aceita in planos:
            conexao.execute(
                """
                INSERT OR IGNORE INTO fin_plano_contas (
                    empresa_id, codigo, nome, natureza, grupo_dre, aceita_lancamento
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (empresa_id, codigo, nome, natureza, grupo, aceita),
            )
        for nome, natureza, codigo in (
            ("Vendas", "Receita", "1.1"),
            ("Serviços", "Receita", "1.2"),
            ("Impostos", "Despesa", "2.1"),
            ("Fornecedores", "Despesa", "3.1"),
            ("Administrativo", "Despesa", "4.1"),
            ("Marketing", "Despesa", "4.2"),
            ("Tecnologia", "Despesa", "4.3"),
            ("Pessoal", "Despesa", "4.4"),
            ("Tarifas bancárias", "Despesa", "5.1"),
        ):
            plano = conexao.execute(
                "SELECT id FROM fin_plano_contas WHERE empresa_id=? AND codigo=?",
                (empresa_id, codigo),
            ).fetchone()
            conexao.execute(
                """
                INSERT OR IGNORE INTO fin_categorias (
                    empresa_id, nome, natureza, plano_conta_id
                ) VALUES (?, ?, ?, ?)
                """,
                (empresa_id, nome, natureza, int(plano["id"])),
            )

    # Migra o livro simples uma única vez. O prefixo legado evita colisão
    # com registros criados no novo domínio.
    conexao.execute(
        """
        INSERT INTO fin_lancamentos (
            id, empresa_id, filial_id, centro_custo_id, natureza, descricao,
            competencia, vencimento, liquidacao, valor_original_centavos,
            valor_liquidado_centavos, status, criado_por, atualizado_por,
            criado_em, atualizado_em, origem_modulo, origem_recurso_tipo,
            origem_recurso_id, contabilizado, conciliado
        )
        SELECT
            -id, empresa_id, filial_id, centro_custo_id, tipo, descricao,
            COALESCE(vencimento, substr(criado_em, 1, 10)), vencimento,
            CASE WHEN status IN ('Pago', 'Recebido') THEN vencimento END,
            COALESCE(valor_centavos, ROUND(valor * 100)),
            CASE WHEN status IN ('Pago', 'Recebido')
                 THEN COALESCE(valor_centavos, ROUND(valor * 100)) ELSE 0 END,
            status, criado_por, criado_por, criado_em,
            COALESCE(atualizado_em, criado_em), 'legado',
            'lancamentos_financeiros', id,
            CASE WHEN status IN ('Pago', 'Recebido') THEN 1 ELSE 0 END,
            0
        FROM lancamentos_financeiros legado
        WHERE NOT EXISTS (
            SELECT 1 FROM fin_lancamentos novo
            WHERE novo.origem_modulo='legado'
              AND novo.origem_recurso_id=legado.id
        )
        """
    )

    # Alçadas padrão, editáveis futuramente pela administração.
    for empresa in empresas:
        empresa_id = int(empresa["id"])
        for regra in (
            ("Até R$ 1.000", 0, 100_000, 1, "Gestor"),
            ("De R$ 1.000 a R$ 10.000", 100_001, 1_000_000, 1, "Gerente"),
            ("De R$ 1.000 a R$ 10.000", 100_001, 1_000_000, 2, "Financeiro"),
            ("Acima de R$ 10.000", 1_000_001, None, 1, "Diretor"),
            ("Acima de R$ 10.000", 1_000_001, None, 2, "Financeiro"),
        ):
            conexao.execute(
                """
                INSERT OR IGNORE INTO fin_regras_aprovacao (
                    empresa_id, nome, valor_minimo_centavos,
                    valor_maximo_centavos, nivel, perfil_aprovador
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (empresa_id, *regra),
            )

