"""Interface de linha de comando do agente de TI."""

from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import sys

from agente_ti import VERSAO_AGENTE
from agente_ti.collector import coletar_payload
from agente_ti.config import (
    caminho_config_padrao,
    caminho_segredo_padrao,
    carregar_configuracao,
    criar_configuracao,
    salvar_configuracao,
)
from agente_ti.credentials import VARIAVEL_TOKEN, carregar_token, salvar_token
from agente_ti.runtime import AgentRuntime, executar_uma_vez
from agente_ti.windows import (
    consultar_tarefa,
    executavel_atual,
    instalar_tarefa,
    proteger_diretorio,
    remover_tarefa,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="DataIntelligenceTIAgent",
        description="Agente autorizado de inventário e telemetria do módulo Tecnologia.",
    )
    parser.add_argument("--version", action="version", version=VERSAO_AGENTE)
    sub = parser.add_subparsers(dest="comando", required=True)

    configurar = sub.add_parser("configure", help="Cria configuração e protege a credencial.")
    configurar.add_argument("--server-url", required=True)
    configurar.add_argument("--patrimonio", required=True)
    configurar.add_argument("--agent-id", required=True, help="ID fornecido pela Central de Tecnologia.")
    configurar.add_argument("--interval", type=int, default=60)
    configurar.add_argument("--timeout", type=int, default=15)
    configurar.add_argument("--provider", choices=("AnyDesk", "TeamViewer", "RustDesk"))
    configurar.add_argument("--provider-executable")
    configurar.add_argument("--ca-bundle")
    configurar.add_argument("--allow-private-http", action="store_true", help="Permite HTTP somente para IP privado em laboratório LAN.")
    configurar.add_argument("--config", type=Path, default=caminho_config_padrao())

    for nome, ajuda in (
        ("collect", "Mostra os dados locais sem realizar envio."),
        ("once", "Executa somente um heartbeat."),
        ("run", "Mantém o agente enviando heartbeats."),
    ):
        comando = sub.add_parser(nome, help=ajuda)
        comando.add_argument("--config", type=Path, default=caminho_config_padrao())
        if nome == "once":
            comando.add_argument("--dry-run", action="store_true")

    instalar = sub.add_parser("install", help="Instala o executável no Agendador do Windows.")
    instalar.add_argument("--config", type=Path, default=caminho_config_padrao())
    instalar.add_argument("--executable", type=Path)
    sub.add_parser("uninstall", help="Remove a tarefa de inicialização automática.")
    sub.add_parser("task-status", help="Consulta o estado da tarefa do Windows.")
    return parser


def _configurar(args) -> int:
    config = criar_configuracao(
        args.server_url,
        args.patrimonio,
        intervalo_segundos=args.interval,
        timeout_segundos=args.timeout,
        ca_bundle=args.ca_bundle,
        provedor_remoto=args.provider,
        executavel_remoto=args.provider_executable,
        agent_id=args.agent_id,
        permitir_http_privado=args.allow_private_http,
    )
    token = os.environ.get(VARIAVEL_TOKEN, "").strip()
    if not token:
        token = getpass.getpass("Token de provisionamento do agente: ").strip()
    if len(token) < 24:
        raise ValueError("O token precisa possuir pelo menos 24 caracteres.")
    destino = salvar_configuracao(config, args.config)
    if os.name == "nt":
        salvar_token(token, caminho_segredo_padrao(destino))
        proteger_diretorio(destino.parent)
    elif not os.environ.get(VARIAVEL_TOKEN):
        raise OSError(f"Neste sistema, defina {VARIAVEL_TOKEN} antes da configuração.")
    print(f"Configuração criada em: {destino}")
    print(f"Agent ID: {config.agent_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.comando == "configure":
            return _configurar(args)
        if args.comando == "uninstall":
            remover_tarefa()
            print("Agente removido da inicialização automática.")
            return 0
        if args.comando == "task-status":
            print(consultar_tarefa())
            return 0

        config = carregar_configuracao(args.config)
        if args.comando == "collect":
            print(json.dumps(coletar_payload(config), ensure_ascii=False, indent=2))
            return 0
        if args.comando == "install":
            executavel = args.executable or executavel_atual()
            proteger_diretorio(args.config.parent)
            instalar_tarefa(executavel, args.config)
            print("Agente instalado para iniciar com o Windows.")
            return 0

        if args.comando == "once":
            token = None
            if not args.dry_run:
                token = carregar_token(caminho_segredo_padrao(args.config))
            payload, resposta = executar_uma_vez(config, token=token, dry_run=args.dry_run)
            if args.dry_run:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"Heartbeat confirmado: HTTP {resposta.status}, {resposta.latencia_ms} ms")
            return 0
        if args.comando == "run":
            token = carregar_token(caminho_segredo_padrao(args.config))
            AgentRuntime(config, token, args.config.parent).executar()
            return 0
    except (ValueError, FileNotFoundError, PermissionError, OSError, RuntimeError) as erro:
        print(f"[ERRO] {erro}", file=sys.stderr)
        return 1
    return 2
