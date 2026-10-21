# 只加载被测函数并替换系统操作，不安装软件、不配置防火墙、不启动服务。
$ErrorActionPreference = 'Stop'
$file = Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts/deploy_windows.ps1'
$tokens = $null
$parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($file, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -gt 0) { throw ($parseErrors | Out-String) }
foreach ($definition in $ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst]}, $false)) {
    Invoke-Expression $definition.Extent.Text
}

$Root = Join-Path ([IO.Path]::GetTempPath()) 'SmartAM path 测试'
$Backend = Join-Path $Root 'backend'
$Python = Join-Path $Root '.venv/Scripts/python.exe'
$Url = 'http://127.0.0.1:8000/slm/dashboard'
function Get-NetTCPConnection { [pscustomobject]@{OwningProcess=1234} }
function Get-CimInstance { [pscustomobject]@{ExecutablePath=$Python; CommandLine=('python "'+(Join-Path $Backend 'main.py')+'"')} }
function Platform-Ready { return $true }
function Start-Process { $script:Opened=$true }
$Opened = $false
Invoke-Deployment
if (-not $Opened) { throw 'Existing platform was not reused' }

function Get-CimInstance { [pscustomobject]@{ExecutablePath='other.exe';CommandLine='other.exe'} }
$rejected = $false
try { Invoke-Deployment } catch { $rejected = $_.Exception.Message.Contains('1234') }
if (-not $rejected) { throw 'Foreign process was not protected' }

$RuleName = 'SmartAM-Platform-LAN-8000'
$Profile = 3
function Get-NetFirewallRule { [pscustomobject]@{Enabled='True';Direction='Inbound';Action='Allow';Profile=$Profile} }
function Get-NetFirewallPortFilter { [pscustomobject]@{Protocol='TCP';LocalPort='8000'} }
function Get-NetFirewallAddressFilter { [pscustomobject]@{RemoteAddress='LocalSubnet'} }
if (-not (Firewall-Ready)) { throw 'Existing matching firewall rule was not reused' }
$Profile = 7
if (Firewall-Ready) { throw 'Overly broad firewall rule was accepted' }

$hostExecutable = [Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
$failed = $false
try { Invoke-Checked $hostExecutable @('-NoProfile', '-Command', 'exit 7') }
catch { $failed = $_.Exception.Message.Contains('7') }
if (-not $failed) { throw 'Native installer failure was swallowed' }
Write-Host 'PASS: parse, existing service, occupied port, firewall scope, native failure'
