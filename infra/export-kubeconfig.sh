#!/usr/bin/env bash
# Creates infra/jenkins/kubeconfig so the Jenkins container can talk to Minikube.
set -euo pipefail
cd "$(dirname "$0")"

MINIKUBE_IP=$(minikube ip)
minikube kubectl -- config view --flatten --minify --context minikube \
  | sed "s#server: https://.*#server: https://${MINIKUBE_IP}:8443#" > jenkins/kubeconfig

echo "Wrote infra/jenkins/kubeconfig (API server: https://${MINIKUBE_IP}:8443)"
