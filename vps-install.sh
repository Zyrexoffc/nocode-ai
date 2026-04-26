#!/bin/bash
set -e

REPO="https://github.com/Zyrexoffc/nocode-ai.git"
INSTALL_DIR="/root/nocode-ai"
CONFIG_DIR="/root/.nocodeai"

echo ""
echo "╭─────────────────────────────────────────╮"
echo "│   NOCOD.AI v3.0 - Installer          │"
echo "╰─────────────────────────────────────────╯"
echo ""

# Hapus yang lama kalau ada
if [ -d "$INSTALL_DIR" ]; then
    echo "→ Removing old installation..."
    rm -rf "$INSTALL_DIR"
fi

# Hapus config directory kalau ada conflict
if [ -f "$CONFIG_DIR" ]; then
    rm -f "$CONFIG_DIR"
fi

# Clone repo
echo "→ Cloning NocodAI from GitHub..."
git clone "$REPO" "$INSTALL_DIR" 2>&1 || {
    echo "✘ Clone failed!"
    exit 1
}

cd "$INSTALL_DIR"

# Install dependencies
echo "→ Checking Python..."
if command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "✘ Python not found! Install python3 first."
    exit 1
fi

# Install requests library
echo "→ Installing dependencies..."
$PYTHON -m pip install requests -q 2>/dev/null || pip install requests -q 2>/dev/null || true

echo ""
echo "✓ Installation complete!"
echo ""
echo "╭─────────────────────────────────────────╮"
echo "│  Run: cd $INSTALL_DIR       │"
echo "│  Then: $PYTHON nocodeai           │"
echo "╰─────────────────────────────────────────╯"
echo ""
