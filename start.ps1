# Starts the Research Agent A2A server, waits for its Agent Card, then runs the
# Summary Agent. Stops the server again when you exit.
#
#   .\start.ps1          # ADK web UI at http://localhost:8000 (default)
#   .\start.ps1 run      # chat in the terminal
#   .\start.ps1 e2e      # run the end-to-end A2A test
#
# Run from this folder with the virtual environment activated.

param(
    [ValidateSet('web', 'run', 'e2e')]
    [string]$Mode = 'web'
)

$ErrorActionPreference = 'Stop'
$port = if ($env:RESEARCH_AGENT_PORT) { $env:RESEARCH_AGENT_PORT } else { '8001' }
$cardUrl = "http://localhost:$port/.well-known/agent-card.json"

Write-Host "Starting Research Agent A2A server on port $port..."
$server = Start-Process python -PassThru -NoNewWindow -ArgumentList @(
    '-m', 'uvicorn', 'research_agent.server:a2a_app', '--host', 'localhost', '--port', $port
)

try {
    $ready = $false
    foreach ($i in 1..30) {
        try {
            Invoke-WebRequest -Uri $cardUrl -UseBasicParsing -TimeoutSec 2 | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) { throw "Research Agent did not start: no Agent Card at $cardUrl" }
    Write-Host "Research Agent is up. Agent Card: $cardUrl"

    switch ($Mode) {
        'web' { adk web }
        'run' { adk run summary_agent }
        'e2e' { python test_e2e.py }
    }
} finally {
    Write-Host 'Stopping Research Agent server...'
    Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
}
