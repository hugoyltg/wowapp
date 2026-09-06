$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    & $VenvPython "app/main.py"
} else {
    Write-Host "[ERROR] Virtual environment .venv not found." -ForegroundColor Red
    Write-Host "Please set up .venv first."
}
