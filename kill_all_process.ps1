# Função para matar processos de uma porta específica
function Kill-PortProcesses {
    param (
        [int]$Port
    )

    Write-Host "Matando processos na porta $Port..." -ForegroundColor Yellow

    $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    $procIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique

    if ($procIds) {
        foreach ($procId in $procIds) {
            Write-Host "Matando processo PID: $procId" -ForegroundColor Red
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
        Write-Host "Processos na porta $Port terminados!" -ForegroundColor Green
    }
    else {
        Write-Host "Nenhum processo na porta $Port" -ForegroundColor Cyan
    }

    # Verificação pós-cleanup
    Start-Sleep -Seconds 1
    netstat -ano | findstr :$Port
}

# Matar processos nas portas 8000 e 3000
Kill-PortProcesses -Port 8000
Kill-PortProcesses -Port 3000
