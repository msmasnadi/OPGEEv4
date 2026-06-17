#!/usr/bin/env bash
# Run the built-in OPGEE example analysis (no extra input files required).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output_builtin"

mkdir -p "${OUTPUT_DIR}"

echo "Running built-in OPGEE example analysis (gas_lifting_field)..."
opg run -a example -o "${OUTPUT_DIR}" --cluster-type serial

echo ""
echo "Demo complete. Results written to: ${OUTPUT_DIR}"
ls -la "${OUTPUT_DIR}"
