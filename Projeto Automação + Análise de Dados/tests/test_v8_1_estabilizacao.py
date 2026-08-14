"""Regressões de integridade, interface e temporários da V8.1."""

import os
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from dados.fontes import limpar_temporarios_antigos
from enterprise.banco import inicializar_enterprise
from enterprise.datasets import (
    atualizar_metadados_conjunto,
    importar_conjunto,
    obter_conjunto,
    substituir_arquivo_conjunto,
)
from enterprise.organizacao import (
    criar_empresa,
    criar_filial,
    definir_contexto_empresa,
)
from interface.central_analytics import ESQUEMAS_ANALYTICS
from interface.configuracao_modulos_ui import (
    ESQUEMAS_RECURSOS,
    PAINEIS_MODULOS,
)
from interface.navegacao_analytics import MENU_ANALYTICS


class EstabilizacaoV81Tests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()

    def _ambiente(self):
        temporario = tempfile.TemporaryDirectory()
        pasta = Path(temporario.name)
        patch_db = patch.object(banco, "DB_PATH", pasta / "teste.db")
        patch_storage = patch.object(banco, "STORAGE_DIR", pasta / "storage")
        patch_db.start()
        patch_storage.start()
        self.addCleanup(patch_db.stop)
        self.addCleanup(patch_storage.stop)
        self.addCleanup(temporario.cleanup)
        banco.inicializar_banco()
        admin = criar_admin_inicial(
            "Administrador", "admin", "SenhaAdmin#123"
        )
        SESSAO.iniciar(admin)
        inicializar_enterprise()
        return admin, pasta

    def test_usuario_novo_e_vinculado_ao_contexto_atual(self):
        admin, _ = self._ambiente()
        with banco.conectar() as conexao:
            empresa_inicial = conexao.execute(
                "SELECT id FROM empresas ORDER BY id LIMIT 1"
            ).fetchone()["id"]
        segunda = criar_empresa("Empresa Secundária", ator=admin)
        definir_contexto_empresa(segunda)
        filial = criar_filial("Filial Secundária", "SEC", ator=admin)
        definir_contexto_empresa(segunda, filial)

        usuario = criar_usuario(
            "Analista Secundário",
            "analista.sec",
            "SenhaForte#123",
            ator=admin,
            perfil_acesso="analista",
        )
        with banco.conectar() as conexao:
            vinculos = conexao.execute(
                "SELECT empresa_id, filial_id FROM usuarios_empresas "
                "WHERE usuario_id=?",
                (usuario["id"],),
            ).fetchall()
            self.assertEqual(
                [(item["empresa_id"], item["filial_id"]) for item in vinculos],
                [(segunda, filial)],
            )
            with self.assertRaises(sqlite3.IntegrityError):
                conexao.execute(
                    "UPDATE usuarios_empresas SET empresa_id=? "
                    "WHERE usuario_id=? AND empresa_id=?",
                    (empresa_inicial, usuario["id"], segunda),
                )

    def test_limpeza_remove_apenas_temporarios_gerenciados_antigos(self):
        _admin, pasta = self._ambiente()
        temporarios = banco.STORAGE_DIR / "importacoes_temp"
        temporarios.mkdir(parents=True, exist_ok=True)
        antigo = temporarios / "fonte_antiga.csv"
        recente = temporarios / "sqlite_recente.csv"
        usuario = temporarios / "arquivo_do_usuario.csv"
        fora = pasta / "fonte_fora.csv"
        for arquivo in (antigo, recente, usuario, fora):
            arquivo.write_text("a,b\n1,2", encoding="utf-8")
        instante_antigo = time.time() - 48 * 3600
        os.utime(antigo, (instante_antigo, instante_antigo))
        os.utime(usuario, (instante_antigo, instante_antigo))
        os.utime(fora, (instante_antigo, instante_antigo))

        self.assertEqual(limpar_temporarios_antigos(24), 1)
        self.assertFalse(antigo.exists())
        self.assertTrue(recente.exists())
        self.assertTrue(usuario.exists())
        self.assertTrue(fora.exists())

    def test_toda_secao_departamental_tem_formulario_especifico(self):
        faltantes = []
        for modulo, configuracao in PAINEIS_MODULOS.items():
            for secao, _icone, _titulo in configuracao["menu"]:
                # Marketing V10.3 possui formulários/domínio próprios e não usa
                # mais ESQUEMAS_RECURSOS genéricos.
                if modulo == "marketing":
                    continue
                if secao not in {"visao", "registros"} and secao not in ESQUEMAS_RECURSOS:
                    faltantes.append((modulo, secao))
        self.assertEqual(faltantes, [])

    def test_toda_secao_analytics_tem_esquema_ou_fluxo_proprio(self):
        fluxos_proprios = {"visao", "insights", "alertas", "regras", "nova", "importacoes", "conjuntos"}
        faltantes = [
            chave
            for chave, _icone, _titulo in MENU_ANALYTICS
            if chave not in fluxos_proprios and chave not in ESQUEMAS_ANALYTICS
        ]
        self.assertEqual(faltantes, [])

    def test_dataset_permite_metadados_e_substituicao_versionada(self):
        admin, pasta = self._ambiente()
        origem = pasta / "vendas_1.csv"
        origem.write_text("produto,valor\nA,10\n", encoding="utf-8")
        conjunto_id = importar_conjunto(origem, nome="Vendas", ator=admin)
        primeira = obter_conjunto(conjunto_id, admin)
        arquivo_anterior = Path(primeira["caminho"])

        atualizar_metadados_conjunto(
            conjunto_id,
            nome="Vendas mensais",
            descricao="Base validada",
            tags="vendas,mensal",
            ator=admin,
        )
        nova_origem = pasta / "vendas_2.csv"
        nova_origem.write_text(
            "produto,valor\nA,10\nB,20\n", encoding="utf-8"
        )
        substituir_arquivo_conjunto(conjunto_id, nova_origem, admin)
        atualizado = obter_conjunto(conjunto_id, admin)

        self.assertEqual(atualizado["nome"], "Vendas mensais")
        self.assertEqual(atualizado["descricao"], "Base validada")
        self.assertEqual(atualizado["tags"], "vendas,mensal")
        self.assertEqual(atualizado["versao"], 2)
        self.assertEqual(atualizado["total_registros"], 2)
        self.assertFalse(arquivo_anterior.exists())


if __name__ == "__main__":
    unittest.main()
