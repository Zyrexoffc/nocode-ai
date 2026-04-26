#!/usr/bin/env python3
import json, re, subprocess, os, sys, requests, time, datetime

MUTED = "\033[0;2m"
RED = "\033[0;31m"
ORANGE = "\033[38;5;214m"
NC = "\033[0m"
BLD = "\033[1m"
CYN = "\033[96m"
GRN = "\033[92m"
WHT = "\033[97m"
YEL = "\033[93m"
BLK = "\033[40m"

class NocodAI:
    def __init__(s):
        s.h = []
        s.ws = os.getcwd()
        s.tm = datetime.datetime.now().strftime("%Y-%m-%d")
        s.ti = datetime.datetime.now().strftime("%H:%M:%S")
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
        print(f"{MUTED}                   {NC}             ▄     ")
        print(f"{MUTED}█▀▀█ █▀▀█ █▀▀█ █▀▀▄ {NC}█▀▀▀ █▀▀█ █▀▀█ █▀▀█")
        print(f"{MUTED}█░░█ █░░█ █▀▀▀ █░░█ {NC}█░░░ █░░█ █░░█ █▀▀▀")
        print(f"{MUTED}▀▀▀▀ █▀▀▀ ▀▀▀▀ ▀  ▀ {NC}▀▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀")
        print(f"\n{MUTED}OpenCode includes free models, to start:{NC}\n")
        print(f"{MUTED}cd <project>  {NC}# Open directory")
        print(f"{MUTED}nocodeai    {NC}# Run command")
        
        if not s.ck():
            print(f"\n{RED}[*] Error: Ollama not running{NC}")
            print(f"{MUTED}Please start Ollama first: ollama serve{NC}")
            return
        
        if not s.cm():
            print(f"\n{ORANGE}[*] Downloading model...{NC}")
            subprocess.run(["ollama","pull",s.model],timeout=600)
        
        s.sp="""You are NocodAI, a helpful AI assistant.
1. LEGAL: Only legal activities.
2. TOOLS: shell, file_read, file_write, file_edit, file_delete, file_list, mkdir, search, git, system.
3. OUTPUT: Use code blocks.
4. LANGUAGE: Same as user."""
        
        print(f"\n{BLD}{CYN}╭───────────────────────────────────{BLK}{CYN} Input {BLD}{CYN}──────────────────────────────────╮{NC}")
        print(f"{BLD}{CYN}│{NC} Type your message or @path               {BLD}{CYN}│{NC}")
        print(f"{BLD}{CYN}│{NC} {WHT}~{' '*35}{BLD}{CYN}│{NC}")
        print(f"{BLD}{CYN}╰───────────────────────────────────────────────────────────────────╯{NC}\n")
        
        while 1:
            p=input(f"{BLK}{GRN}│{WHT} > {NC}")
            if p.lower() in ["exit","quit","q"]: 
                print(f"{CYN}[*] Goodbye!{NC}")
                break
            
            s.h.append({"role":"user","content":p})
            print(f"\n{MUTED}Thinking...{NC}")
            full="".join([c for c in s.gs(p,s.sp)])
            
            print(f"\n{BLK}{ORANGE}╭───────────────────────────────────{BLK}{ORANGE} Response {BLK}{ORANGE}───────────────────────────╮{NC}")
            for line in full.split('\n'):
                if line.strip():
                    print(f"{BLK}{ORANGE}│{NC} {WHT}{line}{NC}")
            print(f"{BLK}{ORANGE}╰───────────���─��─────────────────────────────────────────────────────╯{NC}\n")
            
            s.h.append({"role":"assistant","content":full})
            tools = s.pt(full)
            if tools:
                for t in tools:
                    n,a=t.get("name",""),t.get("arguments",{})
                    print(f"{YEL}>>> {n}{NC}")
                    r=s.ex(n,a)
                    print(f"{YEL}{r[:200]}{NC}\n")
            
            print(f"{BLK}{CYN}╭───────────────────────────────────{BLK}{CYN} Input {BLD}{CYN}──────────────────────────────────╮{NC}")
            print(f"{BLK}{CYN}│{NC} Type your message or @path               {BLK}{CYN}│{NC}")
            print(f"{BLK}{CYN}│{NC} {WHT}~{' '*35}{BLK}{CYN}│{NC}")
            print(f"{BLK}{CYN}╰───────────────────────────────────────────────────────────────────╯{NC}")

if __name__=="__main__": NocodAI().run()