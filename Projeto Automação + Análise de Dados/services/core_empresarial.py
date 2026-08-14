"""Fachada única do CORE empresarial V11 para Desktop, Web e integrações."""
from enterprise.core_v11.busca import busca_universal, reindexar_core
from enterprise.core_v11.colaboracao import (
    adicionar_comentario, caixa_entrada, criar_evento_calendario, listar_calendario,
    listar_comentarios, listar_dashboards, salvar_dashboard, salvar_preferencia_contextual,
)
from enterprise.core_v11.documentos import (
    listar_documentos, registrar_documento, registrar_evidencia_assinatura, solicitar_assinatura,
)
from enterprise.core_v11.integracoes import listar_credenciais, registrar_referencia_credencial, registrar_rotacao
from enterprise.core_v11.metadados import (
    aplicar_etiqueta, criar_etiqueta, definir_campo, listar_campos, obter_campos_valores,
    salvar_campos_valores, salvar_configuracao,
)
from enterprise.core_v11.organizacao import arvore_organizacional, atualizar_unidade, criar_unidade, listar_unidades
from enterprise.core_v11.pessoas import criar_pessoa, listar_pessoas, obter_pessoa, vincular_papel
from enterprise.core_v11.seguranca import (
    adicionar_membro, atribuir_funcao, criar_funcao_contextual, criar_grupo, listar_grupos_funcoes,
)
from enterprise.core_v11.transferencias import exportar_registros, importar_registros_bytes, listar_transferencias

__all__ = tuple(nome for nome in globals() if not nome.startswith("_"))
