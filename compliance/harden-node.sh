#!/usr/bin/env bash
# Hardening for the Minikube node (Debian 12), derived from the OpenSCAP-generated
# fix script for CIS Level 1 Server, trimmed to the changes that are safe on a
# Kubernetes node. Idempotent: safe to run more than once.
#
# Run from the host:   docker exec -i minikube bash -s < compliance/harden-node.sh
#
# Deliberately NOT applied (accepted, see README):
#   - libpam-pwquality     no password logins; would make ~15 rules applicable and failing
#   - iptables-persistent  conflicts with kube-proxy-managed firewall rules
#   - nftables base chains empty accept-all chains, check-box compliance only
#   - remove rsync         may be required by Minikube
#   - root PATH rules      no automatic fix exists; investigated separately
set -u

UMASK=027
BACKUP=/root/hardening-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP"
for f in /etc/pam.d/su /etc/bash.bashrc /etc/profile; do
  [ -f "$f" ] && cp -a "$f" "$BACKUP/$(echo "$f" | tr / _)"
done
echo "backups in $BACKUP"

echo "[1/6] su restricted to the empty group 'sugroup' (pam_wheel)"
groupadd -f sugroup
if [ -f /etc/pam.d/su ]; then
  if grep -qE '^\s*auth\s+required\s+pam_wheel\.so' /etc/pam.d/su; then
    sed -i -E 's/^(\s*auth\s+required\s+pam_wheel\.so).*/\1 group=sugroup use_uid/' /etc/pam.d/su
  else
    echo 'auth required pam_wheel.so group=sugroup use_uid' >> /etc/pam.d/su
  fi
fi

echo "[2/6] user initialization files: mode 0740 or less"
echo "[3/6] interactive home directories: mode 0750 or less"
awk -F: '$3>=1000 && $3!=65534 && $6!="" && $6!="/" && $7!~/nologin$/ {print $6}' /etc/passwd |
while read -r home; do
  [ -d "$home" ] || continue
  find "$home" -maxdepth 1 -type f -name '.*' -exec chmod u-s,g-wxs,o-rwx {} +
  find "$home" -maxdepth 0 -type d -perm /7027 -exec chmod u-s,g-ws,o-rwx {} +
done

echo "[4/6] default umask $UMASK in /etc/bash.bashrc"
if grep -qE '^[^#]*\bumask' /etc/bash.bashrc; then
  sed -i -E "s/^([^#]*\bumask)[[:space:]]+[[:digit:]]+/\1 $UMASK/" /etc/bash.bashrc
else
  echo "umask $UMASK" >> /etc/bash.bashrc
fi

echo "[5/6] default umask $UMASK in /etc/profile"
for f in /etc/profile /etc/profile.d/*.sh /etc/profile.d/sh.local; do
  if [ -f "$f" ] && grep -qE '^[^#]*umask' "$f"; then
    sed -i -E "s/^(\s*umask\s*)[0-7]+/\1$UMASK/" "$f"
  fi
done
grep -qrE '^[^#]*umask' /etc/profile* || echo "umask $UMASK" >> /etc/profile

echo "[6/6] permissions of regular files directly in /var/log"
find -P /var/log/ -maxdepth 1 -type f -perm /u+xs,g+xws,o+xwrt -exec chmod u-xs,g-xws,o-xwrt {} +

echo "done. Rescan to verify."
