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
import threading
import urllib.request
import ssl

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
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def setup_logging(self):
        log_file = self.config.get('logging', {}).get('file', '/root/.nocode/logs/agent.log')
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
        prompt_path = os.path.join(os.path.dirname(__file__), 'config', 'system_prompt.txt')
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
