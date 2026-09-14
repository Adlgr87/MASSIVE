#!/usr/bin/env bash
# Security audit script for MASSIVE (PRODUCTION_ARCHITECTURE_SPEC.md §5.3)
# Runs bandit (SAST) + pip-audit (dependency CVE scanner)
set -euo pipefail
echo "=== MASSIVE Security Audit ==="
FAIL=0
echo "[1/2] Running Bandit..."
bandit -r backend/ -q 2>&1 | tee /tmp/bandit-output.txt || FAIL=1
echo "[2/2] Running pip-audit..."
pip-audit -r requirements.txt 2>&1 | tee /tmp/pip-audit-output.txt || FAIL=1
echo "" && [ $FAIL -eq 0 ] && echo "=== Security audit clean ===" || echo "=== Issues found — review ==="
exit $FAIL
