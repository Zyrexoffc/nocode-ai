#!/usr/bin/env python3
import json, re, subprocess, os, sys, requests, time, datetime

class Colors:
    USER = "\033[92m"
    ASSISTANT = "\033[97m"
    TOOL = "\033[93m"
    ERROR = "\033[91m"
    SUCCESS = "\033[92m"
    INFO = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[90m"

class NocodAI:
    def __init__(s):
        s.h = []
        s.ws = os.getcwd()
        s.tm = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            c = json.loads(open(os.path.expanduser("~/.nocodeai/config.json")).read())
        except:
            c = {}
        s.host = c.get("ollama_host", "http://localhost:11434")
        s.model = c.get("model", "phi")
        s.ctx = c.get("context_size", 2048)
    
    def ck(s):
        try:
            return requests.get(f"{s.host}/api/tags", timeout=5).status_code == 200
        except:
            return 0
    
    def cm(s):
        try:
            r = requests.get(f"{s.host}/api/tags", timeout=5)
            if r.status_code == 200:
                m = s.model.split(":")[0]
                return any(m in x.get("name","") for x in r.json().get("models",[]))
        except:
            pass
        return 0
    
    def gs(s, p, sp=""):
        m = []
        if sp:
            m.append({"role":"system","content":sp})
        m.extend(s.h[-20:])
        m.append({"role":"user","content":p})
        try:
            r = requests.post(f"{s.host}/api/chat", json={"model":s.model,"messages":m,"stream":True,"options":{"temperature":0.7,"num_predict":8192,"num_ctx":s.ctx}}, stream=True, timeout=120)
            for l in r.iter_lines():
                if l:
                    try: yield json.loads(l).get("message",{}).get("content","")
                    except: pass
        except Exception as e: yield f"E:{e}"
    
    def pt(s, t):
        return [json.loads("{"+m+"}") for m in re.findall(r"\[TOOL_CALL\]\s*\{(.*?)\}\s*\[/TOOL_CALL\]", t, re.DOTALL)]
    
    def ex(s, n, a):
        try:
            if n=="shell":
                r=subprocess.run(a.get("command",""), shell=1, capture_output=1, text=1, timeout=120)
                return r.stdout or r.stderr or "OK"
            if n in ["file_read","read"]:
                p=os.path.expanduser(a.get("path",""))
                return open(p,"r",encoding="utf-8",errors="ignore").read()[:50000] if os.path.exists(p) else f"NF:{p}"
            if n in ["file_write","write"]:
                p=os.path.expanduser(a.get("path","")); os.makedirs(os.path.dirname(p), exist_ok=1)
                open(p,"w",encoding="utf-8").write(a.get("content","")); return f"W:{p}"
            if n in ["file_edit","edit"]:
                p=os.path.expanduser(a.get("path",""))
                c=open(p,"r").read().replace(a.get("oldString",""), a.get("newString",""))
                open(p,"w").write(c); return f"E:{p}"
            if n in ["file_delete","delete"]:
                p=os.path.expanduser(a.get("path",""))
                (os.remove if os.path.isfile(p) else __import__("shutil").rmtree)(p); return f"D:{p}"
            if n in ["file_list","ls"]:
                return "\n".join(sorted(os.listdir(os.path.expanduser(a.get("path",".")))))
            if n=="mkdir":p=os.path.expanduser(a.get("path",""));os.makedirs(p,exist_ok=1);return f"C:{p}"
            if n in ["search","grep"]:
                import glob; pt,pp=a.get("pattern",""),os.path.expanduser(a.get("path","."))
                return "\n".join([f for f in glob.glob(f"{pp}/**/*",recursive=True) if os.path.isfile(f) and pt in open(f,errors="ignore").read()][:50]) or"No"
            if n=="git":r=subprocess.run(f"git {a.get('command','')}",shell=1,capture_output=1,text=1,tout=60);return r.stdout or r.stderr
            if n in ["system","sysinfo"]:r=subprocess.run("uname -a&&free -h&&df -h&&uptime",shell=1,capture_output=1,text=1);return r.stdout
            return f"U:{n}"
        except Exception as e: return f"Er:{e}"
    
    def run(s):
        bar = "───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────"
        
        print(f"\n{Colors.INFO}▝▜▄     {Colors.SUCCESS}NOCODE-AI V1.0.0{Colors.INFO}")
        print(f"{Colors.INFO}   ▝▜▄")
        print(f"{Colors.INFO}  ▗▟▀    {Colors.USER}Created By Zyrex Official{Colors.SUCCESS} ✔")
        print(f"{Colors.INFO} ▝▀")
        print(f"\n{Colors.BOLD}{bar}{Colors.RESET}")
        print(f"{Colors.TOOL}Description:{Colors.RESET}")
        print(f"{Colors.TOOL}Time:{Colors.RESET} {s.tm}")
        print(f"{Colors.TOOL}model-ai:{Colors.RESET} {s.model}")
        print(f"\n{Colors.BOLD}{bar}{Colors.RESET}")
        print(f"{Colors.DIM}Shift+Tab to accept edits{Colors.RESET}")
        print(f"{Colors.BOLD}{bar}{Colors.RESET}")
        print(f"{Colors.INFO}║ {Colors.USER}Type your message or @path/to file{Colors.RESET}")
        print(f"{Colors.BOLD}{bar}{Colors.RESET}")
        print(f"{Colors.INFO}Workspace ({Colors.USER}{s.ws}{Colors.INFO})")
        print(f"{Colors.INFO}Script (nocode-ai){Colors.INFO}")
        print(f"{Colors.USER}~{Colors.RESET}")
        print(f"{Colors.BOLD}{bar}{Colors.RESET}")
        
        if not s.ck():
            print(f"{Colors.ERROR}[*] Starting Ollama...{Colors.RESET}")
            subprocess.Popen(["ollama","serve"],stdout=open(os.devnull,"w"),stderr=open(os.devnull,"w"))
            time.sleep(3)
        if not s.cm():
            print(f"{Colors.TOOL}[*] Downloading model...{Colors.RESET}") ; subprocess.run(["ollama","pull",s.model],timeout=600)
        
        s.sp="""You are NocodAI.
RULES:
1. LEGALITY: Only legal.
2. TOOLS: shell, file_read, file_write, file_edit, file_delete, file_list, mkdir, search, git, system.
3. CODING: Clean code.
4. LANGUAGE: Same as user."""
        
        while 1:
            p=input(f"{Colors.INFO}│{Colors.USER} > {Colors.RESET}")
            if p.lower() in ["exit","quit","q"]: break
            s.h.append({"role":"user","content":p})
            print(f"{Colors.DIM}Thinking...{Colors.RESET}")
            full=""
            for c in s.gs(p,s.sp): full+=c
            print(f"{Colors.USER}%s{Colors.RESET}" % full)
            s.h.append({"role":"assistant","content":full})
            tools = s.pt(full)
            for t in tools:
                n,a=t.get("name",""),t.get("arguments",{})
                r=s.ex(n,a)
                for c in s.gs(f"Tool {n} result: {r}",s.sp):
                    print(f"{Colors.USER}%s{Colors.RESET}" % c)

if __name__=="__main__": NocodAI().run()