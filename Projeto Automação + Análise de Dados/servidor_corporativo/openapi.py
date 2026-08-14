"""Documento OpenAPI 3.1 gerado a partir dos contratos públicos da API v1."""
from __future__ import annotations

from servidor_corporativo import VERSAO_SERVIDOR


def documento_openapi() -> dict:
    erro = {
        "type": "object", "required": ["ok", "error", "request_id"],
        "properties": {
            "ok": {"type": "boolean", "const": False},
            "error": {"type": "object", "required": ["code", "message"], "properties": {
                "code": {"type": "string"}, "message": {"type": "string"},
            }},
            "request_id": {"type": "string"},
        },
    }
    paths: dict = {
        "/api/v1/health": {"get": {"security": [], "summary": "Liveness do servidor", "responses": {"200": {"description": "Operacional"}}}},
        "/api/v1/health/ready": {"get": {"security": [], "summary": "Readiness do servidor", "responses": {"200": {"description": "Pronto"}, "503": {"description": "Indisponível"}}}},
        "/api/v1/auth/login": {"post": {"security": [], "summary": "Autentica senha e MFA", "requestBody": {"required": True}, "responses": {"200": {"description": "Sessão criada"}, "401": {"description": "Credencial inválida"}, "429": {"description": "Rate limit"}}}},
        "/api/v1/auth/logout": {"post": {"summary": "Revoga a sessão atual", "responses": {"200": {"description": "Revogada"}}}},
        "/api/v1/account/sessions": {"get": {"summary": "Lista sessões do usuário", "responses": {"200": {"description": "Sessões"}}}},
        "/api/v1/automations/jobs": {"get": {"summary": "Lista execuções da fila", "responses": {"200": {"description": "Jobs"}}}},
        "/api/v1/metrics": {"get": {"summary": "Métricas Prometheus (admin)", "responses": {"200": {"description": "Exposition format 0.0.4"}, "403": {"description": "Proibido"}}}},
        "/api/v1/privacy/read-audit": {"get": {"summary": "Auditoria de leituras sensíveis (admin)", "responses": {"200": {"description": "Trilha LGPD"}}}},
        "/api/v1/account/mfa/setup": {"post": {"summary": "Inicia configuração MFA", "responses": {"201": {"description": "Segredo pendente"}}}},
        "/api/v1/account/mfa/confirm": {"post": {"summary": "Confirma TOTP e gera recuperação", "responses": {"200": {"description": "MFA ativado"}}}},
        "/api/v1/account/mfa/recovery/regenerate": {"post": {"summary": "Regenera códigos de recuperação", "responses": {"200": {"description": "Códigos novos"}}}},
        "/api/v1/account/sessions/revoke-all": {"post": {"summary": "Revoga todas as sessões", "responses": {"200": {"description": "Revogadas"}}}},
        "/api/v1/webhooks": {
            "get": {"summary": "Lista webhooks (admin)", "responses": {"200": {"description": "Endpoints sem segredos"}}},
            "post": {"summary": "Cadastra webhook HTTPS (admin)", "responses": {"201": {"description": "Segredo retornado uma vez"}}},
        },
        "/api/v1/webhooks/events": {"post": {"summary": "Publica evento assinado na fila", "responses": {"202": {"description": "Entregas enfileiradas"}}}},
        "/api/v1/privacy/retention/policies": {"post": {"summary": "Define política de retenção", "responses": {"201": {"description": "Política salva"}}}},
        "/api/v1/privacy/retention/run-rh": {"post": {"summary": "Simula ou executa retenção RH", "responses": {"200": {"description": "Resultado"}}}},
        "/api/v1/backups/{backup_id}/restore": {"post": {
            "summary": "Enfileira restauração com dupla confirmação", "parameters": [
                {"name": "backup_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                {"name": "X-Confirm-Restore", "in": "header", "required": True, "schema": {"type": "string"}},
            ], "responses": {"202": {"description": "Aguardando aprovação humana"}},
        }},
        "/api/v1/users/{user_id}": {"patch": {
            "summary": "Atualiza usuário com concorrência otimista", "parameters": [
                {"name": "user_id", "in": "path", "required": True, "schema": {"type": "integer"}},
                {"name": "If-Match", "in": "header", "required": True, "schema": {"type": "string"}},
            ], "responses": {"200": {"description": "Atualizado"}, "409": {"description": "Conflito de versão"}, "428": {"description": "If-Match ausente"}},
        }},
        "/api/v1/core/search": {"get": {"summary": "Busca universal escopada", "parameters": [
            {"name": "q", "in": "query", "required": True, "schema": {"type": "string"}},
            {"name": "modulo", "in": "query", "schema": {"type": "string"}},
        ], "responses": {"200": {"description": "Resultados paginados"}}}},
        "/api/v1/core/inbox": {"get": {"summary": "Caixa de entrada de ações", "responses": {"200": {"description": "Notificações, tarefas e aprovações"}}}},
        "/api/v1/core/calendar": {
            "get": {"summary": "Calendário corporativo", "responses": {"200": {"description": "Eventos"}}},
            "post": {"summary": "Cria evento corporativo", "responses": {"201": {"description": "Evento criado"}}},
        },
        "/api/v1/core/dashboards": {
            "get": {"summary": "Lista dashboards configuráveis", "responses": {"200": {"description": "Dashboards"}}},
            "post": {"summary": "Cria ou atualiza dashboard", "responses": {"201": {"description": "Dashboard salvo"}, "409": {"description": "Conflito de versão"}}},
        },
        "/api/v1/core/people": {
            "get": {"summary": "Lista cadastro mestre de pessoas", "responses": {"200": {"description": "Pessoas paginadas"}}},
            "post": {"summary": "Cria pessoa", "responses": {"201": {"description": "Pessoa criada"}}},
        },
        "/api/v1/operations/types": {
            "get": {"summary": "Catálogo configurável de tipos", "responses": {"200": {"description": "Tipos e schemas"}}},
            "post": {"summary": "Cria ou versiona um tipo", "responses": {"201": {"description": "Tipo salvo"}}},
        },
        "/api/v1/operations/records": {
            "get": {"summary": "Lista registros operacionais", "responses": {"200": {"description": "Registros paginados"}}},
            "post": {"summary": "Cria registro e inicia workflow", "responses": {"201": {"description": "Registro criado"}}},
        },
        "/api/v1/operations/records/{record_id}": {
            "get": {"summary": "Detalha registro, relações e workflow", "parameters": [
                {"name": "record_id", "in": "path", "required": True, "schema": {"type": "integer"}},
            ], "responses": {"200": {"description": "Registro detalhado"}}},
            "patch": {"summary": "Atualiza dados ou restaura/arquiva com If-Match", "responses": {"200": {"description": "Registro atualizado"}, "409": {"description": "Conflito de versão"}}},
            "delete": {"summary": "Move o registro para a lixeira com If-Match", "responses": {"200": {"description": "Registro removido logicamente"}, "409": {"description": "Conflito de versão"}}},
        },
        "/api/v1/operations/records/{record_id}/transition": {"post": {"summary": "Conclui etapa com aprovação contextual", "parameters": [
            {"name": "record_id", "in": "path", "required": True, "schema": {"type": "integer"}},
        ], "responses": {"200": {"description": "Fluxo avançado"}, "409": {"description": "Conflito de versão"}}}},
        "/api/v1/employees/me/360": {"get": {"summary": "Meu perfil 360°", "responses": {"200": {"description": "Visão de autoatendimento"}}}},
        "/api/v1/employees/{employee_id}/360": {"get": {"summary": "Funcionário 360° por visão contextual", "parameters": [
            {"name": "employee_id", "in": "path", "required": True, "schema": {"type": "integer"}},
            {"name": "view", "in": "query", "schema": {"type": "string", "enum": ["meu_perfil", "gestor", "rh", "ti", "auditor"]}},
        ], "responses": {"200": {"description": "Perfil filtrado"}, "403": {"description": "Visão não autorizada"}}}},
        "/api/v1/core/transfers/export": {"post": {"summary": "Exporta registros para CSV, JSON ou XLSX", "responses": {"201": {"description": "Exportação gerenciada"}}}},
        "/api/v1/core/transfers/import": {"post": {"summary": "Importa registros com mapeamento", "responses": {"201": {"description": "Importação rastreada"}}}},
    }
    for path, titulo in {
        "/api/v1/crm/leads": "Leads", "/api/v1/comercial/oportunidades": "Oportunidades",
        "/api/v1/marketing/campanhas": "Campanhas", "/api/v1/juridico/processos": "Processos jurídicos",
        "/api/v1/administrativo/solicitacoes": "Solicitações administrativas",
    }.items():
        paths[path] = {
            "get": {"summary": f"Lista {titulo}", "parameters": [
                {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1}},
                {"name": "page_size", "in": "query", "schema": {"type": "integer", "minimum": 1, "maximum": 100}},
            ], "responses": {"200": {"description": "Lista paginada"}}},
            "post": {"summary": f"Cria {titulo}", "parameters": [
                {"name": "Idempotency-Key", "in": "header", "schema": {"type": "string", "minLength": 8, "maxLength": 200}},
            ], "requestBody": {"required": True}, "responses": {"201": {"description": "Criado"}, "400": {"description": "Payload inválido"}}},
        }
    return {
        "openapi": "3.1.0",
        "info": {"title": "Data Intelligence Corporate API", "version": VERSAO_SERVIDOR},
        "servers": [{"url": "/"}], "paths": paths,
        "tags": [
            {"name": "Identidade"}, {"name": "Automações"},
            {"name": "Privacidade"}, {"name": "Observabilidade"}, {"name": "CORE V11"},
            {"name": "Funcionário 360"}, {"name": "Operações"},
        ],
        "components": {
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
            "schemas": {"Error": erro},
        },
        "security": [{"bearerAuth": []}],
    }


__all__ = ("documento_openapi",)
