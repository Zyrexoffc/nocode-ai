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
curl -fsSL "https://raw.githubusercontent.com/Zyrexoffc/nocode-ai/main/src/core/agent.py" -o ~/.nocodeai/agent.py

# Config (use phi - smallest model for low RAM VPS)
echo '{ "model": "phi", "ollama_host": "http://localhost:11434", "temperature": 0.7, "max_tokens": 2048, "context_size": 2048 }' > ~/.nocodeai/config.json

# System prompt  
echo '你是 nocode-ai。工具: shell, file_read, file_write, file_edit, file_delete, file_list, mkdir, search, git, system' > ~/.nocode/config/system_prompt.txt

# Create launcher
cat > /usr/local/bin/nocodeai << 'EOF'
#!/bin/bash
cd ~ && python3 ~/.nocodeai/agent.py "$@"
EOF
chmod +x /usr/local/bin/nocodeai

# Hide it
mv ~/.nocode /root/.nocodeai
ln -sf /root/.nocodeai ~/.nocodeai

# Start Ollama
echo "[5/5] Start..."
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 3

echo ""
echo "===================================="
echo "  DONE! Run: ~/.nocodeai"
echo "===================================="