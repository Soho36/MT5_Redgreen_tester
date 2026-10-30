param([string]$NinjaTraderBin = 'C:\Program Files\NinjaTrader 8\bin')
$ErrorActionPreference = 'Stop'
$projectTests = 'I:\PycharmProjects\Accounts_staggering\nt8\tests'
$sources = @(
    'C:\Users\Liikurserv\Documents\NinjaTrader 8\bin\Custom\Strategies\@Strategy.cs',
    'C:\Users\Liikurserv\Documents\NinjaTrader 8\bin\Custom\MarketAnalyzerColumns\@MarketAnalyzerColumn.cs',
    (Join-Path $PSScriptRoot 'RTLSessionVWAP.cs'),
    (Join-Path $PSScriptRoot 'RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_MaxRedRun_VWAP.cs'),
    (Join-Path $PSScriptRoot 'RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_Routed_MaxRedRun_VWAP.cs'),
    'I:\PycharmProjects\RT30_min_nt8_standalone\RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_MaxRedRun.cs',
    'I:\PycharmProjects\Accounts_staggering\nt8\RR_m_w_r_stoplimits_and_tplimit_InstanceID_WindowRR_Offsets_SafeExits_Routed_MaxRedRun.cs',
    'I:\PycharmProjects\Accounts_staggering\nt8\PropRouter.cs'
)
# Compile together to prove original and new strategy names coexist.
& (Join-Path $projectTests 'compile-nt8.ps1') -Sources $sources -NinjaTraderBin $NinjaTraderBin
exit $LASTEXITCODE
