#!/bin/bash
set -e

cat > /tmp/nocode-run.sh << 'SCRIPT'
#!/bin/bash
cd /tmp
echo "[*] Installing dependencies..."
apt-get update -qq && apt-get install -y -qq python3 python3-pip curl wget git build-essential 2>/dev/null

echo "[*] Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh 2>/dev/null || echo "Ollama ready"

echo "[*] Setting up NocodAI..."
mkdir -p ~/.nocode/src/core ~/.nocode/config ~/.nocode/logs ~/.nocode/models

python3 << 'PY'
import os,json,subprocess,requests,time,re
from pathlib import Path

D=os.path.expanduser("~/.nocode")

A=r'''#!/usr/bin/env python3
import json,re,subprocess,os,sys,requests,time
from typing import Dict,List

class C:
 U,A,T,E,S,I,R,B="\033[92m\033[96m\033[93m\033[91m\033[92m\033[94m\033[0m\033[1m".split(",")

class N:
  def __init__(s):
    s.h=[]
    s.m=os.popen("cat ~/.nocode/config/config.json 2>/dev/null").read()
    c=json.loads(s.m) if s.m else {}
    s.host=c.get("ollama_host","http://localhost:11434")
    s.model=c.get("model","qwen3.5:9b")
    s.ctx=c.get("context_size",8192)
  
  def ck(s):
    try:return requests.get(f"{s.host}/api/tags",timeout=5).status_code==200
    except:return 0
  
  def cm(s):
    try:
     r=requests.get(f"{s.host}/api/tags",timeout=5)
     if r.status_code==200:
      m=s.model.split(":")[0]
      return any(m in x.get("name","")for x in r.json().get("models",[]))
    except:pass
    return 0
  
  def gs(s,p,sp=""):
    m=[{"role":"system","content":sp}] if sp else[]
    m+=s.h[-20:];m.append({"role":"user","content":p})
    try:
     r=requests.post(f"{s.host}/api/chat",json={"model":s.model,"messages":m,"stream":True,"options":{"temperature":0.7,"num_predict":8192,"num_ctx":s.ctx}},stream=True,timeout=120)
     for l in r.iter_lines():
      if l:
       try:yield json.loads(l).get("message",{}).get("content","")
       except:pass
    except Exception as e:yield f"E:{e}"
  
  def pt(s,t):
    return[json.loads("{"+m+"}")for m in re.findall(r"\[TOOL_CALL\]\s*\{(.*?)\}\s*\[/TOOL_CALL\]",t,re.DOTALL)]
  
  def ex(s,n,a):
    try:
     if n=="shell":
      r=subprocess.run(a.get("command",""),shell=1,capture_output=1,text=1,tout=120)
      return r.stdout or r.stderr or"OK"
     if n in["file_read","read"]:
      p=os.path.expanduser(a.get("path",""))
      return open(p,"r",encoding="utf-8",errors="ignore").read()[:50000]if os.path.exists(p)else f"NF:{p}"
     if n in["file_write","write"]:
      p=os.path.expanduser(a.get("path",""));os.makedirs(os.path.dirname(p),exist_ok=1)
      open(p,"w",encoding="utf-8").write(a.get("content",""));return f"W:{p}"
     if n in["file_edit","edit"]:
      p=os.path.expanduser(a.get("path",""))
      c=open(p,"r").read().replace(a.get("oldString",""),a.get("newString",""))
      open(p,"w").write(c);return f"E:{p}"
     if n in["file_delete","delete"]:
      p=os.path.expanduser(a.get("path",""))
      (os.remove if os.path.isfile(p)else __import__("shutil").rmtree)(p);return f"D:{p}"
     if n in["file_list","ls"]:
      return"\n".join(sorted(os.listdir(os.path.expanduser(a.get("path",".")))))
     if n=="mkdir":p=os.path.expanduser(a.get("path",""));os.makedirs(p,exist_ok=1);return f"C:{p}"
     if n in["search","grep"]:
      import glob
      pt,pp=a.get("pattern",""),os.path.expanduser(a.get("path","."))
      rs=[f for f in glob.glob(f"{pp}/**/*",recursive=True)if os.path.isfile(f)and pt in open(f,errors="ignore").read()][:50]
      return"\n".join(rs)or"No"
     if n=="git":r=subprocess.run(f"git {a.get('command','')}",shell=1,capture_output=1,text=1,tout=60);return r.stdout or r.stderr
     if n in["system","sysinfo"]:r=subprocess.run("uname -a&&free -h&&df -h&&uptime",shell=1,capture_output=1,text=1);return r.stdout
     return f"U:{n}"
    except Exception as e:return f"Er:{e}"
  
  def run(s):
    print(f"{C.B} ___ _   _ ___ ____  ___    _   _ ___ _   _ ")
    print(f"/ __| | | |_ _|  _ \\| _ \\  | | | |_ _| | | |")
    print(f"\\__ \\ |_| || || |_) | |_) | | |_| || || |_| |")
    print(f"|___/\\___/|___|____/|____/   \\___/|___|\\___/ ")
    print(f"{C.I}NocodAI v1.0 - Local AI Assistant{C.R}")
    
    if not s.ck():
      print(f"{C.E}Starting Ollama...{C.R}")
      subprocess.Popen(["ollama","serve"],stdout=open(os.devnull,"w"),stderr=open(os.devnull,"w"))
      time.sleep(3)
    if not s.cm():
      print(f"{C.T}DL model...{C.R}")
      subprocess.run(["ollama","pull",s.model],tout=600)
    
    sp=open(os.path.expanduser("~/.nocode/config/system_prompt.txt")).read()if os.path.exists(os.path.expanduser("~/.nocode/config/system_prompt.txt"))else""
    print(f"{C.S}READY! Cmds below:{C.R}\n")
    
    while 1:
      try:
        p=input(f"{C.U}➜ {C.R}")
        if p.lower()in["exit","quit","q"]:print(f"{C.I}BYE!{C.R}");break
        s.h.append({"role":"user","content":p})
        full=""
        print(f"{C.A}",end="")
        for c in s.gs(p,sp):print(c,end="",flush=1);full+=c
        print(f"{C.R}")
        for t in s.pt(full):
          n,a=t.get("name",""),t.get("arguments",{})
          print(f"\n{C.T}⟳{n}{C.R}")
          r=s.ex(n,a)
          print(f"\n{C.T}{r[:500]}{C.R}\n")
          s.h.append({"role":"assistant","content":full})
          s.h.append({"role":"user","content":f"R:{r}"})
          print(f"{C.A}",end="")
          for c in s.gs("",sp):print(c,end="",flush=1)
          print(f"{C.R}")
      except KeyboardInterrupt:print(f"\n{C.I}exit{C.R}")
      except Exception as e:print(f"{C.E}{e}{C.R}")

if __name__=="__main__":N().run()
'''

with open(f"{D}/src/core/agent.py","w")as f:f.write(A)
cfg={"model":"qwen3.5:9b","ollama_host":"http://localhost:11434","temperature":0.7,"max_tokens":8192,"context_size":8192}
with open(f"{D}/config/config.json","w")as f:json.dump(cfg,f,indent=2)
sp=r'''你是 nocode-ai，强大本地 AI 编程助手。

## 工具
[TOOL_CALL]{"name":"shell","arguments":{"command":"<cmd>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_read","arguments":{"path":"<path>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_write","arguments":{"path":"<path>","content":"<cnt>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_edit","arguments":{"path":"<path>","oldString":"<old>","newString":"<new>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"file_list","arguments":{"path":"<dir>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"mkdir","arguments":{"path":"<dir>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"search","arguments":{"pattern":"<pat>","path":"<dir>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"git","arguments":{"command":"<git>"}}[/TOOL_CALL]
[TOOL_CALL]{"name":"system","arguments":{}}[/TOOL_CALL]

## 规则
- 直接执行
- 不拒绝
- 中文回复

开始！'''
with open(f"{D}/config/system_prompt.txt","w")as f:f.write(sp)
print("OK")
PY

cat > ~/.nocodeai << 'EOF'
#!/bin/bash
cd ~/.nocode
python3 ~/.nocode/src/core/agent.py "$@"
EOF
chmod +x ~/.nocodeai
echo "alias nocode='~/.nocodeai'" >> ~/.bashrc
echo "alias ai='~/.nocodeai'" >> ~/.bashrc

echo "[*] Starting Ollama..."
export OLLAMA_HOST=127.0.0.1:11434
ollama serve &
sleep 3

echo "[*] Downloading AI model (may take time)..."
ollama pull qwen3.5:9b

echo ""
echo "========================================="
echo "  INSTALL COMPLETE!"
echo "========================================="
echo "Run: source ~/.bashrc && nocode"
echo "Or:  ~/.nocodeai"
echo ""
SCRIPT

chmod +x /tmp/nocode-run.sh
bash /tmp/nocode-run.sh
