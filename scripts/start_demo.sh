#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/venv/bin/python}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

DEMO_VEHICLES="${DEMO_VEHICLES:-1200}"
DEMO_CUSTOMERS="${DEMO_CUSTOMERS:-100}"
DEMO_DEALS="${DEMO_DEALS:-50}"
DEMO_LOGS="${DEMO_LOGS:-1000}"

SEED_FIRST=1

usage() {
  cat <<'EOF'
Usage: ./scripts/start_demo.sh [--no-seed]

Options:
  --no-seed   Skip DB reseeding and start services only.
  -h, --help  Show this help text.

Environment overrides:
  PYTHON_BIN      Python executable path (default: ./venv/bin/python)
  BACKEND_PORT    Backend port (default: 8000)
  FRONTEND_PORT   Frontend port (default: 5173)
  DEMO_VEHICLES   Inventory count for seeding (default: 1200)
  DEMO_CUSTOMERS  Demo customer count (default: 100)
  DEMO_DEALS      Demo deal count (default: 50)
  DEMO_LOGS       Compliance log count (default: 1000)
EOF
}

for arg in "$@"; do
  case "$arg" in
    --no-seed)
      SEED_FIRST=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python executable not found at: $PYTHON_BIN" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required but not found in PATH." >&2
  exit 1
fi

if ! "$PYTHON_BIN" -c "import reportlab" >/dev/null 2>&1; then
  echo "Warning: reportlab is not installed in the active environment."
  echo "         PDF endpoints still work with the built-in text-based generator."
fi

if [[ ! -d "$ROOT_DIR/frontend/node_modules" ]]; then
  echo "Installing frontend dependencies..."
  (cd "$ROOT_DIR/frontend" && npm install)
fi

if [[ "$SEED_FIRST" -eq 1 ]]; then
  echo "Seeding demo database..."
  "$PYTHON_BIN" -m scripts.seed_data \
    --vehicles "$DEMO_VEHICLES" \
    --customers "$DEMO_CUSTOMERS" \
    --deals "$DEMO_DEALS" \
    --compliance-logs "$DEMO_LOGS"
fi

BACK_PID=""
FRONT_PID=""

cleanup() {
  set +e
  if [[ -n "$BACK_PID" ]] && kill -0 "$BACK_PID" 2>/dev/null; then
    kill "$BACK_PID" 2>/dev/null
  fi
  if [[ -n "$FRONT_PID" ]] && kill -0 "$FRONT_PID" 2>/dev/null; then
    kill "$FRONT_PID" 2>/dev/null
  fi
  wait "$BACK_PID" "$FRONT_PID" 2>/dev/null
}

trap cleanup EXIT INT TERM

echo "Starting backend on http://localhost:${BACKEND_PORT} ..."
(
  cd "$ROOT_DIR/backend"
  "$PYTHON_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload
) &
BACK_PID=$!

echo "Starting frontend on http://localhost:${FRONTEND_PORT} ..."
(
  cd "$ROOT_DIR/frontend"
  npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"
) &
FRONT_PID=$!

echo
echo "Demo is running:"
echo "  Frontend: http://localhost:${FRONTEND_PORT}"
echo "  Backend : http://localhost:${BACKEND_PORT}"
echo "Press Ctrl+C to stop both services."
echo

wait "$BACK_PID" "$FRONT_PID"
