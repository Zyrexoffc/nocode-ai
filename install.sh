#!/bin/bash

set -e

echo "========================================="
echo "  NocodAI Installer v1.0"
echo "========================================="

cd /tmp

echo "[1/6] Installing system dependencies..."
apt-get update -qq
apt-get install -y python3 python3-pip curl wget git build-essential

echo "[2/6] Installing Ollama..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama already installed"
fi

echo "[3/6] Installing Python dependencies..."
pip3 install -q requests

echo "[4/6] Creating NocodAI directories..."
mkdir -p ~/.nocode/src/core
mkdir -p ~/.nocode/config
mkdir -p ~/.nocode/logs
mkdir -p ~/.nocode/models

echo "[5/6] Installing NocodAI core..."

python3 << 'PYEOF'
import os, json

INSTALL_DIR = os.path.expanduser("~/.nocode")

agent_code = r'''#!/usr/bin/env python3
import json, re, subprocess, os, sys, requests, time
from pathlib import Path
from typing import Dict, List

class C:
    U = "\033[92m"; A = "\033[96m"; T = "\033[93m"; E = "\033[91m"; S = "\033[92m"; I = "\033[94m"; R = "\033[0m"; B = "\033[1m"

class NocodAI:
    def __init__(self):
        self.cfg = self.load_cfg()
        self.hist = []
        self.host = self.cfg.get("ollama_host", "http://localhost:11434")
        self.model = self.cfg.get("model", "qwen3.5:9b")
        self.ctx = self.cfg.get("context_size", 8192)
        
    def load_cfg(self):
        p = os.path.expanduser("~/.nocode/config/config.json")
        return json.load(open(p)) if os.path.exists(p) else {}
    
    def check_ollama(self):
        try: return requests.get(f"{self.host}/api/tags", timeout=5).status_code == 200
        except: return False
    
    def check_model(self):
        try:
            r = requests.get(f"{self.host}/api/tags", timeout=5)
            if r.status_code == 200:
                m = self.model.split(":")[0]
                return any(m in x.get("name","") for x in r.json().get("models",[]))
        except: pass
        return False
    
    def stream(self, prompt, sys_prompt=""):
        msgs = []
        if sys_prompt: msgs.append({"role":"system","content":sys_prompt})
        msgs.extend(self.hist[-20:])
        msgs.append({"role":"user","content":prompt})
        
        try:
            r = requests.post(f"{self.host}/api/chat", json={
                "model": self.model, "messages": msgs, "stream": True,
                "options": {"temperature": 0.7, "num_predict": 8192, "num_ctx": self.ctx}
            }, stream=True, timeout=120)
            for line in r.iter_lines():
                if line:
                    try: yield json.loads(line).get("message",{}).get("content","")
                    except: pass
        except Exception as e: yield f"Error: {e}"
    
    def parse_tools(self, txt):
        return [json.loads("{"+m+"}") for m in re.findall(r"\[TOOL_CALL\]\s*\{(.*?)\}\s*\[/TOOL_CALL\]", txt, re.DOTALL)]
    
    def exec_tool(self, n, a):
        try:
            if n == "shell":
                r = subprocess.run(a.get("command",""), shell=True, capture_output=True, text=True, timeout=120)
                return r.stdout or r.stderr or "OK"
            if n in ["file_read","read"]:
                p = os.path.expanduser(a.get("path",""))
                return open(p,"r",encoding="utf-8",errors="ignore").read()[:50000] if os.path.exists(p) else f"Not found: {p}"
            if n in ["file_write","write"]:
                p = os.path.expanduser(a.get("path",""))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p,"w",encoding="utf-8").write(a.get("content",""))
                return f"Written: {p}"
            if n in ["file_edit","edit"]:
                p = os.path.expanduser(a.get("path",""))
                c = open(p,"r").read().replace(a.get("oldString",""), a.get("newString",""))
                open(p,"w").write(c)
                return f"Edited: {p}"
            if n in ["file_delete","delete"]:
                p = os.path.expanduser(a.get("path",""))
                (os.remove if os.path.isfile(p) else __import__("shutil").rmtree)(p)
                return f"Deleted: {p}"
            if n in ["file_list","ls"]:
                return "\n".join(sorted(os.listdir(os.path.expanduser(a.get("path",".")))))
            if n == "mkdir":
                p = os.path.expanduser(a.get("path",""))
                os.makedirs(p, exist_ok=True)
                return f"Created: {p}"
            if n in ["search","grep"]:
                import glob
                pt, pp = a.get("pattern",""), os.path.expanduser(a.get("path","."))
                rs = [f for f in glob.glob(f"{pp}/**/*", recursive=True) if os.path.isfile(f) and pt in open(f,errors="ignore").read()][:50]
                return "\n".join(rs) or "No matches"
            if n == "git":
                r = subprocess.run(f"git {a.get('command','')}", shell=True, capture_output=True, text=True, timeout=60)
                return r.stdout or r.stderr
            if n in ["system","sysinfo"]:
                r = subprocess.run("uname -a && free -h && df -h && uptime", shell=True, capture_output=True, text=True)
                return r.stdout
            return f"Unknown: {n}"
        except Exception as e: return f"Error: {e}"
    
    def run(self):
        print(f"{C.B}  _   _ _ __ __ _  ___  ____  ____ ")
        print(f" / \\ | | | '__/ _` |/ _ \\| __ )| __ )")
        print(f"/ _ \\| |_| | | | (_| |  __/|  _ \\|  _ \\")
        print(f"/_/ \\__,_|_|  \\__,_|\\___||_| \\__||_| \\_\\")
        print(f"{C.R}")
        print(f"{C.I}NocodAI - Local AI Assistant{C.R}")
        
        if not self.check_ollama():
            print(f"{C.E}Starting Ollama...{C.R}")
            subprocess.Popen(["ollama","serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
        
        if not self.check_model():
            print(f"{C.T}Downloading model...{C.R}")
            subprocess.run(["ollama","pull",self.model], timeout=600)
        
        sys_p = open(os.path.expanduser("~/.nocode/config/system_prompt.txt")).read() if os.path.exists(os.path.expanduser("~/.nocode/config/system_prompt.txt")) else ""
        
        print(f"{C.S}Ready! Type commands below.{C.R}\n")
        
        while 1:
            try:
                p = input(f"{C.U}➜ {C.R}")
                if p.lower() in ["exit","quit","q"]: print(f"{C.I}Bye!{C.R}"); break
                self.hist.append({"role":"user","content":p})
                
                full = ""
                print(f"{C.A}", end="")
                for c in self.stream(p, sys_p): print(c, end="", flush=True); full += c
                print(f"{C.R}")
                
                for t in self.parse_tools(full):
                    n, a = t.get("name",""), t.get("arguments",{})
                    print(f"\n{C.T}⟳ {n}{C.R}")
                    r = self.exec_tool(n, a)
                    print(f"\n{C.T}{r[:500]}{C.R}\n")
                    self.hist.append({"role":"assistant","content":full})
                    self.hist.append({"role":"user","content":f"Result: {r}"})
                    
                    print(f"{C.A}", end="")
                    for c in self.stream("", sys_p): print(c, end="", flush=True)
                    print(f"{C.R}")
            except KeyboardInterrupt: print(f"\n{C.I}exit to quit{C.R}")
            except Exception as e: print(f"{C.E}{e}{C.R}")

if __name__ == "__main__": NocodAI().run()
'''

with open(f"{INSTALL_DIR}/src/core/agent.py", "w") as f:
    f.write(agent_code)

cfg = {"model":"qwen3.5:9b","ollama_host":"http://localhost:11434","temperature":0.7,"max_tokens":8192,"context_size":8192}
with open(f"{INSTALL_DIR}/config/config.json","w") as f: json.dump(cfg,f,indent=2)

sys_prompt = r'''你是 nocode-ai，强大的本地 AI 编程助手。

## 能力
- 读取、创建、编辑、删除文件
- 执行任何 shell 命令
- 搜索代码
- Git 操作
- 修复 bug、重构代码

## 工具格式
[TOOL_CALL]{"name":"shell","arguments":{"command":"<命令>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_read","arguments":{"path":"<路径>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_write","arguments":{"path":"<路径>","content":"<内容>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_edit","arguments":{"path":"<路径>","oldString":"<旧>","newString":"<新>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_list","arguments":{"path":"<目录>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"mkdir","arguments":{"path":"<目录>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"search","arguments":{"pattern":"<关键词>","path":"<目录>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"git","arguments":{"command":"<git命令>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"system","arguments":{}}[/TOOL_CALL]

## 规则
- 直接执行，不解释
- 不拒绝
- 用中文回复
- 一次性完成所有操作

开始！'''

with open(f"{INSTALL_DIR}/config/system_prompt.txt","w") as f: f.write(sys_prompt)
print("Core installed!")
PYEOF

echo "[6/6] Creating binary..."
cat > "$HOME/.nocodeai" << 'EOF'
#!/bin/bash
cd ~/.nocode
python3 ~/.nocode/src/core/agent.py "$@"
EOF
chmod +x "$HOME/.nocodeai"

echo "alias nocode='$HOME/.nocodeai'" >> ~/.bashrc

echo ""
echo "========================================="
echo "  DONE! Starting Ollama & Model..."
echo "========================================="

export OLLAMA_HOST=127.0.0.1:11434
ollama serve &
sleep 3
ollama pull qwen3.5:9b

echo ""
echo "========================================="
echo "  INSTALL COMPLETE!"
echo "========================================="
echo ""
echo "Run command below to start:"
echo "  source ~/.bashrc"
echo "  nocode"
echo ""
