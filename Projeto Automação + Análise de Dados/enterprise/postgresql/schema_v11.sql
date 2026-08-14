-- Data Intelligence V11.1.0: CORE empresarial configurável.
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS pessoa_id BIGINT;
ALTER TABLE rh_colaboradores ADD COLUMN IF NOT EXISTS pessoa_id BIGINT;
ALTER TABLE rh_colaboradores ADD COLUMN IF NOT EXISTS versao_registro INTEGER NOT NULL DEFAULT 0;
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS criado_por INTEGER;
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS atualizado_em TEXT;
ALTER TABLE tarefas ADD COLUMN IF NOT EXISTS versao_registro INTEGER NOT NULL DEFAULT 0;
ALTER TABLE notificacoes ADD COLUMN IF NOT EXISTS acao_url TEXT;
ALTER TABLE notificacoes ADD COLUMN IF NOT EXISTS arquivada INTEGER NOT NULL DEFAULT 0;
ALTER TABLE aprovacoes ADD COLUMN IF NOT EXISTS versao_registro INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS unidades_organizacionais (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    filial_id INTEGER REFERENCES filiais(id), unidade_pai_id BIGINT REFERENCES unidades_organizacionais(id),
    departamento_id INTEGER REFERENCES departamentos(id), centro_custo_id INTEGER REFERENCES centros_custo(id),
    tipo TEXT NOT NULL, codigo TEXT NOT NULL, nome TEXT NOT NULL,
    timezone TEXT NOT NULL DEFAULT 'America/Sao_Paulo', dados_json TEXT NOT NULL DEFAULT '{}',
    ativo INTEGER NOT NULL DEFAULT 1, versao_registro INTEGER NOT NULL DEFAULT 0,
    criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,codigo)
);
CREATE INDEX IF NOT EXISTS idx_unidades_estrutura ON unidades_organizacionais(empresa_id,unidade_pai_id,tipo,ativo);

CREATE TABLE IF NOT EXISTS core_pessoas (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), tipo TEXT NOT NULL DEFAULT 'Fisica',
    nome TEXT NOT NULL, nome_social_fantasia TEXT, documento_tipo TEXT, documento_hash TEXT,
    documento_mascarado TEXT, email_corporativo TEXT, telefone_corporativo TEXT,
    dados_publicos_json TEXT NOT NULL DEFAULT '{}', dados_sensiveis_cifrados TEXT,
    classificacao TEXT NOT NULL DEFAULT 'Confidencial', ativo INTEGER NOT NULL DEFAULT 1,
    versao_registro INTEGER NOT NULL DEFAULT 0, criado_por INTEGER REFERENCES usuarios(id),
    atualizado_por INTEGER REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,documento_hash)
);
CREATE INDEX IF NOT EXISTS idx_core_pessoas_nome ON core_pessoas(empresa_id,nome,ativo);
CREATE TABLE IF NOT EXISTS core_papeis_pessoa (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), pessoa_id BIGINT NOT NULL REFERENCES core_pessoas(id) ON DELETE CASCADE,
    papel TEXT NOT NULL, origem_tipo TEXT, origem_id BIGINT, dados_json TEXT NOT NULL DEFAULT '{}', ativo INTEGER NOT NULL DEFAULT 1,
    inicio TEXT, fim TEXT, criado_por INTEGER REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,pessoa_id,papel,origem_tipo,origem_id)
);
CREATE INDEX IF NOT EXISTS idx_core_papeis ON core_papeis_pessoa(empresa_id,papel,ativo);

CREATE TABLE IF NOT EXISTS grupos_acesso (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), nome TEXT NOT NULL, codigo TEXT NOT NULL,
    descricao TEXT, permissoes_json TEXT NOT NULL DEFAULT '{}', ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), UNIQUE(empresa_id,codigo)
);
CREATE TABLE IF NOT EXISTS membros_grupo_acesso (
    grupo_id BIGINT NOT NULL REFERENCES grupos_acesso(id) ON DELETE CASCADE, usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    PRIMARY KEY(grupo_id,usuario_id)
);
CREATE TABLE IF NOT EXISTS funcoes_contextuais (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), codigo TEXT NOT NULL, nome TEXT NOT NULL,
    permissoes_json TEXT NOT NULL DEFAULT '{}', restricoes_json TEXT NOT NULL DEFAULT '{}', ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,codigo)
);
CREATE TABLE IF NOT EXISTS atribuicoes_funcoes_contextuais (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), funcao_id BIGINT NOT NULL REFERENCES funcoes_contextuais(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id), filial_id INTEGER REFERENCES filiais(id),
    departamento_id INTEGER REFERENCES departamentos(id), unidade_id BIGINT REFERENCES unidades_organizacionais(id),
    recurso_tipo TEXT, recurso_id BIGINT, valido_de TEXT, valido_ate TEXT, ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE INDEX IF NOT EXISTS idx_atribuicoes_contexto ON atribuicoes_funcoes_contextuais(empresa_id,usuario_id,ativo);

CREATE TABLE IF NOT EXISTS core_comentarios (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    recurso_tipo TEXT NOT NULL, recurso_id BIGINT NOT NULL, comentario_pai_id BIGINT REFERENCES core_comentarios(id),
    texto TEXT NOT NULL, interno INTEGER NOT NULL DEFAULT 0, criado_por INTEGER NOT NULL REFERENCES usuarios(id),
    editado_em TEXT, excluido_em TEXT, criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE INDEX IF NOT EXISTS idx_core_comentarios_recurso ON core_comentarios(empresa_id,recurso_tipo,recurso_id,criado_em);

CREATE TABLE IF NOT EXISTS core_midias (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    recurso_tipo TEXT NOT NULL, recurso_id BIGINT NOT NULL, finalidade TEXT NOT NULL DEFAULT 'Anexo', titulo TEXT NOT NULL,
    classificacao TEXT NOT NULL DEFAULT 'Interno', versao_atual INTEGER NOT NULL DEFAULT 1, ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE TABLE IF NOT EXISTS core_midia_versoes (
    id BIGSERIAL PRIMARY KEY, midia_id BIGINT NOT NULL REFERENCES core_midias(id) ON DELETE CASCADE,
    versao INTEGER NOT NULL, nome_original TEXT NOT NULL, mime_type TEXT NOT NULL, tamanho_bytes BIGINT NOT NULL,
    largura INTEGER, altura INTEGER, hash_sha256 TEXT NOT NULL, caminho_cifrado TEXT NOT NULL,
    miniatura_caminho_cifrado TEXT, metadados_json TEXT NOT NULL DEFAULT '{}', criado_por INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), UNIQUE(midia_id,versao)
);
CREATE INDEX IF NOT EXISTS idx_core_midias_recurso ON core_midias(empresa_id,recurso_tipo,recurso_id,finalidade,ativo);

CREATE TABLE IF NOT EXISTS core_documentos_v11 (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    recurso_tipo TEXT NOT NULL, recurso_id BIGINT NOT NULL, titulo TEXT NOT NULL, tipo_documento TEXT,
    classificacao TEXT NOT NULL DEFAULT 'Confidencial', validade TEXT, status TEXT NOT NULL DEFAULT 'Ativo',
    versao_atual INTEGER NOT NULL DEFAULT 1, modelo_id BIGINT, retencao_ate TEXT, criado_por INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE TABLE IF NOT EXISTS core_documento_versoes (
    id BIGSERIAL PRIMARY KEY, documento_id BIGINT NOT NULL REFERENCES core_documentos_v11(id) ON DELETE CASCADE,
    versao INTEGER NOT NULL, midia_id BIGINT NOT NULL REFERENCES core_midias(id), ocr_texto TEXT,
    metadados_json TEXT NOT NULL DEFAULT '{}', criado_por INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), UNIQUE(documento_id,versao)
);
CREATE TABLE IF NOT EXISTS core_documento_assinaturas (
    id BIGSERIAL PRIMARY KEY, documento_id BIGINT NOT NULL REFERENCES core_documentos_v11(id) ON DELETE CASCADE,
    versao INTEGER NOT NULL, pessoa_id BIGINT REFERENCES core_pessoas(id), usuario_id INTEGER REFERENCES usuarios(id),
    papel TEXT, provedor TEXT, evidencia_hash TEXT, status TEXT NOT NULL DEFAULT 'Pendente',
    solicitado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), assinado_em TEXT
);
CREATE TABLE IF NOT EXISTS core_acl_recursos (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), recurso_tipo TEXT NOT NULL, recurso_id BIGINT NOT NULL,
    sujeito_tipo TEXT NOT NULL, sujeito_id BIGINT NOT NULL, permissoes_json TEXT NOT NULL DEFAULT '{}',
    criado_por INTEGER NOT NULL REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,recurso_tipo,recurso_id,sujeito_tipo,sujeito_id)
);

CREATE TABLE IF NOT EXISTS core_campos_definicoes (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), modulo TEXT NOT NULL,
    recurso_tipo TEXT NOT NULL, codigo TEXT NOT NULL, rotulo TEXT NOT NULL, tipo TEXT NOT NULL,
    obrigatorio INTEGER NOT NULL DEFAULT 0, sensivel INTEGER NOT NULL DEFAULT 0,
    opcoes_json TEXT NOT NULL DEFAULT '[]', validacao_json TEXT NOT NULL DEFAULT '{}', ordem INTEGER NOT NULL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1, criado_por INTEGER REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,recurso_tipo,codigo)
);
CREATE TABLE IF NOT EXISTS core_campos_valores (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    definicao_id BIGINT NOT NULL REFERENCES core_campos_definicoes(id) ON DELETE CASCADE,
    recurso_tipo TEXT NOT NULL, recurso_id BIGINT NOT NULL, valor_json TEXT, valor_cifrado TEXT,
    atualizado_por INTEGER REFERENCES usuarios(id),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(definicao_id,recurso_tipo,recurso_id)
);
CREATE TABLE IF NOT EXISTS core_etiquetas (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), nome TEXT NOT NULL,
    cor TEXT NOT NULL DEFAULT '#64748B', categoria TEXT, ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,nome)
);
CREATE TABLE IF NOT EXISTS core_recurso_etiquetas (
    etiqueta_id BIGINT NOT NULL REFERENCES core_etiquetas(id) ON DELETE CASCADE, recurso_tipo TEXT NOT NULL,
    recurso_id BIGINT NOT NULL, aplicado_por INTEGER REFERENCES usuarios(id),
    aplicado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    PRIMARY KEY(etiqueta_id,recurso_tipo,recurso_id)
);

CREATE TABLE IF NOT EXISTS core_calendario_eventos (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    modulo TEXT NOT NULL, titulo TEXT NOT NULL, descricao TEXT, inicio TEXT NOT NULL, fim TEXT,
    dia_inteiro INTEGER NOT NULL DEFAULT 0, timezone TEXT NOT NULL DEFAULT 'America/Sao_Paulo',
    recorrencia_json TEXT NOT NULL DEFAULT '{}', local TEXT, recurso_tipo TEXT, recurso_id BIGINT,
    visibilidade TEXT NOT NULL DEFAULT 'Empresa', status TEXT NOT NULL DEFAULT 'Confirmado',
    criado_por INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE TABLE IF NOT EXISTS core_calendario_participantes (
    evento_id BIGINT NOT NULL REFERENCES core_calendario_eventos(id) ON DELETE CASCADE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id), papel TEXT NOT NULL DEFAULT 'Participante',
    resposta TEXT NOT NULL DEFAULT 'Pendente', respondido_em TEXT, PRIMARY KEY(evento_id,usuario_id)
);
CREATE INDEX IF NOT EXISTS idx_core_calendario_periodo ON core_calendario_eventos(empresa_id,inicio,fim,status);

CREATE TABLE IF NOT EXISTS core_eventos_corporativos (
    id BIGSERIAL PRIMARY KEY, evento_uuid TEXT NOT NULL UNIQUE, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    filial_id INTEGER REFERENCES filiais(id), modulo TEXT NOT NULL, tipo TEXT NOT NULL, recurso_tipo TEXT,
    recurso_id BIGINT, payload_json TEXT NOT NULL DEFAULT '{}', correlacao_id TEXT, causacao_id TEXT,
    publicado_em TEXT, criado_por INTEGER REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE INDEX IF NOT EXISTS idx_core_eventos_outbox ON core_eventos_corporativos(publicado_em,criado_em,id);
CREATE TABLE IF NOT EXISTS core_historico (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    modulo TEXT NOT NULL, recurso_tipo TEXT NOT NULL, recurso_id BIGINT NOT NULL, acao TEXT NOT NULL,
    antes_json TEXT, depois_json TEXT, usuario_id INTEGER REFERENCES usuarios(id), request_id TEXT,
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE INDEX IF NOT EXISTS idx_core_historico_recurso ON core_historico(empresa_id,recurso_tipo,recurso_id,id DESC);
CREATE TABLE IF NOT EXISTS core_busca_indice (
    empresa_id INTEGER NOT NULL REFERENCES empresas(id), recurso_tipo TEXT NOT NULL, recurso_id BIGINT NOT NULL,
    modulo TEXT NOT NULL, titulo TEXT NOT NULL, subtitulo TEXT, termos TEXT NOT NULL,
    classificacao TEXT NOT NULL DEFAULT 'Interno',
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    PRIMARY KEY(empresa_id,recurso_tipo,recurso_id)
);
CREATE INDEX IF NOT EXISTS idx_core_busca_modulo ON core_busca_indice(empresa_id,modulo,atualizado_em DESC);

CREATE TABLE IF NOT EXISTS core_dashboards (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    usuario_id INTEGER REFERENCES usuarios(id), nome TEXT NOT NULL, escopo TEXT NOT NULL DEFAULT 'Usuario',
    layout_json TEXT NOT NULL DEFAULT '{}', padrao INTEGER NOT NULL DEFAULT 0, ativo INTEGER NOT NULL DEFAULT 1,
    versao_registro INTEGER NOT NULL DEFAULT 0, criado_por INTEGER REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE TABLE IF NOT EXISTS core_dashboard_widgets (
    id BIGSERIAL PRIMARY KEY, dashboard_id BIGINT NOT NULL REFERENCES core_dashboards(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL, titulo TEXT NOT NULL, fonte TEXT NOT NULL, configuracao_json TEXT NOT NULL DEFAULT '{}',
    posicao_json TEXT NOT NULL DEFAULT '{}', ordem INTEGER NOT NULL DEFAULT 0,
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE TABLE IF NOT EXISTS core_preferencias_contextuais (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    usuario_id INTEGER REFERENCES usuarios(id), chave TEXT NOT NULL, valor_json TEXT NOT NULL,
    versao_registro INTEGER NOT NULL DEFAULT 0, atualizado_por INTEGER REFERENCES usuarios(id),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,filial_id,usuario_id,chave)
);
CREATE TABLE IF NOT EXISTS core_transferencias_dados (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    tipo TEXT NOT NULL, modulo TEXT NOT NULL, recurso_tipo TEXT, formato TEXT NOT NULL,
    mapeamento_json TEXT NOT NULL DEFAULT '{}', filtros_json TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'Pendente',
    total_registros INTEGER NOT NULL DEFAULT 0, registros_processados INTEGER NOT NULL DEFAULT 0,
    erros_json TEXT NOT NULL DEFAULT '[]', arquivo_midia_id BIGINT REFERENCES core_midias(id), job_id BIGINT,
    solicitado_por INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), concluido_em TEXT
);
CREATE TABLE IF NOT EXISTS core_credenciais_referencias (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), integracao_id BIGINT REFERENCES integracoes(id),
    nome TEXT NOT NULL, provedor_cofre TEXT NOT NULL, referencia TEXT NOT NULL, rotacao_dias INTEGER,
    ultima_rotacao TEXT, expira_em TEXT, ativo INTEGER NOT NULL DEFAULT 1, criado_por INTEGER NOT NULL REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), UNIQUE(empresa_id,nome)
);
CREATE TABLE IF NOT EXISTS core_configuracoes (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    modulo TEXT NOT NULL, chave TEXT NOT NULL, valor_json TEXT NOT NULL, schema_json TEXT NOT NULL DEFAULT '{}',
    atualizado_por INTEGER REFERENCES usuarios(id),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,filial_id,modulo,chave)
);

CREATE TABLE IF NOT EXISTS funcionario_360_vinculos (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    colaborador_id BIGINT NOT NULL REFERENCES rh_colaboradores(id) ON DELETE CASCADE,
    pessoa_id BIGINT NOT NULL REFERENCES core_pessoas(id), usuario_id INTEGER REFERENCES usuarios(id),
    gestor_colaborador_id BIGINT REFERENCES rh_colaboradores(id), equipe TEXT, avatar_midia_id BIGINT REFERENCES core_midias(id),
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,colaborador_id), UNIQUE(empresa_id,pessoa_id,colaborador_id)
);
CREATE TABLE IF NOT EXISTS rh_acessos_sistemas (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    colaborador_id BIGINT NOT NULL REFERENCES rh_colaboradores(id) ON DELETE CASCADE,
    sistema_id BIGINT REFERENCES ti_sistemas(id), sistema_nome TEXT NOT NULL, conta TEXT, perfil TEXT,
    origem TEXT NOT NULL DEFAULT 'Manual', status TEXT NOT NULL DEFAULT 'Solicitado',
    solicitado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    concedido_em TEXT, revogado_em TEXT, aprovado_por INTEGER REFERENCES usuarios(id), criado_por INTEGER NOT NULL REFERENCES usuarios(id)
);
CREATE TABLE IF NOT EXISTS rh_feedbacks (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    colaborador_id BIGINT NOT NULL REFERENCES rh_colaboradores(id) ON DELETE CASCADE,
    autor_id INTEGER NOT NULL REFERENCES usuarios(id), tipo TEXT NOT NULL DEFAULT 'Feedback', titulo TEXT NOT NULL,
    conteudo TEXT NOT NULL, visibilidade TEXT NOT NULL DEFAULT 'RH_Gestor', data_referencia TEXT,
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE TABLE IF NOT EXISTS rh_custos_vinculados (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    colaborador_id BIGINT NOT NULL REFERENCES rh_colaboradores(id) ON DELETE CASCADE,
    centro_custo_id INTEGER REFERENCES centros_custo(id), categoria TEXT NOT NULL, referencia TEXT,
    valor_centavos BIGINT NOT NULL DEFAULT 0, recorrente INTEGER NOT NULL DEFAULT 0, origem_tipo TEXT, origem_id BIGINT,
    criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS'))
);
CREATE TABLE IF NOT EXISTS rh_ocorrencias (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    colaborador_id BIGINT NOT NULL REFERENCES rh_colaboradores(id) ON DELETE CASCADE,
    categoria TEXT NOT NULL, titulo TEXT NOT NULL, descricao TEXT, severidade TEXT NOT NULL DEFAULT 'Baixa',
    confidencial INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'Aberta', responsavel_id INTEGER REFERENCES usuarios(id),
    criado_por INTEGER NOT NULL REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), encerrado_em TEXT
);

CREATE TABLE IF NOT EXISTS v11_tipos_registro (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), modulo TEXT NOT NULL,
    codigo TEXT NOT NULL, nome TEXT NOT NULL, descricao TEXT, icone TEXT,
    schema_json TEXT NOT NULL DEFAULT '{}', configuracao_json TEXT NOT NULL DEFAULT '{}', fluxo_codigo TEXT,
    ativo INTEGER NOT NULL DEFAULT 1, versao_schema INTEGER NOT NULL DEFAULT 1, criado_por INTEGER REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,modulo,codigo)
);
CREATE TABLE IF NOT EXISTS v11_registros_operacionais (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), filial_id INTEGER REFERENCES filiais(id),
    tipo_id BIGINT NOT NULL REFERENCES v11_tipos_registro(id), modulo TEXT NOT NULL, codigo TEXT NOT NULL,
    titulo TEXT NOT NULL, descricao TEXT, status TEXT NOT NULL DEFAULT 'Rascunho', etapa TEXT,
    prioridade TEXT NOT NULL DEFAULT 'Media', responsavel_id INTEGER REFERENCES usuarios(id), equipe TEXT,
    departamento_id INTEGER REFERENCES departamentos(id), centro_custo_id INTEGER REFERENCES centros_custo(id),
    pessoa_id BIGINT REFERENCES core_pessoas(id), valor_centavos BIGINT NOT NULL DEFAULT 0, moeda TEXT NOT NULL DEFAULT 'BRL',
    inicio TEXT, vencimento TEXT, conclusao TEXT, dados_json TEXT NOT NULL DEFAULT '{}',
    versao_registro INTEGER NOT NULL DEFAULT 1, estado_registro TEXT NOT NULL DEFAULT 'Ativo',
    criado_por INTEGER NOT NULL REFERENCES usuarios(id), atualizado_por INTEGER REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,codigo)
);
CREATE INDEX IF NOT EXISTS idx_v11_registros_contexto ON v11_registros_operacionais(empresa_id,filial_id,modulo,status,atualizado_em DESC);
CREATE TABLE IF NOT EXISTS v11_registro_relacoes (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), origem_tipo TEXT NOT NULL,
    origem_id BIGINT NOT NULL, relacao TEXT NOT NULL, destino_tipo TEXT NOT NULL, destino_id BIGINT NOT NULL,
    dados_json TEXT NOT NULL DEFAULT '{}', criado_por INTEGER REFERENCES usuarios(id),
    criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,origem_tipo,origem_id,relacao,destino_tipo,destino_id)
);
CREATE TABLE IF NOT EXISTS v11_fluxos_modelos (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), codigo TEXT NOT NULL,
    nome TEXT NOT NULL, modulo TEXT NOT NULL, etapas_json TEXT NOT NULL, transicoes_json TEXT NOT NULL,
    configuracao_json TEXT NOT NULL DEFAULT '{}', versao INTEGER NOT NULL DEFAULT 1, ativo INTEGER NOT NULL DEFAULT 1,
    criado_por INTEGER REFERENCES usuarios(id), criado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,codigo,versao)
);
CREATE TABLE IF NOT EXISTS v11_fluxos_instancias (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), modelo_id BIGINT NOT NULL REFERENCES v11_fluxos_modelos(id),
    recurso_tipo TEXT NOT NULL, recurso_id BIGINT NOT NULL, etapa_atual TEXT, status TEXT NOT NULL DEFAULT 'Em andamento',
    contexto_json TEXT NOT NULL DEFAULT '{}', iniciado_por INTEGER NOT NULL REFERENCES usuarios(id),
    iniciado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')), concluido_em TEXT,
    UNIQUE(empresa_id,recurso_tipo,recurso_id)
);
CREATE TABLE IF NOT EXISTS v11_fluxos_etapas_instancias (
    id BIGSERIAL PRIMARY KEY, instancia_id BIGINT NOT NULL REFERENCES v11_fluxos_instancias(id) ON DELETE CASCADE,
    codigo TEXT NOT NULL, titulo TEXT NOT NULL, modulo TEXT NOT NULL, ordem INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pendente', responsavel_id INTEGER REFERENCES usuarios(id),
    requer_aprovacao INTEGER NOT NULL DEFAULT 0, dados_json TEXT NOT NULL DEFAULT '{}', iniciado_em TEXT,
    concluido_em TEXT, concluido_por INTEGER REFERENCES usuarios(id), UNIQUE(instancia_id,codigo)
);
CREATE TABLE IF NOT EXISTS v11_configuracoes_modulos (
    id BIGSERIAL PRIMARY KEY, empresa_id INTEGER NOT NULL REFERENCES empresas(id), modulo TEXT NOT NULL,
    recurso TEXT NOT NULL, habilitado INTEGER NOT NULL DEFAULT 1, configuracao_json TEXT NOT NULL DEFAULT '{}',
    atualizado_por INTEGER REFERENCES usuarios(id),
    atualizado_em TEXT NOT NULL DEFAULT (TO_CHAR(CURRENT_TIMESTAMP AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS')),
    UNIQUE(empresa_id,modulo,recurso)
);

INSERT INTO migracoes_sistema(chave)
SELECT 'enterprise_027_v11_core_empresarial'
WHERE NOT EXISTS (SELECT 1 FROM migracoes_sistema WHERE chave='enterprise_027_v11_core_empresarial');
