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
$StateDir = Join-Path $Root '.deployment'
$Port = 8000
$StartOnly = $false
function Get-NetTCPConnection { [pscustomobject]@{OwningProcess=1234;LocalPort=8003} }
function Get-CimInstance { [pscustomobject]@{ExecutablePath=(Join-Path $Root 'base/python.exe'); CommandLine=('python "'+(Join-Path $Backend 'main.py')+'"')} }
function Platform-Ready { return $true }
function Start-Process { param($FilePath); $script:Opened=$FilePath }
$Opened = $null
Invoke-Deployment
if ($Opened -ne 'http://127.0.0.1:8003/slm/dashboard' -or $Port -ne 8003) { throw 'Existing platform port was not reused' }

# 外部程序即使占用 8003，也不会被当作本项目或被终止。
function Get-CimInstance { [pscustomobject]@{ExecutablePath='other.exe';CommandLine='other.exe'} }
if ($null -ne (Find-ProjectListener)) { throw 'Foreign process was reused' }
$StartOnly = $true
function Test-InstalledPlatform { throw 'START_ONLY_CHECK' }
function Find-Python { throw 'Daily startup tried to install an environment' }
$checked = $false
try { Invoke-Deployment } catch { $checked = $_.Exception.Message -eq 'START_ONLY_CHECK' }
if (-not $checked) { throw 'Daily startup did not use installed-only checks' }

Set-PlatformPort 8003
if ($RuleName -ne 'SmartAM-Platform-LAN-8003') { throw 'Firewall rule has wrong port' }
$Profile = 3
function Get-NetFirewallRule { [pscustomobject]@{Enabled='True';Direction='Inbound';Action='Allow';Profile=$Profile} }
function Get-NetFirewallPortFilter { [pscustomobject]@{Protocol='TCP';LocalPort='8003'} }
function Get-NetFirewallAddressFilter { [pscustomobject]@{RemoteAddress='LocalSubnet'} }
if (-not (Firewall-Ready)) { throw 'Existing matching firewall rule was not reused' }
$Profile = 7
if (Firewall-Ready) { throw 'Overly broad firewall rule was accepted' }

# 常规启动的完整分支：后端实际监听 8007，健康检查、防火墙和浏览器必须跟随它。
function Get-NetTCPConnection {
    param($State, $OwningProcess)
    if ($null -ne $OwningProcess -and 7790 -in $OwningProcess) { [pscustomobject]@{OwningProcess=7790;LocalPort=8007} }
}
function Get-CimInstance {
    param($ClassName, $Filter)
    if ($Filter -eq 'ParentProcessId=7788') { [pscustomobject]@{ProcessId=7790} }
}
function Test-InstalledPlatform { $script:CheckedInstalled=$true }
$fakeProcess = [pscustomobject]@{Id=7788;HasExited=$false;ExitCode=0}
$fakeProcess | Add-Member ScriptMethod WaitForExit { }
function Start-Process {
    param($FilePath, $ArgumentList, $WorkingDirectory, [switch]$NoNewWindow, [switch]$PassThru)
    if ($FilePath -eq $Python) { return $fakeProcess }
    $script:Opened = $FilePath
}
function Firewall-Ready { $script:FirewallPort=$Port; return $true }
function Get-NetConnectionProfile { }
function Get-NetIPAddress { [pscustomobject]@{IPAddress='192.168.1.20'} }
$lock = [pscustomobject]@{}
$lock | Add-Member ScriptMethod Dispose { }
$CheckedInstalled=$false
Invoke-Deployment
if (-not $CheckedInstalled -or $FirewallPort -ne 8007 -or $Opened -ne 'http://127.0.0.1:8007/slm/dashboard') { throw 'Daily startup did not follow the actual listener port' }

$hostExecutable = [Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
$failed = $false
try { Invoke-Checked $hostExecutable @('-NoProfile', '-Command', 'exit 7') }
catch { $failed = $_.Exception.Message.Contains('7') }
if (-not $failed) { throw 'Native installer failure was swallowed' }
Write-Host 'PASS: parse, reuse alternate port, protect foreign process, daily startup, dynamic firewall, native failure'
