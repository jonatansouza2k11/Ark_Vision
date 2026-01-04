# backup_task.ps1
# Script para agendar backup diário no Windows

$scriptPath = "D:\Archivos\Downloads\Edx\IA\CV\OpenCV"
$pythonPath = "D:\Archivos\Downloads\Edx\IA\CV\OpenCV\cv_env\Scripts\python.exe"
$backupScript = "backup_logs.py"

# Navega até o diretório
Set-Location $scriptPath

# Ativa ambiente virtual e executa backup
& $pythonPath $backupScript

# Executa limpeza (dry-run) uma vez por mês
$day = (Get-Date).Day
if ($day -eq 1) {
    Write-Host "🗑️ Executando limpeza mensal..."
    & $pythonPath $backupScript --cleanup --no-dry-run
}

# Log da execução
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path "logs\backup_schedule.log" -Value "$timestamp - Backup executado"
Write-Host "✅ Backup concluído em $timestamp"


#Agendar no Windows:
# Abre o Task Scheduler
#taskschd.msc

# Ou crie via PowerShell (execute como Admin):
#$action = New-ScheduledTaskAction -Execute "PowerShell.exe" `
#    -Argument "-File D:\Archivos\Downloads\Edx\IA\CV\OpenCV\backup_task.ps1"

#$trigger = New-ScheduledTaskTrigger -Daily -At "02:00AM"

#$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

#Register-ScheduledTask -TaskName "ARK_YOLO_LogBackup" `
#    -Action $action `
#    -Trigger $trigger `
#    -Principal $principal `
#    -Description "Backup diário de logs do ARK YOLO System"
