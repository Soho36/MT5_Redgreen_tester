param([string]$StudyDir = (Join-Path $PSScriptRoot '..\Reports\exit_thresholds_20260930'))
$ErrorActionPreference = 'Stop'
$StudyDir = (Resolve-Path -LiteralPath $StudyDir).Path
$taskTerminal = 'I:\Programs\1AMP Global (USA) MT5 Exchange-Traded Futures Only\terminal64.exe'
$taskData = Join-Path $env:APPDATA 'MetaQuotes\Terminal\F5855995045EF8A4C3CA7AE968872CF2'
$taskCommon = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
$taskAgentLogs = Join-Path $env:APPDATA 'MetaQuotes\Tester\F5855995045EF8A4C3CA7AE968872CF2\Agent-127.0.0.1-3000\logs'
$taskManifest = Get-Content -LiteralPath (Join-Path $StudyDir 'manifest.json') -Raw | ConvertFrom-Json

function Assert-TerminalIdle {
    $active = Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $taskTerminal }
    if ($active) { throw 'AMP terminal is already running; leave it undisturbed.' }
}

function Get-LogOffsets {
    $offsets = @{}
    foreach ($dir in @((Join-Path $taskData 'Tester\logs'), $taskAgentLogs)) {
        Get-ChildItem -LiteralPath $dir -Filter '*.log' -File | ForEach-Object { $offsets[$_.FullName] = $_.Length }
    }
    return $offsets
}

function Save-NewLogs($before, $tag) {
    foreach ($kind in @('tester','agent')) {
        $dir = if ($kind -eq 'tester') { Join-Path $taskData 'Tester\logs' } else { $taskAgentLogs }
        $text = ''
        foreach ($file in Get-ChildItem -LiteralPath $dir -Filter '*.log' -File) {
            $offset = if ($before.ContainsKey($file.FullName)) { [long]$before[$file.FullName] } else { 0L }
            if ($file.Length -le $offset) { continue }
            $stream = [System.IO.File]::Open($file.FullName, 'Open', 'Read', 'ReadWrite')
            try {
                [void]$stream.Seek($offset, 'Begin')
                $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::Unicode, $true)
                $text += $reader.ReadToEnd()
                $reader.Dispose()
            } finally { $stream.Dispose() }
        }
        [System.IO.File]::WriteAllText((Join-Path $StudyDir "$tag.$kind.log"), $text, [System.Text.Encoding]::UTF8)
        if ($kind -eq 'tester' -and $text -notmatch 'automatic testing finished') {
            throw "No completed-test evidence for $tag"
        }
    }
}

Assert-TerminalIdle
$taskInstall = Join-Path $taskData 'MQL5\Experts\CodexExitResearch'
New-Item -ItemType Directory -Path $taskInstall -Force | Out-Null
foreach ($ext in @('mq5','ex5')) {
    Copy-Item -LiteralPath (Join-Path $StudyDir "RTL_exit_comparison.$ext") -Destination $taskInstall -Force
}
foreach ($job in $taskManifest.jobs) {
    $done = Join-Path $StudyDir ($job.tag + '.completed.json')
    if (Test-Path -LiteralPath $done) { Write-Output "Already completed: $($job.tag)"; continue }
    Assert-TerminalIdle
    $offsets = Get-LogOffsets
    $start = [DateTime]::UtcNow
    $process = Start-Process -FilePath $taskTerminal -ArgumentList ('/config:"' + $job.ini + '"') -WindowStyle Hidden -PassThru
    while (-not $process.WaitForExit(5000)) {
        if (([DateTime]::UtcNow - $start).TotalSeconds -gt 180) {
            throw "MT5 exceeded 180 seconds for $($job.tag); process left running for inspection."
        }
    }
    Save-NewLogs $offsets $job.tag
    foreach ($name in @($job.csv, ($job.csv -replace '\.csv$', '_stats.csv'))) {
        $path = Join-Path $taskCommon $name
        if ((Get-Item -LiteralPath $path).LastWriteTimeUtc -lt $start) { throw "Stale export $path" }
        Copy-Item -LiteralPath $path -Destination $StudyDir
    }
    Copy-Item -LiteralPath (Join-Path $taskData $job.report) -Destination $StudyDir
    Get-ChildItem -LiteralPath $taskData -Filter ($job.tag + '*.png') -File | Copy-Item -Destination $StudyDir
    @{tag=$job.tag; started_utc=$start.ToString('o'); ended_utc=[DateTime]::UtcNow.ToString('o'); exit_code=$process.ExitCode} |
        ConvertTo-Json | Set-Content -LiteralPath $done -Encoding utf8
    Write-Output "Completed $($job.tag) in $([math]::Round(([DateTime]::UtcNow-$start).TotalSeconds,1)) seconds"
}
