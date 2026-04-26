#!/bin/bash
set -e

echo "NocodAI Installer v6 - Clean Install"
echo "===================================="

# Remove old files
echo "[1/6] Cleaning old files..."
rm -rf ~/.nocode ~/.nocode-ai ~/.nocodeai /usr/local/bin/nocodeai 2>/dev/null || true

# Install deps
echo "[2/6] Deps..."
apt-get update -qq && apt-get install -y -qq python3 python3-pip curl wget 2>/dev/null

# Install Ollama  
echo "[3/6] Ollama..."
curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null || echo "OK"

# Create hidden folder
echo "[4/6] Setup..."
mkdir -p ~/.nocodeai

# Download agent.py from GitHub
echo "[5/6] Download agent..."
curl -fsSL "https://raw.githubusercontent.com/Zyrexoffc/nocode-ai/main/src/core/agent.py" -o ~/.nocodeai/agent.py

# Config (phi - lightest model for low RAM VPS)
echo '{"model": "phi", "ollama_host": "http://localhost:11434", "temperature": 0.7, "max_tokens": 2048, "context_size": 2048}' > ~/.nocodeai/config.json

# Create launcher
cat > /usr/local/bin/nocodeai << 'EOF'
#!/bin/bash
cd ~ && python3 ~/.nocodeai/agent.py "$@"
EOF
chmod +x /usr/local/bin/nocodeai

# Start Ollama
echo "[6/6] Start..."
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 3

# Pull model if not exists
ollama pull phi 2>/dev/null || true

echo ""
echo "===================================="
echo "  DONE! Run: nocodeai"
echo "===================================="