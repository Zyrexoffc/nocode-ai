#!/usr/bin/env python3
import json,re,subprocess,os,sys,requests,time

class C:
    U = "\033[92m"
    A = "\033[96m"
    T = "\033[93m"
    E = "\033[91m"
    S = "\033[92m"
    I = "\033[94m"
    R = "\033[0m"
    B = "\033[1m"

class NocodAI:
    def __init__(s):
        s.h = []
        try:
            c = json.loads(open(os.path.expanduser("~/.nocode/config/config.json")).read())
        except:
            c = {}
        s.host = c.get("ollama_host", "http://localhost:11434")
        s.model = c.get("model", "qwen3.5:9b")
        s.ctx = c.get("context_size", 8192)
    
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
            r = requests.post(
                f"{s.host}/api/chat",
                json={
                    "model": s.model,
                    "messages": m,
                    "stream": True,
                    "options": {"temperature": 0.7, "num_predict": 8192, "num_ctx": s.ctx}
                },
                stream=True,
                timeout=120
            )
            for l in r.iter_lines():
                if l:
                    try:
                        yield json.loads(l).get("message",{}).get("content","")
                    except:
                        pass
        except Exception as e:
            yield f"E:{e}"
    
    def pt(s, t):
        return [json.loads("{"+m+"}") for m in re.findall(r"\[TOOL_CALL\]\s*\{(.*?)\}\s*\[/TOOL_CALL\]", t, re.DOTALL)]
    
    def ex(s, n, a):
        try:
            if n == "shell":
                r = subprocess.run(a.get("command",""), shell=1, capture_output=1, text=1, timeout=120)
                return r.stdout or r.stderr or "OK"
            
            if n in ["file_read","read"]:
                p = os.path.expanduser(a.get("path",""))
                if not os.path.exists(p):
                    return f"NF:{p}"
                with open(p,"r",encoding="utf-8",errors="ignore") as f:
                    return f.read()[:50000]
            
            if n in ["file_write","write"]:
                p = os.path.expanduser(a.get("path",""))
                os.makedirs(os.path.dirname(p), exist_ok=1)
                with open(p,"w",encoding="utf-8") as f:
                    f.write(a.get("content",""))
                return f"W:{p}"
            
            if n in ["file_edit","edit"]:
                p = os.path.expanduser(a.get("path",""))
                if not os.path.exists(p):
                    return f"NF:{p}"
                c = open(p,"r").read().replace(a.get("oldString",""), a.get("newString",""))
                open(p,"w").write(c)
                return f"E:{p}"
            
            if n in ["file_delete","delete"]:
                p = os.path.expanduser(a.get("path",""))
                if os.path.isfile(p):
                    os.remove(p)
                elif os.path.isdir(p):
                    import shutil
                    shutil.rmtree(p)
                return f"D:{p}"
            
            if n in ["file_list","ls"]:
                p = os.path.expanduser(a.get("path","."))
                return "\n".join(sorted(os.listdir(p)))
            
            if n == "mkdir":
                p = os.path.expanduser(a.get("path",""))
                os.makedirs(p, exist_ok=1)
                return f"C:{p}"
            
            if n in ["search","grep"]:
                import glob
                pt = a.get("pattern","")
                pp = os.path.expanduser(a.get("path","."))
                rs = []
                for f in glob.glob(f"{pp}/**/*", recursive=True):
                    if os.path.isfile(f):
                        try:
                            with open(f, errors="ignore") as fp:
                                if pt in fp.read():
                                    rs.append(f)
                        except:
                            pass
                return "\n".join(rs[:50]) or "No match"
            
            if n == "git":
                r = subprocess.run(f"git {a.get('command','')}", shell=1, capture_output=1, text=1, timeout=60)
                return r.stdout or r.stderr
            
            if n in ["system","sysinfo"]:
                r = subprocess.run("uname -a && free -h && df -h && uptime", shell=1, capture_output=1, text=1)
                return r.stdout
            
            return f"U:{n}"
        except Exception as e:
            return f"Er:{e}"
    
    def run(s):
        print(f"{C.B}  _   _ ___ _   _ ____  ___ ")
        print(f" / \\ | | |_ _| | \\| _ \\ ")
        print(f"/ _ \\| |_| || || |_| | | |")
        print(f"/_/ \\\\__/|___||___/|____/")
        print(f"{C.I}NocodAI v1.0{C.R}")
        
        if not s.ck():
            print(f"{C.E}Starting Ollama...{C.R}")
            subprocess.Popen(["ollama","serve"], stdout=open(os.devnull,"w"), stderr=open(os.devnull,"w"))
            time.sleep(3)
        
        if not s.cm():
            print(f"{C.T}Downloading model...{C.R}")
            subprocess.run(["ollama","pull",s.model], timeout=600)
        
        sp_path = os.path.expanduser("~/.nocode/config/system_prompt.txt")
        sp = ""
        if os.path.exists(sp_path):
            with open(sp_path) as f:
                sp = f.read()
        
        print(f"{C.S}READY!{C.R}\n")
        
        while 1:
            try:
                p = input(f"{C.U}>>> {C.R}")
                if p.lower() in ["exit","quit","q"]:
                    print(f"{C.I}BYE!{C.R}")
                    break
                
                s.h.append({"role":"user","content":p})
                full = ""
                print(f"{C.A}", end="")
                for c in s.gs(p, sp):
                    print(c, end="", flush=1)
                    full += c
                print(f"{C.R}")
                
                for t in s.pt(full):
                    n = t.get("name","")
                    a = t.get("arguments",{})
                    print(f"\n{C.T}>>> {n}{C.R}")
                    r = s.ex(n, a)
                    print(f"\n{C.T}{r[:500]}{C.R}\n")
                    s.h.append({"role":"assistant","content":full})
                    s.h.append({"role":"user","content":f"R:{r}"})
                    
                    print(f"{C.A}", end="")
                    for c in s.gs("", sp):
                        print(c, end="", flush=1)
                    print(f"{C.R}")
            
            except KeyboardInterrupt:
                print(f"\n{C.I}type exit{C.R}")
            except Exception as e:
                print(f"{C.E}{e}{C.R}")

if __name__ == "__main__":
    NocodAI().run()