"""Dependências compartilhadas do módulo empresarial V9.8."""
from core.versao import VERSAO_INTERFACE
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from auth.sessao import SESSAO
from services.catalogo import obter_modulo
from services.contexto import tem_permissao
from services.modulos import alterar_estado_registro, atualizar_registro, calcular_resumo_modulo, criar_registro, listar_registros_paginados, movimentar_estoque, obter_registro
from services.organizacao import listar_centros_custo, listar_departamentos
from interface.componentes import AreaRolavel, criar_botao, criar_cabecalho, criar_card, criar_estado_vazio, preparar_janela_secundaria, criar_sidebar
from interface.configuracao_modulos_ui import PAINEIS_MODULOS
from interface.tema import CORES, LAYOUT, adicionar_divisorias_treeview, configurar_estilos_ttk
