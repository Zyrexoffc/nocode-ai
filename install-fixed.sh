#!/bin/bash
set -e

echo "NocodAI Installer v5 - Simple Version"
echo "===================================="

# Install deps
echo "[1/5] Deps..."
apt-get update -qq && apt-get install -y -qq python3 python3-pip curl wget 2>/dev/null

# Install Ollama  
echo "[2/5] Ollama..."
curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null || echo "OK"

# Create dirs
echo "[3/5] Setup..."
mkdir -p ~/.nocode/src/core ~/.nocode/config ~/.nocode/logs

# Download agent.py directly from GitHub
echo "[4/5] Download agent..."
curl -fsSL "https://raw.githubusercontent.com/Zyrexoffc/nocode-ai/main/src/core/agent.py" -o ~/.nocode/src/core/agent.py

# Config
echo '{ "model": "qwen3.5:9b", "ollama_host": "http://localhost:11434", "temperature": 0.7, "max_tokens": 8192, "context_size": 8192 }' > ~/.nocode/config/config.json

# System prompt  
echo '你是 nocode-ai。工具: shell, file_read, file_write, file_edit, file_delete, file_list, mkdir, search, git, system' > ~/.nocode/config/system_prompt.txt

# Binary
echo '#!/bin/bash
python3 ~/.nocode/src/core/agent.py "$@"' > ~/.nocodeai
chmod +x ~/.nocodeai

# Alias
grep -q "alias nocode" ~/.bashrc || echo "alias nocode='~/.nocodeai'" >> ~/.bashrc

# Start Ollama
echo "[5/5] Start..."
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 3

echo ""
echo "===================================="
echo "  DONE! Run: ~/.nocodeai"
echo "===================================="