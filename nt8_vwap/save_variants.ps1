[CmdletBinding()]
param([switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'sources.json') -Raw | ConvertFrom-Json
$allowed = @(
    'I:\PycharmProjects\RT30_min_nt8_standalone',
    'I:\PycharmProjects\Accounts_staggering\nt8'
)
$copies = @()
foreach ($entry in $manifest) {
    $actualHash = (Get-FileHash -LiteralPath $entry.source -Algorithm SHA256).Hash
    if ($actualHash -ne $entry.source_sha256) { throw "Original changed since preparation: $($entry.source)" }
    $destinationDirectory = [IO.Path]::GetFullPath((Split-Path -Parent $entry.source))
    if ($allowed -notcontains $destinationDirectory) { throw "Unexpected destination: $destinationDirectory" }
    foreach ($name in @($entry.output, 'RTLSessionVWAP.cs', 'README_VWAP.md')) {
        $source = Join-Path $PSScriptRoot $name
        $destination = Join-Path $destinationDirectory $name
        if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing prepared file: $source" }
        if (Test-Path -LiteralPath $destination) { throw "Refusing to overwrite existing file: $destination" }
        $copies += [pscustomobject]@{ Source = $source; Destination = $destination }
    }
}
foreach ($copy in $copies) {
    if ($CheckOnly) { Write-Host ('Ready: ' + $copy.Destination); continue }
    # Atomic refusal to overwrite; only new sibling files are created.
    [IO.File]::Copy($copy.Source, $copy.Destination, $false)
    if ((Get-FileHash -LiteralPath $copy.Source).Hash -ne (Get-FileHash -LiteralPath $copy.Destination).Hash) {
        throw "Saved-file verification failed: $($copy.Destination)"
    }
    Write-Host ('Saved and verified: ' + $copy.Destination)
}
foreach ($entry in $manifest) {
    if ((Get-FileHash -LiteralPath $entry.source -Algorithm SHA256).Hash -ne $entry.source_sha256) {
        throw "Original hash changed: $($entry.source)"
    }
}
Write-Host 'Both original strategy hashes are unchanged.'
