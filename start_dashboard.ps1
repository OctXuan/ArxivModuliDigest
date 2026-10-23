$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

$python = Get-Command python -ErrorAction SilentlyContinue
$pythonArgs = @()
if ($python) {
  & $python.Source --version *> $null
  if ($LASTEXITCODE -ne 0) { $python = $null }
}
if (-not $python) {
  $python = Get-Command py -ErrorAction SilentlyContinue
  $pythonArgs = @('-3')
  if ($python) {
    & $python.Source @pythonArgs --version *> $null
    if ($LASTEXITCODE -ne 0) { $python = $null }
  }
}
if (-not $python) { Write-Error "Python 3.10+ was not found. Install Python and make sure python or py is on PATH."; exit 1 }

Write-Host "Fetching the latest arXiv papers..."
& $python.Source @pythonArgs .\arxiv_digest.py --include-seen
if ($LASTEXITCODE -ne 0) { Write-Error "Paper fetch failed. Check your network connection and try again."; exit $LASTEXITCODE }

$port = 8765
$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $port)
try { $listener.Start(); $listener.Stop() } catch { $listener.Stop(); $port = 8766 }
$url = "http://127.0.0.1:$port/"
$serverArgs = $pythonArgs + @("-m", "http.server", "$port", "--bind", "127.0.0.1")
Start-Process -FilePath $python.Source -ArgumentList $serverArgs -WorkingDirectory $projectDir -WindowStyle Hidden
Start-Sleep -Milliseconds 800
Start-Process $url
Write-Host "Dashboard is running at $url"
