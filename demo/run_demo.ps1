# Run the OPGEE demo on the bundled single-field model (Windows PowerShell).
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutputDir = Join-Path $ScriptDir "output"

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

Write-Host "Running OPGEE demo (analysis: demo, field: demo-field)..."

opg run `
  -m (Join-Path $ScriptDir "demo_model.xml") `
  -a demo `
  -o $OutputDir `
  --cluster-type serial

Write-Host ""
Write-Host "Demo complete. Results written to: $OutputDir"
Write-Host "Primary output file: $(Join-Path $OutputDir 'carbon_intensity.csv')"
Get-ChildItem $OutputDir
