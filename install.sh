#!/bin/bash
# hermes-model-menu-cleanup Skill Installer
# Cross-platform: Hermes Agent / OpenClaw

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Hermes Model Menu Cleanup 技能安装程序${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

SKILL_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_NAME="hermes-model-menu-cleanup"

# Detect platform
if [ -d "$HOME/.hermes" ]; then
    echo -e "${GREEN}侦测到 Hermes Agent 环境。${NC}"
    INSTALL_DIR="$HOME/.hermes/skills/devops/$SKILL_NAME"
elif [ -d "$HOME/.openclaw" ]; then
    echo -e "${GREEN}侦测到 OpenClaw 环境。${NC}"
    INSTALL_DIR="$HOME/.openclaw/workspace/skills/devops/$SKILL_NAME"
else
    echo -e "${RED}❌ 找不到 Hermes 或 OpenClaw 目录。${NC}"
    exit 1
fi

echo -e "${YELLOW}安装目录：${INSTALL_DIR}${NC}"

# 1. Copy skill files
echo -e "\n${YELLOW}[1/3] 复制技能档案...${NC}"
mkdir -p "$INSTALL_DIR"
rsync -av --exclude 'venv/' --exclude '__pycache__/' --exclude '.git/' --exclude '.github/' \
    "$SKILL_SOURCE_DIR/" "$INSTALL_DIR/"
echo -e "${GREEN}✅ 技能档案复制完成。${NC}"

# 2. Execute permissions
echo -e "\n${YELLOW}[2/3] 赋予脚本执行权限...${NC}"
chmod +x "$INSTALL_DIR/scripts/audit-model-menu.py" "$INSTALL_DIR/install.sh"
echo -e "${GREEN}✅ 执行权限设定完成。${NC}"

# 3. Verification
echo -e "\n${YELLOW}[3/3] 验证安装...${NC}"
if [ -f "$INSTALL_DIR/SKILL.md" ] && [ -f "$INSTALL_DIR/scripts/audit-model-menu.py" ]; then
    echo -e "${GREEN}✅ 安装验证成功！${NC}"
    echo ""
    echo -e "${BLUE}用法：${NC}"
    echo -e "  在 Hermes Agent 中输入："
    echo -e "  ${GREEN}加载 hermes-model-menu-cleanup 技能${NC}"
    echo ""
    echo -e "  或直接执行诊断脚本："
    echo -e "  ${GREEN}python3 ${INSTALL_DIR}/scripts/audit-model-menu.py${NC}"
else
    echo -e "${RED}❌ 安装验证失败，请手动检查。${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ 'hermes-model-menu-cleanup' 技能安装程序完成！${NC}"
echo -e "${BLUE}========================================${NC}"
