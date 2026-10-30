"""URL-009 / NFR-003 SSRF 방어."""

import asyncio
import ipaddress
import socket

from app.core.errors import AppError, ErrorCode

BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal", "metadata"}


def _is_forbidden_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    # is_global 은 사설·루프백·링크로컬(169.254.169.254 메타데이터 포함)·예약 대역을 모두 제외한다
    return not ip.is_global or ip.is_multicast


async def resolve_public_ips(host: str) -> list[str]:
    """호스트를 DNS 조회하고, 하나라도 비공개 대역이면 거부한다."""
    if host in BLOCKED_HOSTNAMES or host.endswith(".localhost") or host.endswith(".internal"):
        raise AppError(ErrorCode.PRIVATE_NETWORK_TARGET)

    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise AppError(ErrorCode.DNS_RESOLUTION_FAILED) from e

    ips = sorted({info[4][0] for info in infos})
    if not ips:
        raise AppError(ErrorCode.DNS_RESOLUTION_FAILED)
    for ip in ips:
        if _is_forbidden_ip(ipaddress.ip_address(ip.split("%")[0])):
            raise AppError(ErrorCode.PRIVATE_NETWORK_TARGET)
    return ips


def parse_ip_host(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None
