"""V11.1: governança legal, direitos de titulares e acesso remoto controlado."""
from __future__ import annotations


def _colunas(conexao, tabela: str) -> set[str]:
    return {str(item["name"]) for item in conexao.execute(f"PRAGMA table_info({tabela})").fetchall()}


def upgrade(conexao) -> None:
    colunas_assinatura = _colunas(conexao, "core_documento_assinaturas")
    for nome, definicao in (
        ("tipo_assinatura", "TEXT NOT NULL DEFAULT 'Simples'"),
        ("nivel_garantia", "TEXT"),
        ("evidencia_json", "TEXT NOT NULL DEFAULT '{}'"),
    ):
        if nome not in colunas_assinatura:
            conexao.execute(f"ALTER TABLE core_documento_assinaturas ADD COLUMN {nome} {definicao}")
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS compliance_tratamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            controlador TEXT NOT NULL,
            operador TEXT,
            encarregado TEXT,
            finalidade TEXT NOT NULL,
            base_legal TEXT NOT NULL,
            categorias_titulares TEXT NOT NULL,
            categorias_dados TEXT NOT NULL,
            dados_sensiveis INTEGER NOT NULL DEFAULT 0 CHECK (dados_sensiveis IN (0,1)),
            compartilhamentos TEXT,
            transferencia_internacional INTEGER NOT NULL DEFAULT 0 CHECK (transferencia_internacional IN (0,1)),
            paises_salvaguardas TEXT,
            prazo_retencao TEXT NOT NULL,
            medidas_seguranca TEXT NOT NULL,
            responsavel_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Em revisão',
            versao_registro INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER NOT NULL,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_compliance_tratamentos_status
            ON compliance_tratamentos(empresa_id, status, atualizado_em DESC);

        CREATE TABLE IF NOT EXISTS compliance_solicitacoes_titulares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            protocolo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            titular_nome TEXT NOT NULL,
            titular_documento_hash TEXT,
            canal TEXT NOT NULL,
            identidade_verificada INTEGER NOT NULL DEFAULT 0 CHECK (identidade_verificada IN (0,1)),
            escopo TEXT,
            status TEXT NOT NULL DEFAULT 'Recebida',
            responsavel_id INTEGER,
            recebido_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            prazo_resposta TEXT NOT NULL,
            respondido_em TEXT,
            fundamento_recusa TEXT,
            resposta_resumo TEXT,
            evidencia_documento_id INTEGER,
            versao_registro INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER NOT NULL,
            atualizado_por INTEGER,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, protocolo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_compliance_titulares_prazo
            ON compliance_solicitacoes_titulares(empresa_id, status, prazo_resposta);

        CREATE TABLE IF NOT EXISTS compliance_incidentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            protocolo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            detectado_em TEXT NOT NULL,
            confirmado_em TEXT,
            dados_afetados TEXT,
            titulares_afetados INTEGER,
            risco_dano TEXT NOT NULL DEFAULT 'Em avaliação',
            medidas_contencao TEXT,
            status TEXT NOT NULL DEFAULT 'Em avaliação',
            responsavel_id INTEGER,
            comunicar_anpd INTEGER NOT NULL DEFAULT 0 CHECK (comunicar_anpd IN (0,1)),
            comunicar_titulares INTEGER NOT NULL DEFAULT 0 CHECK (comunicar_titulares IN (0,1)),
            prazo_regulatorio TEXT,
            comunicado_anpd_em TEXT,
            comunicado_titulares_em TEXT,
            justificativa_decisao TEXT,
            versao_registro INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER NOT NULL,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            encerrado_em TEXT,
            UNIQUE (empresa_id, protocolo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_compliance_incidentes_prazo
            ON compliance_incidentes(empresa_id, status, prazo_regulatorio);

        CREATE TABLE IF NOT EXISTS compliance_ripd (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tratamento_id INTEGER,
            codigo TEXT NOT NULL,
            titulo TEXT NOT NULL,
            necessidade_proporcionalidade TEXT NOT NULL,
            riscos_json TEXT NOT NULL DEFAULT '[]',
            salvaguardas_json TEXT NOT NULL DEFAULT '[]',
            risco_residual TEXT NOT NULL DEFAULT 'Em avaliação',
            aprovado_por INTEGER,
            status TEXT NOT NULL DEFAULT 'Rascunho',
            versao INTEGER NOT NULL DEFAULT 1,
            criado_por INTEGER NOT NULL,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo, versao),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (tratamento_id) REFERENCES compliance_tratamentos(id),
            FOREIGN KEY (aprovado_por) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS compliance_terceiros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            papel TEXT NOT NULL DEFAULT 'Operador',
            dados_tratados TEXT NOT NULL,
            finalidade TEXT NOT NULL,
            contrato_dpa INTEGER NOT NULL DEFAULT 0 CHECK (contrato_dpa IN (0,1)),
            transferencia_internacional INTEGER NOT NULL DEFAULT 0 CHECK (transferencia_internacional IN (0,1)),
            mecanismo_transferencia TEXT,
            avaliacao_seguranca TEXT,
            proxima_revisao TEXT,
            status TEXT NOT NULL DEFAULT 'Em avaliação',
            versao_registro INTEGER NOT NULL DEFAULT 0,
            criado_por INTEGER NOT NULL,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_compliance_terceiros_revisao
            ON compliance_terceiros(empresa_id, status, proxima_revisao);

        CREATE TABLE IF NOT EXISTS compliance_bloqueios_retencao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            recurso_tipo TEXT NOT NULL,
            recurso_id INTEGER NOT NULL,
            motivo TEXT NOT NULL,
            fundamento TEXT NOT NULL,
            valido_ate TEXT,
            status TEXT NOT NULL DEFAULT 'Ativo',
            criado_por INTEGER NOT NULL,
            encerrado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            encerrado_em TEXT,
            UNIQUE (empresa_id, recurso_tipo, recurso_id, status),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (encerrado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS analytics_catalogo_decisoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'Regra determinística',
            finalidade TEXT NOT NULL,
            dados_entrada TEXT NOT NULL,
            logica_resumo TEXT NOT NULL,
            impacto_pessoas TEXT NOT NULL DEFAULT 'Nenhum',
            revisao_humana INTEGER NOT NULL DEFAULT 1 CHECK (revisao_humana IN (0,1)),
            responsavel_id INTEGER,
            versao TEXT NOT NULL DEFAULT '1',
            status TEXT NOT NULL DEFAULT 'Em homologação',
            ultima_validacao TEXT,
            criado_por INTEGER NOT NULL,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, codigo, versao),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_remote_politicas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nome TEXT NOT NULL,
            exige_chamado INTEGER NOT NULL DEFAULT 1 CHECK (exige_chamado IN (0,1)),
            exige_consentimento INTEGER NOT NULL DEFAULT 1 CHECK (exige_consentimento IN (0,1)),
            acesso_nao_assistido INTEGER NOT NULL DEFAULT 0 CHECK (acesso_nao_assistido IN (0,1)),
            permite_clipboard INTEGER NOT NULL DEFAULT 0 CHECK (permite_clipboard IN (0,1)),
            permite_transferencia INTEGER NOT NULL DEFAULT 0 CHECK (permite_transferencia IN (0,1)),
            permite_terminal INTEGER NOT NULL DEFAULT 0 CHECK (permite_terminal IN (0,1)),
            duracao_max_minutos INTEGER NOT NULL DEFAULT 60,
            justificativa_nao_assistido TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
            criado_por INTEGER NOT NULL,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_ti_remote_politica_ativa
            ON ti_remote_politicas(empresa_id, ativo) WHERE ativo=1;

        CREATE TABLE IF NOT EXISTS ti_remote_autorizacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            politica_id INTEGER NOT NULL,
            ativo_id INTEGER NOT NULL,
            chamado_id INTEGER,
            tecnico_id INTEGER NOT NULL,
            motivo TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            consentimento_confirmado INTEGER NOT NULL DEFAULT 0 CHECK (consentimento_confirmado IN (0,1)),
            permissoes_json TEXT NOT NULL DEFAULT '{}',
            status TEXT NOT NULL DEFAULT 'Emitida',
            expira_em TEXT NOT NULL,
            consumido_em TEXT,
            encerrado_em TEXT,
            resultado TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (politica_id) REFERENCES ti_remote_politicas(id),
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id),
            FOREIGN KEY (chamado_id) REFERENCES ti_chamados(id),
            FOREIGN KEY (tecnico_id) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_ti_remote_autorizacoes_ativas
            ON ti_remote_autorizacoes(empresa_id, status, expira_em);

        CREATE TABLE IF NOT EXISTS ti_remote_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            autorizacao_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            detalhe_json TEXT NOT NULL DEFAULT '{}',
            hash_anterior TEXT,
            hash_evento TEXT NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (autorizacao_id) REFERENCES ti_remote_autorizacoes(id)
        );
        CREATE INDEX IF NOT EXISTS idx_ti_remote_eventos_sessao
            ON ti_remote_eventos(autorizacao_id, id);
        """
    )
