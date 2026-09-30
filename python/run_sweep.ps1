# Runs single MT5 tests from a template INI, one per (tag, from, to, MaxRedRun).
# Usage: run_sweep.ps1 -OutDir <dir> -Jobs "tag|from|to|maxrun", ...
param([string]$OutDir, [string[]]$Jobs)

$terminal = "I:\Programs\1AMP Global (USA) MT5 Exchange-Traded Futures Only\terminal64.exe"
$dataDir  = "$env:APPDATA\MetaQuotes\Terminal\F5855995045EF8A4C3CA7AE968872CF2"
$common   = "$env:APPDATA\MetaQuotes\Terminal\Common\Files"
$template = Get-Content "I:\PycharmProjects\MT5_Redgreen_tester\Reports\location_validation_20260929\early_off.ini" -Raw -Encoding Unicode
New-Item -ItemType Directory -Force $OutDir | Out-Null

foreach ($job in $Jobs) {
    $tag, $from, $to, $maxRun = $job.Split('|')
    $ini = $template `
        -replace 'codex_location_20260929_early_off', $tag `
        -replace '(?m)^FromDate=.*$', "FromDate=$from" `
        -replace '(?m)^ToDate=.*$',   "ToDate=$to" `
        -replace '(?m)^MaxRedRun=.*$', "MaxRedRun=$maxRun"
    $iniPath = Join-Path $OutDir "$tag.ini"
    Set-Content $iniPath $ini -Encoding Unicode -NoNewline

    $p = Start-Process -FilePath $terminal -ArgumentList "/config:`"$iniPath`"" -PassThru
    $p.WaitForExit()

    Copy-Item "$common\runband_${tag}_1.00*.csv" $OutDir
    Copy-Item "$dataDir\$tag*" $OutDir -ErrorAction SilentlyContinue
    "$tag done (exit $($p.ExitCode))"
}
