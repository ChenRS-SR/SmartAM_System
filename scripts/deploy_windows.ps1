param([switch]$ConfigureFirewall)

# 批处理只负责入口；检测、退出码和含中文/空格的路径由 PowerShell 处理。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONUTF8 = '1'
$Root = Split-Path -Parent $PSScriptRoot
$StateDir = Join-Path $Root '.deployment'
$Frontend = Join-Path $Root 'frontend'
$Backend = Join-Path $Root 'backend'
$Venv = Join-Path $Root '.venv'
$Python = Join-Path $Venv 'Scripts\python.exe'
$StateTool = Join-Path $PSScriptRoot 'deployment_state.py'
$Url = 'http://127.0.0.1:8000/slm/dashboard'
$RuleName = 'SmartAM-Platform-LAN-8000'

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "命令执行失败（退出码 $LASTEXITCODE）：$Program $($Arguments -join ' ')"
    }
}

function Refresh-Path {
    # 安装器更新注册表 PATH 后，使当前窗口立即可用；保留已有环境的搜索路径。
    $env:Path = $env:Path + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}

function Find-Python {
    $candidates = @()
    if (Test-Path $Python) { $candidates += $Python }
    $candidates += @(Get-Command python.exe -All -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    foreach ($registry in @('HKCU:\Software\Python\PythonCore', 'HKLM:\Software\Python\PythonCore')) {
        foreach ($version in @(Get-ChildItem $registry -ErrorAction SilentlyContinue)) {
            $install = Get-Item (Join-Path $version.PSPath 'InstallPath') -ErrorAction SilentlyContinue
            if ($null -ne $install) { $candidates += Join-Path $install.GetValue('') 'python.exe' }
        }
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        # WindowsApps 的商店占位符不等于已安装的 Python。
        if ($candidate -like '*\WindowsApps\*' -or -not (Test-Path $candidate)) { continue }
        $resolved = & $candidate -c "import sys,struct; sys.exit(1) if not ((3,10) <= sys.version_info[:2] < (3,14) and struct.calcsize('P')==8) else print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0) { return [string]$resolved }
    }
    return $null
}

function Find-Node {
    $candidates = @(Get-Command node.exe -All -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source)
    $candidates += Join-Path $env:ProgramFiles 'nodejs\node.exe'
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (-not (Test-Path $candidate)) { continue }
        # 与仓库现有 jsdom/Vitest 的引擎要求保持一致，避免仅能构建但安装报错。
        & $candidate -e "const [a,b]=process.versions.node.split('.').map(Number);process.exit(((a===20&&b>=19)||(a===22&&b>=12)||a>=24)&&process.arch==='x64'?0:1)" 2>$null
        if ($LASTEXITCODE -eq 0 -and (Test-Path (Join-Path (Split-Path $candidate) 'npm.cmd'))) { return $candidate }
    }
    return $null
}

function Install-Runtime {
    param([string]$Id)
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($null -eq $winget) {
        throw "缺少运行环境且未找到 WinGet。请安装 Windows‘应用安装程序’，或先安装 Python 3.10–3.13 x64 和 Node.js LTS，再重运行本脚本。"
    }
    Invoke-Checked $winget.Source @('install', '--id', $Id, '--exact', '--source', 'winget', '--architecture', 'x64', '--accept-package-agreements', '--accept-source-agreements')
    Refresh-Path
}

function Firewall-Ready {
    $rule = Get-NetFirewallRule -Name $RuleName -ErrorAction SilentlyContinue
    if ($null -eq $rule) { return $false }
    $port = $rule | Get-NetFirewallPortFilter
    $address = $rule | Get-NetFirewallAddressFilter
    return ($rule.Enabled -eq 'True' -and $rule.Direction -eq 'Inbound' -and $rule.Action -eq 'Allow' -and
        [int]$rule.Profile -eq 3 -and [string]$port.Protocol -eq 'TCP' -and
        [string]$port.LocalPort -eq '8000' -and [string]$address.RemoteAddress -eq 'LocalSubnet')
}

function Set-LanFirewall {
    # 只管理本应用命名的规则，仅允许可信网络上的本地子网访问 8000。
    $rule = Get-NetFirewallRule -Name $RuleName -ErrorAction SilentlyContinue
    if ($null -eq $rule) {
        New-NetFirewallRule -Name $RuleName -DisplayName 'SmartAM Platform (LAN TCP 8000)' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -Profile Domain,Private -RemoteAddress LocalSubnet | Out-Null
    } else {
        Set-NetFirewallRule -Name $RuleName -Enabled True -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000 -Profile Domain,Private -RemoteAddress LocalSubnet | Out-Null
    }
    if (-not (Firewall-Ready)) { throw '局域网防火墙规则未生效，请检查系统策略。' }
}

function Platform-Ready {
    # 健康检查直连回环地址，不能被客户端的 Privoxy/系统代理接管。
    $request = [Net.HttpWebRequest]::Create('http://127.0.0.1:8000/api/device-type/current')
    $request.Proxy = $null
    $request.Timeout = 1000
    $request.ReadWriteTimeout = 1000
    $reader = $null
    $response = $null
    try {
        $response = $request.GetResponse()
        $reader = New-Object IO.StreamReader($response.GetResponseStream())
        $data = $reader.ReadToEnd() | ConvertFrom-Json
        return $data.success -eq $true
    } catch [System.Net.WebException] {
        return $false
    } finally {
        if ($null -ne $reader) { $reader.Dispose() }
        if ($null -ne $response) { $response.Dispose() }
    }
}

function Invoke-Deployment {
    $listeners = @(Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue)
    if ($listeners.Count -gt 0) {
        $owner = Get-CimInstance Win32_Process -Filter "ProcessId=$($listeners[0].OwningProcess)"
        $mainFile = Join-Path $Backend 'main.py'
        if ($owner.ExecutablePath -eq $Python -and $null -ne $owner.CommandLine -and $owner.CommandLine.Contains($mainFile) -and (Platform-Ready)) {
            Write-Host '本项目已运行，跳过安装和启动，打开现有页面。更新代码后请先关闭原服务窗口再启动。' -ForegroundColor Green
            Start-Process $Url
            return
        }
        throw "8000 端口已被进程 $($listeners[0].OwningProcess) 占用。请先确认并关闭该服务，本脚本不会强制终止它。"
    }

    Write-Host '[1/6] 检查 Python 和项目环境'
    $basePython = Find-Python
    if (Test-Path $Venv) {
        if ($basePython -ne $Python) { throw '.venv 已存在但 Python 不可用或版本不兼容。请先检查该目录，不会自动删除重建。' }
        Write-Host '项目虚拟环境可用，跳过创建。'
    } else {
        if ($null -eq $basePython) {
            Install-Runtime 'Python.Python.3.13'
            $basePython = Find-Python
            if ($null -eq $basePython) { throw '安装后仍未找到合适的 Python，请检查安装输出。' }
        }
        Invoke-Checked $basePython @('-m', 'venv', $Venv)
    }
    # torch / OpenCV 的 Windows 二进制依赖 VC++ x64 运行库，已有安装则不重复安装。
    $vcRuntime = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64' -ErrorAction SilentlyContinue
    if ($null -eq $vcRuntime -or $vcRuntime.Installed -ne 1 -or [version]($vcRuntime.Version -replace '^v', '') -lt [version]'14.29') {
        Install-Runtime 'Microsoft.VCRedist.2015+.x64'
    } else { Write-Host 'VC++ x64 运行库已安装，跳过。' }

    Write-Host '[2/6] 检查 Node.js 和 npm'
    $node = Find-Node
    if ($null -eq $node) {
        Install-Runtime 'OpenJS.NodeJS.LTS'
        $node = Find-Node
        if ($null -eq $node) { throw '安装后仍未找到合适的 Node.js/npm，请检查安装输出。' }
    }
    $env:Path = (Split-Path $node) + ';' + $env:Path
    $npm = Join-Path (Split-Path $node) 'npm.cmd'
    $runtime = (& $node --version) + '/' + (& $npm --version) + '/win32-x64'
    Write-Host "使用 $node ($runtime)"

    Write-Host '[3/6] 检查后端依赖'
    & $Python $StateTool check-backend
    if ($LASTEXITCODE -ne 0) {
        Invoke-Checked $Python @('-m', 'pip', 'install', '-r', (Join-Path $Backend 'requirements.txt'))
        Invoke-Checked $Python @($StateTool, 'check-backend')
    } else { Write-Host '后端依赖及版本检查通过，跳过安装。' }
    Invoke-Checked $Python @('-c', 'import fastapi, uvicorn, cv2, torch, torchvision, pandas, sklearn')

    Write-Host '[4/6] 检查前端依赖和构建'
    Push-Location $Frontend
    try {
        & $Python $StateTool check-frontend --runtime $runtime
        $dependenciesReady = $LASTEXITCODE -eq 0
        if ($dependenciesReady) {
            & $npm ls --all --include=dev *> $null
            $dependenciesReady = $LASTEXITCODE -eq 0
        }
        if (-not $dependenciesReady) {
            # 锁文件固定版本；失败时不写成功记录，下次重新检查。
            Invoke-Checked $npm @('ci', '--include=dev', '--no-audit', '--no-fund')
            Invoke-Checked $Python @($StateTool, 'record-frontend', '--runtime', $runtime)
        } else { Write-Host '前端依赖未变化且安装完整，跳过安装。' }
        $env:VITE_API_BASE_URL = ''
        $env:VITE_MOCK_MODE = 'false'
        & $Python $StateTool check-build --runtime $runtime
        if ($LASTEXITCODE -ne 0 -or -not $dependenciesReady) {
            # Windows PowerShell 5.1 会删除空环境变量；由 Python 写入真正的空值。
            Invoke-Checked $Python @($StateTool, 'build')
            Invoke-Checked $Python @($StateTool, 'record-build', '--runtime', $runtime)
        } else { Write-Host '源码、构建配置和产物均未变化，跳过构建。' }
    } finally { Pop-Location }

    Write-Host '[5/6] 检查局域网防火墙规则'
    if (-not (Firewall-Ready)) {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $principal = New-Object Security.Principal.WindowsPrincipal($identity)
        if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { Set-LanFirewall }
        else {
            Write-Host '首次配置需允许 Windows 管理员确认，仅放行本地子网 TCP 8000。'
            $elevated = Start-Process powershell.exe -Verb RunAs -Wait -PassThru -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "' + $PSCommandPath + '" -ConfigureFirewall')
            if ($elevated.ExitCode -ne 0 -or -not (Firewall-Ready)) { throw '防火墙配置未完成，请允许管理员确认后重新运行。' }
        }
    } else { Write-Host '防火墙规则已就绪，跳过配置。' }
    $publicNetworks = @(Get-NetConnectionProfile | Where-Object NetworkCategory -eq 'Public')
    if ($publicNetworks.Count -gt 0) { Write-Host '注意：公用网络不在放行范围内；可信的工厂局域网请在 Windows 中设为专用网络。' -ForegroundColor Yellow }

    Write-Host '[6/6] 启动平台'
    $env:SMARTAM_RELOAD = '0'
    $env:SMARTAM_ACCESS_LOG = '0'
    $process = Start-Process -FilePath $Python -ArgumentList ('"' + (Join-Path $Backend 'main.py') + '"') -WorkingDirectory $Backend -NoNewWindow -PassThru
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($process.HasExited) { throw "后端启动失败（退出码 $($process.ExitCode)），请检查 logs 目录。" }
        if (Platform-Ready) { $ready = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) {
        # 只结束本次创建且未就绪的进程，不影响其他服务。
        Stop-Process -Id $process.Id
        throw '60 秒内服务未就绪，已停止本次启动的进程，请检查日志后重试。'
    }
    Write-Host "本机访问：$Url" -ForegroundColor Green
    Get-NetIPAddress -AddressFamily IPv4 -AddressState Preferred |
        Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' } |
        ForEach-Object { Write-Host "网卡地址：http://$($_.IPAddress):8000/slm/dashboard" }
    Write-Host '请选择访问电脑可达的网卡地址。保持此窗口打开，Ctrl+C 停止服务。' -ForegroundColor Green
    Start-Process $Url
    # 完成部署后释放锁，重复双击可识别已有进程并直接打开页面。
    $script:lock.Dispose()
    $script:lock = $null
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "平台退出，退出码：$($process.ExitCode)" }
}

$lock = $null
$transcript = $false
try {
    if ($ConfigureFirewall) { Set-LanFirewall; exit 0 }
    if (-not [Environment]::Is64BitOperatingSystem) { throw '此部署脚本需要 Windows 10/11 x64。' }
    New-Item -ItemType Directory -Path $StateDir -Force | Out-Null
    # 文件锁跨窗口生效；异常退出后由系统释放，不会留下永久锁定状态。
    try { $lock = [IO.File]::Open((Join-Path $StateDir 'deploy.lock'), 'OpenOrCreate', 'ReadWrite', 'None') }
    catch [IO.IOException] { throw '已有部署窗口正在安装或启动，请等待它完成；不要同时重复安装。' }
    $logDir = Join-Path $Root 'logs\deployment'
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    Get-ChildItem $logDir -Filter '*.log' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 4 | Remove-Item
    Start-Transcript -Path (Join-Path $logDir ((Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')) | Out-Null
    $transcript = $true
    Invoke-Deployment
} catch {
    Write-Host "部署未完成：$($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    if ($transcript) { Stop-Transcript | Out-Null }
    if ($null -ne $lock) { $lock.Dispose() }
}
