#!/usr/bin/env bash
set -euo pipefail

prepare_release() {
    release_dir="/opt/drone-field/releases/$(date -u +%Y%m%dT%H%M%SZ)"
    install -d -m 0755 "$release_dir"
    tar -xzf "$archive" -C "$release_dir"
    install -m 0600 "$runtime_env" "$release_dir/.env"
    printf '\nAPP_IMAGE_TAG=%s\n' "$(basename "$release_dir")" >> "$release_dir/.env"
}

start_release() {
    cd "$release_dir"
    docker compose -p drone-field --profile public build app
    docker compose -p drone-field --profile public up -d --wait --wait-timeout 300
    ln -sfn "$release_dir" /opt/drone-field/current
}

main() {
    archive=$(realpath "${1:?缺少程式壓縮檔}")
    runtime_env=$(realpath "${2:?缺少執行環境檔}")
    prepare_release
    start_release
    printf '%s\n' "部署目錄：$release_dir"
}

main "$@"
