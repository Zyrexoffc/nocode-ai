#!/usr/bin/env python3
import os, sys, json, subprocess, requests, re

K = "\033[40m"
D = "\033[100m"
W = "\033[97m"
H = "\033[90m"
N = "\033[0m"
BOLD = "\033[1m"
Y = "\033[43m"
C = "\033[46m"

def check_ollama():
    try: return requests.get("http://localhost:11434/api/tags", timeout=3).status_code==200
    except: return 0

def chat(msg, hist):
    msgs = [{"role":"system","content":"You are NocodAI, a helpful coding assistant."}]
    msgs.extend(hist[-10:])
    msgs.append({"role":"user","content":msg})
    try:
        r = requests.post("http://localhost:11434/api/chat", json={"model":"phi","messages":msgs,"stream":True}, stream=True, timeout=120)
        out = []
        for x in r.iter_lines():
            if x:
                d = json.loads(x)
                c = d.get("message",{}).get("content","")
                if c: out.append(c)
        return "".join(out)
    except Exception as e: return f"Error: {e}"

def box(title, lines, bg, col):
    print(bg, end="")
    sp = " " * 80
    print(sp)
    if title:
        t = " " + title + " "
        pad = 78 - len(t)
        print(W + col + t + (" " * pad))
    for ln in lines:
        print(" " + H + ln[:78] + (" " * (78 - len(ln[:78]))))
    print(sp + N)
    print(N)

os.system("clear")

print(K + D, end="")
sp = " " * 80
print(sp)
title = "  NOCOD.AI - OpenCode Style AI Assistant" + (" " * 37)
print(title)
print(sp + N)
print()

if not check_ollama():
    box("ERROR", ["Ollama tidak berjalan!", "Jalankan: ollama serve"], K+D, Y)
else:
    box("CONNECTED", ["Ollama Ready (model: phi)", "Ketik pesan untuk mulai..."], K+D, C)
    print()
    
    print(K + D, end="")
    print(sp)
    msg = "  Message:" + (" " * 67)
    print(msg)
    pr = "  > " + (" " * 76)
    print(pr)
    print(sp + N)
    print()

hist = []
while 1:
    msg = input(f"{W}> ").strip()
    if not msg: continue
    if msg.lower() in ["exit","quit","q"]: break
    
    print(f"\n{H}Thinking...\n")
    resp = chat(msg, hist)
    hist.append({"role":"user","content":msg})
    hist.append({"role":"assistant","content":resp})
    
    lines = resp.split("\n")
    box("RESPONSE", lines[:15], K+D, Y)
    print()
    
    print(K + D, end="")
    print(sp)
    msg = "  Message:" + (" " * 67)
    print(msg)
    pr = "  > " + (" " * 76)
    print(pr)
    print(sp + N)
    print()