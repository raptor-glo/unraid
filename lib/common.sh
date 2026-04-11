#!/usr/bin/env bash
# Common helpers for all user scripts.
# Source this at the top of any script:
#
#   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#   source "$SCRIPT_DIR/../../../lib/common.sh"
#
# This also sources config.env automatically.

_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$_LIB_DIR/../config.env"

# Print a timestamped log line
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Exit with an error if a required command is missing
require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "ERROR: Required command '$1' not found. Aborting."
        exit 1
    }
}

# Return a timestamped log file path under /boot/logs/, creating the dir if needed
log_file() {
    local name="$1"
    local logdir="/boot/logs"
    mkdir -p "$logdir"
    echo "$logdir/${name}-$(date +%Y%m%d-%H%M%S).log"
}
