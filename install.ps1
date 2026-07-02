$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$installer = Join-Path $scriptDir "scripts\install_student_os.py"

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 $installer @args
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    python $installer @args
    exit $LASTEXITCODE
}

throw "Python 3 was not found in PATH. Install Python 3 and rerun install.ps1."
