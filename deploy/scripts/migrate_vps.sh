#!/usr/bin/env bash
set -euo pipefail

# Run this script on the NEW VPS. It installs a fresh Git checkout, then copies
# runtime data from the SOURCE VPS. It never writes to the source host.

SOURCE_HOST="${SOURCE_HOST:-}"
SOURCE_USER="${SOURCE_USER:-root}"
SOURCE_SSH_PORT="${SOURCE_SSH_PORT:-22}"
SOURCE_APP_DIR="${SOURCE_APP_DIR:-/opt/lush-temp-mail/app}"

TARGET_BASE_DIR="${TARGET_BASE_DIR:-/opt/lush-temp-mail}"
TARGET_APP_DIR="${TARGET_APP_DIR:-$TARGET_BASE_DIR/app}"
REPO_URL="${REPO_URL:-https://github.com/lushmediadev/Lush-Temp-Mail.git}"
BRANCH="${BRANCH:-main}"

COMPOSE_FILE="${COMPOSE_FILE:-deploy/docker-compose.nginx.yml}"
SKIP_ENV="${SKIP_ENV:-0}"
SKIP_DATA="${SKIP_DATA:-0}"
START_APP="${START_APP:-1}"
SOURCE_SSH_OPTS="${SOURCE_SSH_OPTS:-}"

timestamp="$(date +%Y%m%d%H%M%S)"

usage() {
  cat <<'USAGE'
Usage:
  SOURCE_HOST=OLD_VPS_IP bash deploy/scripts/migrate_vps.sh

Optional env:
  SOURCE_USER=root
  SOURCE_SSH_PORT=22
  SOURCE_APP_DIR=/opt/lush-temp-mail/app
  TARGET_APP_DIR=/opt/lush-temp-mail/app
  REPO_URL=https://github.com/lushmediadev/Lush-Temp-Mail.git
  BRANCH=main
  COMPOSE_FILE=deploy/docker-compose.nginx.yml
  SKIP_ENV=1
  SKIP_DATA=1
  START_APP=0
  SOURCE_SSH_OPTS="-i /root/.ssh/source_vps_key"

The target VPS must be able to SSH into SOURCE_HOST. Prefer SSH keys.
USAGE
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

if [ -z "$SOURCE_HOST" ]; then
  echo "ERROR: SOURCE_HOST is required." >&2
  usage >&2
  exit 2
fi

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: missing command: $1" >&2
    exit 2
  }
}

install_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y git rsync openssh-client docker.io
  apt-get install -y docker-compose-v2 || apt-get install -y docker-compose-plugin || true
}

ssh_source() {
  # shellcheck disable=SC2086
  ssh -p "$SOURCE_SSH_PORT" -o StrictHostKeyChecking=accept-new $SOURCE_SSH_OPTS "$SOURCE_USER@$SOURCE_HOST" "$@"
}

rsync_from_source() {
  local source_path="$1"
  local target_path="$2"
  local ssh_cmd
  ssh_cmd="ssh -p $SOURCE_SSH_PORT -o StrictHostKeyChecking=accept-new $SOURCE_SSH_OPTS"
  rsync -az --partial --info=progress2 -e "$ssh_cmd" "$SOURCE_USER@$SOURCE_HOST:$source_path" "$target_path"
}

backup_existing_target() {
  if [ -e "$TARGET_APP_DIR" ] && [ ! -d "$TARGET_APP_DIR/.git" ]; then
    local backup_dir="${TARGET_APP_DIR}.pre-migrate-${timestamp}"
    echo "Backing up existing non-git app dir to $backup_dir"
    mv "$TARGET_APP_DIR" "$backup_dir"
  fi
}

sync_git_checkout() {
  mkdir -p "$(dirname "$TARGET_APP_DIR")"
  if [ -d "$TARGET_APP_DIR/.git" ]; then
    if [ "$(git -C "$TARGET_APP_DIR" branch --show-current)" != "$BRANCH" ]; then
      echo "ERROR: target checkout is not on $BRANCH; inspect it before updating." >&2
      exit 2
    fi
    git -C "$TARGET_APP_DIR" pull --ff-only origin "$BRANCH"
  else
    git clone --branch "$BRANCH" "$REPO_URL" "$TARGET_APP_DIR"
  fi
}

copy_runtime() {
  mkdir -p "$TARGET_APP_DIR/deploy/data"

  if [ "$SKIP_ENV" != "1" ]; then
    if ssh_source "test -f '$SOURCE_APP_DIR/deploy/.env'"; then
      if [ -f "$TARGET_APP_DIR/deploy/.env" ]; then
        cp -a "$TARGET_APP_DIR/deploy/.env" "$TARGET_APP_DIR/deploy/.env.bak-$timestamp"
      fi
      rsync_from_source "$SOURCE_APP_DIR/deploy/.env" "$TARGET_APP_DIR/deploy/.env"
    else
      echo "WARN: source .env not found; leaving target .env unchanged."
    fi
  fi

  if [ "$SKIP_DATA" != "1" ]; then
    if ssh_source "test -d '$SOURCE_APP_DIR/deploy/data'"; then
      if [ -d "$TARGET_APP_DIR/deploy/data" ]; then
        mkdir -p "$TARGET_APP_DIR/deploy/backups"
        tar -C "$TARGET_APP_DIR/deploy" -czf "$TARGET_APP_DIR/deploy/backups/data-before-migrate-$timestamp.tgz" data
      fi
      rsync_from_source "$SOURCE_APP_DIR/deploy/data/" "$TARGET_APP_DIR/deploy/data/"
    else
      echo "WARN: source deploy/data not found; leaving target data unchanged."
    fi
  fi
}

start_app() {
  cd "$TARGET_APP_DIR"
  docker compose -f "$COMPOSE_FILE" --env-file deploy/.env up -d --build
  docker compose -f "$COMPOSE_FILE" ps
}

verify_app() {
  if docker ps --format '{{.Names}}' | grep -qx 'lushmail-app'; then
    docker exec lushmail-app python -c 'from urllib.request import urlopen; print(urlopen("http://127.0.0.1:8010/api/health", timeout=10).read().decode())'
  else
    echo "WARN: lushmail-app is not running; skipped container health check."
  fi
}

install_packages
need_cmd git
need_cmd rsync
need_cmd ssh
need_cmd docker

backup_existing_target
sync_git_checkout
copy_runtime

if [ "$START_APP" = "1" ]; then
  start_app
  verify_app
else
  echo "START_APP=0, skipped compose up."
fi

echo "Done. Target app: $TARGET_APP_DIR"
