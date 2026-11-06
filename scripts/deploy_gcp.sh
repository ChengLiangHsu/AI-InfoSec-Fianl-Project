#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

load_settings() {
    cd "$ROOT_DIR"
    [[ -f .env.cloud && -f .env ]] || { printf '%s\n' '請先設定 .env.cloud 與 .env。' >&2; exit 1; }
    set -a
    # 此檔由部署者建立，僅包含本機部署設定，不接受網頁輸入。
    source .env.cloud
    set +a
    : "${GCP_PROJECT:?請設定 GCP_PROJECT}"
    : "${GCP_ZONE:=asia-east1-b}"
    : "${GCP_INSTANCE:=drone-field-demo}"
    : "${GCP_MACHINE:=e2-highmem-4}"
    : "${SITE_DOMAIN:?請設定 SITE_DOMAIN}"
    : "${DUCKDNS_TOKEN:?請設定 DUCKDNS_TOKEN}"
    [[ "$SITE_DOMAIN" =~ ^[a-z0-9-]+\.duckdns\.org$ ]] || { printf '%s\n' 'DuckDNS 子網域格式錯誤。' >&2; exit 1; }
    command -v gcloud >/dev/null || { printf '%s\n' '請先安裝 Google Cloud CLI 並執行 gcloud auth login。' >&2; exit 1; }
    gcloud projects describe "$GCP_PROJECT" --format='value(projectId)' >/dev/null
    region=${GCP_ZONE%-*}
}

ensure_network_rules() {
    if ! gcloud compute networks describe "$GCP_INSTANCE-network" --project="$GCP_PROJECT" >/dev/null 2>&1; then
        gcloud compute networks create "$GCP_INSTANCE-network" --subnet-mode=custom --project="$GCP_PROJECT"
    fi
    if ! gcloud compute networks subnets describe "$GCP_INSTANCE-subnet" --region="$region" --project="$GCP_PROJECT" >/dev/null 2>&1; then
        gcloud compute networks subnets create "$GCP_INSTANCE-subnet" --network="$GCP_INSTANCE-network" \
            --region="$region" --range=10.42.0.0/24 --project="$GCP_PROJECT"
    fi
    if ! gcloud compute firewall-rules describe "$GCP_INSTANCE-web" --project="$GCP_PROJECT" >/dev/null 2>&1; then
        gcloud compute firewall-rules create "$GCP_INSTANCE-web" --project="$GCP_PROJECT" \
            --network="$GCP_INSTANCE-network" --allow=tcp:80,tcp:443 --source-ranges=0.0.0.0/0 --target-tags="$GCP_INSTANCE"
    fi
    if ! gcloud compute firewall-rules describe "$GCP_INSTANCE-iap" --project="$GCP_PROJECT" >/dev/null 2>&1; then
        gcloud compute firewall-rules create "$GCP_INSTANCE-iap" --project="$GCP_PROJECT" \
            --network="$GCP_INSTANCE-network" --allow=tcp:22 --source-ranges=35.235.240.0/20 --target-tags="$GCP_INSTANCE"
    fi
}

ensure_instance() {
    if ! gcloud compute addresses describe "$GCP_INSTANCE-ip" --region="$region" --project="$GCP_PROJECT" >/dev/null 2>&1; then
        gcloud compute addresses create "$GCP_INSTANCE-ip" --region="$region" --project="$GCP_PROJECT"
    fi
    PUBLIC_IP=$(gcloud compute addresses describe "$GCP_INSTANCE-ip" --region="$region" --project="$GCP_PROJECT" --format='value(address)')
    export PUBLIC_IP
    if ! gcloud compute instances describe "$GCP_INSTANCE" --zone="$GCP_ZONE" --project="$GCP_PROJECT" >/dev/null 2>&1; then
        gcloud compute instances create "$GCP_INSTANCE" --zone="$GCP_ZONE" --project="$GCP_PROJECT" \
            --machine-type="$GCP_MACHINE" --image-family=ubuntu-2404-lts-amd64 --image-project=ubuntu-os-cloud \
            --boot-disk-size=150GB --boot-disk-type=pd-balanced --no-boot-disk-auto-delete \
            --network="$GCP_INSTANCE-network" --subnet="$GCP_INSTANCE-subnet" \
            --address="$PUBLIC_IP" --tags="$GCP_INSTANCE" --no-service-account --no-scopes
    fi
}

ensure_instance_running() {
    local instance_status instance_ip
    instance_status=$(gcloud compute instances describe "$GCP_INSTANCE" --zone="$GCP_ZONE" \
        --project="$GCP_PROJECT" --format='value(status)')
    if [[ "$instance_status" == TERMINATED ]]; then
        gcloud compute instances start "$GCP_INSTANCE" --zone="$GCP_ZONE" --project="$GCP_PROJECT"
    elif [[ "$instance_status" != RUNNING ]]; then
        printf '%s\n' "主機狀態為 $instance_status，請等待主機操作完成後重試。" >&2
        exit 1
    fi
    instance_ip=$(gcloud compute instances describe "$GCP_INSTANCE" --zone="$GCP_ZONE" \
        --project="$GCP_PROJECT" --format='value(networkInterfaces[0].accessConfigs[0].natIP)')
    if [[ "$instance_ip" != "$PUBLIC_IP" ]]; then
        printf '%s\n' '既有主機未使用本次保留的 IP，已停止部署，請先檢查主機設定。' >&2
        exit 1
    fi
}

wait_for_ssh() {
    local attempt
    for attempt in {1..12}; do
        if gcloud compute ssh "$GCP_INSTANCE" --zone="$GCP_ZONE" --project="$GCP_PROJECT" \
            --tunnel-through-iap --ssh-flag='-o ConnectTimeout=10' \
            --command='mkdir -p ~/drone-field-incoming && chmod 700 ~/drone-field-incoming'; then
            return
        fi
        printf '%s\n' "等待主機 SSH 啟動（$attempt/12）……" >&2
        sleep 10
    done
    printf '%s\n' '無法透過 IAP 連線；請檢查 SSH／IAP 權限及主機狀態。' >&2
    return 1
}

prepare_payload() {
    payload_dir=$(mktemp -d)
    trap 'rm -rf "$payload_dir"' EXIT
    tar --exclude='frontend/node_modules' --exclude='frontend/dist' --exclude='src/odm' \
        --exclude='*/__pycache__' -czf "$payload_dir/source.tar.gz" \
        Dockerfile .dockerignore compose.yaml pyproject.toml uv.lock README.md src frontend deploy scripts
    install -m 0600 .env "$payload_dir/runtime.env"
    printf '\nCOOKIE_SECURE=true\nPUBLIC_ORIGIN=https://%s\nSITE_DOMAIN=%s\n' \
        "$SITE_DOMAIN" "$SITE_DOMAIN" >> "$payload_dir/runtime.env"
}

publish_payload() {
    gcloud compute scp "$payload_dir/source.tar.gz" "$payload_dir/runtime.env" \
        "$GCP_INSTANCE:drone-field-incoming/" --zone="$GCP_ZONE" --project="$GCP_PROJECT" --tunnel-through-iap
    gcloud compute ssh "$GCP_INSTANCE" --zone="$GCP_ZONE" --project="$GCP_PROJECT" --tunnel-through-iap \
        --command='set -eu; cd ~/drone-field-incoming; chmod 600 runtime.env; tar -xzf source.tar.gz scripts/bootstrap_gcp.sh scripts/publish_release.sh; sudo bash scripts/bootstrap_gcp.sh; sudo bash scripts/publish_release.sh source.tar.gz runtime.env; rm runtime.env'
}

main() {
    load_settings
    gcloud services enable compute.googleapis.com iap.googleapis.com --project="$GCP_PROJECT"
    ensure_network_rules
    ensure_instance
    ensure_instance_running
    python3 scripts/update_dns.py
    prepare_payload
    wait_for_ssh
    publish_payload
    curl --fail --silent --show-error --retry 12 --retry-delay 10 --retry-all-errors "https://$SITE_DOMAIN/healthz"
    printf '\n%s\n' "公開網址：https://$SITE_DOMAIN"
}

main "$@"
