"""Domínio especializado de Tecnologia e Serviços 2.0.

O esquema cobre Service Desk, ativos/CMDB, telemetria, rede autorizada,
licenças, sistemas, monitoramento, contratos, mudanças, problemas,
segurança e acesso remoto auditado. Descoberta e acesso nunca são
executados implicitamente: o banco apenas registra autorização, evidências
e sessões iniciadas por um operador identificado.
"""

from __future__ import annotations


def upgrade(conexao) -> None:
    conexao.executescript(
        """
        CREATE TABLE IF NOT EXISTS ti_ativos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            memoria_gb REAL NOT NULL DEFAULT 0 CHECK (memoria_gb >= 0),
            armazenamento_gb REAL NOT NULL DEFAULT 0 CHECK (armazenamento_gb >= 0),
            usuario_responsavel_id INTEGER,
            departamento_id INTEGER,
            centro_custo_id INTEGER,
            localizacao TEXT,
            status TEXT NOT NULL DEFAULT 'Disponível',
            estado_conectividade TEXT NOT NULL DEFAULT 'Desconhecido',
            saude_percentual REAL CHECK (saude_percentual IS NULL OR saude_percentual BETWEEN 0 AND 100),
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, patrimonio),
            UNIQUE (empresa_id, numero_serie),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (usuario_responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id),
            FOREIGN KEY (estoque_item_id) REFERENCES est_itens(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_ti_ativos_contexto
            ON ti_ativos (empresa_id, filial_id, status, estado_conectividade, ativo);

        CREATE TABLE IF NOT EXISTS ti_chamados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            sla_inicia_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            primeira_resposta_em TEXT,
            resolvido_em TEXT,
            causa TEXT,
            solucao TEXT,
            satisfacao INTEGER CHECK (satisfacao IS NULL OR satisfacao BETWEEN 1 AND 5),
            criado_por INTEGER,
            atualizado_por INTEGER,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (solicitante_id) REFERENCES usuarios(id),
            FOREIGN KEY (tecnico_id) REFERENCES usuarios(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id),
            FOREIGN KEY (sistema_id) REFERENCES ti_sistemas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id),
            FOREIGN KEY (atualizado_por) REFERENCES usuarios(id)
        );
        CREATE INDEX IF NOT EXISTS idx_ti_chamados_fila
            ON ti_chamados (empresa_id, filial_id, status, prioridade, criado_em DESC);

        CREATE TABLE IF NOT EXISTS ti_chamado_comentarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chamado_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            comentario TEXT NOT NULL,
            interno INTEGER NOT NULL DEFAULT 0 CHECK (interno IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (chamado_id) REFERENCES ti_chamados(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_historico (
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
        CREATE INDEX IF NOT EXISTS idx_ti_historico_recurso
            ON ti_historico (empresa_id, recurso_tipo, recurso_id, criado_em DESC);
        CREATE TRIGGER IF NOT EXISTS trg_ti_historico_sem_update
        BEFORE UPDATE ON ti_historico BEGIN
            SELECT RAISE(ABORT, 'O histórico de Tecnologia é imutável');
        END;
        CREATE TRIGGER IF NOT EXISTS trg_ti_historico_sem_delete
        BEFORE DELETE ON ti_historico BEGIN
            SELECT RAISE(ABORT, 'O histórico de Tecnologia é imutável');
        END;

        CREATE TABLE IF NOT EXISTS ti_telemetria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ativo_id INTEGER NOT NULL,
            cpu_percentual REAL CHECK (cpu_percentual IS NULL OR cpu_percentual BETWEEN 0 AND 100),
            memoria_percentual REAL CHECK (memoria_percentual IS NULL OR memoria_percentual BETWEEN 0 AND 100),
            disco_percentual REAL CHECK (disco_percentual IS NULL OR disco_percentual BETWEEN 0 AND 100),
            espaco_livre_gb REAL CHECK (espaco_livre_gb IS NULL OR espaco_livre_gb >= 0),
            uptime_segundos INTEGER CHECK (uptime_segundos IS NULL OR uptime_segundos >= 0),
            latencia_ms REAL CHECK (latencia_ms IS NULL OR latencia_ms >= 0),
            agente_versao TEXT,
            coletado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id)
        );
        CREATE INDEX IF NOT EXISTS idx_ti_telemetria_ativo
            ON ti_telemetria (ativo_id, coletado_em DESC);

        CREATE TABLE IF NOT EXISTS ti_manutencoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            ativo_id INTEGER NOT NULL,
            chamado_id INTEGER,
            problema TEXT NOT NULL,
            diagnostico TEXT,
            fornecedor_id INTEGER,
            status TEXT NOT NULL DEFAULT 'Triagem',
            inicio_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            previsao_em TEXT,
            concluido_em TEXT,
            custo_centavos INTEGER NOT NULL DEFAULT 0 CHECK (custo_centavos >= 0),
            criado_por INTEGER,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id),
            FOREIGN KEY (chamado_id) REFERENCES ti_chamados(id),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_emprestimos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            ativo_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            manutencao_id INTEGER,
            motivo TEXT,
            entregue_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            previsto_devolucao TEXT,
            devolvido_em TEXT,
            status TEXT NOT NULL DEFAULT 'Ativo',
            criado_por INTEGER,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (manutencao_id) REFERENCES ti_manutencoes(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_segmentos_rede (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            UNIQUE (empresa_id, cidr),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (departamento_id) REFERENCES departamentos(id),
            FOREIGN KEY (autorizado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_dispositivos_rede (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            primeira_deteccao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ultima_deteccao TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            origem TEXT NOT NULL DEFAULT 'Agente',
            investigado_por INTEGER,
            UNIQUE (segmento_id, endereco_ip),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (segmento_id) REFERENCES ti_segmentos_rede(id),
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id),
            FOREIGN KEY (investigado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_licencas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id),
            FOREIGN KEY (centro_custo_id) REFERENCES centros_custo(id),
            FOREIGN KEY (financeiro_recorrencia_id) REFERENCES fin_recorrencias(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_licenca_atribuicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            licenca_id INTEGER NOT NULL,
            usuario_id INTEGER,
            ativo_id INTEGER,
            identificador TEXT,
            atribuido_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            revogado_em TEXT,
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            FOREIGN KEY (licenca_id) REFERENCES ti_licencas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id),
            CHECK (usuario_id IS NOT NULL OR ativo_id IS NOT NULL OR identificador IS NOT NULL)
        );

        CREATE TABLE IF NOT EXISTS ti_sistemas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            sla_disponibilidade REAL NOT NULL DEFAULT 99.0 CHECK (sla_disponibilidade BETWEEN 0 AND 100),
            ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (empresa_id, nome, ambiente),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (servidor_ativo_id) REFERENCES ti_ativos(id),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id),
            FOREIGN KEY (responsavel_ti_id) REFERENCES usuarios(id),
            FOREIGN KEY (responsavel_negocio_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_sistema_dependencias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sistema_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            nome TEXT NOT NULL,
            ativo_id INTEGER,
            sistema_dependencia_id INTEGER,
            criticidade TEXT NOT NULL DEFAULT 'Média',
            FOREIGN KEY (sistema_id) REFERENCES ti_sistemas(id),
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id),
            FOREIGN KEY (sistema_dependencia_id) REFERENCES ti_sistemas(id)
        );

        CREATE TABLE IF NOT EXISTS ti_monitores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            filial_id INTEGER,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            ativo_id INTEGER,
            sistema_id INTEGER,
            alvo TEXT,
            intervalo_segundos INTEGER NOT NULL DEFAULT 60 CHECK (intervalo_segundos >= 30),
            limite_aviso REAL,
            limite_critico REAL,
            status TEXT NOT NULL DEFAULT 'Sem dados',
            ultimo_valor REAL,
            ultima_verificacao TEXT,
            habilitado INTEGER NOT NULL DEFAULT 1 CHECK (habilitado IN (0, 1)),
            criado_por INTEGER,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id),
            FOREIGN KEY (sistema_id) REFERENCES ti_sistemas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_eventos_monitoramento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            monitor_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            valor REAL,
            mensagem TEXT,
            coletado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (monitor_id) REFERENCES ti_monitores(id)
        );

        CREATE TABLE IF NOT EXISTS ti_conhecimento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (autor_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_contratos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (fornecedor_id) REFERENCES cmp_fornecedores(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (documento_id) REFERENCES documentos(id)
        );

        CREATE TABLE IF NOT EXISTS ti_problemas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            concluido_em TEXT,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_problema_chamados (
            problema_id INTEGER NOT NULL,
            chamado_id INTEGER NOT NULL,
            PRIMARY KEY (problema_id, chamado_id),
            FOREIGN KEY (problema_id) REFERENCES ti_problemas(id),
            FOREIGN KEY (chamado_id) REFERENCES ti_chamados(id)
        );

        CREATE TABLE IF NOT EXISTS ti_mudancas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            concluido_em TEXT,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id),
            FOREIGN KEY (aprovacao_id) REFERENCES aprovacoes(id)
        );

        CREATE TABLE IF NOT EXISTS ti_incidentes_seguranca (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            detectado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            encerrado_em TEXT,
            UNIQUE (empresa_id, numero),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id),
            FOREIGN KEY (sistema_id) REFERENCES ti_sistemas(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_acessos_remotos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (ativo_id) REFERENCES ti_ativos(id),
            FOREIGN KEY (chamado_id) REFERENCES ti_chamados(id),
            FOREIGN KEY (tecnico_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_alertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reconhecido_em TEXT,
            resolvido_em TEXT,
            UNIQUE (empresa_id, tipo, recurso_tipo, recurso_id, status),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (filial_id) REFERENCES filiais(id),
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS ti_permissoes_acoes (
            usuario_id INTEGER NOT NULL,
            empresa_id INTEGER NOT NULL,
            acao TEXT NOT NULL,
            permitido INTEGER NOT NULL DEFAULT 0 CHECK (permitido IN (0, 1)),
            atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (usuario_id, empresa_id, acao),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        );
        """
    )
