# Start OCSS GT Lobby Check-In Streamlit application
# Run this script from the project root directory.

param(
    [int]$Port = 8501,
    [string]$Host = "localhost"
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir

Set-Location $ProjectRoot

# Activate virtual environment if it exists
$VenvActivate = Join-Path $ProjectRoot "venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    Write-Host "Activating virtual environment..."
    & $VenvActivate
} else {
    Write-Warning "Virtual environment not found at $VenvActivate. Using system Python."
}

Write-Host "Starting OCSS GT Lobby Check-In on http://${Host}:${Port} ..."

streamlit run app/main_app.py `
    --server.port $Port `
    --server.address $Host `
    --server.headless true `
    --server.enableCORS false `
    --server.enableXsrfProtection true
