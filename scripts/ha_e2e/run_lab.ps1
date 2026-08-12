param(
    [switch]$Fresh,
    [int]$Port = 18123
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
$ConfigRoot = [IO.Path]::GetFullPath((Join-Path $ProjectRoot ".dev\ha-config"))
$StateFile = Join-Path $ProjectRoot ".dev\runner-state.json"
$Artifacts = Join-Path $ProjectRoot "artifacts\ha-e2e"
$BundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$BundledNode = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$PythonCommand = Get-Command python -ErrorAction SilentlyContinue
$Python = if (Test-Path -LiteralPath $BundledPython) {
    $BundledPython
}
elseif ($PythonCommand -and $PythonCommand.Source -notlike "*\WindowsApps\*") {
    $PythonCommand.Source
}
else {
    ""
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python 3 was not found."
}

if ($Fresh) {
    & (Join-Path $ProjectRoot "scripts\dev.ps1") stop -Port $Port
    $expectedPrefix = $ProjectRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $ConfigRoot.StartsWith($expectedPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to reset a config directory outside the project: $ConfigRoot"
    }
    if (Test-Path -LiteralPath $ConfigRoot) {
        Remove-Item -LiteralPath $ConfigRoot -Recurse -Force
    }
    if (Test-Path -LiteralPath $StateFile) {
        Remove-Item -LiteralPath $StateFile -Force
    }
}

& (Join-Path $ProjectRoot "scripts\dev.ps1") start -Port $Port
$BaseUrl = "http://127.0.0.1:$Port"
& $Python (Join-Path $PSScriptRoot "run_scenarios.py") `
    --base-url $BaseUrl `
    --phase bootstrap `
    --state-file $StateFile `
    --output-dir $Artifacts
if ($LASTEXITCODE -ne 0) { throw "HA bootstrap scenario failed." }

if (-not (Test-Path -LiteralPath $BundledNode)) {
    throw "Bundled Node.js was not found."
}
& $BundledNode (Join-Path $PSScriptRoot "configure_dashboard.mjs") `
    --base-url $BaseUrl `
    --state-file $StateFile `
    --card-mode advanced `
    --check-onboarding true
if ($LASTEXITCODE -ne 0) { throw "Editable Lovelace dashboard setup failed." }

& $Python (Join-Path $PSScriptRoot "wait_for_config_entry.py") `
    --storage (Join-Path $ConfigRoot ".storage\core.config_entries") `
    --entity-registry (Join-Path $ConfigRoot ".storage\core.entity_registry") `
    --vacuum vacuum.valetudo_fixture_robot `
    --vacuum vacuum.cloud_fixture_robot `
    --state $StateFile `
    --wait-seconds 60
if ($LASTEXITCODE -ne 0) { throw "Config entry was not flushed to HA storage." }

& (Join-Path $ProjectRoot "scripts\dev.ps1") restart -Port $Port
& $Python (Join-Path $PSScriptRoot "run_scenarios.py") `
    --base-url $BaseUrl `
    --phase restart `
    --state-file $StateFile `
    --output-dir $Artifacts
if ($LASTEXITCODE -ne 0) { throw "HA restart scenario failed." }

$HomeAssistantLog = Join-Path $ConfigRoot "home-assistant.log"
if (Test-Path -LiteralPath $HomeAssistantLog) {
    $LogText = Get-Content -LiteralPath $HomeAssistantLog -Raw
    $FatalPatterns = @(
        "Setup failed for custom integration 'robbie_advanced_cc'",
        "Error setting up entry .*robbie_advanced_cc",
        "Failed to load services.yaml for integration: robbie_advanced_cc",
        "custom_components\.robbie_advanced_cc.*Traceback"
    )
    foreach ($Pattern in $FatalPatterns) {
        if ($LogText -match $Pattern) {
            throw "HA log gate failed for pattern: $Pattern"
        }
    }
}

Write-Host "Robbie HA lab passed and remains available at $BaseUrl"
Write-Host "Login: e2e-owner / e2e-only-disposable-password"
