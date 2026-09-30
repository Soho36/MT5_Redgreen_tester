# Corrected repeat of the user's exact RR grid. No source or user profile edits.
$ErrorActionPreference = 'Stop'
$study = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\Reports\rr_cap3_corrected_20260930'))
$terminal = 'I:\Programs\1AMP Global (USA) MT5 Exchange-Traded Futures Only\terminal64.exe'
$data = Join-Path $env:APPDATA 'MetaQuotes\Terminal\F5855995045EF8A4C3CA7AE968872CF2'
$common = Join-Path $env:APPDATA 'MetaQuotes\Terminal\Common\Files'
$active = Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $terminal }
if ($active) { throw 'AMP terminal is already running; leave it undisturbed.' }
$logOffsets = @{}
Get-ChildItem -LiteralPath (Join-Path $data 'Tester\logs') -Filter '*.log' -File | ForEach-Object { $logOffsets[$_.FullName]=$_.Length }
$started = [DateTime]::UtcNow
@{started_utc=$started.ToString('o'); expert_sha256=(Get-FileHash -LiteralPath (Join-Path $data 'MQL5\Experts\CodexLocationValidation\RTL_runband_location.ex5')).Hash} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $study 'started.json') -Encoding utf8
$process = Start-Process -FilePath $terminal -ArgumentList ('/config:"'+(Join-Path $study 'optimization.ini')+'"') -WindowStyle Hidden -PassThru
$lastCount = -1
while (-not $process.WaitForExit(5000)) {
    $count = @(Get-ChildItem -LiteralPath $common -Filter 'runband_rr_cap3_corrected_20260930_*_stats.csv' -File | Where-Object { $_.LastWriteTimeUtc -ge $started }).Count
    if ($count -ne $lastCount) { Write-Output "Completed pass exports: $count / 46"; $lastCount=$count }
    if (([DateTime]::UtcNow-$started).TotalMinutes -gt 30) { throw 'Optimization exceeded 30 minutes; terminal left running for inspection.' }
}
$logText = ''
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $data 'Tester\logs') -Filter '*.log' -File) {
    $offset = if ($logOffsets.ContainsKey($file.FullName)) { [long]$logOffsets[$file.FullName] } else { 0L }
    if ($file.Length -le $offset) { continue }
    $stream = [System.IO.File]::Open($file.FullName, 'Open', 'Read', 'ReadWrite')
    try {
        [void]$stream.Seek($offset,'Begin')
        $reader=[System.IO.StreamReader]::new($stream,[System.Text.Encoding]::Unicode,$true)
        $logText += $reader.ReadToEnd()
        $reader.Dispose()
    } finally { $stream.Dispose() }
}
[System.IO.File]::WriteAllText((Join-Path $study 'tester.log'),$logText,[System.Text.Encoding]::UTF8)
$exports = @(Get-ChildItem -LiteralPath $common -Filter 'runband_rr_cap3_corrected_20260930_*.csv' -File | Where-Object { $_.LastWriteTimeUtc -ge $started })
if ($exports.Count -ne 92) { throw "Expected 92 fresh trade/stats files; found $($exports.Count). Inspect logs." }
$exports | Copy-Item -Destination $study
Get-ChildItem -LiteralPath $data -Filter 'rr_cap3_corrected_20260930*' -File | Copy-Item -Destination $study
@{started_utc=$started.ToString('o'); ended_utc=[DateTime]::UtcNow.ToString('o'); exit_code=$process.ExitCode; exports=$exports.Count} |
    ConvertTo-Json | Set-Content -LiteralPath (Join-Path $study 'completed.json') -Encoding utf8
Write-Output 'Finished corrected 46-pass optimization; evidence copied.'
