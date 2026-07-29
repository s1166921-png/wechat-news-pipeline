param(
    [string]$PackageName = "wechat-news-pipeline-portable"
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$DistRoot = Join-Path $Root "dist"
$PackageDir = Join-Path $DistRoot $PackageName
$ZipPath = Join-Path $DistRoot "$PackageName.zip"

Set-Location $Root

if (-not (Test-Path ".env")) {
    throw "Missing .env. Please create .env with DEEPSEEK_API_KEY and ARK_API_KEY before packaging."
}

if (Test-Path $PackageDir) {
    Remove-Item -LiteralPath $PackageDir -Recurse -Force
}
if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name "wechat-news-pipeline" `
    --collect-all trafilatura `
    --collect-all curl_cffi `
    --hidden-import "docx" `
    --hidden-import "bs4" `
    --hidden-import "lxml" `
    app.py

$BuiltDir = Join-Path $DistRoot "wechat-news-pipeline"
if (-not (Test-Path $BuiltDir)) {
    throw "PyInstaller output not found: $BuiltDir"
}

Move-Item -LiteralPath $BuiltDir -Destination $PackageDir

Copy-Item -LiteralPath (Join-Path $Root "frontend") -Destination (Join-Path $PackageDir "frontend") -Recurse
Copy-Item -LiteralPath (Join-Path $Root "config") -Destination (Join-Path $PackageDir "config") -Recurse
Copy-Item -LiteralPath (Join-Path $Root ".env") -Destination (Join-Path $PackageDir ".env")
Copy-Item -LiteralPath (Join-Path $Root ".env.example") -Destination (Join-Path $PackageDir ".env.example")

$OutputDir = Join-Path $PackageDir "output"
New-Item -ItemType Directory -Force -Path (Join-Path $OutputDir "articles") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $OutputDir "images") | Out-Null

$StartBat = @'
@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动微信文章生成系统...
echo.
echo 如果浏览器没有自动打开，请访问 http://127.0.0.1:8888/
start "open-wechat-news-pipeline" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 4; Start-Process 'http://127.0.0.1:8888/'"
"%~dp0wechat-news-pipeline.exe"
pause
'@
Set-Content -LiteralPath (Join-Path $PackageDir "启动程序.bat") -Value $StartBat -Encoding UTF8

$Readme = @'
微信自动化文章生成系统 - 绿色版

使用方法：
1. 解压整个文件夹。
2. 双击“启动程序.bat”。
3. 浏览器会自动打开 http://127.0.0.1:8888/

说明：
- 当前包内已经包含 .env API 配置，可以直接使用。
- 请不要把这个压缩包发给别人，因为里面包含你的 API Key。
- 生成的文章和图片会保存在 output 文件夹。
- 如果 8888 端口被占用，请先关闭其他正在运行的本程序。

手动启动：
双击 wechat-news-pipeline.exe 后，在浏览器访问 http://127.0.0.1:8888/
'@
Set-Content -LiteralPath (Join-Path $PackageDir "使用说明.txt") -Value $Readme -Encoding UTF8

Compress-Archive -LiteralPath $PackageDir -DestinationPath $ZipPath -Force

Write-Host "Portable package created:"
Write-Host $ZipPath

