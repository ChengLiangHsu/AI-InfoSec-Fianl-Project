#!/usr/bin/env bash
set -euo pipefail

install_docker() {
    if command -v docker >/dev/null && docker compose version >/dev/null 2>&1; then
        return
    fi
    apt-get update
    apt-get install -y ca-certificates curl
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    cat > /etc/apt/sources.list.d/docker.sources <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
}

main() {
    if [[ $EUID -ne 0 ]]; then
        printf '%s\n' '請透過 sudo 執行主機初始化。' >&2
        exit 1
    fi
    install_docker
    install -d -m 0755 /opt/drone-field/releases
}

main "$@"
