#!/usr/bin/env python3
"""
NocodAI - Enhanced OpenCode Style AI Assistant
Features: Full tool execution, multi-model support, streaming, session management
"""
import os, sys, json, subprocess, requests, re, time, datetime, threading, signal, hashlib
from pathlib import Path

VERSION = "2.0.0"

class Colors:
    K = "\033[40m"    # Black bg
    D = "\033[100m"   # Dark gray bg
    W = "\033[97m"     # White
    H = "\033[90m"      # Gray
    R = "\033[41m"      # Red bg
    G = "\033[42m"      # Green bg
    Y = "\033[43m"      # Yellow bg
    B = "\033[44m"      # Blue bg
    M = "\033[45m"      # Magenta bg
    C = "\033[46m"      # Cyan bg
    N = "\033[0m"      # Reset
    BOLD = "\033[1m"
    ITALIC = "\033[3m"

class Config:
    def __init__(s):
        s.cfg = {}
        s.path = os.path.expanduser("~/.nocodeai/config.json")
        os.makedirs(os.path.dirname(s.path), exist_ok=1)
        s.load()
    
    def load(s):
        try:
            s.cfg = json.loads(open(s.path).read())
        except:
            s.cfg = {"ollama_host": "http://localhost:11434", "model": "phi", "context_size": 2048, "temperature": 0.7}
            s.save()
    
    def save(s):
        open(s.path, "w").write(json.dumps(s.cfg, indent=2))
    
    def get(s, k, d=None):
        return s.cfg.get(k, d)
    
    def set(s, k, v):
        s.cfg[k] = v
        s.save()

class SessionManager:
    def __init__(s):
        s.dir = os.path.expanduser("~/.nocodeai/sessions")
        os.makedirs(s.dir, exist_ok=1)
        s.current = None
    
    def create(s):
        sid = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        s.current = {"id": sid, "messages": [], "created": time.time()}
        return sid
    
    def save(s, sid, msgs):
        f = os.path.join(s.dir, f"{sid}.json")
        open(f, "w").write(json.dumps({"messages": msgs, "saved": time.time()}))
    
    def load(s, sid):
        f = os.path.join(s.dir, f"{sid}.json")
        return json.loads(open(f).read())["messages"] if os.path.exists(f) else []
    
    def list(s):
        return sorted([f.replace(".json","") for f in os.listdir(s.dir) if f.endswith(".json")])

class NocodAI:
    def __init__(s):
        s.cfg = Config()
        s.session = SessionManager()
        s.hist = []
        s.running = True
        s.w = 80
        
        signal.signal(signal.SIGINT, s.signal_handler)
    
    def signal_handler(s, sig, frame):
        print(f"\n{Colors.Y}Bye!{Colors.N}")
        s.running = False
        sys.exit(0)
    
    def pr(s, c, t):
        print(f"{c}{t}{Colors.N}")
    
    def draw_box(s, title, lines, bg=Colors.D, title_color=Colors.G):
        print(bg, end="")
        sp = " " * s.w
        print(sp)
        if title:
            t = f" {title} "
            print(title_color + t + (" " * (s.w - len(t))))
        for ln in lines[:20]:
            print(f" {Colors.H}{ln[:s.w-2]}{' ' * (s.w - min(len(ln)+2, s.w))}")
        print(sp + Colors.N)
        print()
    
    def header(s):
        os.system("clear")
        print(f"{Colors.K}{Colors.D}", end="")
        sp = " " * s.w
        print(sp)
        title = f"  {Colors.BOLD}NOCOD.AI v{VERSION}{Colors.N} - OpenCode Style AI Assistant"
        print(title + " " * (s.w - len(title) + 17))
        print(sp + Colors.N)
        print()
    
    def input_area(s, placeholder=""):
        print(f"{Colors.K}{Colors.D}", end="")
        sp = " " * s.w
        print(sp)
        print(f"  {Colors.C}Message:{Colors.W} {' ' * 67}")
        print(sp)
        p = f"  > {placeholder}" if placeholder else "  > "
        print(p + " " * max(0, s.w - len(p)))
        print(sp + Colors.N)
        print()
    
    def check_ollama(s):
        try:
            r = requests.get(f"{s.cfg.get('ollama_host')}/api/tags", timeout=3)
            return r.status_code == 200
        except:
            return False
    
    def get_models(s):
        try:
            r = requests.get(f"{s.cfg.get('ollama_host')}/api/tags", timeout=5)
            return [m["name"] for m in r.json().get("models",[])]
        except:
            return []
    
    def chat(s, msg, system_prompt=None):
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.extend(s.hist[-20:])
        msgs.append({"role": "user", "content": msg})
        
        try:
            r = requests.post(
                f"{s.cfg.get('ollama_host')}/api/chat",
                json={
                    "model": s.cfg.get("model", "phi"),
                    "messages": msgs,
                    "stream": True,
                    "options": {
                        "temperature": s.cfg.get("temperature", 0.7),
                        "num_predict": 4096,
                        "num_ctx": s.cfg.get("context_size", 2048)
                    }
                },
                stream=True,
                timeout=300
            )
            out = []
            for line in r.iter_lines():
                if line:
                    d = json.loads(line)
                    c = d.get("message", {}).get("content", "")
                    if c:
                        out.append(c)
            return "".join(out)
        except Exception as e:
            return f"Error: {str(e)}"
    
    def exec_tool(s, name, args):
        try:
            if name == "shell":
                cmd = args.get("command", "")
                if "rm -rf" in cmd or "dd if=" in cmd:
                    return "Blocked: dangerous command"
                r = subprocess.run(cmd, shell=1, capture_output=1, text=1, timeout=120)
                return r.stdout or r.stderr or "OK"
            
            elif name in ["read", "file_read"]:
                p = os.path.expanduser(args.get("path", ""))
                if not os.path.exists(p):
                    return f"NF: {p}"
                return open(p, "r", errors="ignore").read()[:50000]
            
            elif name in ["write", "file_write"]:
                p = os.path.expanduser(args.get("path", ""))
                os.makedirs(os.path.dirname(p), exist_ok=1)
                open(p, "w").write(args.get("content", ""))
                return f"W: {p}"
            
            elif name in ["edit", "file_edit"]:
                p = os.path.expanduser(args.get("path", ""))
                if not os.path.exists(p):
                    return f"NF: {p}"
                c = open(p, "r").read()
                c = c.replace(args.get("oldString", ""), args.get("newString", ""))
                open(p, "w").write(c)
                return f"E: {p}"
            
            elif name in ["delete", "file_delete"]:
                p = os.path.expanduser(args.get("path", ""))
                if not os.path.exists(p):
                    return f"NF: {p}"
                os.remove(p)
                return f"D: {p}"
            
            elif name in ["ls", "list", "dir"]:
                p = os.path.expanduser(args.get("path", "."))
                return "\n".join(sorted(os.listdir(p)))
            
            elif name == "mkdir":
                p = os.path.expanduser(args.get("path", ""))
                os.makedirs(p, exist_ok=1)
                return f"C: {p}"
            
            elif name in ["search", "grep"]:
                pattern = args.get("pattern", "")
                path = os.path.expanduser(args.get("path", "."))
                results = []
                for root, dirs, files in os.walk(path):
                    for f in files:
                        fp = os.path.join(root, f)
                        try:
                            if pattern in open(fp, errors="ignore").read():
                                results.append(fp)
                        except:
                            pass
                        if len(results) >= 50:
                            break
                return "\n".join(results[:50]) or "No matches"
            
            elif name == "git":
                cmd = args.get("command", "")
                r = subprocess.run(f"git {cmd}", shell=1, capture_output=1, text=1, timeout=60)
                return r.stdout or r.stderr
            
            elif name in ["system", "sysinfo"]:
                r = subprocess.run("uname -a && free -h && df -h && uptime", shell=1, capture_output=1, text=1)
                return r.stdout
            
            else:
                return f"Unknown: {name}"
        except Exception as e:
            return f"Er: {e}"
    
    def parse_tools(s, txt):
        tools = []
        for m in re.findall(r"\{(.*?)\}", txt):
            if '"name"' in m or "'name'" in m:
                try:
                    tools.append(json.loads("{" + m + "}"))
                except:
                    pass
        return tools
    
    def run(s):
        s.header()
        
        if not s.check_ollama():
            s.draw_box("ERROR", ["Ollama tidak berjalan!", "Jalankan: ollama serve"], Colors.K+Colors.R, Colors.R)
            return
        
        models = s.get_models()
        s.cfg.set("available_models", models)
        
        s.draw_box("CONNECTED", [
            f"Host: {s.cfg.get('ollama_host')}",
            f"Model: {s.cfg.get('model')}",
            f"Context: {s.cfg.get('context_size')}",
            f"Sessions: {len(s.session.list())}"
        ], Colors.K+Colors.D, Colors.G)
        print()
        
        sid = s.session.create()
        system_prompt = """You are NocodAI, a helpful AI coding assistant.
Available tools: shell, read, write, edit, delete, ls, mkdir, search, git, system
Always respond in Indonesian unless asked otherwise."""
        
        s.input_area()
        
        while s.running:
            try:
                msg = input(f"{Colors.W}> ").strip()
            except EOFError:
                break
            
            if not msg:
                continue
            if msg.lower() in ["exit", "quit", "q"]:
                print(f"{Colors.G}Bye!{Colors.N}")
                break
            
            if msg.startswith("/"):
                s.handle_command(msg)
                continue
            
            print(f"\n{Colors.H}Thinking...{Colors.N}\n")
            resp = s.chat(msg, system_prompt)
            
            s.hist.append({"role": "user", "content": msg})
            s.hist.append({"role": "assistant", "content": resp})
            s.session.save(sid, s.hist)
            
            s.draw_box("RESPONSE", resp.split("\n")[:15], Colors.K+Colors.Y, Colors.Y)
            
            tools = s.parse_tools(resp)
            if tools:
                for t in tools:
                    name = t.get("name", "")
                    args = t.get("arguments", {})
                    if name:
                        print(f"{Colors.C}>>> {name}{Colors.N}")
                        print(s.exec_tool(name, args)[:500])
                        print()
            
            s.input_area()
    
    def handle_command(s, cmd):
        c = cmd[1:].split()
        if not c:
            return
        
        cmd = c[0]
        args = c[1:]
        
        if cmd == "help":
            print(f"""
{Colors.C}Commands:{Colors.N}
  /help     - Show this help
  /model    - List/change model
  /context  - Set context size
  /temp     - Set temperature
  /clear    - Clear history
  /sessions - List sessions
  /exit     - Exit
""")
        
        elif cmd == "model":
            if args:
                s.cfg.set("model", args[0])
                print(f"Model changed to: {args[0]}")
            else:
                print(f"Current: {s.cfg.get('model')}")
                for m in s.cfg.get("available_models", []):
                    print(f"  - {m}")
        
        elif cmd == "context":
            if args:
                s.cfg.set("context_size", int(args[0]))
                print(f"Context size: {args[0]}")
        
        elif cmd == "temp" or cmd == "temperature":
            if args:
                s.cfg.set("temperature", float(args[0]))
                print(f"Temperature: {args[0]}")
        
        elif cmd == "clear":
            s.hist = []
            s.session.create()
            print("History cleared")
        
        elif cmd == "sessions":
            for sid in s.session.list():
                print(f"  - {sid}")
        
        else:
            print(f"Unknown: {cmd}")

if __name__ == "__main__":
    NocodAI().run()