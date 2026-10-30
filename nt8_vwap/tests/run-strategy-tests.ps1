[CmdletBinding()]
param(
    [string]$SourceRoot,
    [string]$LegacyRoutedSource = 'I:\PycharmProjects\Accounts_staggering\nt8\RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_Routed_MaxRedRun.cs'
)
$ErrorActionPreference = 'Stop'
if (-not $SourceRoot) { $SourceRoot = Split-Path -Parent $PSScriptRoot }

function Extract-Method([string]$Source, [string]$Start, [string]$Next) {
    $begin = $Source.IndexOf($Start, [StringComparison]::Ordinal)
    if ($begin -lt 0) { throw "Method not found: $Start" }
    $end = $Source.IndexOf($Next, $begin, [StringComparison]::Ordinal)
    if ($end -lt 0) { throw "Method boundary not found: $Next" }
    return $Source.Substring($begin, $end - $begin)
}

$standalone = [IO.File]::ReadAllText((Join-Path $SourceRoot 'RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_MaxRedRun_VWAP.cs'))
$routed = [IO.File]::ReadAllText((Join-Path $SourceRoot 'RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_Routed_MaxRedRun_VWAP.cs'))
$legacy = [IO.File]::ReadAllText($LegacyRoutedSource)
$template = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'strategy_gate_tests.cs.txt'))
$code = $template.Replace('/* STANDALONE GATE */', (Extract-Method $standalone 'private bool IsVwapEntryRejected(' 'private bool ExceedsMaxRedRun('))
$code = $code.Replace('/* ROUTED GATE */', (Extract-Method $routed 'private bool IsVwapEntryRejected(' 'private bool ExceedsMaxRedRun('))
$code = $code.Replace('/* ROUTED CONFIG */', (Extract-Method $routed 'private string BuildRouterConfigKey(' 'private bool IsAccountConnected('))
$code = $code.Replace('/* LEGACY CONFIG */', (Extract-Method $legacy 'private string BuildRouterConfigKey(' 'private bool IsAccountConnected('))
Add-Type -TypeDefinition $code
$count = [VwapStrategyTests]::Run()
Write-Host "PASS: $count strategy gate and router manifest assertions (actual extracted production methods)."
