#!/usr/bin/env bash
# Generate Python gRPC stubs from proto/*.proto using grpcio-tools.
#
# Usage:
#   ./scripts/gen_protos.sh [output_dir]   # default: gen/python
#
# Requires grpcio-tools in the active environment:
#   pip install grpcio-tools
#
# Generated code is NOT committed; services import it from gen/python
# (or regenerate into their own build context). Buf users can run
# `buf generate` instead (see buf.gen.yaml).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROTO_DIR="${REPO_ROOT}/proto"
OUT_DIR="${1:-${REPO_ROOT}/gen/python}"

# Interpreter resolution: $PYTHON override > project venv > python3 on PATH.
if [[ -n "${PYTHON:-}" ]]; then
  : # use caller-provided interpreter
elif [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  PYTHON="${REPO_ROOT}/.venv/bin/python"
else
  PYTHON="$(command -v python3)"
fi

if ! "${PYTHON}" -c "import grpc_tools.protoc" >/dev/null 2>&1; then
  echo "error: grpcio-tools not installed for ${PYTHON}" >&2
  echo "       run: ${PYTHON} -m pip install grpcio-tools" >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"

"${PYTHON}" -m grpc_tools.protoc \
  --proto_path="${PROTO_DIR}" \
  --python_out="${OUT_DIR}" \
  --pyi_out="${OUT_DIR}" \
  --grpc_python_out="${OUT_DIR}" \
  "${PROTO_DIR}"/*.proto

echo "Generated Python stubs for:"
ls "${PROTO_DIR}"/*.proto | xargs -n1 basename | sed 's/^/  - /'
echo "Output: ${OUT_DIR}"
