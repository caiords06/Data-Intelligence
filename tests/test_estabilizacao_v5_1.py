from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from auth import banco
from auth.autenticacao import (
    criar_admin_inicial,
    criar_usuario,
    definir_perfil_acesso_usuario,
)
from auth.sessao import SESSAO
from enterprise.banco import inicializar_enterprise
from enterprise.contexto import (
    aplicar_perfil_padrao_usuario,
    obter_contexto,
    salvar_permissoes_usuario,
    tem_permissao,
)
from enterprise.perfis_acesso import PERFIS_ACESSO, obter_permissoes_perfil
from interface.componentes import ITENS_NAVEGACAO


class EstabilizacaoV51Tests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()

    def _ambiente(self):
        temporario = tempfile.TemporaryDirectory()
        pasta = Path(temporario.name)
        patch_db = patch.object(banco, "DB_PATH", pasta / "teste.db")
        patch_storage = patch.object(banco, "STORAGE_DIR", pasta)
        patch_db.start()
        patch_storage.start()
        self.addCleanup(patch_db.stop)
        self.addCleanup(patch_storage.stop)
        self.addCleanup(temporario.cleanup)
        banco.inicializar_banco()
        admin = criar_admin_inicial("Administrador", "admin", "SenhaAdmin#123")
        SESSAO.iniciar(admin)
        inicializar_enterprise()
        obter_contexto()
        return admin

    def _usuario(self, admin, login, perfil):
        usuario = criar_usuario(
            login.replace("_", " ").title(),
            login,
            "SenhaUsuario#123",
            ator=admin,
            perfil_acesso=perfil,
        )
        aplicar_perfil_padrao_usuario(usuario["id"], perfil, admin)
        return usuario

    def test_sidebar_nao_expoe_atalhos_da_central_e_nova_analise(self):
        chaves = {item[0] for item in ITENS_NAVEGACAO}
        self.assertIn("modulos", chaves)
        self.assertNotIn("analytics", chaves)
        self.assertNotIn("nova", chaves)

    def test_banco_v5_recebe_perfil_sem_perder_usuario_existente(self):
        with tempfile.TemporaryDirectory() as pasta_nome:
            pasta = Path(pasta_nome)
            caminho = pasta / "legado.db"
            with closing(sqlite3.connect(caminho)) as conexao, conexao:
                conexao.execute(
                    """
                    CREATE TABLE usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL,
                        usuario TEXT NOT NULL UNIQUE,
                        senha_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        perfil TEXT NOT NULL,
                        ativo INTEGER NOT NULL DEFAULT 1,
                        criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        ultimo_login TEXT
                    )
                    """
                )
                conexao.execute(
                    """
                    INSERT INTO usuarios (
                        nome, usuario, senha_hash, salt, perfil
                    ) VALUES ('Administrador', 'admin', 'hash', 'salt', 'admin')
                    """
                )
            with patch.object(banco, "DB_PATH", caminho), patch.object(
                banco, "STORAGE_DIR", pasta
            ):
                banco.inicializar_banco()
                usuario = banco.buscar_usuario("admin")
            self.assertEqual(usuario["perfil_acesso"], "administrador")

    def test_upgrade_preserva_acesso_analitico_existente_na_v5(self):
        admin = self._ambiente()
        usuario = criar_usuario(
            "Analista legado",
            "analista_legado",
            "SenhaUsuario#123",
            ator=admin,
        )
        empresa_id = SESSAO.empresa_id
        with banco.conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO permissoes_modulos (
                    usuario_id, empresa_id, modulo,
                    pode_ler, pode_escrever, pode_aprovar
                ) VALUES (?, ?, 'analytics', 0, 0, 0)
                """,
                (usuario["id"], empresa_id),
            )
            conexao.execute(
                "DELETE FROM migracoes_sistema "
                "WHERE chave = 'v5_1_perfis_departamentais'"
            )
        inicializar_enterprise()
        self.assertTrue(tem_permissao(usuario, "analytics", "ler"))
        self.assertTrue(tem_permissao(usuario, "analytics", "escrever"))

    def test_perfis_cobrem_departamentos_e_combinacoes_plus(self):
        esperados = {
            "rh", "financeiro", "estoque", "compras", "ti",
            "marketing", "administrativo", "juridico", "comercial",
        }
        self.assertTrue(esperados.issubset(PERFIS_ACESSO))
        self.assertTrue({f"{perfil}_plus" for perfil in esperados}.issubset(PERFIS_ACESSO))

    def test_perfis_base_nao_recebem_modulos_extras_ou_aprovacao(self):
        for perfil in (
            "rh", "financeiro", "estoque", "compras", "ti", "marketing",
            "administrativo", "juridico", "comercial",
        ):
            with self.subTest(perfil=perfil):
                permissoes = obter_permissoes_perfil(perfil)
                acessiveis = {
                    modulo
                    for modulo, valores in permissoes.items()
                    if valores["ler"]
                }
                self.assertEqual(acessiveis, {perfil})
                self.assertFalse(
                    any(valores["aprovar"] for valores in permissoes.values())
                )

    def test_rh_e_rh_plus_possuem_acessos_adaptativos(self):
        admin = self._ambiente()
        rh = self._usuario(admin, "usuario_rh", "rh")
        rh_plus = self._usuario(admin, "usuario_rh_plus", "rh_plus")

        self.assertFalse(tem_permissao(rh, "analytics", "ler"))
        self.assertTrue(tem_permissao(rh, "rh", "escrever"))
        self.assertFalse(tem_permissao(rh, "financeiro", "ler"))
        self.assertTrue(tem_permissao(rh_plus, "rh", "ler"))
        self.assertTrue(tem_permissao(rh_plus, "financeiro", "escrever"))

    def test_estoque_plus_e_marketing_plus_somam_modulos_relacionados(self):
        admin = self._ambiente()
        estoque = self._usuario(admin, "usuario_estoque", "estoque")
        estoque_plus = self._usuario(
            admin, "usuario_estoque_plus", "estoque_plus"
        )
        marketing_plus = self._usuario(
            admin, "usuario_marketing_plus", "marketing_plus"
        )

        self.assertFalse(tem_permissao(estoque, "compras", "ler"))
        self.assertTrue(tem_permissao(estoque_plus, "compras", "escrever"))
        self.assertTrue(tem_permissao(marketing_plus, "marketing", "ler"))
        self.assertTrue(tem_permissao(marketing_plus, "comercial", "ler"))
        self.assertFalse(tem_permissao(marketing_plus, "financeiro", "ler"))

    def test_perfil_pode_ser_trocado_e_depois_personalizado(self):
        admin = self._ambiente()
        usuario = self._usuario(admin, "usuario_ti", "ti")

        definir_perfil_acesso_usuario(
            usuario["id"], "ti_plus", ator=admin
        )
        usuario["perfil_acesso"] = "ti_plus"
        aplicar_perfil_padrao_usuario(usuario["id"], "ti_plus", admin)
        self.assertTrue(tem_permissao(usuario, "administrativo", "ler"))

        salvar_permissoes_usuario(
            usuario["id"],
            {"ti": {"ler": True, "escrever": False, "aprovar": False}},
            admin,
        )
        self.assertTrue(tem_permissao(usuario, "ti", "ler"))
        self.assertFalse(tem_permissao(usuario, "ti", "escrever"))
        self.assertTrue(tem_permissao(usuario, "administrativo", "ler"))

    def test_perfil_invalido_falha_de_forma_fechada(self):
        admin = self._ambiente()
        usuario = criar_usuario(
            "Usuário seguro",
            "usuario_seguro",
            "SenhaUsuario#123",
            ator=admin,
        )
        usuario["perfil_acesso"] = "perfil_inexistente"
        self.assertFalse(tem_permissao(usuario, "financeiro", "ler"))
        self.assertFalse(tem_permissao(usuario, "analytics", "ler"))


if __name__ == "__main__":
    unittest.main()
