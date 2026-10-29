param(
    [switch]$Clean,
    [switch]$Run,
    [string]$Python
)

$ErrorActionPreference = 'Stop'
$gameDirectory = Join-Path $PSScriptRoot 'tuman'
$pythonArguments = @()
if (-not $Python) {
    $localPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (Test-Path -LiteralPath $localPython) {
        $Python = $localPython
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $Python = 'python'
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $Python = 'py'
        $pythonArguments = @('-3')
    } else {
        throw 'Python not found. Install Python or pass -Python C:\path\python.exe.'
    }
}

Push-Location -LiteralPath $gameDirectory
try {
    & $Python @pythonArguments -m PyInstaller --version
    if ($LASTEXITCODE -ne 0) {
        throw 'Install build dependencies: python -m pip install -r requirements-build.txt (from the repository root).'
    }
    $buildArguments = @('-m', 'PyInstaller', '--noconfirm', 'Tuman.spec')
    if ($Clean) { $buildArguments += '--clean' }
    & $Python @pythonArguments @buildArguments
    if ($LASTEXITCODE -ne 0) { throw 'Build failed. See the output above.' }
    $executable = Join-Path $gameDirectory 'dist/Tuman/Tuman.exe'
    Write-Host "Ready: $executable"
    if ($Run) { Start-Process -FilePath $executable -WorkingDirectory (Split-Path $executable) -WindowStyle Hidden }
} finally {
    Pop-Location
}
