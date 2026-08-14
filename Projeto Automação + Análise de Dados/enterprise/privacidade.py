"""Governança de privacidade, auditoria de leitura e retenção LGPD."""
from __future__ import annotations

from datetime import date, timedelta
import hashlib
import json
import logging
from pathlib import Path
from typing import Iterable

from auth import banco
from auth.banco import conectar, registrar_auditoria
from enterprise.contexto import obter_escopo_ator


CLASSIFICACAO_DADOS = {
    "cpf": "pessoal_identificador",
    "rg": "pessoal_identificador",
    "nascimento": "pessoal",
    "endereco": "pessoal",
    "telefone": "pessoal",
    "email_pessoal": "pessoal",
    "contato_emergencia": "pessoal",
    "salario_centavos": "pessoal_financeiro",
    "banco": "pessoal_financeiro",
    "agencia": "pessoal_financeiro",
    "conta": "pessoal_financeiro",
    "chave_pix": "pessoal_financeiro",
    "documentos": "pessoal_documental",
    "dependentes": "pessoal_familiar",
}


def mascarar_cpf(valor: str | None) -> str | None:
    digitos = "".join(x for x in str(valor or "") if x.isdigit())
    if len(digitos) != 11:
        return None if not valor else "***.***.***-**"
    return f"***.***.{digitos[6:9]}-**"


def mascarar_conta(valor: str | None) -> str | None:
    texto = str(valor or "").strip()
    if not texto:
        return None
    return "•" * max(4, len(texto) - 2) + texto[-2:]


def mascarar_email(valor: str | None) -> str | None:
    texto = str(valor or "").strip()
    if "@" not in texto:
        return None if not texto else "***"
    nome, dominio = texto.split("@", 1)
    return f"{nome[:1] or '*'}***@{dominio}"


def mascarar_registro(registro: dict, campos: Iterable[str] | None = None) -> dict:
    """Retorna cópia segura para listas, logs e telas de menor privilégio."""
    saida = dict(registro)
    selecionados = set(campos or CLASSIFICACAO_DADOS)
    for campo in selecionados:
        if campo not in saida:
            continue
        if campo == "cpf":
            saida[campo] = mascarar_cpf(saida[campo])
        elif campo in {"conta", "agencia", "chave_pix", "banco"}:
            saida[campo] = mascarar_conta(saida[campo])
        elif campo in {"email_pessoal"}:
            saida[campo] = mascarar_email(saida[campo])
        elif campo == "salario_centavos":
            saida[campo] = None
        elif saida[campo] is not None:
            saida[campo] = "***"
    return saida


def registrar_leitura_sensivel(
    *,
    ator: dict,
    modulo: str,
    entidade: str,
    entidade_id: int | None,
    campos: Iterable[str],
    finalidade: str | None = None,
    request_id: str | None = None,
) -> None:
    """Registra somente metadados; valores pessoais nunca entram no log."""
    empresa_id, filial_id = obter_escopo_ator(ator)
    classificados = sorted({str(c) for c in campos if str(c) in CLASSIFICACAO_DADOS})
    if not classificados:
        return
    with conectar() as con:
        con.execute(
            """INSERT INTO auditoria_leituras_sensiveis
               (empresa_id,filial_id,usuario_id,modulo,entidade,entidade_id,
                campos,finalidade,request_id) VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                int(empresa_id), filial_id, int(ator["id"]), str(modulo)[:80],
                str(entidade)[:100], int(entidade_id) if entidade_id is not None else None,
                json.dumps(classificados, ensure_ascii=False), str(finalidade or "Operação do sistema")[:240],
                str(request_id or "")[:80] or None,
            ),
        )


def listar_leituras_sensiveis(ator: dict, *, limite: int = 200) -> list[dict]:
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("A consulta da trilha de privacidade exige administrador.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as con:
        rows = con.execute(
            """SELECT a.*,u.nome usuario_nome FROM auditoria_leituras_sensiveis a
               LEFT JOIN usuarios u ON u.id=a.usuario_id
               WHERE a.empresa_id=? ORDER BY a.id DESC LIMIT ?""",
            (int(empresa_id), max(1, min(int(limite), 2000))),
        ).fetchall()
    saida: list[dict] = []
    for row in rows:
        item = dict(row)
        item["campos"] = json.loads(item["campos"] or "[]")
        saida.append(item)
    return saida


def definir_politica_retencao(
    modulo: str,
    entidade: str,
    dias_retencao: int,
    ator: dict,
    *,
    acao: str = "Anonimizar",
) -> int:
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("A política de retenção exige administrador.")
    dias = int(dias_retencao)
    if dias < 30 or dias > 36500:
        raise ValueError("A retenção deve ficar entre 30 e 36.500 dias.")
    acao_norm = str(acao).strip().capitalize()
    if acao_norm not in {"Anonimizar", "Revisar"}:
        raise ValueError("Ação de retenção inválida.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as con:
        cursor = con.execute(
            """INSERT INTO politicas_retencao
               (empresa_id,modulo,entidade,dias_retencao,acao,criado_por)
               VALUES (?,?,?,?,?,?)
               ON CONFLICT(empresa_id,modulo,entidade) DO UPDATE SET
               dias_retencao=excluded.dias_retencao,acao=excluded.acao,ativo=1,
               atualizado_em=CURRENT_TIMESTAMP RETURNING id""",
            (int(empresa_id), str(modulo)[:80], str(entidade)[:100], dias, acao_norm, int(ator["id"])),
        )
        row = cursor.fetchone()
    return int(row["id"] if hasattr(row, "keys") else row[0])


def _anonimizar_colaborador(con, colaborador_id: int, empresa_id: int, ator_id: int) -> list[str] | None:
    row = con.execute(
        "SELECT id,matricula,foto_caminho FROM rh_colaboradores WHERE id=? AND empresa_id=?",
        (int(colaborador_id), int(empresa_id)),
    ).fetchone()
    if row is None:
        return None
    documentos = con.execute(
        "SELECT caminho FROM rh_documentos WHERE colaborador_id=?",
        (int(colaborador_id),),
    ).fetchall()
    arquivos = [str(item["caminho"]) for item in documentos if item["caminho"]]
    if row["foto_caminho"]:
        arquivos.append(str(row["foto_caminho"]))
    pseudonimo = hashlib.sha256(f"{empresa_id}:{colaborador_id}".encode("ascii")).hexdigest()[:12]
    con.execute(
        """UPDATE rh_colaboradores SET
           nome_completo=?,nome_social=NULL,cpf=NULL,rg=NULL,nascimento=NULL,estado_civil=NULL,
           nacionalidade=NULL,endereco=NULL,telefone=NULL,email_pessoal=NULL,email_corporativo=NULL,
           contato_emergencia=NULL,banco=NULL,agencia=NULL,conta=NULL,chave_pix=NULL,foto_caminho=NULL,
           motivo_desligamento=NULL,atualizado_por=?,atualizado_em=CURRENT_TIMESTAMP WHERE id=?""",
        (f"Titular anonimizado {pseudonimo}", int(ator_id), int(colaborador_id)),
    )
    con.execute(
        "UPDATE rh_dependentes SET nome='Dependente anonimizado',nascimento=NULL,cpf=NULL WHERE colaborador_id=?",
        (int(colaborador_id),),
    )
    con.execute("DELETE FROM rh_documentos WHERE colaborador_id=?", (int(colaborador_id),))
    return arquivos


def _excluir_arquivos_retidos(referencias: Iterable[str]) -> list[str]:
    """Remove anexos somente depois do commit e apenas dentro do storage corporativo."""
    storage = Path(banco.STORAGE_DIR).resolve()
    pendentes: list[str] = []
    for referencia in referencias:
        bruto = Path(str(referencia)).expanduser()
        caminho = bruto.resolve() if bruto.is_absolute() else (storage / bruto).resolve()
        if caminho != storage and storage not in caminho.parents:
            logging.getLogger(__name__).error("Retenção recusou caminho fora do storage: %s", referencia)
            pendentes.append(str(referencia))
            continue
        try:
            if caminho.is_file():
                caminho.unlink()
        except OSError:
            logging.getLogger(__name__).exception("Falha ao excluir arquivo sujeito à retenção: %s", caminho)
            pendentes.append(str(referencia))
    return pendentes


def executar_retencao_rh(ator: dict, *, simular: bool = True) -> dict:
    """Aplica retenção apenas com confirmação explícita; por padrão, simula."""
    if str(ator.get("perfil", "")).lower() != "admin":
        raise PermissionError("A execução de retenção exige administrador.")
    empresa_id, _ = obter_escopo_ator(ator)
    with conectar() as con:
        politica = con.execute(
            """SELECT dias_retencao,acao FROM politicas_retencao
               WHERE empresa_id=? AND modulo='RH' AND entidade='colaborador' AND ativo=1""",
            (int(empresa_id),),
        ).fetchone()
        if politica is None:
            raise ValueError("Defina a política RH/colaborador antes de executar a retenção.")
        limite = (date.today() - timedelta(days=int(politica["dias_retencao"]))).isoformat()
        rows = con.execute(
            """SELECT c.id,c.matricula,c.desligamento FROM rh_colaboradores c
               WHERE c.empresa_id=? AND c.desligamento IS NOT NULL AND c.desligamento<=?
                 AND NOT EXISTS (
                    SELECT 1 FROM compliance_bloqueios_retencao b
                    WHERE b.empresa_id=c.empresa_id AND b.recurso_tipo='rh_colaboradores'
                      AND b.recurso_id=c.id AND b.status='Ativo'
                      AND (b.valido_ate IS NULL OR b.valido_ate>=CURRENT_DATE)
                 )
               ORDER BY c.id""",
            (int(empresa_id), limite),
        ).fetchall()
        candidatos = [dict(row) for row in rows]
        processados = 0
        arquivos_para_excluir: list[str] = []
        if not simular and str(politica["acao"]) == "Anonimizar":
            for item in candidatos:
                arquivos = _anonimizar_colaborador(con, int(item["id"]), int(empresa_id), int(ator["id"]))
                if arquivos is not None:
                    processados += 1
                    arquivos_para_excluir.extend(arquivos)
    arquivos_pendentes = _excluir_arquivos_retidos(arquivos_para_excluir) if not simular else []
    if not simular:
        registrar_auditoria(
            "retencao_lgpd_executada", usuario_id=int(ator["id"]),
            detalhes=f"modulo=RH;entidade=colaborador;processados={processados}",
        )
    return {
        "simulacao": bool(simular), "limite": limite, "candidatos": len(candidatos),
        "processados": processados, "ids": [int(item["id"]) for item in candidatos],
        "arquivos_pendentes": arquivos_pendentes,
    }


__all__ = (
    "CLASSIFICACAO_DADOS", "definir_politica_retencao", "executar_retencao_rh",
    "listar_leituras_sensiveis", "mascarar_conta", "mascarar_cpf", "mascarar_email",
    "mascarar_registro", "registrar_leitura_sensivel",
)
