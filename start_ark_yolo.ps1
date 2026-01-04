# start_ark_yolo.ps1
# Atalho para iniciar ARK YOLO System

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  🚀 ARK YOLO - Starting Application" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$projectPath = "D:\Archivos\Downloads\Edx\IA\CV\OpenCV"

# Navega até o projeto
Set-Location $projectPath

# Ativa ambiente virtual
& .\cv_env\Scripts\Activate.ps1

# Inicia Flask
Write-Host "🔄 Iniciando servidor Flask..." -ForegroundColor Yellow
python app.py

# Mantém janela aberta se houver erro
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Erro ao iniciar. Pressione qualquer tecla..." -ForegroundColor Red
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
