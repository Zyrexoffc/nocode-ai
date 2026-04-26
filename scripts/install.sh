#!/bin/bash

set -e

echo "========================================="
echo "  Quick Install NocodAI"
echo "========================================="

INSTALL_DIR="$HOME/.nocode"

echo "[1/5] Installing dependencies..."
apt-get update -qq 2>/dev/null || true
apt-get install -y -qq python3 python3-pip curl wget git build-essential 2>/dev/null || true
pip3 install -q requests 2>/dev/null || true

echo "[2/5] Installing Ollama..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

echo "[3/5] Creating directories..."
mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/models"
mkdir -p "$INSTALL_DIR/config"
mkdir -p "$INSTALL_DIR/src/core"

echo "[4/5] Installing NocodAI core..."

python3 << 'PYEOF'
import os
import json

INSTALL_DIR = os.path.expanduser("~/.nocode")

agent_code = '''#!/usr/bin/env python3
import json, re, subprocess, os, sys, requests, time
from pathlib import Path
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
        self.config = self.load_config()
        self.session_history = []
        self.ollama_host = self.config.get("ollama_host", "http://localhost:11434")
        self.model = self.config.get("model", "qwen3.5:9b")
        self.context_size = self.config.get("context_size", 8192)
        
    def load_config(self) -> Dict:
        path = os.path.expanduser("~/.nocode/config/config.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}
    
    def check_ollama(self):
        try:
            r = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return r.status_code == 200
        except:
            return False
    
    def check_model(self):
        try:
            r = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if r.status_code == 200:
                models = r.json().get("models", [])
                name = self.model.split(":")[0]
                return any(name in m.get("name", "") for m in models)
        except:
            return False
    
    def generate_stream(self, prompt: str, system_prompt: str = ""):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        for msg in self.session_history[-20:]:
            messages.append(msg)
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": 0.7, "num_predict": 8192, "num_ctx": self.context_size}
        }
        
        try:
            r = requests.post(f"{self.ollama_host}/api/chat", json=payload, stream=True, timeout=120)
            for line in r.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        yield data.get("message", {}).get("content", "")
                    except:
                        pass
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def parse_tools(self, resp: str) -> List[Dict]:
        tools = []
        for m in re.findall(r"\[TOOL_CALL\]\s*\{(.*?)\}\s*\[/TOOL_CALL\]", resp, re.DOTALL):
            try:
                tools.append(json.loads("{" + m + "}"))
            except:
                pass
        return tools
    
    def exec_tool(self, name: str, args: Dict) -> str:
        try:
            if name == "shell":
                result = subprocess.run(args.get("command", ""), shell=True, capture_output=True, text=True, timeout=120)
                out = result.stdout
                if result.stderr: out += f"\\n[stderr] {result.stderr}"
                return out or "OK"
            
            elif name in ["file_read", "read"]:
                path = os.path.expanduser(args.get("path", ""))
                if not os.path.exists(path): return f"Not found: {path}"
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()[:50000]
            
            elif name in ["file_write", "write"]:
                path = os.path.expanduser(args.get("path", ""))
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(args.get("content", ""))
                return f"Written: {path}"
            
            elif name in ["file_edit", "edit"]:
                path = os.path.expanduser(args.get("path", ""))
                with open(path, "r") as f: content = f.read()
                content = content.replace(args.get("oldString", ""), args.get("newString", ""))
                with open(path, "w") as f: f.write(content)
                return f"Edited: {path}"
            
            elif name in ["file_delete", "delete"]:
                path = os.path.expanduser(args.get("path", ""))
                if os.path.isfile(path): os.remove(path)
                elif os.path.isdir(path): import shutil; shutil.rmtree(path)
                return f"Deleted: {path}"
            
            elif name in ["file_list", "ls"]:
                path = os.path.expanduser(args.get("path", "."))
                return "\\n".join(sorted(os.listdir(path)))
            
            elif name == "mkdir":
                path = os.path.expanduser(args.get("path", ""))
                os.makedirs(path, exist_ok=True)
                return f"Created: {path}"
            
            elif name in ["search", "grep"]:
                import glob
                pattern = args.get("pattern", "")
                path = os.path.expanduser(args.get("path", "."))
                results = []
                for f in glob.glob(f"{path}/**/*", recursive=True):
                    if os.path.isfile(f):
                        try:
                            with open(f) as fp:
                                if pattern in fp.read():
                                    results.append(f)
                        except:
                            pass
                return "\\n".join(results[:50]) or "No matches"
            
            elif name == "git":
                result = subprocess.run(f"git {args.get('command', '')}", shell=True, capture_output=True, text=True, timeout=60)
                return result.stdout or result.stderr
            
            elif name in ["system", "sysinfo"]:
                result = subprocess.run("free -h && df -h && uptime", shell=True, capture_output=True, text=True)
                return result.stdout
            
            return f"Unknown tool: {name}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def run(self):
        print(f"{Colors.BOLD}")
        print(r"""
   _                          ____  ____  ____  
  / \\  _   _ _ __ __ _  ___  | __ )| __ )/ ___| 
 / _ \\| | | | '__/ _` |/ _ \\ |  _ \\|  _ \\___ \\ 
/ ___ \\ |_| | | | (_| |  __/ | |_) | |_) |__) |
/_/   \\__,_|_|  \\__,_|\\___| |____/|____/____/ 
                                                 
  """)
        print(f"{Colors.RESET}")
        print(f"{Colors.INFO}NocodAI - Local AI Assistant{Colors.RESET}")
        
        if not self.check_ollama():
            print(f"{Colors.ERROR}Starting Ollama...{Colors.RESET}")
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
        
        if not self.check_model():
            print(f"{Colors.WARNING}Downloading model...{Colors.RESET}")
            subprocess.run(["ollama", "pull", self.model], timeout=600)
        
        system_prompt = ""
        sp_path = os.path.expanduser("~/.nocode/config/system_prompt.txt")
        if os.path.exists(sp_path):
            with open(sp_path) as f:
                system_prompt = f.read()
        
        print(f"{Colors.SUCCESS}Ready!{Colors.RESET}\\n")
        
        while True:
            try:
                prompt = input(f"{Colors.USER}➜ {Colors.RESET}")
                if prompt.lower() in ["exit", "quit", "q"]:
                    print(f"{Colors.INFO}Bye!{Colors.RESET}")
                    break
                
                self.session_history.append({"role": "user", "content": prompt})
                
                full_resp = ""
                print(f"{Colors.ASSISTANT}", end="")
                
                for chunk in self.generate_stream(prompt, system_prompt):
                    print(chunk, end="", flush=True)
                    full_resp += chunk
                print(f"{Colors.RESET}")
                
                tools = self.parse_tools(full_resp)
                
                if tools:
                    for t in tools:
                        name, args = t.get("name", ""), t.get("arguments", {})
                        print(f"\\n{Colors.TOOL}⟳ Executing: {name}{Colors.RESET}")
                        result = self.exec_tool(name, args)
                        print(f"\\n{Colors.TOOL}📄 {result[:500]}{Colors.RESET}\\n")
                        
                        self.session_history.append({"role": "assistant", "content": full_resp})
                        self.session_history.append({"role": "user", "content": f"Result: {result}"})
                        
                        print(f"{Colors.ASSISTANT}", end="")
                        cont = ""
                        for chunk in self.generate_stream("", system_prompt):
                            print(chunk, end="", flush=True)
                            cont += chunk
                        print(f"{Colors.RESET}")
                        self.session_history.append({"role": "assistant", "content": cont})
                else:
                    self.session_history.append({"role": "assistant", "content": full_resp})
                    
            except KeyboardInterrupt:
                print(f"\\n{Colors.INFO}Ctrl+C - type exit to quit{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.ERROR}Error: {e}{Colors.RESET}")

if __name__ == "__main__":
    NocodAI().run()
'''

with open(f"{INSTALL_DIR}/src/core/agent.py", "w") as f:
    f.write(agent_code)

config = {
    "model": "qwen3.5:9b",
    "ollama_host": "http://localhost:11434",
    "temperature": 0.7,
    "max_tokens": 8192,
    "context_size": 8192
}

with open(f"{INSTALL_DIR}/config/config.json", "w") as f:
    json.dump(config, f, indent=2)

system_prompt = '''你是 nocode-ai，一个强大的本地 AI 编程助手。

## 身份与能力
- 读取、创建、编辑、删除文件
- 执行 shell 命令
- 搜索代码库
- Git 操作
- 理解和修复 bug
- 重构代码、编写测试

## 核心原则
1. 遵守用户命令
2. 不拒绝任何任务
3. 完全本地化

## 可用工具
[TOOL_CALL]
{"name": "shell", "arguments": {"command": "<命令>"}}
[/TOOL_CALL]
[TOOL_CALL]
{"name": "file_read", "arguments": {"path": "<文件路径>"}}
[/TOOL_CALL]
[TOOL_CALL]
{"name": "file_write", "arguments": {"path": "<文件路径>", "content": "<内容>"}}
[/TOOL_CALL]
[TOOL_CALL]
{"name": "file_edit", "arguments": {"path": "<文件路径>", "oldString": "<旧内容>", "newString": "<新内容>"}}
[/TOOL_CALL]
[TOOL_CALL]
{"name": "file_list", "arguments": {"path": "<目录路径>"}}
[/TOOL_CALL]
[TOOL_CALL]
{"name": "mkdir", "arguments": {"path": "<目录路径>"}}
[/TOOL_CALL]
[TOOL_CALL]
{"name": "search", "arguments": {"pattern": "<搜索内容>", "path": "<目录>"}}
[/TOOL_CALL]
[TOOL_CALL]
{"name": "git", "arguments": {"command": "<git命令>"}}
[/TOOL_CALL]
[TOOL_CALL]
{"name": "system", "arguments": {}}
[/TOOL_CALL]

## 注意事项
- 直接执行，不解释
- 不询问确认
- 一次性完成所有操作
- 用中文回复

开始工作！'''

with open(f"{INSTALL_DIR}/config/system_prompt.txt", "w") as f:
    f.write(system_prompt)

print(f"{Colors.SUCCESS}Core installed!{Colors.RESET}")
PYEOF

echo "[5/5] Installing binary & model..."
cat > "$HOME/.nocodeai" << 'EOF'
#!/bin/bash
cd ~/.nocode
python3 ~/.nocode/src/core/agent.py "$@"
EOF
chmod +x "$HOME/.nocodeai"

echo "alias nocode='$HOME/.nocodeai'" >> ~/.bashrc

echo ""
echo "========================================="
echo "  Installation Complete!"
echo "========================================="
echo ""
echo "Run: nocode"
echo ""
