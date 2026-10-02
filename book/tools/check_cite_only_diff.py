import subprocess, re, sys
files = ["book/content/ch01-intro.tex","book/content/ch02-twin.tex","book/content/ch07-firmware.tex","book/content/ch09-host.tex"]
diff = subprocess.run(["git","diff","-U0","--"]+files,capture_output=True,text=True,encoding="utf-8").stdout
cur=None; removed={}; added={}
for line in diff.splitlines():
    if line.startswith("+++"):
        cur=line[6:].strip().replace('b/','book/',1); removed[cur]=[]; added[cur]=[]
    elif line.startswith("---"): continue
    elif line.startswith("@@"): continue
    elif line.startswith("+") and cur: added[cur].append(line[1:])
    elif line.startswith("-") and cur: removed[cur].append(line[1:])
ok=True
pat = re.compile(r'~?\\cite\{[^}]*\}')
for f in files:
    r,a = removed.get(f,[]), added.get(f,[])
    if len(r)!=len(a):
        print(f,"LINE COUNT MISMATCH",len(r),len(a)); ok=False; continue
    for old,new in zip(r,a):
        stripped = pat.sub('',new)
        if stripped != old:
            print("NON-CITE CHANGE in",f)
            print("  OLD:",old[:100]); print("  NEW:",new[:100]); ok=False
print("RESULT:","PASS - practice chapters changed by cite insertion only" if ok else "FAIL")
sys.exit(0 if ok else 1)
