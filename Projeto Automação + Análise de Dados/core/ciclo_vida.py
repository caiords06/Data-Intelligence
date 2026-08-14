"""Primitivas centralizadas para ciclo de vida de threads e servidores HTTP."""
from __future__ import annotations

import threading
from typing import Any


def iniciar_servidor_em_thread(servidor: Any, *, nome: str, daemon: bool = True) -> threading.Thread:
    """Inicia ``serve_forever`` e registra a thread no próprio servidor."""
    thread = threading.Thread(target=servidor.serve_forever, name=nome, daemon=daemon)
    setattr(servidor, "_di_serve_thread", thread)
    thread.start()
    return thread


def aguardar_thread(thread: threading.Thread | None, timeout: float = 3.0) -> bool:
    if thread is None or thread is threading.current_thread():
        return True
    if thread.is_alive():
        thread.join(max(0.0, float(timeout)))
    return not thread.is_alive()


def encerrar_servidor(servidor: Any, thread: threading.Thread | None = None, *, timeout: float = 3.0) -> bool:
    """Encerra servidor e aguarda a thread de ``serve_forever`` sem vazar recurso."""
    if servidor is None:
        return True
    thread = thread or getattr(servidor, "_di_serve_thread", None)
    try:
        if thread is not None and thread.is_alive():
            servidor.shutdown()
    finally:
        servidor.server_close()
    return aguardar_thread(thread, timeout)
