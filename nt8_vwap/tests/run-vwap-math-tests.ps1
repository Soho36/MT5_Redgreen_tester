[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$sourcePath = Join-Path (Split-Path -Parent $PSScriptRoot) 'RTLSessionVWAP.cs'
$source = [System.IO.File]::ReadAllText($sourcePath)
$startMarker = '#region RTL VWAP calculation core'
$start = $source.IndexOf($startMarker, [StringComparison]::Ordinal)
$finish = $source.IndexOf('#endregion', $start, [StringComparison]::Ordinal)
if ($start -lt 0 -or $finish -lt 0) { throw 'Calculation core markers missing.' }
$core = "using System;`r`n" + $source.Substring($start + $startMarker.Length, $finish - $start - $startMarker.Length)
$temporaryBase = Join-Path ([System.IO.Path]::GetTempPath()) ('rtl-vwap-' + [Guid]::NewGuid().ToString('N'))
$corePath = $temporaryBase + '.cs'
$exePath = $temporaryBase + '.exe'
try {
    [System.IO.File]::WriteAllText($corePath, $core)
    & 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe' /nologo /target:exe /out:$exePath $corePath (Join-Path $PSScriptRoot 'VwapMathTests.cs')
    if ($LASTEXITCODE -ne 0) { throw 'VWAP calculation test compile failed.' }
    & $exePath
    if ($LASTEXITCODE -ne 0) { throw 'VWAP calculation test failed.' }
}
finally {
    foreach ($path in @($corePath, $exePath)) {
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
    }
}
