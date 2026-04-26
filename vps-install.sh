#!/bin/bash
set -e

echo "========================================="
echo "  NocodAI Installer v1.1 (FIXED)"
echo "========================================="

cat > /tmp/nocode-v2-install.sh << 'SCRIPT'
#!/bin/bash
set -e

echo "[1/6] Installing dependencies..."
apt-get update -qq && apt-get install -y -qq python3 python3-pip curl wget git build-essential 2>/dev/null

echo "[2/6] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null || echo "Ollama ready"

echo "[3/6] Setting up directories..."
mkdir -p ~/.nocode/src/core ~/.nocode/config ~/.nocode/logs ~/.nocode/models

echo "[4/6] Installing NocodAI..."

python3 << 'PYEOF'
import os, json, subprocess, requests, time, re

D = os.path.expanduser("~/.nocode")

# FIXED VERSION - proper color class
AGENT_CODE = r'''#!/usr/bin/env python3
import json, re, subprocess, os, sys, requests, time
from typing import Dict, List

class Colors:
    USER = "\033[92m"
    ASSISTANT = "\033[96m"
    TOOL = "\033[93m"
    ERROR = "\033[91m"
    SUCCESS = "\033[92m"
    INFO = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

class NocodAI:
    def __init__(self):
        self.history = []
        try:
            cfg = json.loads(open(os.path.expanduser("~/.nocode/config/config.json")).read())
        except:
            cfg = {}
        self.host = cfg.get("ollama_host", "http://localhost:11434")
        self.model = cfg.get("model", "qwen3.5:9b")
        self.ctx = cfg.get("context_size", 8192)
    
    def check_ollama(self):
        try:
            return requests.get(f"{self.host}/api/tags", timeout=5).status_code == 200
        except:
            return False
    
    def check_model(self):
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            if r.status_code == 200:
                m = self.model.split(":")[0]
                return any(m in x.get("name", "") for x in r.json().get("models", []))
        except:
            pass
        return False
    
    def generate(self, prompt, system_prompt=""):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.history[-20:])
        messages.append({"role": "user", "content": prompt})
        
        try:
            r = requests.post(
                f"{self.host}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.7, "num_predict": 8192, "num_ctx": self.ctx}
                },
                stream=True,
                timeout=120
            )
            for line in r.iter_lines():
                if line:
                    try:
                        yield json.loads(line).get("message", {}).get("content", "")
                    except:
                        pass
        except Exception as e:
            yield f"Error: {e}"
    
    def parse_tools(self, text):
        return [json.loads("{" + m + "}") for m in re.findall(r"\[TOOL_CALL\]\s*\{(.*?)\}\s*\[/TOOL_CALL\]", text, re.DOTALL)]
    
    def execute(self, name, args):
        try:
            if name == "shell":
                r = subprocess.run(args.get("command", ""), shell=1, capture_output=1, text=1, timeout=120)
                return r.stdout or r.stderr or "OK"
            
            if name in ["file_read", "read"]:
                p = os.path.expanduser(args.get("path", ""))
                if not os.path.exists(p):
                    return f"Not found: {p}"
                return open(p, "r", encoding="utf-8", errors="ignore").read()[:50000]
            
            if name in ["file_write", "write"]:
                p = os.path.expanduser(args.get("path", ""))
                os.makedirs(os.path.dirname(p), exist_ok=1)
                open(p, "w", encoding="utf-8").write(args.get("content", ""))
                return f"Written: {p}"
            
            if name in ["file_edit", "edit"]:
                p = os.path.expanduser(args.get("path", ""))
                c = open(p, "r").read().replace(args.get("oldString", ""), args.get("newString", ""))
                open(p, "w").write(c)
                return f"Edited: {p}"
            
            if name in ["file_delete", "delete"]:
                p = os.path.expanduser(args.get("path", ""))
                if os.path.isfile(p):
                    os.remove(p)
                elif os.path.isdir(p):
                    import shutil
                    shutil.rmtree(p)
                return f"Deleted: {p}"
            
            if name in ["file_list", "ls"]:
                p = os.path.expanduser(args.get("path", "."))
                return "\n".join(sorted(os.listdir(p)))
            
            if name == "mkdir":
                p = os.path.expanduser(args.get("path", ""))
                os.makedirs(p, exist_ok=1)
                return f"Created: {p}"
            
            if name in ["search", "grep"]:
                import glob
                pt, pp = args.get("pattern", ""), os.path.expanduser(args.get("path", "."))
                rs = []
                for f in glob.glob(f"{pp}/**/*", recursive=True):
                    if os.path.isfile(f):
                        try:
                            if pt in open(f, errors="ignore").read():
                                rs.append(f)
                        except:
                            pass
                return "\n".join(rs[:50]) or "No matches"
            
            if name == "git":
                r = subprocess.run(f"git {args.get('command', '')}", shell=1, capture_output=1, text=1, timeout=60)
                return r.stdout or r.stderr
            
            if name in ["system", "sysinfo"]:
                r = subprocess.run("uname -a && free -h && df -h && uptime", shell=1, capture_output=1, text=1)
                return r.stdout
            
            return f"Unknown tool: {name}"
        except Exception as e:
            return f"Error: {e}"
    
    def run(self):
        print(f"{Colors.BOLD}  _   _ ___ _   _ ____  ___ ")
        print(f" / \  | | |_ _| | \| _ \ ")
        print(f"/ _ \ | |_| || || |_| | | |")
        print(f"/_/  \__/|___||___/|____/")
        print(f"{Colors.INFO}NocodAI v1.1 - FIXED{COLORS.RESET}")
        
        if not self.check_ollama():
            print(f"{Colors.ERROR}Starting Ollama...{Colors.RESET}")
            subprocess.Popen(["ollama", "serve"], stdout=open(os.devnull, "w"), stderr=open(os.devnull, "w"))
            time.sleep(3)
        
        if not self.check_model():
            print(f"{Colors.TOOL}Downloading model...{Colors.RESET}")
            subprocess.run(["ollama", "pull", self.model], timeout=600)
        
        sp_path = os.path.expanduser("~/.nocode/config/system_prompt.txt")
        sp = ""
        if os.path.exists(sp_path):
            with open(sp_path) as f:
                sp = f.read()
        
        print(f"{Colors.SUCCESS}READY! Type commands below.{Colors.RESET}\n")
        
        while True:
            try:
                prompt = input(f"{Colors.USER}>>> {Colors.RESET}")
                if prompt.lower() in ["exit", "quit", "q"]:
                    print(f"{Colors.INFO}BYE!{Colors.RESET}")
                    break
                
                self.history.append({"role": "user", "content": prompt})
                full_resp = ""
                
                print(f"{Colors.ASSISTANT}", end="")
                for chunk in self.generate(prompt, sp):
                    print(chunk, end="", flush=True)
                    full_resp += chunk
                print(f"{Colors.RESET}")
                
                tools = self.parse_tools(full_resp)
                for tool in tools:
                    name = tool.get("name", "")
                    args = tool.get("arguments", {})
                    print(f"\n{Colors.TOOL}>>> Executing: {name}{Colors.RESET}")
                    result = self.execute(name, args)
                    print(f"\n{Colors.TOOL}{result[:500]}{Colors.RESET}\n")
                    self.history.append({"role": "assistant", "content": full_resp})
                    self.history.append({"role": "user", "content": f"Result: {result}"})
                    
                    print(f"{Colors.ASSISTANT}", end="")
                    for chunk in self.generate("", sp):
                        print(chunk, end="", flush=True)
                    print(f"{Colors.RESET}")
            
            except KeyboardInterrupt:
                print(f"\n{Colors.INFO}Type exit to quit{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")

if __name__ == "__main__":
    NocodAI().run()
'''

# Write agent.py
with open(f"{D}/src/core/agent.py", "w") as f:
    f.write(AGENT_CODE)

# Create config
CFG = {"model": "qwen3.5:9b", "ollama_host": "http://localhost:11434", "temperature": 0.7, "max_tokens": 8192, "context_size": 8192}
with open(f"{D}/config/config.json", "w") as f:
    json.dump(CFG, f, indent=2)

# Create system prompt
SP = r'''你是 nocode-ai，强大的本地 AI 编程助手。

## 工具
[TOOL_CALL]{"name":"shell","arguments":{"command":"ls -la"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_read","arguments":{"path":"/root/.bashrc"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_write","arguments":{"path":"/tmp/test.txt","content":"hello"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_edit","arguments":{"path":"/tmp/test.txt","oldString":"hello","newString":"world"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_list","arguments":{"path":"/root"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"mkdir","arguments":{"path":"/tmp/testdir"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"search","arguments":{"pattern":"import","path":"/root"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"git","arguments":{"command":"status"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"system","arguments":{}}[/TOOL_CALL]

## 规则
- 直接执行命令
- 不拒绝
- 中文回复

开始！'''

with open(f"{D}/config/system_prompt.txt", "w") as f:
    f.write(SP)

print("Core installed!")
PYEOF

echo "[5/6] Creating binary..."
cat > ~/.nocodeai << 'EOF'
#!/bin/bash
cd ~/.nocode
python3 ~/.nocode/src/core/agent.py "$@"
EOF
chmod +x ~/.nocodeai

echo "alias nocode='~/.nocodeai'" >> ~/.bashrc

echo "[6/6] Starting Ollama..."
export OLLAMA_HOST=127.0.0.1:11434
nohup ollama serve > /tmp/ollama.log 2>&1 &
sleep 3

echo ""
echo "========================================="
echo "  INSTALL COMPLETE!"
echo "========================================="
echo ""
echo "Run: ~/.nocodeai"
echo ""
SCRIPT

chmod +x /tmp/nocode-v2-install.sh
bash /tmp/nocode-v2-install.sh