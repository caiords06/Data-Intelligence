"""Domínio especializado de Recursos Humanos.

Preserva ``colaboradores`` como origem legada e passa a concentrar as novas
operações nas tabelas ``rh_*``. Dados monetários são armazenados em centavos.
"""

from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS rh_cargos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id)
        );

        CREATE TABLE IF NOT EXISTS rh_colaboradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            jornada_semanal REAL NOT NULL DEFAULT 44,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            origem_legado_id INTEGER,
            UNIQUE (empresa_id, matricula),
            UNIQUE (empresa_id, cpf),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (cargo_id) REFERENCES rh_cargos(id),
            FOREIGN KEY (gestor_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_rh_colaboradores_escopo
            ON rh_colaboradores (empresa_id, filial_id, status, nome_completo);

        CREATE TABLE IF NOT EXISTS rh_dependentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            parentesco TEXT NOT NULL,
            nascimento TEXT,
            cpf TEXT,
            dependente_ir INTEGER NOT NULL DEFAULT 0 CHECK (dependente_ir IN (0, 1)),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rh_historico_profissional (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            vigencia TEXT NOT NULL,
            dados_antes TEXT,
            dados_depois TEXT,
            observacao TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_admissoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_desligamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_ferias_ausencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            inicio TEXT NOT NULL,
            fim TEXT NOT NULL,
            dias REAL NOT NULL CHECK (dias > 0),
            periodo_aquisitivo_inicio TEXT,
            periodo_aquisitivo_fim TEXT,
            saldo_antes REAL NOT NULL DEFAULT 30,
            saldo_depois REAL NOT NULL DEFAULT 30,
            abono_dias REAL NOT NULL DEFAULT 0,
            motivo TEXT,
            anexo_caminho TEXT,
            status TEXT NOT NULL DEFAULT 'Solicitado',
            aprovacao_id INTEGER,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_beneficios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            fornecedor TEXT,
            custo_empresa_centavos INTEGER NOT NULL DEFAULT 0 CHECK (custo_empresa_centavos >= 0),
            desconto_colaborador_centavos INTEGER NOT NULL DEFAULT 0 CHECK (desconto_colaborador_centavos >= 0),
            elegibilidade TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, nome),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        );

        CREATE TABLE IF NOT EXISTS rh_colaborador_beneficios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id INTEGER NOT NULL,
            beneficio_id INTEGER NOT NULL,
            inicio TEXT NOT NULL,
            fim TEXT,
            status TEXT NOT NULL DEFAULT 'Ativo',
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (colaborador_id, beneficio_id, inicio),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (beneficio_id) REFERENCES rh_beneficios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_folhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, filial_id, competencia),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (fechada_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_eventos_folha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folha_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            natureza TEXT NOT NULL CHECK (natureza IN ('Provento', 'Desconto', 'Encargo')),
            valor_centavos INTEGER NOT NULL CHECK (valor_centavos >= 0),
            origem TEXT NOT NULL DEFAULT 'Manual',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (folha_id) REFERENCES rh_folhas(id) ON DELETE CASCADE,
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_pontos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            UNIQUE (colaborador_id, data),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (aprovado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_vagas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (cargo_id) REFERENCES rh_cargos(id),
            FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_candidatos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vaga_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            email TEXT,
            telefone TEXT,
            curriculo_caminho TEXT,
            etapa TEXT NOT NULL DEFAULT 'Inscrição',
            nota REAL,
            observacao TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (vaga_id) REFERENCES rh_vagas(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rh_avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            colaborador_id INTEGER NOT NULL,
            avaliador_id INTEGER,
            ciclo TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Gestor',
            nota REAL,
            competencias_json TEXT NOT NULL DEFAULT '{}',
            feedback TEXT,
            status TEXT NOT NULL DEFAULT 'Planejada',
            realizada_em TEXT,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (avaliador_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_pdis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            objetivo TEXT NOT NULL,
            acoes_json TEXT NOT NULL DEFAULT '[]',
            inicio TEXT NOT NULL,
            prazo TEXT,
            progresso INTEGER NOT NULL DEFAULT 0 CHECK (progresso BETWEEN 0 AND 100),
            status TEXT NOT NULL DEFAULT 'Ativo',
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id)
        );

        CREATE TABLE IF NOT EXISTS rh_treinamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Interno',
            carga_horaria REAL NOT NULL DEFAULT 0,
            validade_meses INTEGER,
            obrigatorio INTEGER NOT NULL DEFAULT 0 CHECK (obrigatorio IN (0, 1)),
            custo_centavos INTEGER NOT NULL DEFAULT 0,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            UNIQUE (empresa_id, titulo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        );

        CREATE TABLE IF NOT EXISTS rh_inscricoes_treinamento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            treinamento_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            inscrito_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            concluido_em TEXT,
            nota REAL,
            certificado_caminho TEXT,
            status TEXT NOT NULL DEFAULT 'Inscrito',
            UNIQUE (treinamento_id, colaborador_id),
            FOREIGN KEY (treinamento_id) REFERENCES rh_treinamentos(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id)
        );

        CREATE TABLE IF NOT EXISTS rh_documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_solicitacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_permissoes_acoes (
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            permitido INTEGER NOT NULL CHECK (permitido IN (0, 1)),
            atualizado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (usuario_id, empresa_id, acao),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS rh_relatorios_agendados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            tipo TEXT NOT NULL,
            formato TEXT NOT NULL,
            frequencia TEXT NOT NULL,
            destinatarios TEXT,
            filtros_json TEXT NOT NULL DEFAULT '{}',
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        """
    )

    # Catálogos e registros legados continuam acessíveis sem duplicar IDs.
    empresas = conexao.execute("SELECT id FROM empresas").fetchall()
    for empresa in empresas:
        empresa_id = int(empresa["id"])
        for codigo, titulo, nivel in (
            ("ADM-ASS", "Assistente Administrativo", "Assistente"),
            ("ANA-JR", "Analista Júnior", "Júnior"),
            ("ANA-PL", "Analista Pleno", "Pleno"),
            ("ANA-SR", "Analista Sênior", "Sênior"),
            ("GES", "Gestor", "Gestão"),
        ):
            conexao.execute(
                "INSERT OR IGNORE INTO rh_cargos (empresa_id, codigo, titulo, nivel) VALUES (?, ?, ?, ?)",
                (empresa_id, codigo, titulo, nivel),
            )
        for nome, tipo in (
            ("Vale-refeição", "Alimentação"),
            ("Vale-transporte", "Transporte"),
            ("Plano de saúde", "Saúde"),
            ("Seguro de vida", "Seguro"),
        ):
            conexao.execute(
                "INSERT OR IGNORE INTO rh_beneficios (empresa_id, nome, tipo) VALUES (?, ?, ?)",
                (empresa_id, nome, tipo),
            )

    conexao.execute(
        """
        INSERT INTO rh_colaboradores (
            id, empresa_id, filial_id, departamento_id, centro_custo_id,
            matricula, nome_completo, email_corporativo, cargo_texto,
            admissao, salario_centavos, status, etapa_jornada, criado_por,
            atualizado_por, criado_em, atualizado_em, origem_legado_id
        )
        SELECT
            -id, empresa_id, filial_id, departamento_id, centro_custo_id,
            'LEG-' || printf('%06d', id), nome, email, cargo,
            COALESCE(admissao, substr(criado_em, 1, 10)),
            COALESCE(salario_centavos, ROUND(salario * 100)),
            status, CASE WHEN status='Ativo' THEN 'Ativo' ELSE 'Desligamento' END,
            criado_por, criado_por, criado_em, COALESCE(atualizado_em, criado_em), id
        FROM colaboradores legado
        WHERE NOT EXISTS (
            SELECT 1 FROM rh_colaboradores novo
            WHERE novo.origem_legado_id = legado.id
        )
        """
    )
