#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_PATH}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${DEPLOY_DIR}/.env"

usage() {
  cat <<'EOF'
Usage:
  set_admin_credentials.sh [--role admin|user] --username <new_username> [--password <new_password>]

If --password is omitted, the script will prompt securely.
EOF
}

ROLE="admin"
USERNAME=""
PASSWORD=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --role)
      ROLE="${2:-}"
      shift 2
      ;;
    --username)
      USERNAME="${2:-}"
      shift 2
      ;;
    --password)
      PASSWORD="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "${ROLE}" != "admin" && "${ROLE}" != "user" ]]; then
  echo "Invalid --role: ${ROLE}" >&2
  usage
  exit 1
fi

if [[ -z "${USERNAME}" ]]; then
  echo "Missing --username" >&2
  usage
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

if [[ -z "${PASSWORD}" ]]; then
  read -r -s -p "New ${ROLE} password: " PASSWORD
  echo
fi

python3 - <<'PY' "${ENV_FILE}" "${ROLE}" "${USERNAME}" "${PASSWORD}"
from pathlib import Path
import sys

env_path = Path(sys.argv[1])
role = sys.argv[2].strip().lower()
username = sys.argv[3]
password = sys.argv[4]
username_key = f"{role.upper()}_USERNAME"
password_key = f"{role.upper()}_PASSWORD"

lines = env_path.read_text().splitlines()
updated = []
seen_username = False
seen_password = False

for line in lines:
    if line.startswith(f"{username_key}="):
        updated.append(f"{username_key}={username}")
        seen_username = True
    elif line.startswith(f"{password_key}="):
        updated.append(f"{password_key}={password}")
        seen_password = True
    else:
        updated.append(line)

if not seen_username:
    updated.append(f"{username_key}={username}")
if not seen_password:
    updated.append(f"{password_key}={password}")

env_path.write_text("\n".join(updated) + "\n")
PY

cd "${DEPLOY_DIR}"
docker compose --env-file .env -f docker-compose.vps.yml up -d --build

echo "Updated ${ROLE} credentials and redeployed Lush Temp Mail."
