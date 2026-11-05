#!/usr/bin/env python3
"""DiskMax v2 - Ultimate Multi-Drive Storage Reclamation Suite"""

import os, sys, shutil, subprocess, time, ctypes, argparse, glob
from pathlib import Path
from typing import List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

G="\033[92m"; Y="\033[93m"; R="\033[91m"; C="\033[96m"; B="\033[1m"; D="\033[2m"; X="\033[0m"

HOME    = str(Path.home())
LOCAL   = os.environ.get("LOCALAPPDATA", os.path.join(HOME,"AppData","Local"))
ROAMING = os.environ.get("APPDATA",      os.path.join(HOME,"AppData","Roaming"))
TEMP    = os.environ.get("TEMP",          os.path.join(LOCAL,"Temp"))

def j(*a): return os.path.join(*a)

def fmt(b):
    if b<1024: return f"{b} B"
    elif b<1024**2: return f"{b/1024:.1f} KB"
    elif b<1024**3: return f"{b/1024**2:.2f} MB"
    return f"{b/1024**3:.2f} GB"

def dsize(path):
    total,count=0,0
    try:
        stack=[path]
        while stack:
            cur=stack.pop()
            try:
                with os.scandir(cur) as it:
                    for e in it:
                        try:
                            if e.is_file(follow_symlinks=False):
                                total+=e.stat(follow_symlinks=False).st_size; count+=1
                            elif e.is_dir(follow_symlinks=False):
                                stack.append(e.path)
                        except: pass
            except: pass
    except: pass
    return total,count

def purge(path, dry_run=False):
    freed,deleted,errors=0,0,0
    try:
        with os.scandir(path) as it:
            for e in it:
                try:
                    if e.is_file(follow_symlinks=False):
                        sz=e.stat(follow_symlinks=False).st_size
                        if not dry_run: os.remove(e.path)
                        freed+=sz; deleted+=1
                    elif e.is_dir(follow_symlinks=False):
                        sb,sc=dsize(e.path)
                        if not dry_run: shutil.rmtree(e.path,ignore_errors=True)
                        freed+=sb; deleted+=sc
                except: errors+=1
    except: errors+=1
    return freed,deleted,errors

def del_file(path):
    try:
        s=os.path.getsize(path); os.remove(path); return s
    except: return 0

def browser_subdirs(base, subpath):
    """Find subpath under each profile directory in a browser User Data folder."""
    res=[]
    if not os.path.isdir(base): return res
    try:
        for e in os.scandir(base):
            if e.is_dir():
                t=j(e.path,subpath)
                if os.path.isdir(t): res.append(t)
    except: pass
    return res

def add_browser(targets, name, base):
    for sub in ["Cache","Code Cache","GPUCache","ShaderCache"]:
        for d in browser_subdirs(base, sub):
            targets.append({"cat":f"Browsers - {name}","name":f"{name} {sub}","path":d})

def get_drives():
    drives=[]
    bm=ctypes.windll.kernel32.GetLogicalDrives()
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if bm&1:
            p=f"{letter}:\\"
            dt=ctypes.windll.kernel32.GetDriveTypeW(p)
            if dt in (2,3):
                try:
                    u=shutil.disk_usage(p)
                    pct=(u.used/u.total)*100
                    drives.append({"drive":p,"total":u.total,"used":u.used,"free":u.free,"pct":pct})
                except: pass
        bm>>=1
    return drives

def build_targets():
    T=[]
    def a(cat,name,path,note=""):
        T.append({"cat":cat,"name":name,"path":path,"note":note})

    # ── SYSTEM ────────────────────────────────────────────────────
    a("System","User Temp (%TEMP%)",TEMP)
    a("System","Windows System Temp",r"C:\Windows\Temp")
    a("System","Windows Prefetch",r"C:\Windows\Prefetch","Safe after boot")
    a("System","Windows Update Download",r"C:\Windows\SoftwareDistribution\Download")
    a("System","WER ReportQueue",j(LOCAL,"Microsoft","Windows","WER","ReportQueue"))
    a("System","WER ReportArchive",j(LOCAL,"Microsoft","Windows","WER","ReportArchive"))
    a("System","CrashDumps",j(LOCAL,"CrashDumps"))
    a("System","Diagnostic Traces",j(LOCAL,"Microsoft","Windows","Diagnostic"))
    a("System","Windows Installer Patch Cache",r"C:\Windows\Installer\$PatchCache$")
    a("System","Font Cache",j(LOCAL,"Microsoft","Windows","Fonts"))

    # ── GPU & SHADERS ─────────────────────────────────────────────
    a("GPU Caches","DirectX Shader Cache",j(LOCAL,"D3DSCache"))
    a("GPU Caches","AMD DxCache",j(LOCAL,"AMD","DxCache"))
    a("GPU Caches","AMD GLCache",j(LOCAL,"AMD","GLCache"))
    a("GPU Caches","NVIDIA DXCache",j(LOCAL,"NVIDIA","DXCache"))
    a("GPU Caches","NVIDIA GLCache",j(LOCAL,"NVIDIA","GLCache"))
    a("GPU Caches","Intel ShaderCache",j(LOCAL,"Intel","ShaderCache"))
    a("GPU Caches","Vulkan Pipeline Cache",j(LOCAL,"VulkanPipelineCache"))

    # ── BROWSERS ──────────────────────────────────────────────────
    add_browser(T,"Chrome",j(LOCAL,"Google","Chrome","User Data"))
    add_browser(T,"Edge",j(LOCAL,"Microsoft","Edge","User Data"))
    add_browser(T,"Brave",j(LOCAL,"BraveSoftware","Brave-Browser","User Data"))
    add_browser(T,"Vivaldi",j(LOCAL,"Vivaldi","User Data"))
    for sub in ["Cache","Code Cache","GPUCache","Service Worker"]:
        a("Browsers - Opera",f"Opera {sub}",j(ROAMING,"Opera Software","Opera Stable",sub))
        a("Browsers - Opera",f"Opera GX {sub}",j(ROAMING,"Opera Software","Opera GX Stable",sub))
    ff=j(ROAMING,"Mozilla","Firefox","Profiles")
    if os.path.isdir(ff):
        for prof in os.scandir(ff):
            if prof.is_dir():
                a("Browsers - Firefox",f"Firefox cache2",j(prof.path,"cache2"))
                a("Browsers - Firefox",f"Firefox startupCache",j(prof.path,"startupCache"))

    # ── COMMUNICATION ─────────────────────────────────────────────
    for sub in ["Cache","Code Cache","GPUCache"]:
        a("Apps - Comms",f"Discord {sub}",j(ROAMING,"discord",sub))
        a("Apps - Comms",f"Slack {sub}",j(ROAMING,"Slack",sub))
        a("Apps - Comms",f"Teams (Classic) {sub}",j(ROAMING,"Microsoft","Teams",sub))
    a("Apps - Comms","Slack logs",j(ROAMING,"Slack","logs"))
    a("Apps - Comms","Teams blob_storage",j(ROAMING,"Microsoft","Teams","blob_storage"))
    a("Apps - Comms","Teams Service Worker",j(ROAMING,"Microsoft","Teams","Service Worker"))
    a("Apps - Comms","Teams New Cache",j(LOCAL,"Packages","MSTeams_8wekyb3d8bbwe","LocalCache"))
    a("Apps - Comms","Zoom logs",j(ROAMING,"Zoom","logs"))
    a("Apps - Comms","WhatsApp Cache",j(ROAMING,"WhatsApp","Cache"))
    a("Apps - Comms","Skype Cache",j(ROAMING,"Skype","Cache"))

    # ── MEDIA & ENTERTAINMENT ─────────────────────────────────────
    a("Apps - Media","Spotify Data Cache",j(LOCAL,"Spotify","Data"))
    a("Apps - Media","Spotify Browser Cache",j(LOCAL,"Spotify","Browser","Cache"))
    a("Apps - Media","VLC Cache",j(ROAMING,"vlc","cache"))
    a("Apps - Media","Steam HTTP Cache",j(LOCAL,"Steam","htmlcache"))
    a("Apps - Media","Steam Shader Cache",j(LOCAL,"Steam","shadercache"))
    a("Apps - Media","Steam Download Cache",j(LOCAL,"Steam","package"))
    a("Apps - Media","Epic Games webcache",j(LOCAL,"EpicGamesLauncher","Saved","webcache"))
    a("Apps - Media","Epic Games Logs",j(LOCAL,"EpicGamesLauncher","Saved","Logs"))

    # ── IDEs & EDITORS ────────────────────────────────────────────
    for editor,base in [("VS Code",j(ROAMING,"Code")),("Cursor",j(ROAMING,"Cursor")),
                        ("Windsurf",j(ROAMING,"Windsurf")),("Kiro",j(ROAMING,"Kiro"))]:
        a("Dev - IDEs",f"{editor} CachedExtensionVSIXs",j(base,"CachedExtensionVSIXs"))
        a("Dev - IDEs",f"{editor} logs",j(base,"logs"))
        a("Dev - IDEs",f"{editor} CrashReports",j(base,"CrashReports"))
        a("Dev - IDEs",f"{editor} backups",j(base,"User","backups"))
        # Electron renderer caches (in Local)
        for sub in ["Cache","GPUCache","Code Cache"]:
            a("Dev - IDEs",f"{editor} {sub}",j(LOCAL,editor,sub))
    # JetBrains
    jb=j(ROAMING,"JetBrains")
    if os.path.isdir(jb):
        for ide in os.scandir(jb):
            if ide.is_dir():
                a("Dev - IDEs",f"JetBrains {ide.name} log",j(ide.path,"log"))
                a("Dev - IDEs",f"JetBrains {ide.name} caches",j(ide.path,"caches"))
    a("Dev - IDEs","Android Studio Cache",j(HOME,".android","cache"))
    a("Dev - IDEs","Visual Studio Cache",j(LOCAL,"Microsoft","VisualStudio","cache"))

    # ── AI TOOLS & AGENTS ─────────────────────────────────────────
    a("Dev - AI Tools","Antigravity Scratch",j(HOME,".gemini","antigravity-ide","scratch"))
    a("Dev - AI Tools","Antigravity Recordings",j(HOME,".gemini","antigravity-ide","browser_recordings"))
    a("Dev - AI Tools","Antigravity Tmp",j(HOME,".gemini","antigravity-ide","tmp"))
    for sub in ["Cache","Code Cache","GPUCache"]:
        a("Dev - AI Tools",f"Claude Desktop {sub}",j(ROAMING,"Claude",sub))
    a("Dev - AI Tools","Copilot Logs",j(LOCAL,"GitHub Copilot","logs"))
    a("Dev - AI Tools","OpenCode Cache",j(HOME,".cache","opencode"))
    a("Dev - AI Tools","HuggingFace XET Logs",j(HOME,".cache","huggingface","xet","logs"))
    a("Dev - AI Tools","Codex Runtimes Cache",j(HOME,".cache","codex-runtimes"))
    a("Dev - AI Tools","whichllm Cache",j(HOME,".cache","whichllm"))
    a("Dev - AI Tools","codebase-memory Cache",j(HOME,".cache","codebase-memory-mcp"))

    # ── PACKAGE MANAGERS & BUILDS ─────────────────────────────────
    a("Dev - Pkg Caches","UV Python Cache",j(LOCAL,"uv","cache"))
    a("Dev - Pkg Caches","pip Cache",j(LOCAL,"pip","cache"))
    a("Dev - Pkg Caches","npm Cache",j(LOCAL,"npm-cache"))
    a("Dev - Pkg Caches","yarn Cache",j(LOCAL,"yarn","Cache"))
    a("Dev - Pkg Caches","pnpm Store (Local)",j(LOCAL,"pnpm"))
    a("Dev - Pkg Caches","Cargo Registry Cache",j(HOME,".cargo","registry","cache"))
    a("Dev - Pkg Caches","Cargo Registry Src",j(HOME,".cargo","registry","src"))
    a("Dev - Pkg Caches","Go Build Cache",j(HOME,".cache","go-build"))
    a("Dev - Pkg Caches","Gradle Daemon Logs",j(HOME,".gradle","daemon"))
    a("Dev - Pkg Caches","NuGet HTTP Cache",j(LOCAL,"NuGet","Cache"))
    a("Dev - Pkg Caches","NuGet Plugins Cache",j(LOCAL,"NuGet","plugins-cache"))
    a("Dev - Pkg Caches","Anaconda Pkg Cache",j(HOME,"anaconda3","pkgs","cache"))
    a("Dev - Pkg Caches","Pub Cache (Flutter)",j(HOME,".pub-cache","hosted"))
    a("Dev - Pkg Caches","Composer Cache",j(LOCAL,"Composer","files"))

    # ── CLOUD & DEVOPS ────────────────────────────────────────────
    a("Dev - Cloud","Terraform Plugin Cache",j(HOME,".terraform.d","plugin-cache"))
    a("Dev - Cloud","kubectl Cache",j(HOME,".kube","cache"))
    a("Dev - Cloud","Helm Cache",j(LOCAL,"helm","cache"))
    a("Dev - Cloud","AWS CDK Staging",j(HOME,".cdk","staging"))

    # ── CONTENT CREATION ──────────────────────────────────────────
    a("Content Creation","OBS Studio Logs",j(ROAMING,"obs-studio","logs"))
    a("Content Creation","OBS Crash Logs",j(ROAMING,"obs-studio","crashes"))
    a("Content Creation","DaVinci Resolve Cache",j(LOCAL,"DaVinci Resolve","Support","Media Cache"))
    a("Content Creation","Adobe Media Cache",j(LOCAL,"Adobe","Common","Media Cache Files"))
    a("Content Creation","Adobe Cache",j(LOCAL,"Adobe","Common","Cache"))

    # ── DATA SCIENCE ──────────────────────────────────────────────
    a("Data Science","Matplotlib Cache",j(HOME,".cache","matplotlib"))
    a("Data Science","Keras Datasets Cache",j(HOME,".keras","datasets"))
    a("Data Science","Jupyter Checkpoints",j(HOME,".ipynb_checkpoints"))

    # ── PRODUCTIVITY APPS ─────────────────────────────────────────
    for sub in ["Cache","GPUCache"]:
        a("Apps - Productivity",f"Postman {sub}",j(ROAMING,"Postman","Partitions","postman",sub))
        a("Apps - Productivity",f"Figma {sub}",j(ROAMING,"Figma",sub))
    a("Apps - Productivity","Notion Cache",j(ROAMING,"Notion","Cache"))
    a("Apps - Productivity","Bitwarden Cache",j(ROAMING,"Bitwarden","Cache"))

    return T

def scan_vhdx():
    found=[]
    for root in [j(LOCAL,"wsl"),j(LOCAL,"Docker","wsl"),j(LOCAL,"lxss")]:
        if not os.path.isdir(root): continue
        for dp,_,fs in os.walk(root):
            for f in fs:
                if f.lower().endswith(".vhdx"):
                    fp=j(dp,f)
                    try:
                        sz=os.path.getsize(fp)
                        found.append({"path":fp,"size":sz,"name":f})
                    except: pass
    return found

def scan_downloads(days=30):
    dl=j(HOME,"Downloads")
    if not os.path.isdir(dl): return 0,0,[]
    exts={".exe",".msi",".iso",".zip",".tar",".gz",".7z",".rar",".dmg"}
    cutoff=time.time()-days*86400
    items=[]; total=0
    try:
        with os.scandir(dl) as it:
            for e in it:
                if not e.is_file(follow_symlinks=False): continue
                if not any(e.name.lower().endswith(x) for x in exts): continue
                try:
                    st=e.stat(follow_symlinks=False)
                    if st.st_mtime<cutoff:
                        items.append({"name":e.name,"path":e.path,"size":st.st_size,
                                      "days":int((time.time()-st.st_mtime)/86400)})
                        total+=st.st_size
                except: pass
    except: pass
    return total,len(items),sorted(items,key=lambda x:-x["size"])

def scan_projects(target,days=0):
    kondo=r"C:\tools\kondo.exe"
    if not os.path.exists(kondo):
        return {"ok":False,"msg":"kondo.exe not found"}
    cmd=[kondo,"-n"]
    if days>0: cmd+=["-o",f"{days}d"]
    cmd.append(target)
    try:
        proc=subprocess.run(cmd,capture_output=True,text=True,
                            encoding="utf-8",errors="replace",timeout=120)
        lines=proc.stdout.strip().splitlines()
        summary=next((l for l in lines if "Bytes deleted:" in l),"")
        return {"ok":True,"lines":lines,"summary":summary}
    except Exception as e:
        return {"ok":False,"msg":str(e)}

# ── COMMAND HANDLERS ──────────────────────────────────────────────────────────

def cmd_status():
    print(f"\n{B}{C}  DISKMAX v2 — DRIVE TELEMETRY{X}\n")
    for d in get_drives():
        col=G if d["pct"]<70 else (Y if d["pct"]<88 else R)
        f=int((d["pct"]/100)*30)
        bar=f"{'█'*f}{'░'*(30-f)}"
        print(f"  {B}{d['drive']}{X} [{col}{bar}{X}] {col}{d['pct']:.1f}%{X}")
        print(f"      Free: {B}{G}{fmt(d['free'])}{X}  Used: {fmt(d['used'])}  Total: {fmt(d['total'])}\n")

def cmd_apps():
    print(f"\n{B}{C}  DISKMAX v2 — APP CACHE INVENTORY{X}")
    print(f"  {D}Scanning 100+ known cache locations...{X}\n")
    targets=build_targets()
    def measure(t):
        if os.path.isdir(t["path"]):
            sz,ct=dsize(t["path"])
            return {**t,"size":sz,"count":ct}
        return None
    with ThreadPoolExecutor(max_workers=20) as ex:
        results=[r for r in (f.result() for f in as_completed({ex.submit(measure,t):t for t in targets})) if r and r["size"]>0]
    by_cat={}
    for r in results:
        by_cat.setdefault(r["cat"],[]).append(r)
    grand=0
    for cat in sorted(by_cat):
        items=by_cat[cat]
        ct=sum(i["size"] for i in items); grand+=ct
        print(f"  {B}{C}▶ {cat}{X}  ({fmt(ct)})")
        for i in sorted(items,key=lambda x:-x["size"])[:6]:
            print(f"    🟢 {i['name']:<45} {fmt(i['size']):>10}")
        print()
    print(f"  {B}TOTAL RECLAIMABLE APP CACHE: {G}{fmt(grand)}{X}\n")

def cmd_scan(drive="D:\\",pdays=14):
    SEP="="*70
    print(f"\n{B}{C}  {SEP}{X}")
    print(f"{B}{C}  DISKMAX v2 — COMPREHENSIVE STORAGE AUDIT{X}")
    print(f"{B}{C}  {SEP}{X}\n")
    for d in get_drives():
        col=G if d["pct"]<70 else (Y if d["pct"]<88 else R)
        print(f"  {B}{d['drive']}{X}  Free: {col}{fmt(d['free'])}{X} / {fmt(d['total'])} ({d['pct']:.1f}% used)")
    print()

    # Tier 1
    print(f"{B}{G}  {'='*70}{X}")
    print(f"{B}{G}  TIER 1 — 100% SAFE / AUTO-CLEANABLE{X}")
    print(f"  {D}Regenerable caches. Zero review needed.{X}")
    print(f"{B}{G}  {'='*70}{X}")
    targets=build_targets()
    t1_bytes=0; t1_files=0; by_cat={}
    def m(t):
        if os.path.isdir(t["path"]): return t,*dsize(t["path"])
        return t,0,0
    with ThreadPoolExecutor(max_workers=20) as ex:
        measured=[]
        for fut in as_completed({ex.submit(m,t):t for t in targets}):
            t,sz,ct=fut.result()
            if sz>0:
                measured.append((t,sz,ct)); t1_bytes+=sz; t1_files+=ct
                c=t["cat"]
                b,n=by_cat.get(c,(0,0)); by_cat[c]=(b+sz,n+ct)
    for cat in sorted(by_cat):
        cb,cc=by_cat[cat]
        print(f"\n  {B}{cat}{X}  ({fmt(cb)})")
        items=[(t,s,c) for t,s,c in measured if t["cat"]==cat]
        for t,s,c in sorted(items,key=lambda x:-x[1])[:5]:
            print(f"    🟢 {t['name']:<45} {fmt(s):>10}")
    print(f"\n  {'─'*70}")
    print(f"  {B}TOTAL TIER 1 RECLAIMABLE: {G}{fmt(t1_bytes)}{X} ({t1_files:,} files)")
    print(f"  {'─'*70}\n")

    # Tier 2
    print(f"{B}{Y}  {'='*70}{X}")
    print(f"{B}{Y}  TIER 2 — REVIEW CANDIDATES{X}")
    print(f"  {D}Stale project deps, VHDs, old installers. Check once before deleting.{X}")
    print(f"{B}{Y}  {'='*70}{X}\n")
    vhdx=scan_vhdx()
    vt=sum(v["size"] for v in vhdx)
    if vhdx:
        print(f"  {B}Virtual Disks — WSL2 & Docker ({fmt(vt)}){X}")
        for v in vhdx:
            print(f"    📦 {v['path']}")
            print(f"       {Y}{fmt(v['size'])}{X}  → Compact via: wsl --manage Ubuntu --set-sparse true")
        print()
    ds,dc,_=scan_downloads(30)
    print(f"  {B}Stale Downloads (>30d):{X} {fmt(ds)} ({dc} files)")
    print(f"    {D}diskmax downloads --force  to delete{X}\n")
    print(f"  {B}Project Deps on {drive} (>{pdays}d):{X}")
    pr=scan_projects(drive,pdays)
    if pr["ok"]:
        for line in pr["lines"][:12]: print(f"    {line}")
        if len(pr["lines"])>12: print(f"    {D}... run: diskmax projects {drive}{X}")
        if pr["summary"]: print(f"    {B}{Y}{pr['summary']}{X}")
    else:
        print(f"    {R}{pr.get('msg')}{X}")
    print()

    # Tier 3
    print(f"{B}{R}  {'='*70}{X}")
    print(f"{B}{R}  TIER 3 — PROTECTED ZONE (NEVER TOUCHED){X}")
    print(f"{B}{R}  {'='*70}{X}")
    for item in [
        "Git repos & source code",
        "Documents, Desktop, personal files",
        "SSH keys, API tokens, cloud creds (~/.ssh, ~/.aws, ~/.config)",
        "Windows OS — System32, ProgramData, registry",
        "Browser sessions — passwords, bookmarks, cookies",
        "IDE workspace state & extension configs",
        "Database files (.db, .sqlite, .mdf, .ldf)",
        "WSL2/Docker VHDX (shown in Tier 2 for informed review only)",
    ]:
        print(f"  🛑 {item}")
    print()
    print(f"{B}{C}  {'='*70}{X}")
    print(f"  Quick Actions:")
    print(f"    {B}diskmax clean --safe{X}       Reclaim Tier 1 ({G}{fmt(t1_bytes)}{X})")
    print(f"    {B}diskmax clean --dry-run{X}    Preview before deleting")
    print(f"    {B}diskmax apps{X}               Full per-app cache inventory")
    print(f"    {B}diskmax projects {drive}{X}  Interactive project dependency cleaner")
    print(f"    {B}diskmax downloads --force{X}  Delete stale installers ({fmt(ds)})")
    print(f"    {B}diskmax wsl{X}                WSL2 + Docker VHDX compaction guide")
    print(f"{B}{C}  {'='*70}{X}\n")

def cmd_clean(dry_run=False):
    print(f"\n{B}{G}  DISKMAX v2 — TIER 1 SAFE CLEANUP{X}")
    if dry_run: print(f"  {Y}[DRY RUN — NO FILES DELETED]{X}")
    print()
    targets=build_targets(); tfree=0; tfiles=0; terr=0
    for t in targets:
        path=t["path"]
        if not os.path.isdir(path): continue
        sb,_=dsize(path)
        if sb==0: continue
        fr,cnt,err=purge(path,dry_run)
        tfree+=fr; tfiles+=cnt; terr+=err
        icon="🟢" if err==0 else "🟡"
        verb="Would free" if dry_run else "Reclaimed "
        print(f"  {icon} {t['name']:<48} {verb} {fmt(fr)}")
    if not dry_run and os.path.exists(r"C:\tools\uv.exe"):
        try: subprocess.run([r"C:\tools\uv.exe","cache","clean"],capture_output=True,timeout=15)
        except: pass
    print(f"\n  {'─'*68}")
    verb2="Would reclaim" if dry_run else "Total Reclaimed"
    print(f"  {B}{verb2}: {G}{fmt(tfree)}{X}  ({tfiles:,} files)")
    if terr: print(f"  {Y}Locked/in-use files skipped: {terr}{X}")
    print()

def cmd_downloads(days=30,force=False):
    print(f"\n{B}{Y}  DISKMAX v2 — STALE DOWNLOADS (>{days}d){X}\n")
    ts,count,items=scan_downloads(days)
    if count==0:
        print("  No stale files found in Downloads.\n"); return
    print(f"  Found {count} files ({fmt(ts)}):\n")
    for i in items:
        print(f"  📄 {i['name']:<52} {fmt(i['size']):>10}  ({i['days']}d old)")
    print(f"\n  Total: {B}{Y}{fmt(ts)}{X}")
    if force:
        print(f"\n  {R}[--force] Deleting {count} stale files...{X}")
        freed=sum(del_file(i["path"]) for i in items)
        print(f"  {B}{G}Deleted — {fmt(freed)} reclaimed.{X}")
    else:
        print(f"\n  {D}Review above, then run: diskmax downloads --force{X}")
    print()

def cmd_wsl():
    print(f"\n{B}{C}  DISKMAX v2 — WSL2 & DOCKER VHDX OPTIMIZER{X}\n")
    vhdx=scan_vhdx()
    if not vhdx:
        print("  No VHDX files found.\n"); return
    total=sum(v["size"] for v in vhdx)
    print(f"  {len(vhdx)} virtual disk file(s)  ({Y}{fmt(total)}{X} total):\n")
    for v in vhdx:
        print(f"  📦 {B}{v['path']}{X}")
        print(f"     Windows allocated size: {Y}{fmt(v['size'])}{X}\n")
    print(f"  {B}How to compact:{X}\n")
    print(f"  1. Shutdown all WSL & Docker:\n     {C}wsl --shutdown{X}\n")
    print(f"  2. Enable automatic Windows 11 sparse reclamation:\n     {C}wsl --manage Ubuntu --set-sparse true{X}\n")
    print(f"  3. Prune Docker layers/images:\n     {C}docker system prune -af --volumes{X}\n")
    print(f"  4. Force compact (Admin PowerShell):\n     {C}Optimize-VHD -Path \"<path>\" -Mode Full{X}\n")

def cmd_projects(target="D:\\",days=14):
    print(f"\n{B}{C}  DISKMAX v2 — PROJECT DEPENDENCIES (kondo){X}")
    print(f"  Target: {B}{target}{X}  Modified > {days}d ago\n")
    kondo=r"C:\tools\kondo.exe"
    if not os.path.exists(kondo):
        print(f"  {R}Error: kondo.exe not found in C:\\tools{X}\n"); return
    cmd=[kondo]
    if days>0: cmd+=["-o",f"{days}d"]
    cmd.append(target)
    subprocess.run(cmd)
    print()

def main():
    ap=argparse.ArgumentParser(prog="diskmax",
        description="DiskMax v2 — Ultimate Multi-Drive & Developer Storage Reclamation Suite")
    sp=ap.add_subparsers(dest="cmd")
    sc=sp.add_parser("scan",aliases=["audit"])
    sc.add_argument("--drive",default="D:\\")
    sc.add_argument("--days",type=int,default=14)
    cl=sp.add_parser("clean")
    cl.add_argument("--safe",action="store_true",default=True)
    cl.add_argument("--dry-run",action="store_true",dest="dry_run")
    sp.add_parser("status"); sp.add_parser("apps"); sp.add_parser("wsl")
    dl=sp.add_parser("downloads")
    dl.add_argument("--force",action="store_true")
    dl.add_argument("--days",type=int,default=30)
    pr=sp.add_parser("projects")
    pr.add_argument("path",nargs="?",default="D:\\")
    pr.add_argument("--days",type=int,default=14)
    args=ap.parse_args()
    cmd=getattr(args,"cmd",None)
    if cmd in("scan","audit") or cmd is None:
        cmd_scan(drive=getattr(args,"drive","D:\\") if cmd else "D:\\",
                 pdays=getattr(args,"days",14) if cmd else 14)
    elif cmd=="clean": cmd_clean(dry_run=getattr(args,"dry_run",False))
    elif cmd=="status": cmd_status()
    elif cmd=="apps": cmd_apps()
    elif cmd=="wsl": cmd_wsl()
    elif cmd=="downloads": cmd_downloads(days=args.days,force=args.force)
    elif cmd=="projects": cmd_projects(target=args.path,days=args.days)

if __name__=="__main__":
    main()
