"""Workspace especializado e funcional de Recursos Humanos."""

from __future__ import annotations

import json
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from auth.sessao import SESSAO
from services.contexto import tem_permissao
from services.departamentos.rh import (
    ACOES_RH,
    adicionar_candidato,
    adicionar_dependente,
    adicionar_evento_folha,
    agendar_relatorio,
    analisar_rh,
    abrir_folha,
    alterar_estado_registro_rh,
    atualizar_admissao,
    atualizar_colaborador,
    concluir_desligamento,
    criar_solicitacao,
    criar_vaga,
    decidir_ferias_ausencia,
    decidir_solicitacao,
    exportar_dataframe_rh,
    fechar_folha,
    gerar_contracheque,
    gerar_relatorio_rh,
    iniciar_admissao,
    iniciar_desligamento,
    inscrever_treinamento,
    listar_admissoes,
    listar_auditoria_rh,
    listar_catalogos,
    listar_colaboradores,
    listar_secao,
    obter_colaborador,
    registrar_documento,
    registrar_ponto,
    resumo_rh,
    salvar_avaliacao,
    salvar_beneficio,
    salvar_cargo,
    salvar_pdi,
    salvar_permissao_acao,
    salvar_treinamento,
    solicitar_ferias_ausencia,
    tem_permissao_rh,
    verificar_documento,
    vincular_equipamento,
    vincular_beneficio,
)
from interface.componentes import (
    AreaRolavel,
    GradeResponsiva,
    criar_botao,
    criar_cabecalho,
    criar_card,
    criar_estado_vazio,
    criar_metrica,
    criar_sidebar,
    criar_titulo_secao,
    preparar_janela_secundaria,
)
from interface.grade_editavel import EditorGrade
from interface.componentes_departamentais import renderizar_acessos_rapidos, renderizar_metricas
from interface.navegacao_modulos import criar_sidebar_modulo
from interface.tema import (
    CORES,
    FONTES,
    LAYOUT,
    adicionar_divisorias_treeview,
    configurar_estilos_ttk,
)


COR_RH = "#9C7CFF"

GRUPOS_MENU = (
    ("RECURSOS HUMANOS", (
        ("visao", "⌂", "Visão geral"),
        ("colaboradores", "◉", "Colaboradores 360°"),
        ("recrutamento", "◎", "Recrutamento"),
    )),
    ("OPERAÇÃO E GOVERNANÇA", (
        ("documentos", "▤", "Documentos"),
        ("solicitacoes", "✓", "Solicitações"),
        ("relatorios", "⇥", "Relatórios"),
        ("auditoria", "◎", "Auditoria RH"),
        ("configuracoes", "⚙", "Configurações RH"),
    )),
)

ROTULOS = {chave: titulo for _grupo, itens in GRUPOS_MENU for chave, _icone, titulo in itens}

SUBTITULOS = {
    "colaboradores": "Cadastro mestre, vínculos, histórico, benefícios, documentos e dados profissionais.",
    "admissoes": "Wizard de admissão, checklist documental, integrações e onboarding.",
    "desligamentos": "Rescisão segura, revogação de acessos, devoluções e encerramento.",
    "movimentacoes": "Promoções, mudanças de cargo, salário, departamento e demais alterações.",
    "ponto": "Registros de jornada, horas trabalhadas, extras, atrasos e ajustes.",
    "ferias": "Saldos, períodos aquisitivos, conflitos, aprovações, férias e afastamentos.",
    "beneficios": "Catálogo, elegibilidade, custos e vínculos por colaborador.",
    "folha": "Competências, eventos, proventos, descontos, encargos e contracheques.",
    "cargos": "Estrutura de cargos, níveis, responsabilidades e faixas salariais.",
    "recrutamento": "Vagas, aprovação de abertura, candidatos e funil seletivo.",
    "desempenho": "Ciclos de avaliação, competências, feedbacks e resultados.",
    "treinamentos": "Catálogo, inscrições, obrigatoriedade, certificados e validade.",
    "carreira": "Planos de desenvolvimento, ações, prazos e progresso de carreira.",
    "documentos": "GED de RH com versão, validade, assinatura, hash e acesso restrito.",
    "solicitacoes": "Portal interno para solicitações, aprovações, respostas e acompanhamento.",
}


def _moeda(centavos):
    if centavos is None:
        return "Acesso restrito"
    valor = int(centavos or 0) / 100
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _formatar(valor, campo=""):
    if valor is None:
        return "—"
    if "centavos" in campo:
        return _moeda(valor)
    if campo in {"obrigatorio", "ativo"}:
        return "Sim" if valor else "Não"
    return str(valor)

