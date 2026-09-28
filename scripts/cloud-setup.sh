#!/usr/bin/env bash
# Setup script dell'environment cloud (o locale Linux/WSL).
# Domini da abilitare se la rete li blocca: github.com, objects.githubusercontent.com,
# release-assets.githubusercontent.com, registry.npmjs.org, pypi.org, files.pythonhosted.org
set -e
GITLEAKS_VERSION=8.28.0
SUDO=""; [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null && SUDO=sudo

if ! command -v jq >/dev/null; then
  $SUDO apt-get update -qq && $SUDO apt-get install -y -qq jq
fi
if ! command -v gitleaks >/dev/null; then
  curl -sSL "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz" \
    | tar xz -C /tmp gitleaks && $SUDO mv /tmp/gitleaks /usr/local/bin/
fi
chmod +x .claude/hooks/*.sh scripts/loop/*.sh scripts/tests/*.sh 2>/dev/null || true

# Toolchain del progetto: decommenta ciò che serve.
# node:       command -v node || (curl -fsSL https://deb.nodesource.com/setup_lts.x | $SUDO bash - && $SUDO apt-get install -y nodejs)
# dipendenze: [ -f package-lock.json ] && npm ci
# playwright: npx playwright install --with-deps chromium
# python:     [ -f pyproject.toml ] && pip install -e ".[dev]"
pip install -q -r requirements.txt -r scripts/milan/requirements.txt

echo "setup ok: jq $(jq --version), gitleaks $(gitleaks version)"
