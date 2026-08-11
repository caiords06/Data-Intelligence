"""CLI do Servidor Corporativo."""

from __future__ import annotations

import argparse
import getpass
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

# O diretório precisa ser definido antes de importar auth.banco.
from servidor_corporativo.config import carregar_config, pasta_servidor

os.environ.setdefault("DATA_INTELLIGENCE_DATA_DIR", str(pasta_servidor()))
os.environ.setdefault("DATA_INTELLIGENCE_NODE_ROLE", "servidor")

from auth.banco import inicializar_banco, tem_usuarios
from auth.autenticacao import criar_admin_inicial
from enterprise import inicializar_enterprise
from servidor_corporativo.app import criar_servidor


def _inicializar() -> None:
    inicializar_banco(); inicializar_enterprise()


def _logger() -> None:
    p=pasta_servidor(); p.mkdir(parents=True,exist_ok=True)
    h=RotatingFileHandler(p/"server.log",maxBytes=5*1024*1024,backupCount=5,encoding="utf-8")
    logging.basicConfig(level=logging.INFO,handlers=[h,logging.StreamHandler()],format="%(asctime)s %(levelname)s %(message)s")


def cmd_init(_args) -> int:
    _inicializar()
    if tem_usuarios():
        print("O servidor já possui usuários; bootstrap inicial não será repetido.")
        return 0
    nome=input("Nome do administrador: ").strip()
    usuario=input("Login do administrador: ").strip()
    email=input("E-mail corporativo: ").strip()
    senha=getpass.getpass("Senha: "); confirmar=getpass.getpass("Confirmar senha: ")
    if senha != confirmar:
        print("As senhas não coincidem.",file=sys.stderr); return 2
    criado=criar_admin_inicial(nome,usuario,senha,email or None)
    print(f"Administrador criado: {criado['usuario']} / {criado['email_corporativo']}")
    return 0


def cmd_run(_args) -> int:
    _logger(); _inicializar()
    if not tem_usuarios():
        print("Servidor sem administrador. Execute primeiro: DataIntelligenceServer.exe init-admin",file=sys.stderr); return 3
    cfg=carregar_config(); srv=criar_servidor(cfg)
    esquema="https" if cfg.tls else "http"
    print(f"Servidor corporativo ativo em {esquema}://{cfg.host}:{cfg.porta}")
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    finally: srv.server_close()
    return 0


def main() -> int:
    parser=argparse.ArgumentParser(prog="DataIntelligenceServer")
    sub=parser.add_subparsers(dest="cmd",required=True)
    sub.add_parser("init-admin").set_defaults(fn=cmd_init)
    sub.add_parser("run").set_defaults(fn=cmd_run)
    args=parser.parse_args(); return int(args.fn(args))


if __name__ == "__main__": raise SystemExit(main())
