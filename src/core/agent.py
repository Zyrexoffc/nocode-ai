#!/usr/bin/env python3
import json, re, subprocess, os, sys, requests, time, datetime

M = "\033[0;2m"
R = "\033[0;31m"
O = "\033[38;5;214m"
N = "\033[0m"
B = "\033[1m"
C = "\033[96m"
G = "\033[92m"
W = "\033[97m"
Y = "\033[93m"
K = "\033[40m"

TL = "┌"
TR = "┐"
BL = "└"
BR = "┘"
H = "─"
V = "│"
LT = "├"
RT = "┤"
LB = "┴"
RB = "┬"
PM = "┼"

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
    
    def box(s, title, content):
        w = 50
        lines = content.split('\n')
        print(f"{K}{C}{TL}{H*w}{TR}{N}")
        if title:
            print(f"{K}{C}{V}{N} {B}{C}{title}{N}{' '*(w-len(title)-2)}{C}{V}{N}")
            print(f"{K}{C}{LT}{H*w}{RT}{N}")
        for line in lines:
            if line.strip():
                print(f"{K}{C}{V}{N} {W}{line}{' '*(w-len(line))}{C}{V}{N}")
            else:
                print(f"{K}{C}{V}{N} {C}{V}{N}")
        print(f"{K}{C}{BL}{H*w}{BR}{N}")
    
    def run(s):
        print(f"\n{K}{M}                   {N}             ▄     ")
        print(f"{K}{M}█▀▀█ █▀▀█ █▀▀█ █▀▀▄ {N}█▀▀▀ █▀▀█ █▀▀█ █▀▀█")
        print(f"{K}{M}█░░█ █░░█ █▀▀▀ █░░█ {N}█░░░ █░░█ █░░█ █▀▀▀")
        print(f"{K}{M}▀▀▀▀ █▀▀▀ ▀▀▀▀ ▀  ▀ {N}▀▀▀▀ ▀▀▀▀ ▀▀▀▀ ▀▀▀▀")
        
        print(f"\n{K}{M}OpenCode includes free models, to start:{N}\n")
        print(f"{K}{M}cd <project>  {N}# Open directory")
        print(f"{K}{M}nocodeai    {N}# Run command")
        
        if not s.ck():
            s.box("Error", "Ollama not running\nPlease run: ollama serve")
            return
        if not s.cm():
            print(f"\n{K}{O} Downloading model...{N}")
            subprocess.run(["ollama","pull",s.model],timeout=600)
        
        s.sp="""You are NocodAI.
1. LEGAL: Only legal activities.
2. TOOLS: shell, file_read, file_write, file_edit, file_delete, file_list, mkdir, search, git, system.
3. OUTPUT: Code in blocks.
4. LANGUAGE: Same as user."""
        
        w = 50
        print(f"\n{K}{C}{TL}{H*50}{TR}{N}")
        print(f"{K}{C}{V}{N} {C}Type your message or @path                 {C}{V}{N}")
        print(f"{K}{C}{V}{N} {W}~{' '*46}{C}{V}{N}")
        print(f"{K}{C}{BL}{H*50}{BR}{N}\n")
        
        while 1:
            p=input(f"{K}{G}│{W} > {N}")
            if p.lower() in ["exit","quit","q"]: 
                print(f"{K}{C}[*] Goodbye!{N}")
                break
            
            s.h.append({"role":"user","content":p})
            print(f"\n{K}{M}Thinking...{N}")
            full="".join([c for c in s.gs(p,s.sp)])
            
            print(f"\n{K}{O}{TL}{H*50}{TR}{N}")
            print(f"{K}{O}{V}{N} {O}Response{O}{V}{N}")
            print(f"{K}{O}{LT}{H*50}{RT}{N}")
            for line in full.split('\n'):
                if line.strip():
                    print(f"{K}{O}{V}{N} {W}{line}{' '*(50-len(line))}{K}{O}{V}{N}")
                else:
                    print(f"{K}{O}{V}{N}   {K}{O}{V}{N}")
            print(f"{K}{O}{BL}{H*50}{BR}{N}\n")
            
            s.h.append({"role":"assistant","content":full})
            tools = s.pt(full)
            if tools:
                for t in tools:
                    n,a=t.get("name",""),t.get("arguments",{})
                    print(f"{K}{Y}>>> {n}{N}")
                    r=s.ex(n,a)
                    print(f"{K}{Y}{r[:200]}{N}\n")
            
            print(f"{K}{C}{TL}{H*50}{TR}{N}")
            print(f"{K}{C}{V}{N} {C}Type your message or @path                 {C}{V}{N}")
            print(f"{K}{C}{V}{N} {W}~{' '*46}{C}{V}{N}")
            print(f"{K}{C}{BL}{H*50}{BR}{N}")

if __name__=="__main__": NocodAI().run()