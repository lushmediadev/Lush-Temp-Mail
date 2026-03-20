#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install -m 0755 "${SCRIPT_DIR}/lushtempmail.sh" /usr/local/bin/lushtempmail
install -m 0755 "${SCRIPT_DIR}/set_admin_credentials.sh" /usr/local/bin/lushtempmail-set-admin
