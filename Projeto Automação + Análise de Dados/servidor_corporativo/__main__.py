"""CLI do Servidor Corporativo V11.1.0."""
from __future__ import annotations

import argparse
from dataclasses import replace
import getpass
import json
import logging
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

from servidor_corporativo.config import (
    ConfigServidor, aplicar_ambiente_banco, carregar_config, carregar_config_parcial,
    caminho_segredo_postgresql, pasta_servidor, salvar_config,
)
from core.observabilidade import configurar_logger_rotativo

def _preparar_ambiente_servidor() -> None:
    """Define o papel somente quando a CLI do servidor realmente é executada.

    Evita efeito colateral de importação: importar ``servidor_corporativo.__main__``
    em testes/ferramentas não pode transformar o processo inteiro em nó servidor.
    No executável real, por outro lado, o papel é imposto (não apenas setdefault)
    para impedir que uma variável herdada faça o serviço operar como estação.
    """
    os.environ["DATA_INTELLIGENCE_DATA_DIR"] = str(pasta_servidor())
    os.environ["DATA_INTELLIGENCE_NODE_ROLE"] = "servidor"


def _ativar_backend() -> ConfigServidor:
    _preparar_ambiente_servidor()
    cfg=carregar_config(); aplicar_ambiente_banco(cfg); return cfg


def _inicializar() -> None:
    _ativar_backend()
    from auth.banco import inicializar_banco
    from enterprise import inicializar_enterprise
    from enterprise.postgresql.bootstrap import validar_schema_runtime
    from servidor_corporativo.rpc import validar_rpc_runtime
    inicializar_banco()
    inicializar_enterprise()
    validar_schema_runtime()
    # Não publique /ready se o executável perdeu qualquer módulo importado
    # dinamicamente pelo RPC. Isso transforma erros tardios de telas em falha
    # explícita de instalação/startup.
    validar_rpc_runtime()


def _logger() -> None:
    p=pasta_servidor(); p.mkdir(parents=True,exist_ok=True)
    configurar_logger_rotativo("data_intelligence.corporate_server", p / "server.log", max_bytes=5*1024*1024, backups=5)
    raiz=logging.getLogger(); raiz.setLevel(logging.INFO)
    if not any(isinstance(h,logging.StreamHandler) and not hasattr(h,"baseFilename") for h in raiz.handlers):
        console=logging.StreamHandler(); console.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s")); raiz.addHandler(console)


def _fechar_pool_cli() -> None:
    """Fecha explicitamente o pool em comandos de vida curta do executável."""
    try:
        from enterprise.postgresql.adapter import fechar_pool
        fechar_pool()
    except Exception:
        logging.getLogger(__name__).exception("Falha ao fechar o pool PostgreSQL da CLI")


def cmd_configure_db(args) -> int:
    try:
        payload={}
        if args.bootstrap_file:
            try: payload=json.loads(Path(args.bootstrap_file).read_text(encoding="utf-8-sig"))
            except (OSError,json.JSONDecodeError) as exc:
                print(f"Configuração de banco inválida: {exc}",file=sys.stderr); return 2
        backend=str(payload.get("backend") or args.backend or "postgresql").strip().lower()
        atual=carregar_config_parcial()
        if backend == "sqlite":
            print(
                "SQLite local está desativado. Configure PostgreSQL; SQLite permanece apenas como origem de migração.",
                file=sys.stderr,
            )
            return 2
        if backend not in {"postgres","postgresql","pg"}:
            print("Backend deve ser postgresql.",file=sys.stderr); return 2
        try:
            host=str(payload.get("host") or args.host or "127.0.0.1").strip()
            porta=int(payload.get("porta") or args.porta or 5432)
            banco=str(payload.get("banco") or args.banco or "dataintelligence").strip()
            usuario=str(payload.get("usuario") or args.usuario or "dataintelligence").strip()
            sslmode=str(payload.get("sslmode") or args.sslmode or "prefer").strip().lower()
            pool_min=int(payload.get("pool_min") or args.pool_min or 2)
            pool_max=int(payload.get("pool_max") or args.pool_max or 12)
            password_file=payload.get("password_file") or args.password_file
            if password_file:
                senha=Path(str(password_file)).read_text(encoding="utf-8-sig").strip("\r\n")
            else:
                senha=os.environ.get("DATA_INTELLIGENCE_PG_PASSWORD","") or getpass.getpass("Senha PostgreSQL: ")
            if not senha: raise ValueError("Senha PostgreSQL vazia.")
            if os.name == "nt":
                from core.segredos import salvar_segredo_maquina
                segredo=caminho_segredo_postgresql()
                salvar_segredo_maquina(senha,segredo,descricao="Data Intelligence PostgreSQL")
                referencia=str(segredo)
            else:
                os.environ["DATA_INTELLIGENCE_PG_PASSWORD"]=senha
                referencia="env:DATA_INTELLIGENCE_PG_PASSWORD"
            server_host=str(payload.get("server_host") or atual.host or "127.0.0.1").strip()
            server_porta=int(payload.get("server_porta") or atual.porta or 8770)
            server_tls=bool(payload.get("server_tls")) if "server_tls" in payload else bool(atual.tls)
            server_max_upload=int(payload.get("server_max_upload_mb") or atual.max_upload_mb or 1024)
            server_ambiente=str(payload.get("server_ambiente") or atual.ambiente or "producao").strip().lower()
            cors_bruto = payload.get("server_cors_origins", atual.cors_origins)
            if isinstance(cors_bruto, str):
                cors_origins = tuple(x.strip() for x in cors_bruto.split(",") if x.strip())
            elif isinstance(cors_bruto, (list, tuple)):
                cors_origins = tuple(str(x).strip() for x in cors_bruto if str(x).strip())
            else:
                raise ValueError("server_cors_origins deve ser lista ou texto separado por vírgulas.")
            cfg=replace(
                atual, host=server_host, porta=server_porta, tls=server_tls,
                max_upload_mb=server_max_upload, ambiente=server_ambiente, cors_origins=cors_origins,
                db_backend="postgresql", postgres_host=host, postgres_porta=porta,
                postgres_banco=banco,postgres_usuario=usuario,postgres_sslmode=sslmode,
                postgres_pool_min=pool_min,postgres_pool_max=pool_max,postgres_segredo=referencia
            ).validar()
            aplicar_ambiente_banco(cfg)
            from enterprise.postgresql.adapter import testar_conexao
            info=testar_conexao()
            salvar_config(cfg)
            from enterprise.postgresql.bootstrap import inicializar_schema_postgresql
            inicializar_schema_postgresql()
            # A ausência dos utilitários de backup não invalida a conexão nem
            # impede o servidor de iniciar (o PostgreSQL pode inclusive ser
            # remoto). O botão de backup exibirá a dependência faltante com
            # diagnóstico específico e /health/details também a reporta.
            from enterprise.backups import validar_dependencias_backup
            try:
                validar_dependencias_backup()
            except RuntimeError as aviso_backup:
                print(f"Aviso: backup PostgreSQL indisponível: {aviso_backup}", file=sys.stderr)
            erro_path=pasta_servidor() / "install-db-error.log"
            try: erro_path.unlink(missing_ok=True)
            except OSError: pass
            print(f"PostgreSQL configurado: {info['banco']}@{host}:{porta} ({info['latencia_ms']} ms)")
            return 0
        except Exception as exc:
            mensagem=f"Falha ao configurar PostgreSQL: {exc}"
            try:
                erro_path=pasta_servidor() / "install-db-error.log"
                erro_path.parent.mkdir(parents=True,exist_ok=True)
                erro_path.write_text(mensagem + "\n",encoding="utf-8")
            except OSError:
                pass
            print(mensagem,file=sys.stderr); return 4
    finally:
        _fechar_pool_cli()

def cmd_check_db(_args) -> int:
    try:
        try:
            cfg=_ativar_backend()
            if cfg.db_backend != "postgresql":
                raise RuntimeError("Servidor configurado com backend não suportado. Migre para PostgreSQL.")
            from enterprise.postgresql.adapter import testar_conexao
            from enterprise.postgresql.bootstrap import health_postgresql
            print(json.dumps({"conexao":testar_conexao(),"health":health_postgresql()},ensure_ascii=False,indent=2,default=str))
            return 0
        except Exception as exc:
            print(f"Banco indisponível: {exc}",file=sys.stderr); return 5
    finally:
        _fechar_pool_cli()



def cmd_migrate_sqlite(args) -> int:
    try:
        cfg=_ativar_backend()
        if cfg.db_backend != "postgresql":
            print("Configure PostgreSQL antes de migrar o SQLite.",file=sys.stderr); return 6
        from enterprise.postgresql.migracao import migrar_sqlite_para_postgresql
        resultado=migrar_sqlite_para_postgresql(args.source,exigir_destino_vazio=not args.permitir_destino_com_dados)
        print(json.dumps(resultado,ensure_ascii=False,indent=2,default=str))
        return 0 if resultado.get("ok") else 7
    except Exception as exc:
        print(f"Falha na migração SQLite -> PostgreSQL: {exc}",file=sys.stderr); return 7

def cmd_init(args) -> int:
    _inicializar()
    from auth.banco import tem_usuarios
    from auth.autenticacao import criar_admin_inicial
    if tem_usuarios():
        print("O servidor já possui usuários; bootstrap inicial não será repetido."); return 0
    bootstrap_file=getattr(args,"bootstrap_file",None)
    if bootstrap_file:
        try:
            payload=json.loads(Path(bootstrap_file).read_text(encoding="utf-8-sig")); nome=str(payload.get("nome") or "").strip(); usuario=str(payload.get("usuario") or "").strip(); email=str(payload.get("email") or "").strip(); password_file=Path(str(payload.get("password_file") or "")); senha=password_file.read_text(encoding="utf-8-sig").strip("\r\n")
        except (OSError,ValueError,TypeError,json.JSONDecodeError) as exc:
            print(f"Bootstrap não interativo inválido: {exc}",file=sys.stderr); return 2
        if not nome or not usuario: print("Nome e usuário são obrigatórios.",file=sys.stderr); return 2
    else:
        nome=str(getattr(args,"nome","") or "").strip() or input("Nome do administrador: ").strip(); usuario=str(getattr(args,"usuario","") or "").strip() or input("Login do administrador: ").strip(); email=str(getattr(args,"email","") or "").strip() or input("E-mail corporativo: ").strip(); password_file=getattr(args,"password_file",None)
        if password_file:
            try: senha=Path(password_file).read_text(encoding="utf-8-sig").strip("\r\n")
            except OSError as exc: print(f"Não foi possível ler a senha: {exc}",file=sys.stderr); return 2
        else:
            senha=getpass.getpass("Senha: "); confirmar=getpass.getpass("Confirmar senha: ")
            if senha!=confirmar: print("As senhas não coincidem.",file=sys.stderr); return 2
    criado=criar_admin_inicial(nome,usuario,senha,email or None); print(f"Administrador criado: {criado['usuario']} / {criado['email_corporativo']}"); return 0


def cmd_run(_args) -> int:
    _logger(); _inicializar()
    from auth.banco import tem_usuarios
    from servidor_corporativo.app import criar_servidor
    if not tem_usuarios(): print("Servidor sem administrador. Execute init-admin.",file=sys.stderr); return 3
    cfg=carregar_config(); aplicar_ambiente_banco(cfg); srv=criar_servidor(cfg); esquema="https" if cfg.tls else "http"
    print(f"Servidor corporativo ativo em {esquema}://{cfg.host}:{cfg.porta} · banco={cfg.db_backend}")
    try: srv.serve_forever()
    except KeyboardInterrupt: pass
    finally:
        srv.server_close()
        if cfg.db_backend=="postgresql":
            try:
                from enterprise.postgresql.adapter import fechar_pool
                fechar_pool()
            except Exception:
                logging.getLogger(__name__).exception("Falha ao fechar o pool PostgreSQL do servidor")
    return 0



def cmd_install_task(args) -> int:
    try:
        from servidor_corporativo.windows import executavel_atual, instalar_tarefa
        exe = Path(args.executable).resolve() if args.executable else executavel_atual()
        instalar_tarefa(exe)
        print("Tarefa do Servidor Corporativo instalada.")
        return 0
    except Exception as exc:
        print(f"Falha ao instalar tarefa do servidor: {exc}", file=sys.stderr)
        return 8


def cmd_start_task(_args) -> int:
    try:
        from servidor_corporativo.windows import iniciar_tarefa
        iniciar_tarefa()
        print("Tarefa do Servidor Corporativo iniciada.")
        return 0
    except Exception as exc:
        print(f"Falha ao iniciar tarefa do servidor: {exc}", file=sys.stderr)
        return 9


def cmd_task_status(_args) -> int:
    try:
        from servidor_corporativo.windows import consultar_tarefa
        print(consultar_tarefa())
        return 0
    except Exception as exc:
        print(f"Falha ao consultar tarefa do servidor: {exc}", file=sys.stderr)
        return 10


def cmd_uninstall_task(_args) -> int:
    try:
        from servidor_corporativo.windows import remover_tarefa
        remover_tarefa(ignorar_ausente=True)
        print("Tarefa do Servidor Corporativo removida.")
        return 0
    except Exception as exc:
        print(f"Falha ao remover tarefa do servidor: {exc}", file=sys.stderr)
        return 11


def cmd_wait_ready(args) -> int:
    cfg = carregar_config()
    host = "127.0.0.1"
    esquema = "https" if cfg.tls else "http"
    url = f"{esquema}://{host}:{cfg.porta}/api/v1/health/ready"
    limite = time.monotonic() + max(1, int(args.timeout))
    ultimo = None
    while time.monotonic() < limite:
        try:
            contexto = None
            if esquema == "https":
                import ssl
                contexto = ssl.create_default_context()
            with urllib.request.urlopen(url, timeout=2, context=contexto) as resposta:
                payload = json.loads(resposta.read().decode("utf-8-sig"))
                if resposta.status == 200 and payload.get("ok") and payload.get("pronto"):
                    print("Servidor Corporativo pronto.")
                    return 0
        except Exception as exc:
            ultimo = exc
        time.sleep(0.5)
    print(f"Servidor não ficou pronto em {args.timeout}s: {ultimo}", file=sys.stderr)
    return 12


def main() -> int:
    parser=argparse.ArgumentParser(prog="DataIntelligenceServer"); sub=parser.add_subparsers(dest="cmd",required=True)
    init=sub.add_parser("init-admin"); init.add_argument("--nome"); init.add_argument("--usuario"); init.add_argument("--email"); init.add_argument("--password-file",type=Path); init.add_argument("--bootstrap-file",type=Path); init.set_defaults(fn=cmd_init)
    db=sub.add_parser("configure-db"); db.add_argument("--backend",default="postgresql"); db.add_argument("--host"); db.add_argument("--porta",type=int); db.add_argument("--banco"); db.add_argument("--usuario"); db.add_argument("--sslmode",default="prefer"); db.add_argument("--pool-min",type=int,default=2); db.add_argument("--pool-max",type=int,default=12); db.add_argument("--password-file",type=Path); db.add_argument("--bootstrap-file",type=Path); db.set_defaults(fn=cmd_configure_db)
    sub.add_parser("check-db").set_defaults(fn=cmd_check_db)
    mig=sub.add_parser("migrate-sqlite"); mig.add_argument("--source",type=Path,required=True); mig.add_argument("--permitir-destino-com-dados",action="store_true"); mig.set_defaults(fn=cmd_migrate_sqlite)
    sub.add_parser("run").set_defaults(fn=cmd_run)
    instalar=sub.add_parser("install-task"); instalar.add_argument("--executable",type=Path); instalar.set_defaults(fn=cmd_install_task)
    sub.add_parser("start-task").set_defaults(fn=cmd_start_task)
    sub.add_parser("task-status").set_defaults(fn=cmd_task_status)
    sub.add_parser("uninstall-task").set_defaults(fn=cmd_uninstall_task)
    pronto=sub.add_parser("wait-ready"); pronto.add_argument("--timeout",type=int,default=30); pronto.set_defaults(fn=cmd_wait_ready)
    args=parser.parse_args()
    try:
        return int(args.fn(args))
    finally:
        # Também cobre init-admin, migrate-sqlite e falhas antecipadas de run.
        # fechar_pool() é idempotente e evita threads do psycopg_pool vivas
        # durante a finalização do interpretador/PyInstaller.
        _fechar_pool_cli()

if __name__ == "__main__": raise SystemExit(main())
