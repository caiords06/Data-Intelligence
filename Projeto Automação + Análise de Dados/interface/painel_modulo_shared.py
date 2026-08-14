"""Dependências compartilhadas do painel departamental V9.8."""
from __future__ import annotations
from core.versao import VERSAO_INTERFACE
import tkinter as tk
from tkinter import messagebox, ttk
from auth.sessao import SESSAO
from services.catalogo import obter_modulo
from services.contexto import tem_permissao
from services.modulos import calcular_resumo_modulo
from services.recursos import alterar_estado_recurso, atualizar_recurso, criar_recurso, listar_recursos, obter_recurso, resumo_recursos
from interface.componentes import AreaRolavel, GradeResponsiva, criar_botao, criar_cabecalho, criar_card, criar_chip, criar_estado_vazio, criar_metrica, preparar_janela_secundaria, criar_sidebar, criar_titulo_secao
from interface.grade_editavel import EditorGrade
from interface.navegacao_modulos import criar_sidebar_modulo
from interface.configuracao_modulos_ui import PAINEIS_MODULOS, obter_esquema_recurso
from interface.tema import CORES, FONTES, LAYOUT, adicionar_divisorias_treeview, configurar_estilos_ttk
STATUS_COMUNS=("Pendente","Planejado","Aberto","Em andamento","Em análise","Aprovado","Concluído","Cancelado")
