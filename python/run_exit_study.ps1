param([string]$StudyDir = (Join-Path $PSScriptRoot '..\Reports\exit_thresholds_20260930'),
      [string]$ExpertName = 'RTL_exit_comparison',     # <name>.mq5/.ex5 inside StudyDir
      [string]$InstallFolder = 'CodexExitResearch',    # MQL5\Experts subfolder the INIs reference
      [ValidateRange(1,86400)][int]$TimeoutSeconds = 180,
      [string]$OnlyTag = '')
$ErrorActionPreference = 'Stop'
$StudyDir = (Resolve-Path -LiteralPath $StudyDir).Path
$taskTerminal = 'I:\Programs\1AMP Global (USA) MT5 Exchange-Traded Futures Only\terminal64.exe'
$taskData = Join-Path $env:APPDATA 'MetaQuotes\Terminal\F5855995045EF8A4C3CA7AE968872CF2'
$taskCommon = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
$taskAgentLogs = Join-Path $env:APPDATA 'MetaQuotes\Tester\F5855995045EF8A4C3CA7AE968872CF2\Agent-127.0.0.1-3000\logs'
$taskManifest = Get-Content -LiteralPath (Join-Path $StudyDir 'manifest.json') -Raw | ConvertFrom-Json
$taskJobs = @($taskManifest.jobs | Where-Object { $OnlyTag -eq '' -or $_.tag -eq $OnlyTag })
if ($taskJobs.Count -eq 0) { throw "No study job matches $OnlyTag" }

function Assert-TerminalIdle {
    $active = Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $taskTerminal }
    if ($active) { throw 'AMP terminal is already running; leave it undisturbed.' }
}

function Get-LogFence([string]$Path, [long]$Length) {
    $stream = [System.IO.File]::Open($Path, 'Open', 'Read', 'ReadWrite')
    try {
        $count = [int][math]::Min(128L, $Length)
        [void]$stream.Seek($Length - $count, 'Begin')
        $buffer = [byte[]]::new($count)
        $read = $stream.Read($buffer, 0, $count)
        return [Convert]::ToBase64String($buffer, 0, $read)
    } finally { $stream.Dispose() }
}

function Get-LogOffsets {
    $offsets = @{}
    foreach ($dir in @((Join-Path $taskData 'Tester\logs'), $taskAgentLogs)) {
        Get-ChildItem -LiteralPath $dir -Filter '*.log' -File | ForEach-Object {
            $offsets[$_.FullName] = @{ Length=$_.Length; Fence=(Get-LogFence $_.FullName $_.Length) }
        }
    }
    return $offsets
}

function Save-NewLogs($before, $tag) {
    foreach ($kind in @('tester','agent')) {
        $dir = if ($kind -eq 'tester') { Join-Path $taskData 'Tester\logs' } else { $taskAgentLogs }
        $text = ''
        foreach ($file in Get-ChildItem -LiteralPath $dir -Filter '*.log' -File) {
            $offset = 0L
            if ($before.ContainsKey($file.FullName)) {
                $previous = $before[$file.FullName]
                # MT5 can truncate a large log during a run, then grow it again.
                # A byte fence detects replacement even if its new size is larger.
                if ($file.Length -ge $previous.Length -and (Get-LogFence $file.FullName $previous.Length) -eq $previous.Fence) {
                    $offset = [long]$previous.Length
                }
            }
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
$taskInstall = Join-Path $taskData "MQL5\Experts\$InstallFolder"
New-Item -ItemType Directory -Path $taskInstall -Force | Out-Null
foreach ($ext in @('mq5','ex5')) {
    Copy-Item -LiteralPath (Join-Path $StudyDir "$ExpertName.$ext") -Destination $taskInstall -Force
}
Get-ChildItem -LiteralPath $StudyDir -Filter '*.mqh' -File | Copy-Item -Destination $taskInstall -Force
foreach ($job in $taskJobs) {
    $done = Join-Path $StudyDir ($job.tag + '.completed.json')
    if (Test-Path -LiteralPath $done) { Write-Output "Already completed: $($job.tag)"; continue }
    Assert-TerminalIdle
    $offsets = Get-LogOffsets
    $start = [DateTime]::UtcNow
    $process = Start-Process -FilePath $taskTerminal -ArgumentList ('/config:"' + $job.ini + '"') -WindowStyle Hidden -PassThru
    while (-not $process.WaitForExit(5000)) {
        if (([DateTime]::UtcNow - $start).TotalSeconds -gt $TimeoutSeconds) {
            throw "MT5 exceeded $TimeoutSeconds seconds for $($job.tag); process left running for inspection."
        }
    }
    Save-NewLogs $offsets $job.tag
    if ($process.ExitCode -ne 0) { throw "MT5 exited with code $($process.ExitCode) for $($job.tag)" }
    $taskExports = @($job.csv, ($job.csv -replace '\.csv$', '_stats.csv'))
    if ($job.extra_csv) { $taskExports += @($job.extra_csv) }
    foreach ($name in $taskExports) {
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
