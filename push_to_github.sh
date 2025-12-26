#!/bin/bash
# Script para fazer commit e push para GitHub

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          PUSH PARA GITHUB - ARK YOLO                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Verificar se estamos em um repositório git
if [ ! -d ".git" ]; then
    echo "❌ Não é um repositório git!"
    echo ""
    echo "Para inicializar:"
    echo "  git init"
    echo "  git remote add origin https://github.com/jonatansouza2k11/computacional_vision.git"
    exit 1
fi

echo "📊 Status do repositório:"
git status --short
echo ""

# Adicionar todos os arquivos
echo "📝 Adicionando arquivos..."
git add .
echo "✅ Arquivos adicionados"
echo ""

# Pedir mensagem de commit
echo "📋 Digite a mensagem do commit (padrão: 'Update project'):"
read -p "Mensagem: " commit_msg
commit_msg=${commit_msg:-"Update project"}

# Fazer commit
echo ""
echo "💾 Fazendo commit..."
git commit -m "$commit_msg"
echo "✅ Commit realizado"
echo ""

# Fazer push
echo "📤 Fazendo push para GitHub..."
git push -u origin main
echo "✅ Push realizado com sucesso!"
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║            ✅ PRONTO PARA GITHUB!                            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
