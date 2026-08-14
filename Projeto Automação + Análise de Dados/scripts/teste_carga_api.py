"""Teste de carga HTTP reproduzível para health ou endpoint autenticado."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import statistics
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def requisicao(url: str, token: str | None, timeout: float) -> tuple[bool, float, int]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    inicio = time.perf_counter()
    try:
        with urlopen(Request(url, headers=headers), timeout=timeout) as resposta:
            resposta.read()
            status = int(resposta.status)
        return 200 <= status < 400, (time.perf_counter() - inicio) * 1000, status
    except HTTPError as exc:
        return False, (time.perf_counter() - inicio) * 1000, int(exc.code)
    except (URLError, TimeoutError, OSError):
        return False, (time.perf_counter() - inicio) * 1000, 0


def percentil(valores: list[float], p: float) -> float:
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    return ordenados[min(len(ordenados) - 1, int((len(ordenados) - 1) * p))]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--requisicoes", type=int, default=1000)
    parser.add_argument("--concorrencia", type=int, default=25)
    parser.add_argument("--token")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--max-erros-percentual", type=float, default=1.0)
    parser.add_argument("--max-p95-ms", type=float, default=1500)
    args = parser.parse_args()
    total = max(1, min(args.requisicoes, 1_000_000))
    inicio = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, min(args.concorrencia, 1000))) as pool:
        futuros = [pool.submit(requisicao, args.url, args.token, args.timeout) for _ in range(total)]
        resultados = [f.result() for f in as_completed(futuros)]
    duracao = time.perf_counter() - inicio
    latencias = [x[1] for x in resultados]
    erros = sum(not x[0] for x in resultados)
    resumo = {
        "requisicoes": total, "concorrencia": args.concorrencia,
        "erros": erros, "erros_percentual": round(erros * 100 / total, 3),
        "rps": round(total / max(duracao, 0.001), 2),
        "latencia_media_ms": round(statistics.fmean(latencias), 2),
        "latencia_p50_ms": round(percentil(latencias, 0.50), 2),
        "latencia_p95_ms": round(percentil(latencias, 0.95), 2),
        "latencia_p99_ms": round(percentil(latencias, 0.99), 2),
    }
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
    return int(resumo["erros_percentual"] > args.max_erros_percentual or resumo["latencia_p95_ms"] > args.max_p95_ms)


if __name__ == "__main__":
    raise SystemExit(main())
