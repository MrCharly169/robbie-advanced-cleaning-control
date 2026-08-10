param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "restart", "logs", "status")]
    [string]$Command = "start",
    [int]$Port = 18123
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ConfigRoot = Join-Path $ProjectRoot ".dev\ha-config"
$ConfigFile = Join-Path $ConfigRoot "configuration.yaml"
$DashboardFile = Join-Path $ConfigRoot "ui-lovelace.yaml"
$DockerCommand = Get-Command docker -ErrorAction SilentlyContinue
$Docker = if ($DockerCommand) {
    $DockerCommand.Source
}
else {
    Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker.exe"
}
if (-not (Test-Path -LiteralPath $Docker)) {
    throw "Docker CLI not found. Start or install Docker Desktop first."
}
$env:HA_DEV_PORT = [string]$Port

if ($Command -eq "start") {
    New-Item -ItemType Directory -Force -Path $ConfigRoot | Out-Null
    if (-not (Test-Path -LiteralPath $ConfigFile)) {
        Copy-Item -LiteralPath (Join-Path $ProjectRoot "e2e\ha\configuration.yaml") -Destination $ConfigFile
    }
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "e2e\ha\ui-lovelace.yaml") -Destination $DashboardFile -Force
}

Push-Location $ProjectRoot
try {
    switch ($Command) {
        "start" { & $Docker compose -f compose.dev.yaml up -d }
        "stop" { & $Docker compose -f compose.dev.yaml down }
        "restart" { & $Docker compose -f compose.dev.yaml restart homeassistant }
        "logs" { & $Docker compose -f compose.dev.yaml logs -f homeassistant }
        "status" { & $Docker compose -f compose.dev.yaml ps }
    }
}
finally {
    Pop-Location
}
