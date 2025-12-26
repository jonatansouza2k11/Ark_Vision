# Script PowerShell para fazer commit e push para GitHub
# Execute com: .\push_to_github.ps1

Write-Host "`n╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          PUSH PARA GITHUB - ARK YOLO                         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Verificar se estamos em um repositório git
if (-not (Test-Path ".git")) {
    Write-Host "❌ Não é um repositório git!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Para inicializar:" -ForegroundColor Yellow
    Write-Host "  git init" -ForegroundColor White
    Write-Host "  git remote add origin https://github.com/jonatansouza2k11/computacional_vision.git" -ForegroundColor White
    exit 1
}

Write-Host "📊 Status do repositório:" -ForegroundColor Yellow
git status --short
Write-Host ""

# Adicionar todos os arquivos
Write-Host "📝 Adicionando arquivos..." -ForegroundColor Yellow
git add .
Write-Host "✅ Arquivos adicionados`n" -ForegroundColor Green

# Pedir mensagem de commit
Write-Host "📋 Digite a mensagem do commit (padrão: 'Update project with documentation and structure'):" -ForegroundColor Yellow
$commit_msg = Read-Host "Mensagem"
if ([string]::IsNullOrWhiteSpace($commit_msg)) {
    $commit_msg = "Update project with documentation and structure"
}

# Fazer commit
Write-Host ""
Write-Host "💾 Fazendo commit..." -ForegroundColor Yellow
git commit -m $commit_msg
Write-Host "✅ Commit realizado`n" -ForegroundColor Green

# Mostrar estatísticas
Write-Host "📊 Estatísticas:" -ForegroundColor Yellow
$lastCommit = git log -1 --oneline
Write-Host "  $lastCommit" -ForegroundColor White
Write-Host ""

# Perguntar sobre branch
Write-Host "🔄 Em qual branch deseja fazer push?" -ForegroundColor Yellow
Write-Host "  1) main (padrão)" -ForegroundColor White
Write-Host "  2) develop" -ForegroundColor White
Write-Host "  3) Outra (especifique)" -ForegroundColor White
$branch_option = Read-Host "Escolha"

switch ($branch_option) {
    "1" { $branch = "main" }
    "2" { $branch = "develop" }
    "3" { $branch = Read-Host "Digite o nome da branch" }
    default { $branch = "main" }
}

# Fazer push
Write-Host ""
Write-Host "📤 Fazendo push para GitHub (branch: $branch)..." -ForegroundColor Yellow
git push -u origin $branch

if ($?) {
    Write-Host "✅ Push realizado com sucesso!`n" -ForegroundColor Green
    
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║            ✅ PRONTO PARA GITHUB!                            ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan
    
    Write-Host "Repositório:" -ForegroundColor Yellow
    Write-Host "  https://github.com/jonatansouza2k11/computacional_vision`n" -ForegroundColor White
    
    Write-Host "Branch:" -ForegroundColor Yellow
    Write-Host "  $branch`n" -ForegroundColor White
} else {
    Write-Host "❌ Erro ao fazer push!" -ForegroundColor Red
    Write-Host "Verifique sua conexão com internet e credenciais do GitHub." -ForegroundColor White
    exit 1
}
