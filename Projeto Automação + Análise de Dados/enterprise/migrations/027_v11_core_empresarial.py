"""V11: CORE configurável, Funcionário 360° e operações transversais."""
from __future__ import annotations


def _colunas(conexao, tabela: str) -> set[str]:
    return {str(item["name"]) for item in conexao.execute(f"PRAGMA table_info({tabela})").fetchall()}


def _adicionar_coluna(conexao, tabela: str, nome: str, definicao: str) -> None:
    if nome not in _colunas(conexao, tabela):
        conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {nome} {definicao}")


def upgrade(conexao) -> None:
    _adicionar_coluna(conexao, "usuarios", "pessoa_id", "INTEGER")
    _adicionar_coluna(conexao, "rh_colaboradores", "pessoa_id", "INTEGER")
    _adicionar_coluna(conexao, "rh_colaboradores", "versao_registro", "INTEGER NOT NULL DEFAULT 0")
    _adicionar_coluna(conexao, "tarefas", "criado_por", "INTEGER")
    _adicionar_coluna(conexao, "tarefas", "atualizado_em", "TEXT")
    _adicionar_coluna(conexao, "tarefas", "versao_registro", "INTEGER NOT NULL DEFAULT 0")
    _adicionar_coluna(conexao, "notificacoes", "acao_url", "TEXT")
    _adicionar_coluna(conexao, "notificacoes", "arquivada", "INTEGER NOT NULL DEFAULT 0")
    _adicionar_coluna(conexao, "aprovacoes", "versao_registro", "INTEGER NOT NULL DEFAULT 0")

    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS unidades_organizacionais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            unidade_pai_id INTEGER,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            tipo TEXT NOT NULL,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            timezone TEXT NOT NULL DEFAULT 'America/Sao_Paulo',
            dados_json TEXT NOT NULL DEFAULT '{}',
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            versao_registro INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (unidade_pai_id) REFERENCES unidades_organizacionais(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_unidades_estrutura
            ON unidades_organizacionais(empresa_id, unidade_pai_id, tipo, ativo);

        CREATE TABLE IF NOT EXISTS core_pessoas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Fisica' CHECK (tipo IN ('Fisica','Juridica')),
            nome TEXT NOT NULL,
            nome_social_fantasia TEXT,
            documento_tipo TEXT,
            documento_hash TEXT,
            documento_mascarado TEXT,
            email_corporativo TEXT,
            telefone_corporativo TEXT,
            dados_publicos_json TEXT NOT NULL DEFAULT '{}',
            dados_sensiveis_cifrados TEXT,
            classificacao TEXT NOT NULL DEFAULT 'Confidencial',
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            versao_registro INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, documento_hash),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_core_pessoas_nome ON core_pessoas(empresa_id, nome, ativo);

        CREATE TABLE IF NOT EXISTS core_papeis_pessoa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            pessoa_id INTEGER NOT NULL,
            papel TEXT NOT NULL,
            origem_tipo TEXT,
            origem_id INTEGER,
            dados_json TEXT NOT NULL DEFAULT '{}',
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            inicio TEXT,
            fim TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, pessoa_id, papel, origem_tipo, origem_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (pessoa_id) REFERENCES core_pessoas(id) ON DELETE CASCADE,
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_core_papeis ON core_papeis_pessoa(empresa_id, papel, ativo);

        CREATE TABLE IF NOT EXISTS grupos_acesso (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            codigo TEXT NOT NULL,
            descricao TEXT,
            permissoes_json TEXT NOT NULL DEFAULT '{}',
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS membros_grupo_acesso (
            grupo_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (grupo_id, usuario_id),
            FOREIGN KEY (grupo_id) REFERENCES grupos_acesso(id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS funcoes_contextuais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            permissoes_json TEXT NOT NULL DEFAULT '{}',
            restricoes_json TEXT NOT NULL DEFAULT '{}',
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS atribuicoes_funcoes_contextuais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            funcao_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            filial_id INTEGER,
            departamento_id INTEGER,
            unidade_id INTEGER,
            recurso_tipo TEXT,
            recurso_id INTEGER,
            valido_de TEXT,
            valido_ate TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (funcao_id) REFERENCES funcoes_contextuais(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (unidade_id) REFERENCES unidades_organizacionais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_atribuicoes_contexto
            ON atribuicoes_funcoes_contextuais(empresa_id, usuario_id, ativo);

        CREATE TABLE IF NOT EXISTS core_comentarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            comentario_pai_id INTEGER,
            texto TEXT NOT NULL,
            interno INTEGER NOT NULL DEFAULT 0 CHECK (interno IN (0,1)),
            criado_por INTEGER NOT NULL,
            editado_em TEXT,
            excluido_em TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (comentario_pai_id) REFERENCES core_comentarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_core_comentarios_recurso
            ON core_comentarios(empresa_id, recurso_tipo, recurso_id, criado_em);

        CREATE TABLE IF NOT EXISTS core_midias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            finalidade TEXT NOT NULL DEFAULT 'Anexo',
            titulo TEXT NOT NULL,
            classificacao TEXT NOT NULL DEFAULT 'Interno',
            versao_atual INTEGER NOT NULL DEFAULT 1,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_midia_versoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            midia_id INTEGER NOT NULL,
            versao INTEGER NOT NULL,
            nome_original TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            tamanho_bytes INTEGER NOT NULL,
            largura INTEGER,
            altura INTEGER,
            hash_sha256 TEXT NOT NULL,
            caminho_cifrado TEXT NOT NULL,
            miniatura_caminho_cifrado TEXT,
            metadados_json TEXT NOT NULL DEFAULT '{}',
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (midia_id, versao),
            FOREIGN KEY (midia_id) REFERENCES core_midias(id) ON DELETE CASCADE,
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_core_midias_recurso
            ON core_midias(empresa_id, recurso_tipo, recurso_id, finalidade, ativo);

        CREATE TABLE IF NOT EXISTS core_documentos_v11 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            tipo_documento TEXT,
            classificacao TEXT NOT NULL DEFAULT 'Confidencial',
            validade TEXT,
            status TEXT NOT NULL DEFAULT 'Ativo',
            versao_atual INTEGER NOT NULL DEFAULT 1,
            modelo_id INTEGER,
            retencao_ate TEXT,
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_documento_versoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            documento_id INTEGER NOT NULL,
            versao INTEGER NOT NULL,
            midia_id INTEGER NOT NULL,
            ocr_texto TEXT,
            metadados_json TEXT NOT NULL DEFAULT '{}',
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (documento_id, versao),
            FOREIGN KEY (documento_id) REFERENCES core_documentos_v11(id) ON DELETE CASCADE,
            FOREIGN KEY (midia_id) REFERENCES core_midias(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_documento_assinaturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            documento_id INTEGER NOT NULL,
            versao INTEGER NOT NULL,
            pessoa_id INTEGER,
            usuario_id INTEGER,
            papel TEXT,
            provedor TEXT,
            evidencia_hash TEXT,
            status TEXT NOT NULL DEFAULT 'Pendente',
            solicitado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            assinado_em TEXT,
            FOREIGN KEY (documento_id) REFERENCES core_documentos_v11(id) ON DELETE CASCADE,
            FOREIGN KEY (pessoa_id) REFERENCES core_pessoas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_acl_recursos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            sujeito_tipo TEXT NOT NULL,
            sujeito_id INTEGER NOT NULL,
            permissoes_json TEXT NOT NULL DEFAULT '{}',
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, recurso_tipo, recurso_id, sujeito_tipo, sujeito_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS core_campos_definicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            modulo TEXT NOT NULL,
            recurso_tipo TEXT NOT NULL,
            codigo TEXT NOT NULL,
            rotulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            obrigatorio INTEGER NOT NULL DEFAULT 0 CHECK (obrigatorio IN (0,1)),
            sensivel INTEGER NOT NULL DEFAULT 0 CHECK (sensivel IN (0,1)),
            opcoes_json TEXT NOT NULL DEFAULT '[]',
            validacao_json TEXT NOT NULL DEFAULT '{}',
            ordem INTEGER NOT NULL DEFAULT 0,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, recurso_tipo, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_campos_valores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            definicao_id INTEGER NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            valor_json TEXT,
            valor_cifrado TEXT,
            atualizado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (definicao_id, recurso_tipo, recurso_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (definicao_id) REFERENCES core_campos_definicoes(id) ON DELETE CASCADE,
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_etiquetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            cor TEXT NOT NULL DEFAULT '#64748B',
            categoria TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, nome),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_recurso_etiquetas (
            etiqueta_id INTEGER NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            aplicado_por INTEGER,
            aplicado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (etiqueta_id, recurso_tipo, recurso_id),
            FOREIGN KEY (etiqueta_id) REFERENCES core_etiquetas(id) ON DELETE CASCADE,
            FOREIGN KEY (aplicado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS core_calendario_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            modulo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT,
            inicio TEXT NOT NULL,
            fim TEXT,
            dia_inteiro INTEGER NOT NULL DEFAULT 0 CHECK (dia_inteiro IN (0,1)),
            timezone TEXT NOT NULL DEFAULT 'America/Sao_Paulo',
            recorrencia_json TEXT NOT NULL DEFAULT '{}',
            local TEXT,
            recurso_tipo TEXT,
            recurso_id INTEGER,
            visibilidade TEXT NOT NULL DEFAULT 'Empresa',
            status TEXT NOT NULL DEFAULT 'Confirmado',
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_calendario_participantes (
            evento_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            papel TEXT NOT NULL DEFAULT 'Participante',
            resposta TEXT NOT NULL DEFAULT 'Pendente',
            respondido_em TEXT,
            PRIMARY KEY (evento_id, usuario_id),
            FOREIGN KEY (evento_id) REFERENCES core_calendario_eventos(id) ON DELETE CASCADE,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_core_calendario_periodo
            ON core_calendario_eventos(empresa_id, inicio, fim, status);

        CREATE TABLE IF NOT EXISTS core_eventos_corporativos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento_uuid TEXT NOT NULL UNIQUE,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            modulo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            recurso_tipo TEXT,
            recurso_id INTEGER,
            payload_json TEXT NOT NULL DEFAULT '{}',
            correlacao_id TEXT,
            causacao_id TEXT,
            publicado_em TEXT,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_core_eventos_outbox
            ON core_eventos_corporativos(publicado_em, criado_em, id);
        CREATE TABLE IF NOT EXISTS core_historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            modulo TEXT NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            antes_json TEXT,
            depois_json TEXT,
            usuario_id INTEGER,
            request_id TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_core_historico_recurso
            ON core_historico(empresa_id, recurso_tipo, recurso_id, id DESC);
        CREATE TABLE IF NOT EXISTS core_busca_indice (
            empresa_id INTEGER NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            modulo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            subtitulo TEXT,
            termos TEXT NOT NULL,
            classificacao TEXT NOT NULL DEFAULT 'Interno',
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (empresa_id, recurso_tipo, recurso_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        );
        CREATE INDEX IF NOT EXISTS idx_core_busca_modulo
            ON core_busca_indice(empresa_id, modulo, atualizado_em DESC);

        CREATE TABLE IF NOT EXISTS core_dashboards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER,
            nome TEXT NOT NULL,
            escopo TEXT NOT NULL DEFAULT 'Usuario',
            layout_json TEXT NOT NULL DEFAULT '{}',
            padrao INTEGER NOT NULL DEFAULT 0 CHECK (padrao IN (0,1)),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            versao_registro INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_dashboard_widgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dashboard_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            fonte TEXT NOT NULL,
            configuracao_json TEXT NOT NULL DEFAULT '{}',
            posicao_json TEXT NOT NULL DEFAULT '{}',
            ordem INTEGER NOT NULL DEFAULT 0,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dashboard_id) REFERENCES core_dashboards(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS core_preferencias_contextuais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            usuario_id INTEGER,
            chave TEXT NOT NULL,
            valor_json TEXT NOT NULL,
            versao_registro INTEGER NOT NULL DEFAULT 0,
            atualizado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, filial_id, usuario_id, chave),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_transferencias_dados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            tipo TEXT NOT NULL,
            modulo TEXT NOT NULL,
            recurso_tipo TEXT,
            formato TEXT NOT NULL,
            mapeamento_json TEXT NOT NULL DEFAULT '{}',
            filtros_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'Pendente',
            total_registros INTEGER NOT NULL DEFAULT 0,
            registros_processados INTEGER NOT NULL DEFAULT 0,
            erros_json TEXT NOT NULL DEFAULT '[]',
            arquivo_midia_id INTEGER,
            job_id INTEGER,
            solicitado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            concluido_em TEXT,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (arquivo_midia_id) REFERENCES core_midias(id),
            FOREIGN KEY (solicitado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_credenciais_referencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            integracao_id INTEGER,
            nome TEXT NOT NULL,
            provedor_cofre TEXT NOT NULL,
            referencia TEXT NOT NULL,
            rotacao_dias INTEGER,
            ultima_rotacao TEXT,
            expira_em TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, nome),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (integracao_id) REFERENCES integracoes(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS core_configuracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            modulo TEXT NOT NULL,
            chave TEXT NOT NULL,
            valor_json TEXT NOT NULL,
            schema_json TEXT NOT NULL DEFAULT '{}',
            atualizado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, filial_id, modulo, chave),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS funcionario_360_vinculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            pessoa_id INTEGER NOT NULL,
            usuario_id INTEGER,
            gestor_colaborador_id INTEGER,
            equipe TEXT,
            avatar_midia_id INTEGER,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, colaborador_id),
            UNIQUE (empresa_id, pessoa_id, colaborador_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id) ON DELETE CASCADE,
            FOREIGN KEY (pessoa_id) REFERENCES core_pessoas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (gestor_colaborador_id) REFERENCES rh_colaboradores(id),
            FOREIGN KEY (avatar_midia_id) REFERENCES core_midias(id)
        );
        CREATE TABLE IF NOT EXISTS rh_acessos_sistemas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            sistema_id INTEGER,
            sistema_nome TEXT NOT NULL,
            conta TEXT,
            perfil TEXT,
            origem TEXT NOT NULL DEFAULT 'Manual',
            status TEXT NOT NULL DEFAULT 'Solicitado',
            solicitado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            concedido_em TEXT,
            revogado_em TEXT,
            aprovado_por INTEGER,
            criado_por INTEGER NOT NULL,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id) ON DELETE CASCADE,
            FOREIGN KEY (sistema_id) REFERENCES ti_sistemas(id),
            FOREIGN KEY (aprovado_por) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS rh_feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            autor_id INTEGER NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Feedback',
            titulo TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            visibilidade TEXT NOT NULL DEFAULT 'RH_Gestor',
            data_referencia TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id) ON DELETE CASCADE,
            FOREIGN KEY (autor_id) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS rh_custos_vinculados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            centro_custo_id INTEGER,
            categoria TEXT NOT NULL,
            referencia TEXT,
            valor_centavos INTEGER NOT NULL DEFAULT 0,
            recorrente INTEGER NOT NULL DEFAULT 0 CHECK (recorrente IN (0,1)),
            origem_tipo TEXT,
            origem_id INTEGER,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id) ON DELETE CASCADE,
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS rh_ocorrencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            colaborador_id INTEGER NOT NULL,
            categoria TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT,
            severidade TEXT NOT NULL DEFAULT 'Baixa',
            confidencial INTEGER NOT NULL DEFAULT 1 CHECK (confidencial IN (0,1)),
            status TEXT NOT NULL DEFAULT 'Aberta',
            responsavel_id INTEGER,
            criado_por INTEGER NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            encerrado_em TEXT,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (colaborador_id) REFERENCES rh_colaboradores(id) ON DELETE CASCADE,
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS v11_tipos_registro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            modulo TEXT NOT NULL,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            icone TEXT,
            schema_json TEXT NOT NULL DEFAULT '{}',
            configuracao_json TEXT NOT NULL DEFAULT '{}',
            fluxo_codigo TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            versao_schema INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, modulo, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS v11_registros_operacionais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            tipo_id INTEGER NOT NULL,
            modulo TEXT NOT NULL,
            codigo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT,
            status TEXT NOT NULL DEFAULT 'Rascunho',
            etapa TEXT,
            prioridade TEXT NOT NULL DEFAULT 'Media',
            responsavel_id INTEGER,
            equipe TEXT,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            pessoa_id INTEGER,
            valor_centavos INTEGER NOT NULL DEFAULT 0,
            moeda TEXT NOT NULL DEFAULT 'BRL',
            inicio TEXT,
            vencimento TEXT,
            conclusao TEXT,
            dados_json TEXT NOT NULL DEFAULT '{}',
            versao_registro INTEGER NOT NULL DEFAULT 1,
            estado_registro TEXT NOT NULL DEFAULT 'Ativo',
            criado_por INTEGER NOT NULL,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (tipo_id) REFERENCES v11_tipos_registro(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (pessoa_id) REFERENCES core_pessoas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_v11_registros_contexto
            ON v11_registros_operacionais(empresa_id, filial_id, modulo, status, atualizado_em DESC);
        CREATE TABLE IF NOT EXISTS v11_registro_relacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            origem_tipo TEXT NOT NULL,
            origem_id INTEGER NOT NULL,
            relacao TEXT NOT NULL,
            destino_tipo TEXT NOT NULL,
            destino_id INTEGER NOT NULL,
            dados_json TEXT NOT NULL DEFAULT '{}',
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, origem_tipo, origem_id, relacao, destino_tipo, destino_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS v11_fluxos_modelos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            modulo TEXT NOT NULL,
            etapas_json TEXT NOT NULL,
            transicoes_json TEXT NOT NULL,
            configuracao_json TEXT NOT NULL DEFAULT '{}',
            versao INTEGER NOT NULL DEFAULT 1,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            criado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo, versao),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS v11_fluxos_instancias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            modelo_id INTEGER NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            etapa_atual TEXT,
            status TEXT NOT NULL DEFAULT 'Em andamento',
            contexto_json TEXT NOT NULL DEFAULT '{}',
            iniciado_por INTEGER NOT NULL,
            iniciado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            concluido_em TEXT,
            UNIQUE (empresa_id, recurso_tipo, recurso_id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (modelo_id) REFERENCES v11_fluxos_modelos(id),
            FOREIGN KEY (iniciado_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS v11_fluxos_etapas_instancias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instancia_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            modulo TEXT NOT NULL,
            ordem INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente',
            responsavel_id INTEGER,
            requer_aprovacao INTEGER NOT NULL DEFAULT 0 CHECK (requer_aprovacao IN (0,1)),
            dados_json TEXT NOT NULL DEFAULT '{}',
            iniciado_em TEXT,
            concluido_em TEXT,
            concluido_por INTEGER,
            UNIQUE (instancia_id, codigo),
            FOREIGN KEY (instancia_id) REFERENCES v11_fluxos_instancias(id) ON DELETE CASCADE,
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (concluido_por) REFERENCES usuarios(id)
        );
        CREATE TABLE IF NOT EXISTS v11_configuracoes_modulos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            modulo TEXT NOT NULL,
            recurso TEXT NOT NULL,
            habilitado INTEGER NOT NULL DEFAULT 1 CHECK (habilitado IN (0,1)),
            configuracao_json TEXT NOT NULL DEFAULT '{}',
            atualizado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, modulo, recurso),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        """
    )
