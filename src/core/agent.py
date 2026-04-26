#!/usr/bin/env python3
import json, re, subprocess, os, sys, requests, time, datetime

class C:
    BLK = "\033[40m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YEL = "\033[93m"
    BLU = "\033[94m"
    CYN = "\033[96m"
    WHT = "\033[97m"
    RST = "\033[0m"
    BLD = "\033[1m"
    DIM = "\033[90m"
    PUR = "\033[95m"

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
        print(f"{C.BLK}")
        print(f"{C.BLD}{C.CYN}  _   _ ___ ____  ___ {C.RST}")
        print(f"{C.BLD}{C.CYN} | | | |_ _|  _ \\| _ \\ {C.RST}")
        print(f"{C.BLD}{C.CYN} | |_| || || |_) | |_) |{C.RST}")
        print(f"{C.BLD}{C.CYN} |___| |___|____/|____/ {C.RST}")
        print(f"{C.BLD}{C.GRN}╭{'─'*44}╮{C.RST}")
        print(f"{C.BLD}{C.GRN}│{C.RST} {C.GRN}NOCODE-AI{C.RST} {C.WHT}V2.0.0{C.RST}           {C.GRN}│{C.RST} {C.WHT}Zyrex Official{C.RST}        {C.GRN}│{C.RST}")
        print(f"{C.BLD}{C.GRN}╰{'─'*44}╯{C.RST}")
        
        if not s.ck():
            print(f"{C.YEL}[*] Starting Ollama...{C.RST}")
            subprocess.Popen(["ollama","serve"],stdout=open(os.devnull,"w"),stderr=open(os.devnull,"w"))
            time.sleep(3)
        if not s.cm():
            print(f"{C.YEL}[*] Downloading model...{C.RST}") ; subprocess.run(["ollama","pull",s.model],timeout=600)
        
        w = 44
        h = 2
        d = f" Date: {s.tm}"
        print(f"\n{C.BLK}{C.CYN}╭{'─'*w}╮{C.RST}")
        print(f"{C.BLK}{C.CYN}│{C.RST} {C.CYN}Description:{C.RST} AI Assistant with tool execution     {C.CYN}│{C.RST}")
        print(f"{C.BLK}{C.CYN}│{C.RST} {C.CYN}{d}{' '*(w-len(d))}{C.CYN}│{C.RST}")
        print(f"{C.BLK}{C.CYN}╰{'─'*w}╯{C.RST}")
        
        print(f"\n{C.BLK}{C.CYN}╭{'─'*w}╮{C.RST}")
        print(f"{C.BLK}{C.CYN}│{C.RST} {C.CYN}Type your message or @path               {C.RST}")
        print(f"{C.BLK}{C.CYN}│{C.RST} {C.WHT}~{' '*41}{C.RST}")
        print(f"{C.BLK}{C.CYN}╰{'─'*w}╯{C.RST}")
        
        print(f"\n{C.GRN}✓ Ready!{C.RST}\n")
        
        s.sp="""You are NocodAI.
1. LEGAL: Only legal. REFUSE hacking/malware/piracy.
2. TOOLS: shell, file_read, file_write, file_edit, file_delete, file_list, mkdir, search, git, system.
3. CODING: Clean code.
4. OUTPUT: Code in blocks.
5. LANGUAGE: Same as user."""
        
        while 1:
            p=input(f"{C.BLK}{C.CYN}│{C.WHT} > {C.RST}")
            if p.lower() in ["exit","quit","q"]: 
                print(f"{C.CYN}[*] Bye!{C.RST}")
                break
            
            s.h.append({"role":"user","content":p})
            print(f"{C.DIM}Thinking...{C.RST}")
            full="".join([c for c in s.gs(p,s.sp)])
            
            print(f"\n{C.BLK}{C.BLU}╭{'─'*w}╮{C.RST}")
            for line in full.split('\n'):
                if line.strip():
                    print(f"{C.BLK}{C.BLU}│{C.RST} {C.WHT}{line}{' '*(w-len(line))}{C.BLK}{C.BLU}│{C.RST}")
            print(f"{C.BLK}{C.BLU}╰{'─'*w}╯{C.RST}\n")
            
            s.h.append({"role":"assistant","content":full})
            tools = s.pt(full)
            if tools:
                for t in tools:
                    n,a=t.get("name",""),t.get("arguments",{})
                    print(f"{C.YEL}>>> {n}{C.RST}")
                    r=s.ex(n,a)
                    print(f"{C.YEL}{r[:200]}{C.RST}\n")
                    s.h.append({"role":"user","content":f"Tool {n}: {r}"})
                    full="".join([c for c in s.gs("Final answer.",s.sp)])
                    print(f"\n{C.BLK}{C.GRN}╭{'─'*w}╮{C.RST}")
                    for line in full.split('\n'):
                        if line.strip():
                            print(f"{C.BLK}{C.GRN}│{C.RST} {C.WHT}{line}{' '*(w-len(line))}{C.BLK}{C.GRN}│{C.RST}")
                    print(f"{C.BLK}{C.GRN}╰{'─'*w}╯{C.RST}\n")
            
            print(f"{C.BLK}{C.CYN}╭{'─'*w}╮{C.RST}")
            print(f"{C.BLK}{C.CYN}│{C.RST} {C.CYN}Type your message or @path               {C.RST}")
            print(f"{C.BLK}{C.CYN}│{C.RST} {C.WHT}~{' '*41}{C.RST}")
            print(f"{C.BLK}{C.CYN}╰{'─'*w}╯{C.RST}")

if __name__=="__main__": NocodAI().run()