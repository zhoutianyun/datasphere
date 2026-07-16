 # DataSphere - 一键部署脚本
 # 把网站推送到 GitHub Pages
 
 $ErrorActionPreference = "Stop"
 
 # 颜色
 $Green = "Green"
 $Yellow = "Yellow"
 $Cyan = "Cyan"
 
 Write-Host "========================================" -ForegroundColor $Cyan
 Write-Host "  数据科学个人主页 - GitHub Pages 部署" -ForegroundColor $Cyan
 Write-Host "========================================" -ForegroundColor $Cyan
 Write-Host ""
 
 # 检查 git
 try { git --version | Out-Null } catch {
     Write-Host "[!] 未找到 Git，请先安装 https://git-scm.com" -ForegroundColor Red
     exit 1
 }
 
 Write-Host "[*] 请准备一个 GitHub Personal Access Token" -ForegroundColor $Yellow
 Write-Host ""
 Write-Host "  打开此链接创建:" -ForegroundColor $Cyan
 Write-Host "  https://github.com/settings/tokens/new" -ForegroundColor $Cyan
 Write-Host ""
 Write-Host "  Note: deploy-datasphere" -ForegroundColor $Cyan
 Write-Host "  过期: No expiration" -ForegroundColor $Cyan
 Write-Host "  勾选: repo (全选)" -ForegroundColor $Cyan
 Write-Host ""
 $token = Read-Host "  粘贴你的 Token (ghp_...)"
 if ([string]::IsNullOrWhiteSpace($token)) {
     Write-Host "[!] Token 不能为空" -ForegroundColor Red
     exit 1
 }
 
 $username = "zhoutianyun"
 $repoName = "datasphere"
 
 Write-Host ""
 Write-Host "[1/4] 在 GitHub 上创建仓库..." -ForegroundColor $Green
 $headers = @{
     "Authorization" = "Bearer $token"
     "Content-Type" = "application/json"
     "User-Agent" = "deploy-script"
 }
 $body = @{
     name = $repoName
     description = "数据科学与大数据技术 · 个人主页"
     auto_init = $false
     private = $false
 } | ConvertTo-Json
 
 try {
     $resp = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Method Post -Headers $headers -Body $body
     Write-Host "    -> 仓库创建成功: https://github.com/$username/$repoName" -ForegroundColor $Cyan
 } catch {
     $err = $_.Exception.Response.StatusCode.value__
     if ($err -eq 422) {
         Write-Host "    -> 仓库已存在，继续..." -ForegroundColor $Yellow
     } else {
         Write-Host "[!] 创建失败: $_" -ForegroundColor Red
         exit 1
     }
 }
 
 Write-Host "[2/4] 配置 Git 并推送代码..." -ForegroundColor $Green
 $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
 Set-Location $scriptDir
 
 if (-not (Test-Path ".git")) {
     git init | Out-Null
 }
 git config user.name $username
 git config user.email "$username@users.noreply.github.com"
 
 # 确保 index.html 存在
 if (-not (Test-Path "index.html")) {
     # 查找 .html 文件
     $htmlFile = Get-ChildItem -Filter "*.html" | Select-Object -First 1
     if ($htmlFile) {
         Rename-Item $htmlFile.Name "index.html" -Force
     } else {
         Write-Host "[!] 未找到 HTML 文件!" -ForegroundColor Red
         exit 1
     }
 }
 
 git add index.html
 try {
     git commit -m "Initial commit: Data Science Portfolio" 2>$null
 } catch {}
 
 # 设置远程仓库 (使用 Token)
 $remoteUrl = "https://$username`:$token@github.com/$username/$repoName.git"
 git remote remove origin 2>$null
 git remote add origin $remoteUrl
 git push -u origin master 2>&1
 if ($LASTEXITCODE -ne 0) {
     git push -u origin main 2>&1
 }
 Write-Host "    -> 代码推送成功!" -ForegroundColor $Cyan
 
 Write-Host "[3/4] 开启 GitHub Pages..." -ForegroundColor $Green
 $pagesBody = @{
     source = @{
         branch = "master"
         path = "/"
     }
 } | ConvertTo-Json
 
 try {
     Invoke-RestMethod -Uri "https://api.github.com/repos/$username/$repoName/pages" `
         -Method Post -Headers $headers -Body $pagesBody -ErrorAction SilentlyContinue
 } catch {}
 
 # 如果 master 不行，试试 main
 $pagesBody = @{
     source = @{
         branch = "main"
         path = "/"
     }
 } | ConvertTo-Json
 try {
     Invoke-RestMethod -Uri "https://api.github.com/repos/$username/$repoName/pages" `
         -Method Post -Headers $headers -Body $pagesBody -ErrorAction SilentlyContinue
 } catch {}
 
 Write-Host "[4/4] 等待 Pages 部署 (约 30 秒)..." -ForegroundColor $Green
 Start-Sleep -Seconds 30
 
 $pageUrl = "https://$username.github.io/$repoName/"
 Write-Host ""
 Write-Host "========================================" -ForegroundColor $Cyan
 Write-Host "  部署完成!" -ForegroundColor $Green
 Write-Host "  你的网站地址:" -ForegroundColor $Green
 Write-Host "  $pageUrl" -ForegroundColor $Cyan
 Write-Host "========================================" -ForegroundColor $Cyan
 Write-Host ""
 Write-Host "按 Enter 键打开浏览器访问..."
 $null = Read-Host
 Start-Process $pageUrl
