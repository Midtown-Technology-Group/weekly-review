#Requires -Version 7.0
<#
.SYNOPSIS
    Windows PowerShell wrapper for weekly-review Python tool
.DESCRIPTION
    Activates Python virtual environment and invokes weekly-review
    with proper Windows path handling. Designed for use with Logseq
    knowledge graphs following the work-context-sync pattern.

.PARAMETER Week
    ISO week to generate for (e.g., '2026-W16'). Defaults to current week.

.PARAMETER StartDate
    Start date for custom range (YYYY-MM-DD). Overrides Week.

.PARAMETER EndDate
    End date for custom range (YYYY-MM-DD). Requires StartDate.

.PARAMETER IncludeLastWeek
    Include previous week for comparison/trends.

.PARAMETER DryRun
    Preview output to console without writing file.

.PARAMETER OutputPath
    Custom output path for the review file.

.PARAMETER ConfigPath
    Path to custom config file (default: auto-discover).

.PARAMETER Verbose
    Enable verbose output.

.EXAMPLE
    .\invoke.ps1
    Generate review for current week

.EXAMPLE
    .\invoke.ps1 -Week "2026-W16"
    Generate for specific ISO week

.EXAMPLE
    .\invoke.ps1 -StartDate "2026-04-14" -EndDate "2026-04-20"
    Generate for custom date range

.EXAMPLE
    .\invoke.ps1 -IncludeLastWeek
    Include previous week data for comparison

.EXAMPLE
    .\invoke.ps1 -DryRun
    Preview output without writing file

.EXAMPLE
    .\invoke.ps1 -OutputPath "reviews/custom/my-review.md"
    Write to custom location
#>
[CmdletBinding()]
param(
    [string]$Week = $null,

    [string]$StartDate = $null,

    [string]$EndDate = $null,

    [switch]$IncludeLastWeek = $false,

    [switch]$DryRun = $false,

    [string]$OutputPath = $null,

    [string]$ConfigPath = $null,

    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

# Resolve paths
$ScriptDir = $PSScriptRoot
$ProjectDir = Resolve-Path $ScriptDir
$KnowledgeRoot = Resolve-Path (Join-Path $ScriptDir "..")

# Find Python in virtual environment
$VenvPython = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$SystemPython = (Get-Command python -ErrorAction SilentlyContinue)?.Source

$PythonBin = if (Test-Path $VenvPython) {
    $VenvPython
} elseif ($SystemPython) {
    Write-Warning "Virtual environment not found, using system Python: $SystemPython"
    $SystemPython
} else {
    Write-Error "Python not found. Please install Python 3.10+ or create .venv in $ProjectDir"
    exit 1
}

# Check if weekly-review package is installed
function Test-PackageInstalled {
    param([string]$Package)
    $env:PYTHONPATH = "$ProjectDir\src"
    $result = & $PythonBin -c "import $Package" 2>&1
    return $LASTEXITCODE -eq 0
}

$env:PYTHONPATH = "$ProjectDir\src"
$hasPackage = Test-PackageInstalled -Package "weekly_review"

if (-not $hasPackage) {
    Write-Warning "weekly_review package not found. Attempting to install..."

    Push-Location $ProjectDir
    try {
        if (Test-Path (Join-Path $ProjectDir ".venv\Scripts\Activate.ps1")) {
            & (Join-Path $ProjectDir ".venv\Scripts\Activate.ps1")
        }

        & $PythonBin -m pip install -e "$ProjectDir"

        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install weekly-review package"
            exit 1
        }
    } finally {
        if (Get-Command Deactivate -ErrorAction SilentlyContinue) {
            Deactivate
        }
        Pop-Location
    }
}

# Build command arguments
$CmdArgs = @("-m", "weekly_review")

# Determine week or date range
if ($Week) {
    $CmdArgs += @("generate", $Week)
} elseif ($StartDate -and $EndDate) {
    $CmdArgs += @("generate", "--start-date", $StartDate, "--end-date", $EndDate)
} elseif ($StartDate) {
    $CmdArgs += @("generate", "--start-date", $StartDate)
} else {
    $CmdArgs += @("generate")
}

# Add optional flags
if ($IncludeLastWeek) {
    $CmdArgs += "--include-last-week"
}

if ($DryRun) {
    $CmdArgs += "--dry-run"
}

if ($OutputPath) {
    $CmdArgs += @("--output", $OutputPath)
}

if ($ConfigPath) {
    $CmdArgs += @("--config", $ConfigPath)
}

if ($Verbose) {
    $CmdArgs += "--verbose"
}

# Main execution
Push-Location $KnowledgeRoot
try {
    # Activate virtual environment if available
    $ActivateScript = Join-Path $ProjectDir ".venv\Scripts\Activate.ps1"
    if (Test-Path $ActivateScript) {
        Write-Verbose "Activating virtual environment..."
        & $ActivateScript
    }

    # Set PYTHONPATH
    $env:PYTHONPATH = "$ProjectDir\src"

    Write-Host "Running: weekly-review $CmdArgs" -ForegroundColor Cyan

    # Run the tool
    & $PythonBin @CmdArgs

    if ($LASTEXITCODE -ne 0) {
        Write-Error "weekly-review failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

    if (-not $DryRun) {
        Write-Host "✓ Weekly review generated successfully" -ForegroundColor Green
    }

} finally {
    # Deactivate if activated
    if (Get-Command Deactivate -ErrorAction SilentlyContinue) {
        Deactivate
    }
    Pop-Location
}
