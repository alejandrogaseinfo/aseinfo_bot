#!/usr/bin/env bash
set -euo pipefail

# Run from SSH → Application after OneDeploy has reached complete=true.
# This is intentionally read-only and does not change App Service settings.
APP_ROOT="${APP_ROOT:-/home/site/wwwroot}"
test -f "$APP_ROOT/ai_first.py"
test -f "$APP_ROOT/handler.py"
PYTHONPATH="$APP_ROOT" python -c "import ai_first, handler; print('ai_first_import=ok')"
