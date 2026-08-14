"""Dependências e catálogos da Central Analytics V9.8."""
from __future__ import annotations
from core.versao import VERSAO_INTERFACE
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import threading
from pathlib import Path
from auth.sessao import SESSAO
from historico.repositorio import listar_historico
from services.recursos import alterar_estado_recurso, criar_recurso, listar_recursos
from services.datasets import atualizar_metadados_conjunto, excluir_conjunto, importar_conjunto, listar_conjuntos, obter_conjunto, substituir_arquivo_conjunto
from interface.componentes import AreaRolavel, GradeResponsiva, criar_botao, criar_cabecalho, criar_card, criar_card_acao, criar_chip, criar_estado_vazio, preparar_janela_secundaria, criar_sidebar, criar_titulo_secao
from interface.tema import CORES, FONTES, LAYOUT, adicionar_divisorias_treeview, configurar_estilos_ttk
from interface.navegacao_analytics import MENU_ANALYTICS, criar_sidebar_analytics

ESQUEMAS_ANALYTICS = {
    "relatorios": (
        ("titulo", "Relatório", "texto"),
        ("conjunto", "Conjunto de dados", "texto"),
        ("periodo", "Período", "texto"),
        ("formato", "Formato", "opcoes", ("PDF", "Excel", "CSV", "HTML")),
        ("responsavel", "Responsável", "texto"),
        ("status", "Situação", "opcoes", ("Rascunho", "Configurado", "Gerado")),
    ),
    "visualizacoes": (
        ("nome", "Visualização", "texto"),
        ("conjunto", "Conjunto de dados", "texto"),
        ("grafico", "Tipo de gráfico", "opcoes", ("Barras", "Linha", "Pizza", "Dispersão", "Tabela")),
        ("eixo", "Dimensão / eixo", "texto"),
        ("metrica", "Métrica", "texto"),
        ("status", "Situação", "opcoes", ("Rascunho", "Publicada", "Arquivada")),
    ),
    "agendamentos": (
        ("nome", "Agendamento", "texto"),
        ("rotina", "Rotina", "opcoes", ("Análise", "Relatório", "Importação", "E-mail")),
        ("frequencia", "Frequência", "opcoes", ("Diária", "Semanal", "Mensal", "Uma vez")),
        ("horario", "Horário", "texto"),
        ("responsavel", "Responsável", "texto"),
        ("status", "Situação", "opcoes", ("Ativo", "Pausado", "Concluído")),
    ),
    "alertas": (
        ("nome", "Alerta", "texto"),
        ("metrica", "Indicador monitorado", "texto"),
        ("condicao", "Condição", "opcoes", ("Maior que", "Menor que", "Igual a", "Variação %")),
        ("limite", "Limite", "numero"),
        ("severidade", "Severidade", "opcoes", ("Informativa", "Atenção", "Crítica")),
        ("status", "Situação", "opcoes", ("Ativo", "Pausado", "Disparado")),
    ),
}

CONFIGURACOES_SECOES_ANALYTICS = {
    "relatorios": {
        "subtitulo": (
            "Configure conjunto, período e formato antes da geração. "
            "A configuração permanece auditada para futura prévia e exportação."
        ),
        "acao": "+  CONFIGURAR RELATÓRIO",
        "vazio": "Configure o primeiro relatório analítico.",
    },
    "visualizacoes": {
        "subtitulo": (
            "Defina conjunto, dimensão, métrica e tipo de gráfico para compor "
            "dashboards e relatórios."
        ),
        "acao": "+  NOVA VISUALIZAÇÃO",
        "vazio": "Crie a primeira visualização vinculada aos seus dados.",
    },
    "agendamentos": {
        "subtitulo": (
            "Planeje análises, importações, relatórios e entregas recorrentes "
            "com frequência e horário explícitos."
        ),
        "acao": "+  NOVO AGENDAMENTO",
        "vazio": "Cadastre a primeira rotina programada.",
    },
    "alertas": {
        "subtitulo": (
            "Monitore indicadores do Analytics sem misturar estes eventos com a "
            "Central global de notificações."
        ),
        "acao": "+  NOVO ALERTA",
        "vazio": "Defina uma métrica e um limite para iniciar o monitoramento.",
    },
}
