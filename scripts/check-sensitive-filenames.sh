#!/usr/bin/env bash
set -euo pipefail

status=0
for f in "$@"; do
  if echo "$f" | grep -qE '\.(pem|key|p12|pfx|ppk)$|id_rsa|id_dsa|id_ecdsa|id_ed25519|\.env$'; then
    echo "Blocked sensitive filename: $f"
    status=1
  fi
done
exit $status
