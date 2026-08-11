"""Regressões da reestruturação corporativa V9.

Cobre isolamento de filial, aprovações, backup completo, sessão, servidor
corporativo e garantias da nova camada visual/tabular.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import zipfile

from auth import banco
from auth.autenticacao import criar_admin_inicial, criar_usuario
from auth.sessao import SESSAO
from dados.leitor import LIMITE_ARQUIVO_LOCAL_BYTES, validar_arquivo
from enterprise.banco import inicializar_enterprise
from enterprise.backups import criar_backup, verificar_backup
from enterprise.contexto import garantir_contexto_sessao, obter_contexto, salvar_permissoes_usuario
from enterprise.financeiro import criar_conta, criar_lancamento, decidir_aprovacao, listar_aprovacoes_financeiras
from enterprise.compras import criar_solicitacao, enviar_solicitacao
from enterprise.central import decidir_aprovacao as decidir_aprovacao_central
from enterprise.recursos import criar_recurso, listar_recursos
from enterprise.rh import abrir_folha, fechar_folha
from interface.tema import adicionar_divisorias_treeview
from servidor_corporativo.app import CorporateRequestHandler, CorporateServer
from servidor_corporativo.config import ConfigServidor
from servidor_corporativo import sessoes as sessoes_servidor


class VNextEstabilizacaoTests(unittest.TestCase):
    def tearDown(self):
        SESSAO.encerrar()
        sessoes_servidor._SESSOES.clear()

    def _ambiente(self):
        temporario = tempfile.TemporaryDirectory()
        pasta = Path(temporario.name)
        patch_db = patch.object(banco, "DB_PATH", pasta / "app.db")
        patch_storage = patch.object(banco, "STORAGE_DIR", pasta / "storage")
        patch_db.start(); patch_storage.start()
        self.addCleanup(patch_db.stop); self.addCleanup(patch_storage.stop)
        self.addCleanup(temporario.cleanup)
        banco.inicializar_banco()
        admin = criar_admin_inicial(
            "Administrador", "admin", "SenhaAdmin#123",
            email_corporativo="admin@empresa.local",
        )
        SESSAO.iniciar(admin)
        inicializar_enterprise()
        contexto = obter_contexto()
        return admin, pasta, contexto

    @staticmethod
    def _ator(admin, empresa_id, filial_id):
        return {**admin, "_empresa_id": int(empresa_id), "_filial_id": filial_id}

    def test_recursos_em_contexto_corporativo_enxergam_todas_as_filiais(self):
        admin, _, ctx = self._ambiente()
        empresa = ctx["empresa_id"]
        filial_a = ctx["filial_id"]
        with banco.conectar() as con:
            filial_b = int(con.execute(
                "INSERT INTO filiais (empresa_id,nome,codigo) VALUES (?,?,?)",
                (empresa, "Filial B", "FB"),
            ).lastrowid)
        criar_recurso("marketing", "campanhas", {"identificacao":"Campanha A"}, self._ator(admin, empresa, filial_a))
        criar_recurso("marketing", "campanhas", {"identificacao":"Campanha B"}, self._ator(admin, empresa, filial_b))
        corp = self._ator(admin, empresa, None)
        itens = listar_recursos("marketing", "campanhas", corp, tamanho=50)["registros"]
        self.assertEqual({x["identificacao"] for x in itens}, {"Campanha A", "Campanha B"})

    def test_rh_nao_fecha_folha_de_outra_filial(self):
        admin, _, ctx = self._ambiente()
        empresa = ctx["empresa_id"]
        filial_a = ctx["filial_id"]
        with banco.conectar() as con:
            filial_b = int(con.execute(
                "INSERT INTO filiais (empresa_id,nome,codigo) VALUES (?,?,?)",
                (empresa, "Filial B", "FB"),
            ).lastrowid)

        folha_b = abrir_folha("2026-08", self._ator(admin, empresa, filial_b))
        SESSAO.definir_contexto_empresarial(empresa, filial_a)
        usuario = criar_usuario(
            "Diretora RH", "rh.a", "SenhaRh#123", perfil_acesso="rh_diretoria", ator=admin,
            email_corporativo="rh.a@empresa.local",
        )
        salvar_permissoes_usuario(
            usuario["id"],
            {"rh": {"ler": True, "escrever": True, "aprovar": True}},
            admin,
        )
        # salvar_permissoes incrementa epoch; recupera a versão atual para o ator congelado.
        with banco.conectar() as con:
            epoch = int(con.execute("SELECT sessao_epoch FROM usuarios WHERE id=?", (usuario["id"],)).fetchone()["sessao_epoch"])
        ator_a = {**usuario, "sessao_epoch": epoch, "_empresa_id": empresa, "_filial_id": filial_a}
        with self.assertRaises(ValueError):
            fechar_folha(folha_b, ator_a)
        with banco.conectar() as con:
            status = con.execute("SELECT status FROM rh_folhas WHERE id=?", (folha_b,)).fetchone()["status"]
        self.assertEqual(status, "Aberta")

    def test_alcada_financeira_exige_perfil_mesmo_com_permissao_generica(self):
        admin, _, ctx = self._ambiente()
        conta = criar_conta({"nome":"Conta Principal","saldo_inicial":"100000"}, admin)
        lancamento = criar_lancamento({
            "natureza":"Conta a pagar", "descricao":"Contrato estratégico",
            "valor":"12000", "competencia":"2026-08-01", "vencimento":"2026-08-20",
            "conta_id": conta,
        }, admin)[0]
        etapas = listar_aprovacoes_financeiras(admin, status="Pendente")
        self.assertTrue(etapas)
        usuario = criar_usuario(
            "Aprovador genérico", "aprov.gen", "SenhaAprov#123", perfil_acesso="analista", ator=admin,
            email_corporativo="aprov.gen@empresa.local",
        )
        salvar_permissoes_usuario(usuario["id"], {"financeiro":{"ler":True,"escrever":True,"aprovar":True}}, admin)
        with banco.conectar() as con:
            epoch=int(con.execute("SELECT sessao_epoch FROM usuarios WHERE id=?",(usuario["id"],)).fetchone()["sessao_epoch"])
        ator={**usuario,"sessao_epoch":epoch,"_empresa_id":ctx["empresa_id"],"_filial_id":ctx["filial_id"]}
        with self.assertRaises(PermissionError):
            decidir_aprovacao(lancamento, "Aprovado", "Tentativa fora da alçada", ator)

    def test_compras_executa_multiplas_alcadas_e_central_permanece_sincronizada(self):
        admin, _, _ = self._ambiente()
        solicitacao = criar_solicitacao(
            {
                "titulo": "Infraestrutura corporativa",
                "justificativa": "Aquisição acima da alçada executiva",
                "prioridade": "Alta",
            },
            [{
                "descricao": "Infraestrutura",
                "quantidade": 1,
                "valor_estimado_unitario": "60000,00",
            }],
            admin,
        )
        aprovacao_central = enviar_solicitacao(solicitacao, admin)
        with banco.conectar() as con:
            etapas = con.execute(
                "SELECT ordem,perfil_aprovador,status FROM cmp_aprovacoes_solicitacao WHERE solicitacao_id=? ORDER BY ordem",
                (solicitacao,),
            ).fetchall()
        self.assertEqual([x["perfil_aprovador"] for x in etapas], ["Gestor", "Financeiro", "Diretoria"])

        decidir_aprovacao_central(aprovacao_central, "Aprovado", "Gestor aprovou", admin)
        with banco.conectar() as con:
            central = con.execute("SELECT status FROM aprovacoes WHERE id=?", (aprovacao_central,)).fetchone()["status"]
            recurso = con.execute("SELECT status FROM cmp_solicitacoes WHERE id=?", (solicitacao,)).fetchone()["status"]
        self.assertEqual((central, recurso), ("Pendente", "Aguardando aprovação"))

        decidir_aprovacao_central(aprovacao_central, "Aprovado", "Financeiro aprovou", admin)
        decidir_aprovacao_central(aprovacao_central, "Aprovado", "Diretoria aprovou", admin)
        with banco.conectar() as con:
            central = con.execute("SELECT status FROM aprovacoes WHERE id=?", (aprovacao_central,)).fetchone()["status"]
            recurso = con.execute("SELECT status FROM cmp_solicitacoes WHERE id=?", (solicitacao,)).fetchone()["status"]
            pendentes = con.execute(
                "SELECT COUNT(*) n FROM cmp_aprovacoes_solicitacao WHERE solicitacao_id=? AND status='Pendente'",
                (solicitacao,),
            ).fetchone()["n"]
        self.assertEqual((central, recurso, int(pendentes)), ("Aprovado", "Aprovada", 0))

    def test_backup_completo_inclui_arquivo_persistido_e_manifesto(self):
        admin, pasta, _ = self._ambiente()
        documento = banco.STORAGE_DIR / "documentos" / "manual.txt"
        documento.parent.mkdir(parents=True, exist_ok=True)
        documento.write_text("conteúdo corporativo", encoding="utf-8")
        resultado = criar_backup(admin, pasta / "saida", sincronizar_servidor=False)
        arquivo = Path(resultado["arquivo"])
        validacao = verificar_backup(arquivo, resultado["hash_sha256"])
        self.assertTrue(validacao["integro"] and validacao["hash_valido"])
        with zipfile.ZipFile(arquivo) as zf:
            nomes = set(zf.namelist())
            self.assertIn("database/app.db", nomes)
            self.assertIn("storage/documentos/manual.txt", nomes)
            manifesto = json.loads(zf.read("manifest.json"))
            self.assertEqual(manifesto["versao"], 2)

    def test_sessao_epoch_revoga_sessao_em_memoria(self):
        admin, _, _ = self._ambiente()
        banco.revogar_sessoes_usuario(admin["id"])
        with self.assertRaises(PermissionError):
            garantir_contexto_sessao()
        self.assertFalse(SESSAO.autenticado())

    def test_importacao_local_rejeita_arquivo_acima_de_100mb_antes_do_pandas(self):
        _, pasta, _ = self._ambiente()
        grande = pasta / "gigante.csv"
        with grande.open("wb") as f:
            f.seek(LIMITE_ARQUIVO_LOCAL_BYTES)
            f.write(b"0")
        with self.assertRaisesRegex(ValueError, "excede o limite de 100 MB"):
            validar_arquivo(grande)

    def test_central_de_aprovacoes_mantem_valor_real_e_centavos_consistentes(self):
        admin, _, ctx = self._ambiente()
        with banco.conectar() as con:
            rid = int(con.execute(
                """INSERT INTO aprovacoes
                   (empresa_id,filial_id,solicitante_id,modulo,recurso_tipo,recurso_id,titulo,valor,status)
                   VALUES (?,?,?,?,?,?,?,?, 'Pendente')""",
                (ctx["empresa_id"],ctx["filial_id"],admin["id"],"financeiro","teste",1,"Teste",123.45),
            ).lastrowid)
            row=con.execute("SELECT valor,valor_centavos FROM aprovacoes WHERE id=?",(rid,)).fetchone()
            self.assertEqual(int(row["valor_centavos"]),12345)
            con.execute("UPDATE aprovacoes SET valor_centavos=9876 WHERE id=?",(rid,))
            row=con.execute("SELECT valor,valor_centavos FROM aprovacoes WHERE id=?",(rid,)).fetchone()
            self.assertAlmostEqual(float(row["valor"]),98.76,places=2)

    def test_servidor_corporativo_login_arquivo_exclusao_e_revogacao(self):
        admin, pasta, _ = self._ambiente()
        cfg = ConfigServidor(host="127.0.0.1", porta=8770, tls=False, max_upload_mb=20)
        srv = CorporateServer(("127.0.0.1", 0), CorporateRequestHandler, cfg)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(srv.server_close)
        self.addCleanup(srv.shutdown)
        base=f"http://127.0.0.1:{srv.server_address[1]}"

        def req(path, method="GET", data=None, token=None, headers=None):
            corpo = None
            cab={"Accept":"application/json"}
            if data is not None:
                corpo=json.dumps(data).encode("utf-8"); cab["Content-Type"]="application/json"
            if token: cab["Authorization"]=f"Bearer {token}"
            if headers: cab.update(headers)
            r=urllib.request.Request(base+path,data=corpo,headers=cab,method=method)
            with urllib.request.urlopen(r,timeout=5) as resp:
                raw=resp.read(); return json.loads(raw) if "json" in str(resp.headers.get("Content-Type")) else raw

        login=req("/api/v1/auth/login","POST",{"usuario":"admin","senha":"SenhaAdmin#123"})
        token=login["token"]
        self.assertEqual(login["usuario"]["email_corporativo"],"admin@empresa.local")
        payload=b"relatorio corporativo"
        sha=__import__("hashlib").sha256(payload).hexdigest()
        r=urllib.request.Request(base+"/api/v1/files",data=payload,headers={
            "Authorization":f"Bearer {token}","Content-Type":"application/octet-stream",
            "X-File-Name":"relatorio.txt","X-Module":"financeiro","X-Category":"exportacao","X-SHA256":sha,
        },method="POST")
        with urllib.request.urlopen(r,timeout=5) as resp:
            criado=json.loads(resp.read())
        itens=req("/api/v1/files",token=token)["itens"]
        self.assertEqual(len(itens),1)
        req(f"/api/v1/files/{criado['id']}","DELETE",token=token)
        self.assertEqual(req("/api/v1/files",token=token)["itens"],[])

        # Mudança de senha revoga o bearer por sessao_epoch.
        req("/api/v1/account/password","PATCH",{"senha_atual":"SenhaAdmin#123","nova_senha":"NovaSenha#456"},token=token)
        with self.assertRaises(urllib.error.HTTPError) as cm:
            req("/api/v1/bootstrap",token=token)
        self.assertEqual(cm.exception.code,401)

    def test_divisorias_treeview_artificiais_foram_desativadas(self):
        # A função permanece por compatibilidade, mas não desenha Frames sobre a Treeview.
        class TabelaFake:
            def configure(self, **_kwargs):
                return None
        callback = adicionar_divisorias_treeview(TabelaFake())
        self.assertTrue(callable(callback))
        callback()


if __name__ == "__main__":
    unittest.main()
