"""Mantém a compatibilidade monetária sem criar duas fontes de verdade."""

from __future__ import annotations


def upgrade(conexao) -> None:
    # ``valor_centavos`` é a fonte canônica. O REAL legado permanece apenas
    # para compatibilidade com relatórios/instalações antigas e é derivado.
    conexao.execute(
        """
        UPDATE aprovacoes
        SET valor_centavos = ROUND(COALESCE(valor, 0) * 100)
        WHERE COALESCE(valor_centavos, 0) = 0 AND COALESCE(valor, 0) <> 0
        """
    )
    conexao.execute(
        "UPDATE aprovacoes SET valor = COALESCE(valor_centavos, 0) / 100.0"
    )
    conexao.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS trg_aprovacoes_valor_insert
        AFTER INSERT ON aprovacoes
        BEGIN
            UPDATE aprovacoes
            SET valor_centavos = CASE
                    WHEN COALESCE(NEW.valor_centavos, 0) = 0
                         AND COALESCE(NEW.valor, 0) <> 0
                    THEN ROUND(NEW.valor * 100)
                    ELSE COALESCE(NEW.valor_centavos, 0)
                END,
                valor = CASE
                    WHEN COALESCE(NEW.valor_centavos, 0) = 0
                         AND COALESCE(NEW.valor, 0) <> 0
                    THEN ROUND(NEW.valor * 100) / 100.0
                    ELSE COALESCE(NEW.valor_centavos, 0) / 100.0
                END
            WHERE id = NEW.id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_aprovacoes_valor_centavos_update
        AFTER UPDATE OF valor_centavos ON aprovacoes
        WHEN NEW.valor IS NOT (NEW.valor_centavos / 100.0)
        BEGIN
            UPDATE aprovacoes
            SET valor = NEW.valor_centavos / 100.0
            WHERE id = NEW.id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_aprovacoes_valor_legado_update
        AFTER UPDATE OF valor ON aprovacoes
        WHEN ROUND(NEW.valor * 100) <> NEW.valor_centavos
        BEGIN
            UPDATE aprovacoes
            SET valor = NEW.valor_centavos / 100.0
            WHERE id = NEW.id;
        END;
        """
    )
