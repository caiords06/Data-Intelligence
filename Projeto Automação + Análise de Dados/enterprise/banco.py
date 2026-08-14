"""Bootstrap do schema empresarial; PostgreSQL é canônico em produção."""

from __future__ import annotations

from auth.banco import conectar, backend_banco
from enterprise.migrations import aplicar_migracoes


def inicializar_enterprise() -> None:
    """Cria o núcleo multiempresa e os registros operacionais dos módulos."""
    if backend_banco() == "postgresql":
        from enterprise.postgresql.bootstrap import inicializar_schema_postgresql
        inicializar_schema_postgresql()
        from enterprise.core_v11.provisionamento import provisionar_empresas_existentes
        provisionar_empresas_existentes()
        return
    with conectar() as conexao:
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS empresas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cnpj TEXT,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS filiais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                codigo TEXT NOT NULL,
                cidade TEXT,
                estado TEXT,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (empresa_id, codigo),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            );

            CREATE TABLE IF NOT EXISTS departamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                codigo TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (empresa_id, codigo),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            );

            CREATE TABLE IF NOT EXISTS centros_custo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                departamento_id INTEGER,
                nome TEXT NOT NULL,
                codigo TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (empresa_id, codigo),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (departamento_id) REFERENCES departamentos(id)
            );

            CREATE TABLE IF NOT EXISTS permissoes_modulos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                empresa_id INTEGER NOT NULL,
                modulo TEXT NOT NULL,
                pode_ler INTEGER NOT NULL DEFAULT 0 CHECK (pode_ler IN (0, 1)),
                pode_escrever INTEGER NOT NULL DEFAULT 0 CHECK (pode_escrever IN (0, 1)),
                pode_aprovar INTEGER NOT NULL DEFAULT 0 CHECK (pode_aprovar IN (0, 1)),
                atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (usuario_id, empresa_id, modulo),
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id)
            );

            CREATE TABLE IF NOT EXISTS migracoes_sistema (
                chave TEXT PRIMARY KEY,
                aplicada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS notificacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id)
            );

            CREATE TABLE IF NOT EXISTS atividades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                modulo TEXT NOT NULL,
                acao TEXT NOT NULL,
                descricao TEXT NOT NULL,
                recurso_tipo TEXT,
                recurso_id INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id)
            );

            CREATE TABLE IF NOT EXISTS aprovacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                solicitante_id INTEGER NOT NULL,
                responsavel_id INTEGER,
                modulo TEXT NOT NULL,
                recurso_tipo TEXT NOT NULL,
                recurso_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                valor REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Pendente'
                    CHECK (status IN ('Pendente', 'Aprovado', 'Rejeitado', 'Alteração solicitada')),
                observacao TEXT,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                decidido_em TEXT,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id),
                FOREIGN KEY (solicitante_id) REFERENCES usuarios(id),
                FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS tarefas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id),
                FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS documentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS integracoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                provedor TEXT NOT NULL,
                nome TEXT NOT NULL,
                referencia_credencial TEXT,
                configuracao_json TEXT NOT NULL DEFAULT '{}',
                ativo INTEGER NOT NULL DEFAULT 0 CHECK (ativo IN (0, 1)),
                ultima_sincronizacao TEXT,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (empresa_id, provedor, nome),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id)
            );

            CREATE TABLE IF NOT EXISTS workflows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                nome TEXT NOT NULL,
                evento_modulo TEXT NOT NULL,
                evento_tipo TEXT NOT NULL,
                condicoes_json TEXT NOT NULL DEFAULT '{}',
                acoes_json TEXT NOT NULL DEFAULT '[]',
                ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS colaboradores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                departamento_id INTEGER,
                centro_custo_id INTEGER,
                nome TEXT NOT NULL,
                email TEXT,
                cargo TEXT NOT NULL,
                salario REAL NOT NULL DEFAULT 0,
                admissao TEXT,
                desligamento TEXT,
                status TEXT NOT NULL DEFAULT 'Ativo',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id),
                FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
                FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS lancamentos_financeiros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                centro_custo_id INTEGER,
                tipo TEXT NOT NULL CHECK (tipo IN ('Receita', 'Despesa')),
                descricao TEXT NOT NULL,
                categoria TEXT,
                valor REAL NOT NULL CHECK (valor >= 0),
                vencimento TEXT,
                status TEXT NOT NULL DEFAULT 'Pendente',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS itens_estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                codigo TEXT NOT NULL,
                descricao TEXT NOT NULL,
                categoria TEXT,
                quantidade REAL NOT NULL DEFAULT 0,
                estoque_minimo REAL NOT NULL DEFAULT 0,
                custo REAL NOT NULL DEFAULT 0,
                localizacao TEXT,
                status TEXT NOT NULL DEFAULT 'Ativo',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (empresa_id, filial_id, codigo),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS movimentos_estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                filial_id INTEGER,
                item_id INTEGER NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('Entrada', 'Saída', 'Ajuste')),
                quantidade REAL NOT NULL CHECK (quantidade > 0),
                observacao TEXT,
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (filial_id) REFERENCES filiais(id),
                FOREIGN KEY (item_id) REFERENCES itens_estoque(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS ativos_ti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                patrimonio TEXT NOT NULL,
                nome TEXT NOT NULL,
                tipo TEXT,
                status TEXT NOT NULL DEFAULT 'Disponível',
                responsavel TEXT,
                endereco_ip TEXT,
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (empresa_id, patrimonio),
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS chamados_ti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                categoria TEXT,
                prioridade TEXT NOT NULL DEFAULT 'Média',
                status TEXT NOT NULL DEFAULT 'Aberto',
                responsavel TEXT,
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS campanhas_marketing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                canal TEXT NOT NULL,
                investimento REAL NOT NULL DEFAULT 0,
                leads INTEGER NOT NULL DEFAULT 0,
                conversoes INTEGER NOT NULL DEFAULT 0,
                receita REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Planejada',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS solicitacoes_administrativas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                centro_custo_id INTEGER,
                titulo TEXT NOT NULL,
                categoria TEXT NOT NULL,
                solicitante TEXT,
                valor REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Pendente',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS contratos_juridicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                titulo TEXT NOT NULL,
                parte TEXT NOT NULL,
                valor REAL NOT NULL DEFAULT 0,
                risco TEXT NOT NULL DEFAULT 'Baixo',
                vencimento TEXT,
                status TEXT NOT NULL DEFAULT 'Elaboração',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS oportunidades_comerciais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                cliente TEXT NOT NULL,
                etapa TEXT NOT NULL DEFAULT 'Novo',
                valor REAL NOT NULL DEFAULT 0,
                responsavel TEXT,
                status TEXT NOT NULL DEFAULT 'Aberto',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE TABLE IF NOT EXISTS solicitacoes_compra (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                empresa_id INTEGER NOT NULL,
                centro_custo_id INTEGER,
                item TEXT NOT NULL,
                quantidade REAL NOT NULL DEFAULT 1,
                fornecedor TEXT,
                valor_estimado REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Pendente',
                criado_por INTEGER,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (empresa_id) REFERENCES empresas(id),
                FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
                FOREIGN KEY (criado_por) REFERENCES usuarios(id)
            );

            CREATE INDEX IF NOT EXISTS idx_atividades_empresa_data
                ON atividades (empresa_id, criado_em DESC);
            CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario_lida
                ON notificacoes (usuario_id, lida, criado_em DESC);
            CREATE INDEX IF NOT EXISTS idx_aprovacoes_empresa_status
                ON aprovacoes (empresa_id, status, criado_em DESC);
            CREATE INDEX IF NOT EXISTS idx_financeiro_empresa_vencimento
                ON lancamentos_financeiros (empresa_id, vencimento);
            CREATE INDEX IF NOT EXISTS idx_estoque_empresa_codigo
                ON itens_estoque (empresa_id, codigo);
            """
        )
        empresa = conexao.execute(
            "SELECT id FROM empresas WHERE ativo = 1 ORDER BY id LIMIT 1"
        ).fetchone()
        if empresa is None:
            cursor = conexao.execute(
                "INSERT INTO empresas (nome) VALUES (?)",
                ("Empresa principal",),
            )
            empresa_id = int(cursor.lastrowid)
        else:
            empresa_id = int(empresa["id"])

        _criar_estrutura_padrao(conexao, empresa_id)
        _aplicar_migracoes_v5_1(conexao)
        aplicar_migracoes(conexao)
    from enterprise.core_v11.provisionamento import provisionar_empresas_existentes
    provisionar_empresas_existentes()


def _aplicar_migracoes_v5_1(conexao) -> None:
    """Preserva no upgrade o acesso ao Analytics existente na V5."""
    chave = "v5_1_perfis_departamentais"
    aplicada = conexao.execute(
        "SELECT 1 FROM migracoes_sistema WHERE chave = ?",
        (chave,),
    ).fetchone()
    if aplicada is not None:
        return
    conexao.execute(
        """
        INSERT INTO permissoes_modulos (
            usuario_id, empresa_id, modulo,
            pode_ler, pode_escrever, pode_aprovar
        )
        SELECT u.id, e.id, 'analytics', 1, 1, 0
        FROM usuarios u
        CROSS JOIN empresas e
        WHERE u.perfil = 'usuario' AND u.perfil_acesso = 'analista'
        ON CONFLICT(usuario_id, empresa_id, modulo) DO UPDATE SET
            pode_ler = 1,
            pode_escrever = 1,
            atualizado_em = CURRENT_TIMESTAMP
        """
    )
    conexao.execute(
        "INSERT INTO migracoes_sistema (chave) VALUES (?)",
        (chave,),
    )


def _criar_estrutura_padrao(conexao, empresa_id: int) -> None:
    filial = conexao.execute(
        "SELECT id FROM filiais WHERE empresa_id = ? ORDER BY id LIMIT 1",
        (empresa_id,),
    ).fetchone()
    if filial is None:
        conexao.execute(
            "INSERT INTO filiais (empresa_id, nome, codigo) VALUES (?, ?, ?)",
            (empresa_id, "Matriz", "MAT"),
        )

    departamentos = (
        ("Administração", "ADM"),
        ("Recursos Humanos", "RH"),
        ("Financeiro", "FIN"),
        ("Tecnologia", "TI"),
        ("Marketing", "MKT"),
        ("Comercial", "COM"),
        ("Jurídico", "JUR"),
        ("Estoque e Compras", "SUP"),
    )
    for nome, codigo in departamentos:
        conexao.execute(
            """
            INSERT OR IGNORE INTO departamentos (empresa_id, nome, codigo)
            VALUES (?, ?, ?)
            """,
            (empresa_id, nome, codigo),
        )
        departamento = conexao.execute(
            "SELECT id FROM departamentos WHERE empresa_id = ? AND codigo = ?",
            (empresa_id, codigo),
        ).fetchone()
        conexao.execute(
            """
            INSERT OR IGNORE INTO centros_custo (
                empresa_id, departamento_id, nome, codigo
            ) VALUES (?, ?, ?, ?)
            """,
            (empresa_id, int(departamento["id"]), nome, f"CC-{codigo}"),
        )
