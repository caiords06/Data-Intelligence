"""Mantém valor legado e valor_centavos da Central de Aprovações consistentes."""

from __future__ import annotations


def upgrade(conexao) -> None:
    colunas = {str(x["name"]) for x in conexao.execute("PRAGMA table_info(aprovacoes)").fetchall()}
    if not {"valor", "valor_centavos"}.issubset(colunas):
        return

    # Centavos são a representação canônica. Para registros legados cujo campo
    # em centavos ficou zerado, recuperamos o valor REAL histórico uma única vez.
    conexao.execute(
        """UPDATE aprovacoes
           SET valor_centavos = ROUND(COALESCE(valor, 0) * 100)
           WHERE COALESCE(valor_centavos, 0) = 0 AND ABS(COALESCE(valor, 0)) > 0"""
    )
    conexao.execute(
        "UPDATE aprovacoes SET valor = COALESCE(valor_centavos, 0) / 100.0"
    )

    conexao.executescript(
        """
        DROP TRIGGER IF EXISTS trg_aprovacoes_valor_insert;
        DROP TRIGGER IF EXISTS trg_aprovacoes_valor_update;
        DROP TRIGGER IF EXISTS trg_aprovacoes_centavos_update;

        CREATE TRIGGER trg_aprovacoes_valor_insert
        AFTER INSERT ON aprovacoes
        BEGIN
            UPDATE aprovacoes
               SET valor_centavos = CASE
                       WHEN COALESCE(NEW.valor_centavos, 0) = 0
                            AND ABS(COALESCE(NEW.valor, 0)) > 0
                         THEN ROUND(COALESCE(NEW.valor, 0) * 100)
                       ELSE COALESCE(NEW.valor_centavos, 0)
                   END,
                   valor = CASE
                       WHEN COALESCE(NEW.valor_centavos, 0) != 0
                         THEN NEW.valor_centavos / 100.0
                       ELSE COALESCE(NEW.valor, 0)
                   END
             WHERE id = NEW.id;
        END;

        CREATE TRIGGER trg_aprovacoes_valor_update
        AFTER UPDATE OF valor ON aprovacoes
        WHEN ROUND(COALESCE(NEW.valor, 0) * 100) != COALESCE(NEW.valor_centavos, 0)
        BEGIN
            UPDATE aprovacoes
               SET valor_centavos = ROUND(COALESCE(NEW.valor, 0) * 100)
             WHERE id = NEW.id;
        END;

        CREATE TRIGGER trg_aprovacoes_centavos_update
        AFTER UPDATE OF valor_centavos ON aprovacoes
        WHEN ABS(COALESCE(NEW.valor, 0) - (COALESCE(NEW.valor_centavos, 0) / 100.0)) > 0.000001
        BEGIN
            UPDATE aprovacoes
               SET valor = COALESCE(NEW.valor_centavos, 0) / 100.0
             WHERE id = NEW.id;
        END;
        """
    )
