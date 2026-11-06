"""以環境變數中的憑證更新 DuckDNS，不將金鑰寫入輸出。"""
import ipaddress
import os
import re
from urllib.parse import urlencode
from urllib.request import urlopen


def build_update_url() -> str:
    domain = os.environ["SITE_DOMAIN"]
    if not re.fullmatch(r"[a-z0-9-]+\.duckdns\.org", domain):
        raise ValueError("SITE_DOMAIN 必須是已註冊的 DuckDNS 子網域")
    address = str(ipaddress.ip_address(os.environ["PUBLIC_IP"]))
    query = urlencode({
        "domains": domain.removesuffix(".duckdns.org"),
        "token": os.environ["DUCKDNS_TOKEN"], "ip": address,
    })
    return "https://www.duckdns.org/update?" + query


def update_dns() -> None:
    with urlopen(build_update_url(), timeout=30) as response:
        result = response.read().decode().strip()
    if result != "OK":
        raise ValueError("DuckDNS 未接受更新，請檢查子網域與憑證")


def main() -> None:
    try:
        update_dns()
    except Exception:
        raise SystemExit("DuckDNS 更新失敗，請檢查設定與網路；憑證未輸出。") from None
    print("DuckDNS 更新完成")


if __name__ == "__main__":
    main()
