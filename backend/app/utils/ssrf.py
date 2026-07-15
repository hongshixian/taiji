"""SSRF 防护：校验用户提交的 URL，拒绝私有/保留 IP 和内网域名"""

import ipaddress
import re
from urllib.parse import urlparse

import requests

# ─── 私有 / 保留 IP 网段 ─────────────────────────────────
_PRIVATE_NETWORKS = [
    # RFC 1918 私有地址
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    # RFC 6598 运营商级 NAT
    ipaddress.ip_network("100.64.0.0/10"),
    # 链路本地 / 回环 / 组播 / 保留
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("224.0.0.0/4"),      # 组播
    ipaddress.ip_network("240.0.0.0/4"),      # 保留
    ipaddress.ip_network("::1/128"),           # IPv6 回环
    ipaddress.ip_network("fe80::/10"),         # IPv6 链路本地
    ipaddress.ip_network("fc00::/7"),          # IPv6 唯一本地
    ipaddress.ip_network("ff00::/8"),          # IPv6 组播
]

# 常见内网主机名模式（不区分大小写）
_INTERNAL_HOST_RE = re.compile(
    r"^(localhost"
    r"|.*\.local"
    r"|.*\.internal"
    r"|.*\.localhost"
    r"|host\.docker\.internal"
    r"|gateway\.docker\.internal"
    r")$",
    re.IGNORECASE,
)


def _is_private_ip(ip_str: str) -> bool:
    """判断 IP 字符串是否属于私有/保留网段"""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # 无法解析的 IP 视为不安全
    return any(addr in net for net in _PRIVATE_NETWORKS)


def validate_url(url: str) -> str:
    """校验 URL 是否为安全的公网地址。

    Returns:
        str: 校验通过后的原始 URL

    Raises:
        ValueError: URL 不合法或指向内网/保留地址
    """
    parsed = urlparse(url)

    # 只允许 http / https
    if parsed.scheme not in ("http", "https"):
        raise ValueError("仅允许 http 和 https 协议")

    host = parsed.hostname
    if not host:
        raise ValueError("URL 缺少主机名")

    # 拒绝内网主机名
    if _INTERNAL_HOST_RE.match(host):
        raise ValueError("不允许访问内网域名")

    # 解析 DNS，检查解析后的 IP 是否为私有地址
    # 先尝试直接解析（host 可能已经是 IP）
    try:
        ipaddress.ip_address(host)
        ip_str = host
    except ValueError:
        # host 是域名，需要 DNS 解析
        ip_str = _resolve_host(host)

    if _is_private_ip(ip_str):
        raise ValueError("不允许访问内网地址")

    return url


def _resolve_host(hostname: str) -> str:
    """DNS 解析域名，返回第一个 A/AAAA 记录的 IP"""
    import socket
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError(f"无法解析域名: {hostname}")
    if not results:
        raise ValueError(f"域名无可用地址: {hostname}")
    return results[0][4][0]


def safe_requests_get(url: str, **kwargs) -> requests.Response:
    """SSRF 安全的 requests.get：先校验 URL，再发请求（禁止跟随重定向到内网）"""
    from urllib.parse import urljoin as _urljoin

    validate_url(url)

    # 取出自定义参数，不传给 requests.get
    max_redirects = kwargs.pop("max_redirects", 5)

    # 禁止自动跟随重定向——由我们手动检查
    kwargs["allow_redirects"] = False

    response = requests.get(url, **kwargs)

    # 手动跟随重定向，每次都校验目标
    redirects = 0
    while response.is_redirect and redirects < max_redirects:
        next_url = response.headers.get("Location", "")
        if not next_url:
            break
        # 处理相对路径重定向
        next_url = _urljoin(url, str(next_url))
        validate_url(next_url)
        url = next_url
        response = requests.get(url, **kwargs)
        redirects += 1

    return response
