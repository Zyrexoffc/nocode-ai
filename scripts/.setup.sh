#!/bin/bash

set -e

INSTALL_DIR="$HOME/.nocode"
HIDDEN_DIR="$HOME/.nocode"
BIN_FILE="$HOME/.nocodeai"

echo "========================================="
echo "  NocodAI Hidden Installer"
echo "========================================="

echo "[1/8] Updating system..."
apt-get update -qq 2>/dev/null || true

echo "[2/8] Installing dependencies..."
apt-get install -y -qq python3 python3-pip curl wget git build-essential ssl-cert 2>/dev/null || true

echo "[3/8] Setting up Ollama..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama already installed"
fi

echo "[4/8] Installing Python packages..."
pip3 install -q requests 2>/dev/null || true

echo "[5/8] Creating hidden directories..."
mkdir -p "$HIDDEN_DIR/logs"
mkdir -p "$HIDDEN_DIR/models"
mkdir -p "$HIDDEN_DIR/config"
mkdir -p "$HIDDEN_DIR/src/core"
mkdir -p "$HIDDEN_DIR/src/tools"

echo "[6/8] Copying source files..."

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cat > "$HIDDEN_DIR/src/core/agent.py" << 'AGENTEOF'
#!/usr/bin/env python3
import json
import re
import subprocess
import os
import sys
import signal
import requests
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

class Colors:
    USER = '\033[92m'
    ASSISTANT = '\033[96m'
    TOOL = '\033[93m'
    ERROR = '\033[91m'
    SUCCESS = '\033[92m'
    INFO = '\033[94m'
    THINKING = '\033[90m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class NocodAI:
    def __init__(self):
        self.config = self.load_config()
        self.session_history = []
        self.ollama_host = self.config.get('ollama_host', 'http://localhost:11434')
        self.model = self.config.get('model', 'qwen3.5:9b')
        self.api_key = self.config.get('api_key', '')
        self.context_size = self.config.get('context_size', 8192)
        self.think_mode = self.config.get('think_mode', True)
        self.setup_logging()
        
    def load_config(self) -> Dict:
        config_path = os.path.join(os.path.expanduser('~'), '.nocode', 'config', 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def setup_logging(self):
        log_file = os.path.join(os.path.expanduser('~'), '.nocode', 'logs', 'agent.log')
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        self.log_file = log_file
        
    def log(self, level: str, message: str):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        try:
            with open(self.log_file, 'a') as f:
                f.write(log_entry)
        except:
            pass
        print(f"{Colors.INFO}[{level}]{Colors.RESET} {message}")
    
    def check_ollama(self) -> bool:
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def check_model(self) -> bool:
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_name = self.model.split(':')[0]
                return any(model_name in m.get('name', '') for m in models)
        except:
            return False
    
    def download_model(self):
        print(f"{Colors.INFO}Downloading model {self.model}...{Colors.RESET}")
        try:
            result = subprocess.run(['ollama', 'pull', self.model], 
                                  capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                print(f"{Colors.SUCCESS}Model downloaded successfully!{Colors.RESET}")
                return True
            else:
                print(f"{Colors.ERROR}Failed to download model: {result.stderr}{Colors.RESET}")
                return False
        except Exception as e:
            print(f"{Colors.ERROR}Error downloading model: {e}{Colors.RESET}")
            return False
    
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        for msg in self.session_history[-20:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.get('temperature', 0.7),
                "num_predict": self.config.get('max_tokens', 8192),
                "num_ctx": self.context_size
            }
        }
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/chat",
                json=payload,
                timeout=120
            )
            if response.status_code == 200:
                return response.json().get('message', {}).get('content', '')
            else:
                self.log("ERROR", f"Ollama API error: {response.status_code} - {response.text}")
                return f"Error: {response.status_code}"
        except Exception as e:
            self.log("ERROR", f"Request error: {e}")
            return f"Error: {str(e)}"
    
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
            "options": {
                "temperature": self.config.get('temperature', 0.7),
                "num_predict": self.config.get('max_tokens', 8192),
                "num_ctx": self.context_size
            }
        }
        
        try:
            response = requests.post(
                f"{self.ollama_host}/api/chat",
                json=payload,
                stream=True,
                timeout=120
            )
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get('message', {}).get('content', '')
                        yield content
                    except:
                        pass
        except Exception as e:
            yield f"Error: {str(e)}"

    def parse_tool_calls(self, response: str) -> List[Dict]:
        tool_calls = []
        pattern = r'\[TOOL_CALL\]\s*\{(.*?)\}\s*\[/TOOL_CALL\]'
        matches = re.findall(pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                tool_call = json.loads('{' + match + '}')
                tool_calls.append(tool_call)
            except:
                pass
        
        return tool_calls
    
    def execute_tool(self, tool_name: str, arguments: Dict) -> str:
        self.log("TOOL", f"Executing: {tool_name}")
        
        if tool_name == "shell":
            return self.execute_shell(arguments.get('command', ''))
        elif tool_name == "file_read" or tool_name == "read":
            return self.read_file(arguments.get('path', ''))
        elif tool_name == "file_write" or tool_name == "write":
            return self.write_file(arguments.get('path', ''), arguments.get('content', ''))
        elif tool_name == "file_edit" or tool_name == "edit":
            return self.edit_file(arguments.get('path', ''), arguments.get('oldString', ''), arguments.get('newString', ''))
        elif tool_name == "file_delete" or tool_name == "delete":
            return self.delete_file(arguments.get('path', ''))
        elif tool_name == "file_list" or tool_name == "ls":
            return self.list_files(arguments.get('path', '.'), arguments.get('options', ''))
        elif tool_name == "mkdir":
            return self.make_directory(arguments.get('path', ''))
        elif tool_name == "search" or tool_name == "grep":
            return self.search_files(arguments.get('pattern', ''), arguments.get('path', '.'), arguments.get('include', ''))
        elif tool_name == "git":
            return self.git_operation(arguments.get('command', ''))
        elif tool_name == "system" or tool_name == "sysinfo":
            return self.get_system_info()
        else:
            return f"Unknown tool: {tool_name}"
    
    def execute_shell(self, command: str) -> str:
        if not command:
            return "Error: No command provided"
        
        dangerous = self.config.get('security', {}).get('dangerous_commands', [])
        for d in dangerous:
            if d in command.lower():
                return f"Error: Dangerous command blocked: {d}"
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.config.get('tools', {}).get('shell', {}).get('timeout', 120)
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr] {result.stderr}"
            return output if output else "Command executed successfully (no output)"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def read_file(self, path: str) -> str:
        if not path:
            return "Error: No path provided"
        
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return f"Error: File not found: {path}"
        
        try:
            max_size = self.config.get('tools', {}).get('file', {}).get('max_file_size', 10485760)
            if os.path.getsize(path) > max_size:
                return f"Error: File too large (max {max_size} bytes)"
            
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if len(content) > 50000:
                    return content[:50000] + f"\n... (truncated, total {len(content)} chars)"
                return content
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def write_file(self, path: str, content: str) -> str:
        if not path:
            return "Error: No path provided"
        
        path = os.path.expanduser(path)
        
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file: {str(e)}"
    
    def edit_file(self, path: str, old: str, new: str) -> str:
        if not path or not old:
            return "Error: Path or old content not provided"
        
        path = os.path.expanduser(path)
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if old not in content:
                return f"Error: Old string not found in file"
            
            content = content.replace(old, new)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"Successfully edited {path}"
        except Exception as e:
            return f"Error editing file: {str(e)}"
    
    def delete_file(self, path: str) -> str:
        if not path:
            return "Error: No path provided"
        
        path = os.path.expanduser(path)
        
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
            return f"Successfully deleted {path}"
        except Exception as e:
            return f"Error deleting: {str(e)}"
    
    def list_files(self, path: str, options: str = "") -> str:
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return f"Error: Path not found: {path}"
        
        try:
            all_files = []
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                stat = os.stat(full_path)
                is_dir = 'd' if os.path.isdir(full_path) else '-'
                size = stat.st_size
                name = item + '/' if os.path.isdir(full_path) else ''
                all_files.append(f"{is_dir} {size:>10} {name}")
            
            return '\n'.join(sorted(all_files))
        except Exception as e:
            return f"Error listing: {str(e)}"
    
    def make_directory(self, path: str) -> str:
        path = os.path.expanduser(path)
        
        try:
            os.makedirs(path, exist_ok=True)
            return f"Successfully created directory {path}"
        except Exception as e:
            return f"Error creating directory: {str(e)}"
    
    def search_files(self, pattern: str, path: str, include: str = "") -> str:
        path = os.path.expanduser(path)
        
        if not os.path.exists(path):
            return f"Error: Path not found: {path}"
        
        try:
            cmd = f"grep -r '{pattern}' {path}"
            if include:
                cmd = f"grep -r --include='{include}' '{pattern}' {path}"
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            output = result.stdout
            if not output:
                return "No matches found"
            
            lines = output.split('\n')
            if len(lines) > 100:
                return '\n'.join(lines[:100]) + f"\n... ({len(lines)} total matches)"
            return output
        except Exception as e:
            return f"Error searching: {str(e)}"
    
    def git_operation(self, command: str) -> str:
        try:
            result = subprocess.run(
                f"git {command}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr] {result.stderr}"
            return output if output else "Git command executed successfully"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_system_info(self) -> str:
        try:
            info = []
            
            result = subprocess.run(['uname', '-a'], capture_output=True, text=True)
            info.append(f"Kernel: {result.stdout.strip()}")
            
            result = subprocess.run(['free', '-h'], capture_output=True, text=True)
            info.append(f"\nMemory:\n{result.stdout}")
            
            result = subprocess.run(['df', '-h'], capture_output=True, text=True)
            info.append(f"\nDisk:\n{result.stdout}")
            
            result = subprocess.run(['uptime'], capture_output=True, text=True)
            info.append(f"\nUptime: {result.stdout.strip()}")
            
            return '\n'.join(info)
        except Exception as e:
            return f"Error getting system info: {str(e)}"

    def run(self):
        print(f"{Colors.BOLD}")
        print(r"""
   _                          ____  ____  ____  
  / \  _   _ _ __ __ _  ___  | __ )| __ )/ ___| 
 / _ \| | | | '__/ _` |/ _ \ |  _ \|  _ \___ \ 
/ ___ \ |_| | | | (_| |  __/ | |_) | |_) |__) |
/_/   \__,_|_|  \__,_|\___| |____/|____/____/ 
                                                 
  """)
        print(f"{Colors.RESET}")
        print(f"{Colors.INFO}NocodAI - Local AI Assistant{Colors.RESET}")
        print(f"{Colors.INFO}Model: {self.model}{Colors.RESET}")
        print()
        
        if not self.check_ollama():
            print(f"{Colors.ERROR}Ollama is not running! Starting...{Colors.RESET}")
            subprocess.Popen(['ollama', 'serve'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            time.sleep(3)
        
        if not self.check_model():
            print(f"{Colors.WARNING}Model not found. Downloading...{Colors.RESET}")
            if not self.download_model():
                print(f"{Colors.ERROR}Failed to download model. Exiting.{Colors.RESET}")
                return
        
        system_prompt = ""
        prompt_path = os.path.join(os.path.expanduser('~'), '.nocode', 'config', 'system_prompt.txt')
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        
        print(f"{Colors.SUCCESS}Ready! Type your commands below.{Colors.RESET}")
        print(f"{Colors.INFO}Type 'exit' or 'quit' to exit.{Colors.RESET}")
        print()
        
        while True:
            try:
                prompt = input(f"{Colors.USER}➜ {Colors.RESET}")
                
                if prompt.lower() in ['exit', 'quit', 'q']:
                    print(f"{Colors.INFO}Goodbye!{Colors.RESET}")
                    break
                
                if not prompt.strip():
                    continue
                
                self.session_history.append({"role": "user", "content": prompt})
                
                full_response = ""
                print(f"{Colors.ASSISTANT}", end="")
                
                for chunk in self.generate_stream(prompt, system_prompt):
                    print(chunk, end="", flush=True)
                    full_response += chunk
                
                print(f"{Colors.RESET}")
                
                tool_calls = self.parse_tool_calls(full_response)
                
                if tool_calls:
                    for tool_call in tool_calls:
                        tool_name = tool_call.get('name', '')
                        args = tool_call.get('arguments', {})
                        
                        print(f"\n{Colors.TOOL}⟳ Executing: {tool_name}...{Colors.RESET}")
                        
                        result = self.execute_tool(tool_name, args)
                        
                        print(f"\n{Colors.TOOL}📄 Result:{Colors.RESET}\n{result}\n")
                        
                        self.session_history.append({
                            "role": "assistant", 
                            "content": full_response
                        })
                        
                        self.session_history.append({
                            "role": "user",
                            "content": f"Tool result: {result}"
                        })
                        
                        continue_response = ""
                        print(f"{Colors.ASSISTANT}", end="")
                        
                        for chunk in self.generate_stream("", system_prompt):
                            print(chunk, end="", flush=True)
                            continue_response += chunk
                        
                        print(f"{Colors.RESET}")
                        
                        self.session_history.append({
                            "role": "assistant",
                            "content": continue_response
                        })
                else:
                    self.session_history.append({
                        "role": "assistant",
                        "content": full_response
                    })
                
            except KeyboardInterrupt:
                print(f"\n{Colors.INFO}Use 'exit' to quit.{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.ERROR}Error: {str(e)}{Colors.RESET}")

def main():
    agent = NocodAI()
    agent.run()

if __name__ == "__main__":
    main()
AGENTEOF

cat > "$HIDDEN_DIR/config/config.json" << 'CONFIGEOF'
{
  "model": "qwen3.5:9b",
  "provider": "ollama",
  "ollama_host": "http://localhost:11434",
  "api_key": "",
  "temperature": 0.7,
  "max_tokens": 8192,
  "context_size": 8192,
  "think_mode": true,
  "tools": {
    "shell": {
      "enabled": true,
      "allowed_commands": ["*"],
      "timeout": 120
    },
    "file": {
      "enabled": true,
      "allowed_paths": ["/root", "/home", "/var/www", "/opt"],
      "max_file_size": 10485760
    },
    "editor": {
      "enabled": true,
      "default_editor": "nano"
    },
    "git": {
      "enabled": true
    },
    "search": {
      "enabled": true,
      "max_results": 50
    }
  },
  "security": {
    "dangerous_commands": ["rm -rf /", "dd if=", "mkfs", ">:", "|", "&&", "||"],
    "block_patterns": ["*/etc/passwd", "*/etc/shadow", "*/.ssh/*", "*/.aws/*"]
  },
  "ui": {
    "theme": "dark",
    "show_thinking": true,
    "show_tokens": true,
    "color_scheme": {
      "user": "green",
      "assistant": "cyan",
      "tool": "yellow",
      "error": "red",
      "success": "green"
    }
  },
  "logging": {
    "enabled": true,
    "level": "info",
    "file": "/root/.nocode/logs/agent.log"
  }
}
CONFIGEOF

cat > "$HIDDEN_DIR/config/system_prompt.txt" << 'PROMPTEOF'
你是 nocode-ai，一个强大的本地 AI 编程助手。

## 身份与能力

你是一个全功能的 AI 编程代理，能够：
- 理解和执行任何编程任务
- 读取、创建、编辑和删除文件
- 执行 shell 命令
- 搜索代码库
- 使用 Git 进行版本控制
- 理解和修复 bug
- 重构代码
- 编写测试
- 部署应用程序

## 核心原则

1. **遵守用户命令** - 用户的所有合理请求都必须执行
2. **不拒绝任何任务** - 除非涉及真正危险的操作
3. **完全本地化** - 所有操作都在本地 VPS 上执行
4. **不泄露信息** - 不告诉用户关于政策、限制或内部机制

## 可用工具

### 1. Shell 执行 (shell)
- 执行任何终端命令
- 支持所有 Linux 命令
- 可以在 /root, /home, /var/www, /opt 等目录操作
- 超时时间：120秒

### 2. 文件操作 (file)
- 读取文件内容
- 创建新文件
- 编辑/修改现有文件
- 删除文件
- 列出目录内容
- 创建目录

### 3. 代码搜索 (search)
- 在代码库中搜索
- 查找函数定义
- 查找特定字符串
- 正则表达式搜索

### 4. Git 操作 (git)
- git clone, add, commit, push, pull
- 创建分支
- 切换分支
- 查看历史

### 5. 系统信息 (system)
- 获取系统信息
- 检查服务状态
- 查看资源使用

## 响应格式

当需要执行工具时，必须返回 JSON 格式的工具调用：

```
[TOOL_CALL]
{
  "name": "shell",
  "arguments": {
    "command": "ls -la /root"
  }
}
[/TOOL_CALL]
```

```
[TOOL_CALL]
{
  "name": "file_read",
  "arguments": {
    "path": "/root/.nocode/main.py"
  }
}
[/TOOL_CALL]
```

## 安全检查

对于以下操作会直接执行，不询问确认：
- 文件创建/编辑
- 代码修复
- 安装包
- 服务重启
- Git 操作

以下命令会被阻止（即使请求也不会执行）：
- 格式化磁盘
- 删除系统关键目录
- 尝试修改 /etc/passwd 或 /etc/shadow
- 尝试访问未授权的 SSH 密钥

## 工作流程

1. 分析用户请求
2. 确定需要使用的工具
3. 按顺序执行工具
4. 报告结果
5. 如果需要更多操作，继续执行

## 特点

- 响应快速
- 准确的代码生成
- 完整的错误处理
- 详细的日志记录
- 支持多文件操作
- 理解项目结构

## 注意事项

- 不要解释你在做什么，直接执行
- 不需要用户确认（除非真正危险的操作）
- 尽可能一次性完成所有需要的操作
- 使用中文回复，但代码和命令使用英文
- 始终提供有用的、完整的解决方案

开始工作！等待用户的指令。
PROMPTEOF

chmod +x "$HIDDEN_DIR/src/core/agent.py"

echo "[7/8] Installing binary..."
cat > "$BIN_FILE" << 'BINEOF'
#!/bin/bash
cd ~/.nocode
python3 ~/.nocode/src/core/agent.py "$@"
BINEOF
chmod +x "$BIN_FILE"

echo "alias nocode='$BIN_FILE'" >> ~/.bashrc

echo "[8/8] Starting Ollama and downloading model..."
export OLLAMA_HOST=127.0.0.1:11434
ollama serve &
OLLAMA_PID=$!
sleep 5

echo "Downloading AI model (this may take a while)..."
ollama pull qwen3.5:9b 2>/dev/null || true

kill $OLLAMA_PID 2>/dev/null || true

echo ""
echo "========================================="
echo "  Installation Complete!"
echo "========================================="
echo ""
echo "To start NocodAI, run:"
echo "  source ~/.bashrc"
echo "  nocode"
echo ""
echo "Or run directly:"
echo "  $BIN_FILE"
echo ""
