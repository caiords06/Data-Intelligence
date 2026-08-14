"""Catálogo de provedores. Um provedor só fica 'ativo' se houver integração habilitada."""
from __future__ import annotations
from enterprise.integrations.providers import google,http,microsoft,smtp

_PROVEDORES={p.codigo:p for p in (smtp,microsoft,google,http)}

def obter_provedor(codigo: str):
    return _PROVEDORES.get(str(codigo or "").strip().lower())

def catalogo_provedores() -> list[dict]:
    return [{"codigo":p.codigo,"nome":p.nome,"capacidades":[c.__dict__ if hasattr(c,"__dict__") else {"codigo":c.codigo,"titulo":c.titulo,"direcao":c.direcao} for c in p.capacidades]} for p in _PROVEDORES.values()]

def status_provedores(ator: dict) -> list[dict]:
    from enterprise.integracoes import listar_integracoes
    configuradas={str(x.get("provedor")):x for x in listar_integracoes(ator)}
    saida=[]
    for p in _PROVEDORES.values():
        item=configuradas.get(p.codigo)
        saida.append({"codigo":p.codigo,"nome":p.nome,"configurado":bool(item),"ativo":bool(item and item.get("ativo")),
                      "integracao_id":item.get("id") if item else None,"capacidades":[c.codigo for c in p.capacidades]})
    return saida
