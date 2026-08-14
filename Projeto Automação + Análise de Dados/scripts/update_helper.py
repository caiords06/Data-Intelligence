"""Helper externo que aplica um ZIP verificado e restaura a versão anterior."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.request import urlopen
import zipfile


def _seguro(caminho: Path) -> Path:
    resolvido = caminho.resolve()
    if resolvido == Path(resolvido.anchor) or resolvido == Path.home().resolve() or len(resolvido.parts) < 3:
        raise ValueError(f"Caminho de atualização inseguro: {resolvido}")
    return resolvido


def _filho(raiz: Path, caminho: Path) -> Path:
    destino = _seguro(caminho)
    if destino.parent != raiz.resolve():
        raise ValueError("Diretório transitório saiu da raiz autorizada.")
    return destino


def _health(url: str, timeout: int = 90) -> bool:
    limite = time.monotonic() + max(10, timeout)
    while time.monotonic() < limite:
        try:
            with urlopen(url, timeout=3) as resposta:
                if 200 <= int(resposta.status) < 300:
                    return True
        except OSError:
            pass
        time.sleep(2)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    parser.add_argument("--health-url", required=True)
    parser.add_argument("--start-json", required=True)
    args = parser.parse_args()
    atual = _seguro(args.current); pacote = args.package.resolve()
    comando = json.loads(args.start_json)
    if not pacote.is_file() or not isinstance(comando, list) or not comando:
        raise ValueError("Pacote ou comando de inicialização inválido.")
    raiz = atual.parent
    rollback_raiz = _filho(raiz, raiz / "rollback")
    rollback = _filho(rollback_raiz, rollback_raiz / datetime.now().strftime("%Y%m%d_%H%M%S"))
    staging = _filho(raiz, raiz / f".{atual.name}.staging")
    falha = _filho(raiz, raiz / f".{atual.name}.failed")
    shutil.rmtree(staging, ignore_errors=True); shutil.rmtree(falha, ignore_errors=True)
    staging.mkdir(parents=True)
    with zipfile.ZipFile(pacote) as zf:
        for membro in zf.infolist():
            destino = (staging / membro.filename).resolve()
            if staging not in destino.parents and destino != staging:
                raise ValueError("Pacote contém caminho inseguro.")
            if (membro.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("Pacote contém link simbólico.")
        zf.extractall(staging)
    rollback.parent.mkdir(parents=True, exist_ok=True)
    time.sleep(3)  # concede tempo para o processo chamador finalizar
    os.replace(atual, rollback)
    try:
        os.replace(staging, atual)
        subprocess.Popen([str(x) for x in comando], close_fds=True)
        if not _health(args.health_url):
            raise RuntimeError("Nova versão não atingiu health dentro do prazo.")
        return 0
    except Exception:
        if atual.exists():
            os.replace(atual, falha)
        os.replace(rollback, atual)
        subprocess.Popen([str(x) for x in comando], close_fds=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
