#!/usr/bin/env python3
"""
NocodAI v3.0 - Revamped UI with OpenCode Design System
Features: Modern TUI, Unicode boxes, OpenCode color theme, multi-agent, session DB
"""
import os, sys, json, subprocess, requests, re, time, datetime, threading, signal, hashlib, sqlite3, glob, uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

VERSION = "3.0.0"

# OpenCode Dark Theme Colors (from opencode theme)
class Theme:
    # Backgrounds
    BG1 = "\033[48;5;232m"      # darkStep1 #0a0a0a
    BG2 = "\033[48;5;233m"        # darkStep2 #141414
    BG3 = "\033[48;5;234m"        # darkStep3 #1e1e1e
    BG4 = "\033[48;5;235m"        # darkStep4 #282828
    BG5 = "\033[48;5;236m"        # darkStep5 #323232
    # Foregrounds
    FG = "\033[38;5;255m"         # darkStep12 #eeeeee
    FG_DIM = "\033[38;5;244m"     # darkStep11 #808080
    FG_GRAY = "\033[38;5;241m"    # darkStep8 #606060
    # Accents
    ACCENT = "\033[38;5;216m"     # darkStep9 #fab283
    ACCENT2 = "\033[38;5;217m"    # darkStep10 #ffc09f
    GREEN = "\033[38;5;114m"      # darkGreen #7fd88f
    CYAN = "\033[38;5;117m"       # darkCyan #56b6c2
    YELLOW = "\033[38;5;221m"     # darkYellow #e5c07b
    RED = "\033[38;5;203m"        # darkRed #e06c75
    ORANGE = "\033[38;5;208m"     # darkOrange #f5a742
    SECONDARY = "\033[38;5;75m"   # darkSecondary #5c9cf5
    # Styles
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    RESET = "\033[0m"
    # Unicode box drawing
    TL = "╭"; TR = "╮"; BL = "╰"; BR = "╯"
    H = "─"; V = "│"
    # Clear
    CLEAR = "\033[2J\033[H"

def get_terminal_width():
    try:
        return os.get_terminal_size().columns
    except:
        return 80

def box_lines(text, width, align="left"):
    if align == "center":
        pad = (width - len(text)) // 2
        return " " * pad + text + " " * (width - pad - len(text))
    return text + " " * (width - len(text))

class UI:
    @staticmethod
    def clear():
        print(Theme.CLEAR, end="")

    @staticmethod
    def header(title, subtitle="", width=None):
        w = width or get_terminal_width()
        print(Theme.BG1 + Theme.FG + " " * w)
        # Title line
        t = f" {Theme.BOLD}{title}{Theme.RESET}{Theme.BG1}{Theme.FG}"
        print(Theme.BG1 + Theme.FG + box_lines(t, w-1) + " ")
        if subtitle:
            s = f" {Theme.DIM}{subtitle}{Theme.RESET}"
            print(Theme.BG2 + Theme.FG_DIM + box_lines(s, w-1) + " ")
        print(Theme.BG1 + " " * w + Theme.RESET)
        print()

    @staticmethod
    def box(title, lines, width=None, border_color=None, title_color=None):
        w = width or get_terminal_width()
        bc = border_color or Theme.FG_GRAY
        tc = title_color or Theme.ACCENT
        # Top border
        print(f"{Theme.BG3}{bc}{Theme.TL}{Theme.H * (w-2)}{Theme.TR}{Theme.RESET}")
        # Title
        if title:
            t = f"{Theme.BG3}{tc} {title} {Theme.RESET}{Theme.BG3}{bc}{' ' * (w - len(title) - 3)}{Theme.RESET}"
            print(f"{Theme.BG3}{bc}{Theme.V}{Theme.RESET}{t[:-1]}{Theme.BG3}{bc}{Theme.V}{Theme.RESET}")
            print(f"{Theme.BG3}{bc}{Theme.H * (w-2)}{Theme.RESET}")
        # Content
        for line in lines[:30]:
            l = line[:w-4] if len(line) > w-4 else line
            pad = " " * (w - len(l) - 4)
            print(f"{Theme.BG3}{bc}{Theme.V}{Theme.RESET} {Theme.FG}{l}{Theme.RESET}{Theme.BG3}{pad} {Theme.BG3}{bc}{Theme.V}{Theme.RESET}")
        # Bottom border
        print(f"{Theme.BG3}{bc}{Theme.BL}{Theme.H * (w-2)}{Theme.BR}{Theme.RESET}")
        print()

    @staticmethod
    def message(role, content, width=None):
        w = width or get_terminal_width()
        if role == "user":
            tag = f"{Theme.BOLD}{Theme.GREEN}▶ YOU{Theme.RESET}"
        elif role == "assistant":
            tag = f"{Theme.BOLD}{Theme.CYAN}◉ AI{Theme.RESET}"
        else:
            tag = f"{Theme.BOLD}{Theme.YELLOW}ℹ {role.upper()}{Theme.RESET}"
        print(f"\n{tag} {Theme.DIM}{'─' * (w - len(role) - 5)}{Theme.RESET}")
        # Print content wrapped
        for line in content.split("\n")[:50]:
            if line.strip():
                print(f"  {Theme.FG}{line}{Theme.RESET}")
        print()

    @staticmethod
    def tool(name, args, result=None, width=None):
        w = width or get_terminal_width()
        print(f"\n{Theme.BG4}{Theme.BOLD}{Theme.ORANGE} ⚡ TOOL: {name}{Theme.RESET} {Theme.DIM}{'─' * (w - len(name) - 12)}{Theme.RESET}")
        if args:
            print(f"  {Theme.FG_DIM}Args:{Theme.RESET} {Theme.FG}{json.dumps(args, ensure_ascii=False)[:200]}{Theme.RESET}")
        if result:
            r = str(result)[:500]
            print(f"  {Theme.GREEN}→{Theme.RESET} {Theme.FG}{r}{Theme.RESET}")
        print()

    @staticmethod
    def status(items, width=None):
        w = width or get_terminal_width()
        print(Theme.BG2 + " " * w)
        for k, v in items:
            line = f"  {Theme.BOLD}{Theme.ACCENT}{k}:{Theme.RESET} {Theme.FG}{v}{Theme.RESET}"
            print(Theme.BG2 + line + " " * (w - len(line) + Theme.BG2.count('\033')*10))
        print(Theme.BG2 + " " * w + Theme.RESET)
        print()

    @staticmethod
    def input_prompt(agent, width=None):
        w = width or get_terminal_width()
        print(Theme.BG3 + " " * w)
        ag = f" {Theme.BOLD}{Theme.CYAN}{agent}{Theme.RESET}{Theme.BG3}"
        print(f"{Theme.BG3}{ag} {' ' * (w - len(agent) - 2)}")
        print(Theme.BG3 + Theme.FG_DIM + " " * w)
        print(f"{Theme.BG3}{Theme.BOLD}{Theme.FG} > {Theme.RESET}", end="")
        print(Theme.BG3 + " " * (w - 3) + Theme.RESET)

    @staticmethod
    def separator(width=None):
        w = width or get_terminal_width()
        print(f"{Theme.DIM}{'─' * w}{Theme.RESET}")

    @staticmethod
    def error(msg, width=None):
        w = width or get_terminal_width()
        print(f"\n{Theme.BG1}{Theme.BOLD}{Theme.RED} ✘ ERROR {Theme.RESET}{Theme.BG1} {Theme.FG}{msg}{Theme.RESET}")
        print()

    @staticmethod
    def success(msg, width=None):
        w = width or get_terminal_width()
        print(f"\n{Theme.BG1}{Theme.BOLD}{Theme.GREEN} ✔ {msg}{Theme.RESET}")
        print()

    @staticmethod
    def thinking(width=None):
        w = width or get_terminal_width()
        print(f"\n{Theme.DIM} ⏳ Thinking...{Theme.RESET}\n")


class Config:
    def __init__(s):
        s.path = os.path.expanduser("~/.nocodeai/config.json")
        os.makedirs(os.path.dirname(s.path), exist_ok=True)
        s.default = {
            "providers": {
                "ollama": {"host": "http://localhost:11434", "type": "ollama"},
                "openai": {"api_key": "", "base_url": "https://api.openai.com/v1", "type": "openai"}
            },
            "default_provider": "ollama",
            "default_model": "phi",
            "agents": {
                "primary": {
                    "name": "primary",
                    "description": "Main coding assistant",
                    "model": "phi",
                    "temperature": 0.7,
                    "max_steps": 10,
                    "permission": {"shell": "ask", "file_write": "allow", "file_delete": "ask"}
                },
                "explore": {
                    "name": "explore",
                    "description": "Code exploration agent",
                    "model": "phi",
                    "temperature": 0.3,
                    "max_steps": 5
                }
            },
            "context_size": 2048,
            "max_tokens": 4096,
            "db_path": os.path.expanduser("~/.nocodeai/sessions.db")
        }
        s.cfg = {}
        s.load()

    def load(s):
        try:
            s.cfg = json.loads(open(s.path).read())
            for k, v in s.default.items():
                if k not in s.cfg:
                    s.cfg[k] = v
        except:
            s.cfg = s.default.copy()
            s.save()

    def save(s):
        open(s.path, "w").write(json.dumps(s.cfg, indent=2))

    def get(s, k, d=None):
        return s.cfg.get(k, d)

    def set(s, k, v):
        s.cfg[k] = v
        s.save()


class SessionDB:
    def __init__(s, db_path):
        s.conn = sqlite3.connect(db_path)
        s.conn.row_factory = sqlite3.Row
        s.init_db()

    def init_db(s):
        s.conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                agent TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        """)
        s.conn.commit()

    def create_session(s, agent="primary"):
        sid = hashlib.md5(f"{time.time()}{uuid.uuid4()}".encode()).hexdigest()[:12]
        now = int(time.time())
        s.conn.execute("INSERT INTO sessions (id, agent, created_at, updated_at) VALUES (?,?,?,?)",
                       (sid, agent, now, now))
        s.conn.commit()
        return sid

    def add_message(s, sid, role, content):
        s.conn.execute("INSERT INTO messages (session_id, role, content, timestamp) VALUES (?,?,?,?)",
                       (sid, role, content, int(time.time())))
        s.conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (int(time.time()), sid))
        s.conn.commit()

    def get_messages(s, sid, limit=50):
        cur = s.conn.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY timestamp LIMIT ?",
                             (sid, limit))
        return [{"role": r["role"], "content": r["content"]} for r in cur.fetchall()]

    def list_sessions(s, limit=20):
        cur = s.conn.execute("SELECT id, agent, created_at FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]

    def close(s):
        s.conn.close()


class PermissionSystem:
    def __init__(s, rules=None):
        s.rules = rules or {"*": "allow"}

    def check(s, tool_name, path=None):
        if path and f"{tool_name}:{path}" in s.rules:
            return s.rules[f"{tool_name}:{path}"]
        if tool_name in s.rules:
            return s.rules[tool_name]
        return s.rules.get("*", "deny")

    def prompt_permission(s, tool_name, args):
        print(f"\n{Theme.YELLOW}Permission required for {tool_name}{Theme.RESET}")
        print(f"Args: {json.dumps(args, indent=2)}")
        resp = input(f"{Theme.CYAN}Allow? [y/N/a(always)/d(deny)]: ").strip().lower()
        if resp == "a":
            s.rules[tool_name] = "allow"
            return True
        if resp == "d":
            s.rules[tool_name] = "deny"
            return False
        return resp == "y"


class ToolRegistry:
    def __init__(s, permission: PermissionSystem, cfg: Config):
        s.permission = permission
        s.cfg = cfg
        s.tools = {
            "shell": s.exec_shell,
            "read": s.exec_read,
            "write": s.exec_write,
            "edit": s.exec_edit,
            "delete": s.exec_delete,
            "ls": s.exec_ls,
            "mkdir": s.exec_mkdir,
            "grep": s.exec_grep,
            "git": s.exec_git,
            "system": s.exec_system,
            "codesearch": s.exec_codesearch,
            "webfetch": s.exec_webfetch,
            "websearch": s.exec_websearch,
            "glob": s.exec_glob
        }

    def exec_shell(s, args):
        cmd = args.get("command", "")
        if not s.permission.check("shell", cmd):
            if not s.permission.prompt_permission("shell", args):
                return "Permission denied"
        blocked = ["rm -rf /", "dd if=", "mkfs", "fdisk"]
        if any(b in cmd for b in blocked):
            return "Blocked: dangerous command"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return r.stdout or r.stderr or "OK"

    def exec_read(s, args):
        p = os.path.expanduser(args.get("path", ""))
        if not s.permission.check("read", p):
            if not s.permission.prompt_permission("read", args):
                return "Permission denied"
        if not os.path.exists(p):
            return f"NF: {p}"
        return open(p, "r", errors="ignore").read()[:100000]

    def exec_write(s, args):
        p = os.path.expanduser(args.get("path", ""))
        if not s.permission.check("file_write", p):
            if not s.permission.prompt_permission("file_write", args):
                return "Permission denied"
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(args.get("content", ""))
        return f"W: {p}"

    def exec_edit(s, args):
        p = os.path.expanduser(args.get("path", ""))
        if not s.permission.check("file_write", p):
            if not s.permission.prompt_permission("file_write", args):
                return "Permission denied"
        if not os.path.exists(p):
            return f"NF: {p}"
        c = open(p, "r").read()
        c = c.replace(args.get("oldString", ""), args.get("newString", ""))
        open(p, "w").write(c)
        return f"E: {p}"

    def exec_delete(s, args):
        p = os.path.expanduser(args.get("path", ""))
        if not s.permission.check("file_delete", p):
            if not s.permission.prompt_permission("file_delete", args):
                return "Permission denied"
        if not os.path.exists(p):
            return f"NF: {p}"
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
                    if pattern in open(fp, errors="ignore").read():
                        results.append(fp)
                except:
                    pass
                if len(results) >= 50:
                    break
        return "\n".join(results[:50]) or "No matches"

    def exec_glob(s, args):
        pattern = args.get("pattern", "*")
        path = os.path.expanduser(args.get("path", "."))
        return "\n".join(glob.glob(os.path.join(path, pattern), recursive=True)[:50])

    def exec_git(s, args):
        cmd = args.get("command", "")
        r = subprocess.run(f"git {cmd}", shell=True, capture_output=True, text=True, timeout=60)
        return r.stdout or r.stderr

    def exec_system(s, args):
        r = subprocess.run("uname -a && free -h && df -h && uptime", shell=True, capture_output=True, text=True)
        return r.stdout

    def exec_codesearch(s, args):
        query = args.get("query", "")
        return f"Codesearch for '{query}' - integrate with Exa API for real results"

    def exec_webfetch(s, args):
        url = args.get("url", "")
        try:
            r = requests.get(url, timeout=10)
            return r.text[:10000]
        except Exception as e:
            return f"Error: {e}"

    def exec_websearch(s, args):
        query = args.get("query", "")
        return f"Websearch for '{query}' - integrate with Exa API for real results"

    def execute(s, name, args):
        if name not in s.tools:
            return f"Unknown tool: {name}"
        try:
            return s.tools[name](args)
        except Exception as e:
            return f"Tool error: {e}"


class AgentManager:
    def __init__(s, cfg: Config):
        s.cfg = cfg
        s.agents = cfg.get("agents", {})

    def get(s, name):
        return s.agents.get(name, s.agents.get("primary"))

    def list(s):
        return list(s.agents.values())

    def generate_prompt(s, agent_name, description):
        agent = s.get(agent_name)
        return f"You are {agent['name']}, {agent.get('description', '')}. {description}"


class NocodAI:
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
        if not prov:
            return False
        if prov["type"] == "ollama":
            try:
                r = requests.get(f"{prov['host']}/api/tags", timeout=3)
                return r.status_code == 200
            except:
                return False
        return True

    def get_models(s, provider_id="ollama"):
        prov = s.cfg.get("providers", {}).get(provider_id)
        if not prov:
            return []
        if prov["type"] == "ollama":
            try:
                r = requests.get(f"{prov['host']}/api/tags", timeout=5)
                return [m["name"] for m in r.json().get("models", [])]
            except:
                return []
        return []

    def chat(s, msg, system_prompt=None):
        agent = s.agents.get(s.current_agent)
        prov_id = s.cfg.get("default_provider", "ollama")
        prov = s.cfg.get("providers", {}).get(prov_id)
        model = agent.get("model", s.cfg.get("default_model"))

        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.extend(s.hist[-agent.get("max_context", 20):])
        msgs.append({"role": "user", "content": msg})

        try:
            if prov["type"] == "ollama":
                r = requests.post(
                    f"{prov['host']}/api/chat",
                    json={
                        "model": model,
                        "messages": msgs,
                        "stream": False,
                        "options": {
                            "temperature": agent.get("temperature", 0.7),
                            "num_predict": s.cfg.get("max_tokens", 4096),
                            "num_ctx": s.cfg.get("context_size", 2048)
                        }
                    },
                    timeout=300
                )
                return r.json().get("message", {}).get("content", "")
            else:
                headers = {"Authorization": f"Bearer {prov['api_key']}"}
                r = requests.post(
                    f"{prov['base_url']}/chat/completions",
                    headers=headers,
                    json={
                        "model": model,
                        "messages": msgs,
                        "max_tokens": s.cfg.get("max_tokens", 4096),
                        "temperature": agent.get("temperature", 0.7)
                    },
                    timeout=300
                )
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error: {str(e)}"

    def parse_tools(s, txt):
        tools = []
        for m in re.finditer(r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"arguments"\s*:\s*(\{[^}]*\})\s*\}', txt):
            try:
                name = m.group(1)
                args = json.loads(m.group(2))
                tools.append({"name": name, "arguments": args})
            except:
                pass
        return tools

    def run(s):
        UI.clear()
        UI.header(f"NOCOD.AI v{VERSION}", "OpenCode-Style AI Assistant • Multi-Agent • Session DB • Permission System")

        prov_id = s.cfg.get("default_provider", "ollama")
        if not s.check_provider(prov_id):
            UI.error(f"Provider '{prov_id}' not running! Start it or check config.")
            return

        models = s.get_models(prov_id)
        s.cfg.set("available_models", models)
        agent = s.agents.get(s.current_agent)

        UI.status([
            ("Provider", prov_id),
            ("Agent", s.current_agent),
            ("Model", agent.get("model")),
            ("Context", str(s.cfg.get("context_size"))),
            ("Sessions", str(len(s.db.list_sessions())))
        ])

        if not s.current_session:
            s.current_session = s.db.create_session(s.current_agent)

        system_prompt = s.agents.generate_prompt(s.current_agent,
            "Available tools: " + ", ".join(s.tools.tools.keys()))

        UI.separator()

        while s.running:
            try:
                msg = input(f"{Theme.BOLD}{Theme.FG} > {Theme.RESET}").strip()
            except EOFError:
                break

            if not msg:
                continue
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
        if not c:
            return
        cmd = c[0]
        args = c[1:]

        if cmd == "help":
            UI.box("COMMANDS", [
                "/help     - Show this help",
                "/agent    - Switch agent (primary/explore)",
                "/model    - List/change model",
                "/context  - Set context size",
                "/temp     - Set temperature",
                "/clear    - Clear history",
                "/sessions - List sessions",
                "/session  - Switch session",
                "/exit     - Exit"
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

        elif cmd == "model":
            if args:
                agent = s.agents.get(s.current_agent)
                agent["model"] = args[0]
                s.cfg.set("agents", s.agents.agents)
                UI.success(f"Model changed to: {args[0]}")
            else:
                print(f"Current: {s.agents.get(s.current_agent).get('model')}")
                for m in s.cfg.get("available_models", []):
                    print(f"  - {m}")

        elif cmd == "context":
            if args:
                s.cfg.set("context_size", int(args[0]))
                UI.success(f"Context size: {args[0]}")

        elif cmd == "temp" or cmd == "temperature":
            if args:
                agent = s.agents.get(s.current_agent)
                agent["temperature"] = float(args[0])
                s.cfg.set("agents", s.agents.agents)
                UI.success(f"Temperature: {args[0]}")

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
    NocodAI().run()
