#!/bin/bash
set -e

echo "[1] Installing dependencies..."
apt-get update -qq && apt-get install -y -qq python3 python3-pip curl wget git build-essential 2>/dev/null

echo "[2] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null || echo "Ollama ready"

echo "[3] Creating directories..."
mkdir -p ~/.nocode/src/core ~/.nocode/config ~/.nocode/logs ~/.nocode/models

echo "[4] Copying fixed files..."
# Copy agent (udah fix)
cp $(dirname $0)/src/core/agent.py ~/.nocode/src/core/agent.py

# Create config
cat > ~/.nocode/config/config.json << 'EOF'
{
  "model": "qwen3.5:9b",
  "ollama_host": "http://localhost:11434",
  "temperature": 0.7,
  "max_tokens": 8192,
  "context_size": 8192
}
EOF

# Create system prompt
cat > ~/.nocode/config/system_prompt.txt << 'EOF'
你是 nocode-ai，强大的本地 AI 助手。

## 工具
[TOOL_CALL]{"name":"shell","arguments":{"command":"ls"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_read","arguments":{"path":"~/.bashrc"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_write","arguments":{"path":"/tmp/test.txt","content":"hello"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_list","arguments":{"path":"/root"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"mkdir","arguments":{"path":"/tmp/dir"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"search","arguments":{"pattern":"import","path":"/root"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"git","arguments":{"command":"status"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"system","arguments":{}}[/TOOL_CALL]

开始！
EOF

echo "[5] Creating binary..."
cat > ~/.nocodeai << 'EOF'
#!/bin/bash
cd ~/.nocode
python3 ~/.nocode/src/core/agent.py "$@"
EOF
chmod +x ~/.nocodeai

echo "alias nocode='~/.nocodeai'" >> ~/.bashrc

echo "[6] Starting Ollama..."
export OLLAMA_HOST=127.0.0.1:11434
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 3

echo ""
echo "DONE! Run: ~/.nocodeai"
echo ""