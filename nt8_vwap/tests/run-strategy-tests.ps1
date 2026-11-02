[CmdletBinding()]
param(
    [switch]$GG,
    [string]$SourceRoot,
    [string]$LegacyRoutedSource = 'I:\PycharmProjects\Accounts_staggering\nt8\RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_Routed_MaxRedRun.cs'
)
$ErrorActionPreference = 'Stop'
if (-not $SourceRoot) { $SourceRoot = Split-Path -Parent $PSScriptRoot }
if ($GG) { $LegacyRoutedSource = $LegacyRoutedSource.Replace('RR_m_', 'GG_m_').Replace('MaxRedRun', 'MaxGreenRun') }

function Extract-Method([string]$Source, [string]$Start, [string]$Next) {
    $begin = $Source.IndexOf($Start, [StringComparison]::Ordinal)
    if ($begin -lt 0) { throw "Method not found: $Start" }
    $end = $Source.IndexOf($Next, $begin, [StringComparison]::Ordinal)
    if ($end -lt 0) { throw "Method boundary not found: $Next" }
    return $Source.Substring($begin, $end - $begin)
}

$standaloneName = 'RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_MaxRedRun_VWAP.cs'
$routedName = 'RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_Routed_MaxRedRun_VWAP.cs'
if ($GG) {
    $standaloneName = $standaloneName.Replace('RR_m_', 'GG_m_').Replace('MaxRedRun', 'MaxGreenRun')
    $routedName = $routedName.Replace('RR_m_', 'GG_m_').Replace('MaxRedRun', 'MaxGreenRun')
}
$standalone = [IO.File]::ReadAllText((Join-Path $SourceRoot $standaloneName))
$routed = [IO.File]::ReadAllText((Join-Path $SourceRoot $routedName))
$legacy = [IO.File]::ReadAllText($LegacyRoutedSource)
$template = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'strategy_gate_tests.cs.txt'))
$cap = 'MaxRedRun'
if ($GG) { $template = $template.Replace('MaxRedRun', 'MaxGreenRun'); $cap = 'MaxGreenRun' }
$code = $template.Replace('/* STANDALONE GATE */', (Extract-Method $standalone 'private bool IsVwapEntryRejected(' ('private bool Exceeds' + $cap + '(')))
$code = $code.Replace('/* ROUTED GATE */', (Extract-Method $routed 'private bool IsVwapEntryRejected(' ('private bool Exceeds' + $cap + '(')))
$code = $code.Replace('/* ROUTED CONFIG */', (Extract-Method $routed 'private string BuildRouterConfigKey(' 'private bool IsAccountConnected('))
$code = $code.Replace('/* LEGACY CONFIG */', (Extract-Method $legacy 'private string BuildRouterConfigKey(' 'private bool IsAccountConnected('))
Add-Type -TypeDefinition $code
$count = [VwapStrategyTests]::Run()
Write-Host "PASS: $count strategy gate and router manifest assertions (actual extracted production methods)."
