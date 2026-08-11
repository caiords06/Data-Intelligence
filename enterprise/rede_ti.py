"""Descoberta controlada de rede para segmentos privados explicitamente autorizados.

O scanner é propositalmente conservador: usa somente ICMP/hostname e a tabela
ARP local; não faz varredura de portas, exploração, autenticação remota ou
captura de pacotes. O objetivo é inventário operacional em redes administradas.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress
import os
import re
import socket
import subprocess
import time
from typing import Any


MAX_HOSTS_DESCOBERTA = 1024
MAX_WORKERS = 32


def _flags_sem_janela() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def _ping(endereco: str, timeout_ms: int = 500) -> tuple[bool, float | None]:
    inicio = time.monotonic()
    if os.name == "nt":
        comando = ["ping", "-n", "1", "-w", str(max(100, int(timeout_ms))), endereco]
        timeout = max(1.5, timeout_ms / 1000 + 1)
    else:
        segundos = max(1, int(round(timeout_ms / 1000)))
        comando = ["ping", "-c", "1", "-W", str(segundos), endereco]
        timeout = max(2, segundos + 1)
    try:
        resultado = subprocess.run(
            comando,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
            shell=False,
            creationflags=_flags_sem_janela(),
        )
    except (OSError, subprocess.SubprocessError):
        return False, None
    latencia = (time.monotonic() - inicio) * 1000
    return resultado.returncode == 0, round(latencia, 1) if resultado.returncode == 0 else None


def _resolver_hostname(endereco: str) -> str | None:
    try:
        return socket.gethostbyaddr(endereco)[0][:120]
    except (OSError, socket.herror, socket.gaierror):
        return None


def _arp_cache() -> dict[str, str]:
    try:
        resultado = subprocess.run(
            ["arp", "-a"], capture_output=True, text=True, timeout=4,
            check=False, shell=False, creationflags=_flags_sem_janela(),
        )
    except (OSError, subprocess.SubprocessError):
        return {}
    texto = resultado.stdout or ""
    mapa: dict[str, str] = {}
    # Windows: 192.168.0.1  aa-bb-cc-dd-ee-ff  dynamic
    # Linux/macOS costumam exibir ... (192.168.0.1) at aa:bb:...
    padroes = (
        re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})\b"),
        re.compile(r"\((\d{1,3}(?:\.\d{1,3}){3})\).*?\bat\s+([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})\b", re.I),
    )
    for padrao in padroes:
        for ip, mac in padrao.findall(texto):
            mapa[ip] = mac.upper().replace("-", ":")
    return mapa


def descobrir_hosts(cidr: str, *, timeout_ms: int = 500, max_workers: int = MAX_WORKERS) -> dict[str, Any]:
    rede = ipaddress.ip_network(str(cidr), strict=False)
    if not rede.is_private:
        raise ValueError("A descoberta só é permitida em redes privadas.")
    hosts = [str(ip) for ip in rede.hosts()]
    if len(hosts) > MAX_HOSTS_DESCOBERTA:
        raise ValueError(f"O segmento possui {len(hosts)} hosts. Divida-o em blocos de até {MAX_HOSTS_DESCOBERTA} hosts para descoberta interativa.")
    inicio = time.monotonic()
    encontrados: list[dict[str, Any]] = []
    trabalhadores = max(1, min(int(max_workers), MAX_WORKERS, len(hosts) or 1))
    with ThreadPoolExecutor(max_workers=trabalhadores, thread_name_prefix="ti-discovery") as executor:
        futuros = {executor.submit(_ping, endereco, timeout_ms): endereco for endereco in hosts}
        for futuro in as_completed(futuros):
            endereco = futuros[futuro]
            try:
                respondeu, latencia = futuro.result()
            except Exception:
                respondeu, latencia = False, None
            if respondeu:
                encontrados.append({
                    "endereco_ip": endereco,
                    "hostname": _resolver_hostname(endereco),
                    "ultimo_ping_ms": latencia,
                    "status": "Online",
                    "origem": "Descoberta ICMP",
                })
    arp = _arp_cache()
    respondendo_icmp = {item["endereco_ip"] for item in encontrados}
    for item in encontrados:
        item["endereco_mac"] = arp.get(item["endereco_ip"])
    # A cache ARP pode revelar equipamentos locais que bloqueiam ICMP. Eles são
    # mostrados como "Detectado" e não como "Online", evitando falsa certeza.
    hosts_validos = set(hosts)
    for endereco, mac in arp.items():
        if endereco not in hosts_validos or endereco in respondendo_icmp:
            continue
        encontrados.append({
            "endereco_ip": endereco,
            "hostname": _resolver_hostname(endereco),
            "endereco_mac": mac,
            "ultimo_ping_ms": None,
            "status": "Detectado",
            "origem": "Cache ARP",
        })
    encontrados.sort(key=lambda x: ipaddress.ip_address(x["endereco_ip"]))
    return {
        "cidr": str(rede),
        "total_testados": len(hosts),
        "online": len(respondendo_icmp),
        "detectados": len(encontrados),
        "duracao_segundos": round(time.monotonic() - inicio, 2),
        "dispositivos": encontrados,
    }


def diagnosticar_conectividade(*, gateway: str | None = None, dns_alvo: str = "example.com") -> dict[str, Any]:
    resultado: dict[str, Any] = {
        "gateway_ok": None,
        "gateway_latencia_ms": None,
        "dns_ok": False,
        "dns_endereco": None,
        "internet_ok": False,
        "internet_latencia_ms": None,
        "hostname_local": socket.gethostname(),
    }
    if gateway:
        ok, latencia = _ping(str(gateway), 700)
        resultado["gateway_ok"] = ok
        resultado["gateway_latencia_ms"] = latencia
    try:
        resultado["dns_endereco"] = socket.gethostbyname(dns_alvo)
        resultado["dns_ok"] = True
    except OSError:
        pass
    inicio = time.monotonic()
    for destino in (("1.1.1.1", 443), ("8.8.8.8", 53)):
        try:
            with socket.create_connection(destino, timeout=2):
                resultado["internet_ok"] = True
                resultado["internet_latencia_ms"] = round((time.monotonic() - inicio) * 1000, 1)
                break
        except OSError:
            continue
    return resultado
