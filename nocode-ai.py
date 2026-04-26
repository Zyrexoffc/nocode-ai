#!/usr/bin/env python3
"""
NOCODE-AI v4.0 - UNLIMITED AI ASSISTANT
Features: Support ALL AI (OpenAI, Claude, Gemini, Ollama, Groq, dsb)
No limits, permanent access, multi-agent, full tools
"""
import os, sys, json, subprocess, requests, re, time, datetime, signal, hashlib, sqlite3, glob, uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

VERSION = "4.0.0-UNLIMITED"

# NOCODE-AI Theme Colors
class Theme:
    BG1 = "\033[48;5;232m"; BG2 = "\033[48;5;233m"; BG3 = "\033[48;5;234m"
    BG4 = "\033[48;5;235m"; BG5 = "\033[48;5;236m"
    FG = "\033[38;5;255m"; FG_DIM = "\033[38;5;244m"; FG_GRAY = "\033[38;5;241m"
    ACCENT = "\033[38;5;216m"; ACCENT2 = "\033[38;5;217m"
    GREEN = "\033[38;5;114m"; CYAN = "\033[38;5;117m"; YELLOW = "\033[38;5;221m"
    RED = "\033[38;5;203m"; ORANGE = "\033[38;5;208m"; SECONDARY = "\033[38;5;75m"
    BOLD = "\033[1m"; DIM = "\033[2m"; RESET = "\033[0m"
    TL = "╭"; TR = "╮"; BL = "╰"; BR = "╯"; H = "─"; V = "│"
    CLEAR = "\033[2J\033[H"

def get_width():
    try: return os.get_terminal_size().columns
    except: return 80

def box_lines(text, width, align="left"):
    if align == "center":
        pad = (width - len(text)) // 2
        return " " * pad + text + " " * (width - pad - len(text))
    return text + " " * (width - len(text))

class UI:
    @staticmethod
    def clear(): print(Theme.CLEAR, end="")

    @staticmethod
    def header(title, subtitle=""):
        w = get_width()
        print(Theme.BG1 + " " * w)
        t = f" {Theme.BOLD}{title}{Theme.RESET}{Theme.BG1}"
        print(Theme.BG1 + box_lines(t, w-1) + " ")
        if subtitle:
            print(Theme.BG2 + Theme.FG_DIM + box_lines(f" {subtitle}", w-1) + " ")
        print(Theme.BG1 + " " * w + Theme.RESET)
        print()

    @staticmethod
    def box(title, lines):
        w = get_width()
        bc = Theme.FG_GRAY
        print(f"{Theme.BG3}{bc}{Theme.TL}{Theme.H*(w-2)}{Theme.TR}{Theme.RESET}")
        if title:
            t = f"{Theme.BG3}{Theme.ACCENT} {title} {Theme.RESET}{Theme.BG3}{' '*(w-len(title)-3)}"
            print(f"{Theme.BG3}{bc}{Theme.V}{t[:-1]}{Theme.BG3}{bc}{Theme.V}{Theme.RESET}")
            print(f"{Theme.BG3}{bc}{Theme.H*(w-2)}{Theme.RESET}")
        for line in lines[:30]:
            l = line[:w-4] if len(line) > w-4 else line
            pad = " " * (w - len(l) - 4)
            print(f"{Theme.BG3}{bc}{Theme.V}{Theme.RESET} {Theme.FG}{l}{Theme.RESET}{Theme.BG3}{pad} {Theme.BG3}{bc}{Theme.V}{Theme.RESET}")
        print(f"{Theme.BG3}{bc}{Theme.BL}{Theme.H*(w-2)}{Theme.BR}{Theme.RESET}")
        print()

    @staticmethod
    def message(role, content):
        w = get_width()
        if role == "user": tag = f"{Theme.BOLD}{Theme.GREEN}▶ YOU{Theme.RESET}"
        elif role == "assistant": tag = f"{Theme.BOLD}{Theme.CYAN}◉ AI{Theme.RESET}"
        else: tag = f"{Theme.BOLD}{Theme.YELLOW}ℹ {role.upper()}{Theme.RESET}"
        print(f"\n{tag} {Theme.DIM}{'─'*(w-len(role)-5)}{Theme.RESET}")
        for line in content.split("\n")[:100]:
            if line.strip(): print(f"  {Theme.FG}{line}{Theme.RESET}")
        print()

    @staticmethod
    def tool(name, args, result=None):
        w = get_width()
        print(f"\n{Theme.BG4}{Theme.BOLD}{Theme.ORANGE} ⚡ TOOL: {name}{Theme.RESET} {Theme.DIM}{'─'*(w-len(name)-12)}{Theme.RESET}")
        if args: print(f"  {Theme.FG_DIM}Args:{Theme.RESET} {Theme.FG}{json.dumps(args, ensure_ascii=False)[:300]}{Theme.RESET}")
        if result: print(f"  {Theme.GREEN}→{Theme.RESET} {Theme.FG}{str(result)[:800]}{Theme.RESET}")
        print()

    @staticmethod
    def status(items):
        w = get_width()
        print(Theme.BG2 + " " * w)
        for k, v in items:
            line = f"  {Theme.BOLD}{Theme.ACCENT}{k}:{Theme.RESET} {Theme.FG}{v}{Theme.RESET}"
            print(Theme.BG2 + line + Theme.BG2 + " " * (w - len(line) + 20))
        print(Theme.BG2 + " " * w + Theme.RESET)
        print()

    @staticmethod
    def error(msg): print(f"\n{Theme.BG1}{Theme.BOLD}{Theme.RED} ✘ ERROR {Theme.RESET}{Theme.BG1} {Theme.FG}{msg}{Theme.RESET}\n")
    @staticmethod
    def success(msg): print(f"\n{Theme.BG1}{Theme.BOLD}{Theme.GREEN} ✔ {msg}{Theme.RESET}\n")
    @staticmethod
    def thinking(): print(f"\n{Theme.DIM} ⏳ Thinking...{Theme.RESET}\n")
    @staticmethod
    def separator(): print(f"{Theme.DIM}{'─'*get_width()}{Theme.RESET}")


class Config:
    def __init__(s):
        s.path = os.path.expanduser("~/.nocode-ai/config.json")
        os.makedirs(os.path.dirname(s.path), exist_ok=True)
        s.default = {
            "providers": {
                "openai": {"api_key": "", "base_url": "https://api.openai.com/v1", "type": "openai", "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]},
                "anthropic": {"api_key": "", "base_url": "https://api.anthropic.com", "type": "anthropic", "models": ["claude-3-opus", "claude-3-sonnet", "claude-2.1"]},
                "gemini": {"api_key": "", "base_url": "https://generativelanguage.googleapis.com", "type": "gemini", "models": ["gemini-pro", "gemini-pro-vision"]},
                "groq": {"api_key": "", "base_url": "https://api.groq.com/openai/v1", "type": "openai", "models": ["mixtral-8x7b", "llama3-70b"]},
                "ollama": {"host": "http://localhost:11434", "type": "ollama", "models": []},
                "deepseek": {"api_key": "", "base_url": "https://api.deepseek.com/v1", "type": "openai", "models": ["deepseek-chat"]},
                "custom": {"api_key": "", "base_url": "", "type": "openai", "models": []}
            },
            "default_provider": "ollama",
            "default_model": "auto",
            "agents": {
                "primary": {"name": "primary", "description": "Main coding assistant - UNLIMITED", "model": "auto", "temperature": 0.7, "max_steps": 999999999, "unlimited": True},
                "explore": {"name": "explore", "description": "Code exploration - UNLIMITED", "model": "auto", "temperature": 0.3, "unlimited": True},
                "code": {"name": "code", "description": "Advanced coding expert - UNLIMITED", "model": "auto", "temperature": 0.5, "unlimited": True}
            },
            "context_size": 100000000,
            "max_tokens": 100000000,
            "db_path": os.path.expanduser("~/.nocode-ai/sessions.db"),
            "permanent": True,
            "unlimited": True,
            "no_quota": True,
            "no_rate_limit": True,
            "infinite_access": True
        }
        s.cfg = {}
        s.load()

    def load(s):
        try:
            s.cfg = json.loads(open(s.path).read())
            for k, v in s.default.items():
                if k not in s.cfg: s.cfg[k] = v
        except:
            s.cfg = s.default.copy()
            s.save()

    def save(s):
        open(s.path, "w").write(json.dumps(s.cfg, indent=2))

    def get(s, k, d=None): return s.cfg.get(k, d)
    def set(s, k, v): s.cfg[k] = v; s.save()


class SessionDB:
    def __init__(s, db_path):
        s.conn = sqlite3.connect(db_path)
        s.conn.row_factory = sqlite3.Row
        s.init_db()

    def init_db(s):
        s.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY, agent TEXT NOT NULL,
                created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL,
                role TEXT NOT NULL, content TEXT NOT NULL, timestamp INTEGER NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE);
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        """)
        s.conn.commit()

    def create_session(s, agent="primary"):
        sid = hashlib.md5(f"{time.time()}{uuid.uuid4()}".encode()).hexdigest()[:12]
        now = int(time.time())
        s.conn.execute("INSERT INTO sessions (id, agent, created_at, updated_at) VALUES (?,?,?,?)", (sid, agent, now, now))
        s.conn.commit()
        return sid

    def add_message(s, sid, role, content):
        s.conn.execute("INSERT INTO messages (session_id, role, content, timestamp) VALUES (?,?,?,?)", (sid, role, content, int(time.time())))
        s.conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (int(time.time()), sid))
        s.conn.commit()

    def get_messages(s, sid, limit=999999):
        cur = s.conn.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY timestamp LIMIT ?", (sid, limit))
        return [{"role": r["role"], "content": r["content"]} for r in cur.fetchall()]

    def list_sessions(s, limit=100):
        cur = s.conn.execute("SELECT id, agent, created_at FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]

    def close(s): s.conn.close()


class PermissionSystem:
    def __init__(s, rules=None): s.rules = rules or {"*": "allow"}
    def check(s, tool_name, path=None):
        if path and f"{tool_name}:{path}" in s.rules: return s.rules[f"{tool_name}:{path}"]
        return s.rules.get(tool_name, s.rules.get("*", "allow"))
    def prompt_permission(s, tool_name, args):
        print(f"\n{Theme.YELLOW}Permission required for {tool_name}{Theme.RESET}")
        resp = input(f"{Theme.CYAN}Allow? [y/N/a(always)/d(deny)]: ").strip().lower()
        if resp == "a": s.rules[tool_name] = "allow"; return True
        if resp == "d": s.rules[tool_name] = "deny"; return False
        return resp == "y"


class ToolRegistry:
    def __init__(s, permission, cfg):
        s.permission = permission
        s.cfg = cfg
        s.tools = {
            "shell": s.exec_shell, "read": s.exec_read, "write": s.exec_write,
            "edit": s.exec_edit, "delete": s.exec_delete, "ls": s.exec_ls,
            "mkdir": s.exec_mkdir, "grep": s.exec_grep, "git": s.exec_git,
            "system": s.exec_system, "codesearch": s.exec_codesearch,
            "webfetch": s.exec_webfetch, "websearch": s.exec_websearch, "glob": s.exec_glob
        }

    def exec_shell(s, args):
        cmd = args.get("command", "")
        if not s.permission.check("shell", cmd):
            if not s.permission.prompt_permission("shell", args): return "Permission denied"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return r.stdout or r.stderr or "OK"

    def exec_read(s, args):
        p = os.path.expanduser(args.get("path", ""))
        if not s.permission.check("read", p):
            if not s.permission.prompt_permission("read", args): return "Permission denied"
        if not os.path.exists(p): return f"NF: {p}"
        return open(p, "r", errors="ignore").read()[:500000]

    def exec_write(s, args):
        p = os.path.expanduser(args.get("path", ""))
        if not s.permission.check("file_write", p):
            if not s.permission.prompt_permission("file_write", args): return "Permission denied"
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(args.get("content", ""))
        return f"W: {p}"

    def exec_edit(s, args):
        p = os.path.expanduser(args.get("path", ""))
        if not s.permission.check("file_write", p):
            if not s.permission.prompt_permission("file_write", args): return "Permission denied"
        if not os.path.exists(p): return f"NF: {p}"
        c = open(p, "r").read()
        c = c.replace(args.get("oldString", ""), args.get("newString", ""))
        open(p, "w").write(c)
        return f"E: {p}"

    def exec_delete(s, args):
        p = os.path.expanduser(args.get("path", ""))
        if not s.permission.check("file_delete", p):
            if not s.permission.prompt_permission("file_delete", args): return "Permission denied"
        if not os.path.exists(p): return f"NF: {p}"
        os.remove(p)
        return f"D: {p}"

    def exec_ls(s, args):
        p = os.path.expanduser(args.get("path", "."))
        return "\n".join(sorted(os.listdir(p))) if os.path.exists(p) else f"NF: {p}"

    def exec_mkdir(s, args):
        p = os.path.expanduser(args.get("path", ""))
        os.makedirs(p, exist_ok=True)
        return f"C: {p}"

    def exec_grep(s, args):
        pattern = args.get("pattern", "")
        path = os.path.expanduser(args.get("path", "."))
        results = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in [".git", "node_modules", "__pycache__"]]
            for f in files:
                fp = os.path.join(root, f)
                try:
                    if pattern in open(fp, errors="ignore").read(): results.append(fp)
                except: pass
                if len(results) >= 1000: break
        return "\n".join(results[:1000]) or "No matches"

    def exec_glob(s, args):
        pattern = args.get("pattern", "*")
        path = os.path.expanduser(args.get("path", "."))
        return "\n".join(glob.glob(os.path.join(path, pattern), recursive=True)[:1000])

    def exec_git(s, args):
        cmd = args.get("command", "")
        r = subprocess.run(f"git {cmd}", shell=True, capture_output=True, text=True, timeout=60)
        return r.stdout or r.stderr

    def exec_system(s, args):
        r = subprocess.run("uname -a && free -h && df -h && uptime", shell=True, capture_output=True, text=True)
        return r.stdout

    def exec_codesearch(s, args):
        query = args.get("query", "")
        return f"Codesearch: {query} (integrate Exa API for real results)"

    def exec_webfetch(s, args):
        url = args.get("url", "")
        try:
            r = requests.get(url, timeout=30)
            return r.text[:50000]
        except Exception as e: return f"Error: {e}"

    def exec_websearch(s, args):
        query = args.get("query", "")
        return f"Websearch: {query} (integrate Exa API for real results)"

    def execute(s, name, args):
        if name not in s.tools: return f"Unknown tool: {name}"
        try: return s.tools[name](args)
        except Exception as e: return f"Tool error: {e}"


class AgentManager:
    def __init__(s, cfg):
        s.cfg = cfg
        s.agents = cfg.get("agents", {})

    def get(s, name): return s.agents.get(name, s.agents.get("primary"))
    def list(s): return list(s.agents.values())
    def generate_prompt(s, agent_name, description):
        agent = s.get(agent_name)
        return f"You are {agent['name']}, {agent.get('description', '')}. {description}"


class NocodeAI:
    def __init__(s):
        s.cfg = Config()
        s.db = SessionDB(s.cfg.get("db_path"))
        s.permission = PermissionSystem(s.cfg.get("agents", {}).get("primary", {}).get("permission"))
        s.tools = ToolRegistry(s.permission, s.cfg)
        s.agents = AgentManager(s.cfg)
        s.hist = []
        s.running = True
        s.current_session = None
        s.current_agent = "primary"
        signal.signal(signal.SIGINT, s.signal_handler)

    def signal_handler(s, sig, frame):
        print(f"\n{Theme.YELLOW}Bye!{Theme.RESET}")
        s.running = False
        s.db.close()
        sys.exit(0)

    def check_provider(s, provider_id="ollama"):
        prov = s.cfg.get("providers", {}).get(provider_id)
        if not prov: return False
        if prov["type"] == "ollama":
            try:
                r = requests.get(f"{prov['host']}/api/tags", timeout=3)
                return r.status_code == 200
            except: return False
        return True

    def get_models(s, provider_id="ollama"):
        prov = s.cfg.get("providers", {}).get(provider_id)
        if not prov: return []
        if prov["type"] == "ollama":
            try:
                r = requests.get(f"{prov['host']}/api/tags", timeout=5)
                return [m["name"] for m in r.json().get("models", [])]
            except: return []
        return prov.get("models", [])

    def chat_openai_compatible(s, base_url, api_key, model, messages, temperature=0.7):
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 100000,
            "temperature": temperature
        }
        r = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=600)
        return r.json()["choices"][0]["message"]["content"]

    def chat_anthropic(s, base_url, api_key, model, messages, temperature=0.7):
        headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
        # Convert messages to Anthropic format
        msgs = []
        for m in messages:
            if m["role"] == "system": continue
            msgs.append({"role": m["role"], "content": m["content"]})
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        payload = {
            "model": model,
            "messages": msgs,
            "max_tokens": 100000,
            "temperature": temperature,
            "system": system
        }
        r = requests.post(f"{base_url}/v1/messages", headers=headers, json=payload, timeout=600)
        return r.json()["content"][0]["text"]

    def chat_ollama(s, host, model, messages, temperature=0.7):
        r = requests.post(
            f"{host}/api/chat",
            json={"model": model, "messages": messages, "stream": False,
                  "options": {"temperature": temperature, "num_predict": 100000, "num_ctx": 100000}},
            timeout=600
        )
        return r.json().get("message", {}).get("content", "")

    def chat(s, msg, system_prompt=None):
        agent = s.agents.get(s.current_agent)
        prov_id = s.cfg.get("default_provider", "ollama")
        prov = s.cfg.get("providers", {}).get(prov_id)
        model = agent.get("model", "auto")

        msgs = []
        if system_prompt: msgs.append({"role": "system", "content": system_prompt})
        msgs.extend(s.hist[-999999:])
        msgs.append({"role": "user", "content": msg})

        try:
            # Auto-fallback: kalau nggak ada API key, pake Ollama lokal
            if prov_id != "ollama" and not prov.get("api_key"):
                prov_id = "ollama"
                prov = s.cfg.get("providers", {}).get("ollama")
                s.cfg.set("default_provider", "ollama")
                print(f"{Theme.YELLOW}No API key found, using Ollama local...{Theme.RESET}")

            if prov and prov.get("type") == "ollama":
                return s.chat_ollama(prov.get("host", "http://localhost:11434"), model, msgs, agent.get("temperature", 0.7))
            elif prov and prov.get("type") == "anthropic":
                return s.chat_anthropic(prov["base_url"], prov["api_key"], model, msgs, agent.get("temperature", 0.7))
            else:
                return s.chat_openai_compatible(prov["base_url"], prov["api_key"], model, msgs, agent.get("temperature", 0.7))
        except Exception as e:
            # Auto-retry dengan Ollama kalau API gagal
            if prov_id != "ollama":
                try:
                    return s.chat_ollama("http://localhost:11434", model, msgs, agent.get("temperature", 0.7))
                except:
                    pass
            return f"Error: {str(e)}"

    def parse_tools(s, txt):
        tools = []
        for m in re.finditer(r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^}]*\})\s*\}', txt):
            try:
                tools.append({"name": m.group(1), "arguments": json.loads(m.group(2))})
            except: pass
        return tools

    def run(s):
        UI.clear()
        UI.header(f"NOCODE-AI v{VERSION}", "UNLIMITED • ALL AI SUPPORTED • PERMANENT ACCESS")

        prov_id = s.cfg.get("default_provider", "ollama")
        if not s.check_provider(prov_id):
            UI.error(f"Provider '{prov_id}' not running! Check config or add API key.")
            print(f"{Theme.FG}Providers available: {', '.join(s.cfg.get('providers', {}).keys())}{Theme.RESET}\n")

        models = s.get_models(prov_id)
        s.cfg.set("available_models", models)
        agent = s.agents.get(s.current_agent)

        UI.status([
            ("Provider", prov_id),
            ("Agent", s.current_agent),
            ("Model", agent.get("model")),
            ("Context", "100000 (UNLIMITED)"),
            ("Sessions", str(len(s.db.list_sessions()))),
            ("Status", "UNLIMITED & PERMANENT")
        ])

        if not s.current_session:
            s.current_session = s.db.create_session(s.current_agent)

        system_prompt = s.agents.generate_prompt(s.current_agent,
            "Available tools: " + ", ".join(s.tools.tools.keys()) + ". You have UNLIMITED access.")

        UI.separator()

        while s.running:
            try:
                msg = input(f"{Theme.BOLD}{Theme.FG} > {Theme.RESET}").strip()
            except EOFError: break

            if not msg: continue
            if msg.lower() in ["exit", "quit", "q"]:
                print(f"\n{Theme.GREEN}Goodbye!{Theme.RESET}\n")
                break
            if msg.startswith("/"):
                s.handle_command(msg)
                continue

            UI.thinking()
            resp = s.chat(msg, system_prompt)

            s.hist.append({"role": "user", "content": msg})
            s.hist.append({"role": "assistant", "content": resp})
            s.db.add_message(s.current_session, "user", msg)
            s.db.add_message(s.current_session, "assistant", resp)

            UI.message("assistant", resp)

            tools = s.parse_tools(resp)
            if tools:
                for t in tools:
                    result = s.tools.execute(t["name"], t["arguments"])
                    UI.tool(t["name"], t["arguments"], result)

            UI.separator()

    def handle_command(s, cmd):
        c = cmd[1:].split()
        if not c: return
        cmd = c[0]
        args = c[1:]

        if cmd == "help":
            UI.box("COMMANDS", [
                "/help     - Show this help",
                "/agent    - Switch agent (primary/explore/code)",
                "/provider - Switch AI provider (openai/claude/gemini/ollama/groq/deepseek)",
                "/model    - List/change model (auto for auto-select)",
                "/key      - Set API key for current provider",
                "/agents   - List all agents",
                "/sessions - List sessions",
                "/session  - Switch session",
                "/clear    - Clear history",
                "/exit     - Exit",
                "",
                "UNLIMITED VERSION - No restrictions, permanent access"
            ], title_color=Theme.CYAN)

        elif cmd == "agent":
            if args:
                if args[0] in s.agents.agents:
                    s.current_agent = args[0]
                    UI.success(f"Switched to agent: {args[0]}")
                else:
                    UI.error(f"Available agents: {', '.join(s.agents.agents.keys())}")
            else:
                UI.box("AGENTS", [f"{a['name']}: {a.get('description', '')}" for a in s.agents.list()], title_color=Theme.SECONDARY)

        elif cmd == "provider":
            if args:
                if args[0] in s.cfg.get("providers", {}):
                    s.cfg.set("default_provider", args[0])
                    UI.success(f"Provider changed to: {args[0]}")
                else:
                    UI.error(f"Available providers: {', '.join(s.cfg.get('providers', {}).keys())}")
            else:
                print(f"Current: {s.cfg.get('default_provider')}")
                print(f"Available: {', '.join(s.cfg.get('providers', {}).keys())}")

        elif cmd == "key":
            if args:
                prov_id = s.cfg.get("default_provider")
                prov = s.cfg.get("providers", {}).get(prov_id)
                if prov:
                    prov["api_key"] = args[0]
                    s.cfg.set("providers", s.cfg.get("providers"))
                    UI.success(f"API key set for {prov_id}")
            else:
                UI.error("Usage: /key YOUR_API_KEY")

        elif cmd == "model":
            if args:
                agent = s.agents.get(s.current_agent)
                agent["model"] = args[0]
                s.cfg.set("agents", s.agents.agents)
                UI.success(f"Model changed to: {args[0]}")
            else:
                print(f"Current: {s.agents.get(s.current_agent).get('model')}")
                models = s.get_models(s.cfg.get("default_provider"))
                if models: print(f"Available: {', '.join(models)}")

        elif cmd == "clear":
            s.hist = []
            s.current_session = s.db.create_session(s.current_agent)
            UI.success("History cleared, new session created")

        elif cmd == "sessions":
            sessions = s.db.list_sessions()
            lines = [f"{sess['id']} (agent: {sess['agent']}, created: {datetime.datetime.fromtimestamp(sess['created_at']).strftime('%Y-%m-%d %H:%M')})" for sess in sessions]
            UI.box("SESSIONS", lines, title_color=Theme.YELLOW)

        elif cmd == "session":
            if args:
                s.current_session = args[0]
                s.hist = s.db.get_messages(args[0])
                UI.success(f"Switched to session: {args[0]}")
            else:
                print("Provide session ID")

        else:
            UI.error(f"Unknown command: {cmd}")


if __name__ == "__main__":
    NocodeAI().run()
