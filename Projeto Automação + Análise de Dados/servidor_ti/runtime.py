"""Ciclo de vida do servidor TI embutido no aplicativo desktop."""

from __future__ import annotations

import atexit
import logging
import threading
import time

from auth import banco
from servidor_ti.app import criar_servidor
from servidor_ti.config import carregar_config, url_lan_sugerida
from core.ciclo_vida import aguardar_thread, encerrar_servidor, iniciar_servidor_em_thread
from core.observabilidade import configurar_logger_rotativo

_LOCK = threading.RLock()
_SERVIDOR = None
_THREAD = None
_MONITOR = None
_PARAR = threading.Event()
_ERRO = None


def _logger():
    return configurar_logger_rotativo(
        "data_intelligence.ti_server",
        banco.STORAGE_DIR / "ti-server.log",
        max_bytes=2 * 1024 * 1024,
        backups=4,
    )


def _monitorar_offline():
    while not _PARAR.wait(30):
        try:
            with banco.conectar() as conexao:
                linhas = conexao.execute(
                    """SELECT id,ativo_id FROM ti_agentes
                       WHERE ativo=1 AND status='Online' AND ultimo_heartbeat IS NOT NULL
                         AND datetime(ultimo_heartbeat) < datetime('now','-180 seconds')"""
                ).fetchall()
                for linha in linhas:
                    conexao.execute(
                        "UPDATE ti_agentes SET status='Degradado',atualizado_em=CURRENT_TIMESTAMP WHERE id=?",
                        (int(linha["id"]),),
                    )
                    conexao.execute(
                        """UPDATE ti_ativos SET estado_conectividade='Offline',atualizado_em=CURRENT_TIMESTAMP
                           WHERE id=? AND ativo=1 AND estado_conectividade!='Em manutenção'""",
                        (int(linha["ativo_id"]),),
                    )
        except Exception:
            _logger().exception("Falha ao atualizar estado de agentes expirados")


def iniciar_servidor_embutido() -> dict:
    global _SERVIDOR, _THREAD, _MONITOR, _ERRO
    with _LOCK:
        if _SERVIDOR is not None:
            return status_servidor()
        config = carregar_config()
        if not config.habilitado:
            return {"ativo": False, "habilitado": False, "url": None, "erro": None}
        try:
            servidor = criar_servidor(config)
        except Exception as erro:
            _ERRO = str(erro)
            _logger().exception("Servidor TI não pôde ser iniciado")
            return status_servidor()
        _SERVIDOR = servidor
        _PARAR.clear()
        _THREAD = iniciar_servidor_em_thread(servidor, nome="TI-Agent-API", daemon=True)
        _MONITOR = threading.Thread(target=_monitorar_offline, name="TI-Agent-Offline-Monitor", daemon=True)
        _MONITOR.start()
        _ERRO = None
        _logger().info("Servidor TI iniciado em %s", url_lan_sugerida(config))
        return status_servidor()


def parar_servidor_embutido() -> None:
    global _SERVIDOR, _THREAD, _MONITOR
    with _LOCK:
        _PARAR.set()
        servidor = _SERVIDOR
        _SERVIDOR = None
        thread = _THREAD
        monitor = _MONITOR
        if servidor is not None:
            try:
                encerrar_servidor(servidor, thread, timeout=3.0)
            except OSError:
                pass
        aguardar_thread(monitor, timeout=3.0)
        _THREAD = None
        _MONITOR = None


def status_servidor() -> dict:
    config = carregar_config()
    metricas = None
    if _SERVIDOR is not None and getattr(_SERVIDOR, "observabilidade", None) is not None:
        metricas = _SERVIDOR.observabilidade.snapshot()
    return {
        "ativo": bool(_SERVIDOR is not None and _THREAD is not None and _THREAD.is_alive()),
        "habilitado": bool(config.habilitado),
        "url": url_lan_sugerida(config) if config.habilitado else None,
        "tls": bool(config.tls),
        "porta": int(config.porta),
        "erro": _ERRO,
        "observabilidade": metricas,
    }


atexit.register(parar_servidor_embutido)
