# 测试后端服务状态刷新功能
# 用于验证在后端管理面板点击"刷新状态"时，是否真正更新了服务状态

Write-Host "=== 后端服务状态刷新功能测试 ===" -ForegroundColor Green
Write-Host ""

$backendUrl = "http://localhost:3000"

# 测试函数
function Test-ServiceRefresh {
    param([string]$url, [bool]$withRefresh)
    
    $endpoint = if ($withRefresh) { "$url/api/system/health?refresh=true" } else { "$url/api/system/health" }
    $label = if ($withRefresh) { "带 refresh 参数" } else { "不带 refresh 参数" }
    
    Write-Host "[$label] 请求: $endpoint" -ForegroundColor Cyan
    
    try {
        $response = Invoke-RestMethod -Uri $endpoint -Method Get -ContentType "application/json"
        
        if ($response.success) {
            Write-Host "  ✓ 请求成功" -ForegroundColor Green
            Write-Host "  时间戳: $($response.data.timestamp)" -ForegroundColor Gray
            
            $services = $response.data.services
            Write-Host "  服务状态:" -ForegroundColor Yellow
            
            foreach ($serviceName in $services.PSObject.Properties.Name) {
                $service = $services.$serviceName
                $status = $service.status
                $lastCheck = $service.lastCheck
                $errorCount = $service.errorCount
                
                $statusColor = switch ($status) {
                    "running" { "Green" }
                    "stopped" { "Yellow" }
                    "error" { "Red" }
                    default { "Gray" }
                }
                
                Write-Host "    - $serviceName : " -NoNewline
                Write-Host "$status" -ForegroundColor $statusColor -NoNewline
                Write-Host " (检查时间: $lastCheck, 错误次数: $errorCount)" -ForegroundColor Gray
            }
            
            return $services
        } else {
            Write-Host "  ✗ 请求失败: $($response.error)" -ForegroundColor Red
            return $null
        }
    } catch {
        Write-Host "  ✗ 请求异常: $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
    
    Write-Host ""
}

# 步骤 1: 检查后端是否运行
Write-Host "步骤 1: 检查后端服务是否运行..." -ForegroundColor Yellow
try {
    $ping = Invoke-RestMethod -Uri "$backendUrl/api/system/health" -Method Get -TimeoutSec 5
    Write-Host "  ✓ 后端服务运行中" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "  ✗ 后端服务未运行，请先启动后端服务" -ForegroundColor Red
    Write-Host "    命令: cd backend && npm start" -ForegroundColor Gray
    exit 1
}

# 步骤 2: 获取初始状态（不刷新）
Write-Host "步骤 2: 获取初始缓存状态（不刷新）..." -ForegroundColor Yellow
$initialStatus = Test-ServiceRefresh -url $backendUrl -withRefresh $false
Write-Host ""

Start-Sleep -Seconds 2

# 步骤 3: 强制刷新状态
Write-Host "步骤 3: 强制刷新服务状态（带 refresh=true 参数）..." -ForegroundColor Yellow
$refreshedStatus = Test-ServiceRefresh -url $backendUrl -withRefresh $true
Write-Host ""

# 步骤 4: 对比结果
Write-Host "步骤 4: 对比刷新前后的变化..." -ForegroundColor Yellow

if ($initialStatus -and $refreshedStatus) {
    $changed = $false
    
    foreach ($serviceName in $initialStatus.PSObject.Properties.Name) {
        $initialLastCheck = $initialStatus.$serviceName.lastCheck
        $refreshedLastCheck = $refreshedStatus.$serviceName.lastCheck
        
        if ($refreshedLastCheck -gt $initialLastCheck) {
            Write-Host "  ✓ $serviceName : lastCheck 时间已更新" -ForegroundColor Green
            Write-Host "    初始: $initialLastCheck -> 刷新后: $refreshedLastCheck" -ForegroundColor Gray
            $changed = $true
        } else {
            Write-Host "  ✗ $serviceName : lastCheck 时间未更新" -ForegroundColor Red
            Write-Host "    初始: $initialLastCheck, 刷新后: $refreshedLastCheck" -ForegroundColor Gray
        }
    }
    
    Write-Host ""
    
    if ($changed) {
        Write-Host "✓ 测试通过：刷新功能正常工作，服务状态已更新" -ForegroundColor Green
    } else {
        Write-Host "✗ 测试失败：刷新功能未生效，服务状态未更新" -ForegroundColor Red
        Write-Host "  可能原因：" -ForegroundColor Yellow
        Write-Host "    1. backend/src/api/routes/system.ts 的 refresh 参数处理逻辑有问题" -ForegroundColor Gray
        Write-Host "    2. serviceManager.healthCheckAll() 未正确执行" -ForegroundColor Gray
        Write-Host "    3. 服务状态缓存未更新" -ForegroundColor Gray
    }
} else {
    Write-Host "✗ 无法完成对比，请检查前面的请求是否成功" -ForegroundColor Red
}

Write-Host ""
Write-Host "=== 测试完成 ===" -ForegroundColor Green
