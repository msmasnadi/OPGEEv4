#!/usr/bin/env bash
# Run the OPGEE demo on the bundled single-field model.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${SCRIPT_DIR}/output"

mkdir -p "${OUTPUT_DIR}"

echo "Running OPGEE demo (analysis: demo, field: demo-field)..."
opg run \
  -m "${SCRIPT_DIR}/demo_model.xml" \
  -a demo \
  -o "${OUTPUT_DIR}" \
  --cluster-type serial

echo ""
echo "Demo complete. Results written to: ${OUTPUT_DIR}"
echo "Primary output file: ${OUTPUT_DIR}/carbon_intensity.csv"
ls -la "${OUTPUT_DIR}"
