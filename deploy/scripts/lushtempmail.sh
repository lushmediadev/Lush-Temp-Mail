#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
DEFAULT_DEPLOY_DIR="/opt/lush-temp-mail/app/deploy"
DEPLOY_DIR="${LUSHTEMPMAIL_DEPLOY_DIR:-}"

if [[ -z "${DEPLOY_DIR}" ]]; then
  if [[ -f "${SCRIPT_DIR}/../docker-compose.vps.yml" ]]; then
    DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
  else
    DEPLOY_DIR="${DEFAULT_DEPLOY_DIR}"
  fi
fi

usage() {
  cat <<'EOF'
Usage:
  lushtempmail status
  lushtempmail logs
  lushtempmail redeploy
  lushtempmail update
  lushtempmail set-admin --username <new_admin_username> [--password <new_admin_password>]
EOF
}

run_compose() {
  cd "${DEPLOY_DIR}"
  docker compose --env-file .env -f docker-compose.vps.yml "$@"
}

case "${1:-}" in
  status)
    run_compose ps
    ;;
  logs)
    run_compose logs -f app
    ;;
  redeploy)
    run_compose up -d --build
    ;;
  update)
    git -C "$(cd "${DEPLOY_DIR}/.." && pwd)" pull --ff-only
    run_compose up -d --build
    ;;
  set-admin)
    shift
    "${DEPLOY_DIR}/scripts/set_admin_credentials.sh" "$@"
    ;;
  *)
    usage
    exit 1
    ;;
esac
