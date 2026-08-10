param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "restart", "logs", "status")]
    [string]$Command = "start"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ConfigRoot = Join-Path $ProjectRoot ".dev\ha-config"
$ConfigFile = Join-Path $ConfigRoot "configuration.yaml"

if ($Command -eq "start") {
    New-Item -ItemType Directory -Force -Path $ConfigRoot | Out-Null
    if (-not (Test-Path -LiteralPath $ConfigFile)) {
        Copy-Item -LiteralPath (Join-Path $ProjectRoot "e2e\ha\configuration.yaml") -Destination $ConfigFile
    }
}

Push-Location $ProjectRoot
try {
    switch ($Command) {
        "start" { docker compose -f compose.dev.yaml up -d }
        "stop" { docker compose -f compose.dev.yaml down }
        "restart" { docker compose -f compose.dev.yaml restart homeassistant }
        "logs" { docker compose -f compose.dev.yaml logs -f homeassistant }
        "status" { docker compose -f compose.dev.yaml ps }
    }
}
finally {
    Pop-Location
}
