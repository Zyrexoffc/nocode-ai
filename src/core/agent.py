#!/usr/bin/env python3
import json, re, subprocess, os, sys, requests, time
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
    def __init__(s):
        s.h = []
        s.ws = os.getcwd()
        try:
            c = json.loads(open(os.path.expanduser("~/.nocodeai/config.json")).read())
        except:
            c = {}
        s.host = c.get("ollama_host", "http://localhost:11434")
        s.model = c.get("model", "qwen2.5:3b")
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
        print(f"""{Colors.INFO}
▝▜▄     {Colors.SUCCESS}NOCODE-AI V2.0.0{Colors.INFO}
   ▝▜▄
  ▗▟▀    {Colors.USER}Created By Zyrex Official{Colors.SUCCESS} ✔
 ▝▀
{Colors.BOLD}───────────────────────────────────────────────────────────────────────────────────────────────────────
{Colors.TOOL}Description:{Colors.RESET} 
{Colors.TOOL}Time:{Colors.RESET} 
{Colors.TOOL}Model-AI:{Colors.RESET} %s
{Colors.BOLD}───────────────────────────────────────────────────────────────────────────────────────────────────────
{Colors.INFO}Shift+Tab to accept edits
{Colors.BOLD}───────────────────────────────────────────────────────────────────────────────────────────────────────
{Colors.INFO}> {Colors.USER}Type your message or @path/to/file
{Colors.BOLD}───────────────────────────────────────────────────────────────────────────────────────────────────────
{Colors.INFO}Workspace ({Colors.USER}%s{Colors.INFO})                                                                                                                                      
{Colors.INFO}Script (nocode-ai){Colors.INFO}                                                                  
 {Colors.USER}~{Colors.RESET}                                                           
""" % (s.model, s.ws))
        if not s.ck():
            print(f"{Colors.ERROR}[*] Starting Ollama...{Colors.RESET}")
            subprocess.Popen(["ollama","serve"],stdout=open(os.devnull,"w"),stderr=open(os.devnull,"w"))
            time.sleep(3)
        if not s.cm():
            print(f"{Colors.TOOL}[*] Downloading model...{Colors.RESET}") ; subprocess.run(["ollama","pull",s.model],timeout=600)
        sp="""You are NocodAI, a professional AI assistant.
LEGALITY: Only legal activities. Refuse hacking, malware, illegal.
FILE ACCESS: Root access. Read/edit files when user asks.
CODING: Clean code, best practices.
LANGUAGE: Respond in SAME LANGUAGE user uses."""
        print(f"{Colors.BOLD}───────────────────────────────────────────────────────────────────────────────────────────────────────{Colors.RESET}\n")
        while 1:
            try:
                p=input(f"{Colors.INFO}> {Colors.RESET}")
                if p.lower() in ["exit","quit","q"]: print(f"{Colors.INFO}[*] Goodbye!{Colors.RESET}"); break
                s.h.append({"role":"user","content":p})
                full=""
                print(f"{Colors.ASSISTANT}",end="")
                for c in s.gs(p,sp): print(c,end="",flush=1); full+=c
                print(f"{Colors.RESET}")
                s.h.append({"role":"assistant","content":full})
                tools = s.pt(full)
                if tools:
                    for t in tools:
                        n,a=t.get("name",""),t.get("arguments",{})
                        print(f"\n{Colors.TOOL}>>> Executing: {n}{Colors.RESET}")
                        r=s.ex(n,a)
                        print(f"\n{Colors.TOOL}Result: {r[:500]}{Colors.RESET}\n")
                        s.h.append({"role":"user","content":f"Tool {n} result: {r}"})
                        print(f"{Colors.ASSISTANT}>>> ",end="",flush=1)
                        for c in s.gs("Based on the tool result, provide your final answer.",sp): print(c,end="",flush=1)
                        print(f"{Colors.RESET}")
            except KeyboardInterrupt: print(f"\n{Colors.INFO}exit{Colors.RESET}")
            except Exception as e: print(f"{Colors.ERROR}{e}{Colors.RESET}")

if __name__=="__main__": NocodAI().run()