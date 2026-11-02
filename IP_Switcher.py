"""Windows IP Switcher v3.0 - Windows 10/11 Tkinter application."""
import ctypes, ipaddress, json, os, subprocess, sys, threading, urllib.request
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox

APPDIR=Path(os.getenv("APPDATA") or Path.home())/"WindowsIPSwitcher"
STORE=APPDIR/"profiles.json"
DEFAULT={
 "MikroTik Management":{"ip":"192.168.88.10","mask":"255.255.255.0","gateway":"","dns1":"","dns2":""},
 "BDCOM OLT Management":{"ip":"192.168.1.10","mask":"255.255.255.0","gateway":"","dns1":"","dns2":""},
 "ONU Management":{"ip":"192.168.100.10","mask":"255.255.255.0","gateway":"","dns1":"","dns2":""}
}
def command(args):
 return subprocess.run(args,text=True,capture_output=True,errors="replace",timeout=25,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
def elevated():
 try:return bool(ctypes.windll.shell32.IsUserAnAdmin())
 except Exception:return False
def admins():
 if elevated():return
 exe=sys.executable
 args="" if getattr(sys,"frozen",False) else '"'+str(Path(__file__).resolve())+'"'
 if ctypes.windll.shell32.ShellExecuteW(None,"runas",exe,args,None,1)>32:sys.exit(0)
def adapters():
 p=command(["powershell.exe","-NoProfile","-NonInteractive","-Command","@(Get-NetAdapter | Select-Object -ExpandProperty Name) | ConvertTo-Json -Compress"])
 if p.returncode:raise RuntimeError(p.stderr)
 result=json.loads(p.stdout.strip().lstrip("\ufeff"))
 return sorted([result] if isinstance(result,str) else result or [])
def check(d):
 ip=ipaddress.IPv4Address(d["ip"]); mask=ipaddress.IPv4Address(d["mask"])
 net=ipaddress.IPv4Network(f"{ip}/{mask}",strict=False)
 if str(net.netmask)!=str(mask):raise ValueError("Invalid subnet mask")
 if net.prefixlen<31 and ip in (net.network_address,net.broadcast_address):raise ValueError("Unusable host address")
 gw=d["gateway"]
 if gw:
  gateway=ipaddress.IPv4Address(gw)
  if gateway not in net or gateway==ip:raise ValueError("Gateway must be in this subnet and different from IP")
 if d["dns2"] and not d["dns1"]:raise ValueError("Primary DNS required when secondary DNS is set")
 for key in ("dns1","dns2"):
  if d[key]:ipaddress.IPv4Address(d[key])
 return d
class App:
 def __init__(self,root):
  self.root=root;root.title("Windows IP Switcher v3.0");root.geometry("930x740");root.minsize(780,640)
  root.configure(bg="#101827")
  self.profile=tk.StringVar();self.adapter=tk.StringVar();self.mode=tk.StringVar(value="static")
  self.name=tk.StringVar();self.values={k:tk.StringVar() for k in ("ip","mask","gateway","dns1","dns2")}
  self.public=tk.StringVar(value="Not checked");self.status=tk.StringVar(value="Ready")
  self.busy=False
  try:self.profiles=json.loads(STORE.read_text(encoding="utf-8"))
  except (OSError,ValueError):self.profiles=dict(DEFAULT)
  style=ttk.Style();style.theme_use("clam")
  style.configure("TFrame",background="#101827");style.configure("TLabel",background="#101827",foreground="#f1f5ff",font=("Segoe UI",10))
  style.configure("Title.TLabel",font=("Segoe UI Semibold",21))
  style.configure("TButton",padding=7);style.configure("TEntry",padding=6)
  frame=ttk.Frame(root,padding=20);frame.pack(fill="both",expand=True)
  ttk.Label(frame,text="Windows IP Switcher",style="Title.TLabel").pack(anchor="w")
  ttk.Label(frame,text="Static IPv4 / DHCP • Saved profiles • Public IPv4").pack(anchor="w",pady=(0,12))
  def row(label):
   f=ttk.Frame(frame);f.pack(fill="x",pady=5)
   ttk.Label(f,text=label,width=23).pack(side="left")
   return f
  f=row("Network adapter")
  self.adapterbox=ttk.Combobox(f,textvariable=self.adapter,state="readonly")
  self.adapterbox.pack(side="left",fill="x",expand=True)
  ttk.Button(f,text="Refresh",command=self.refresh_adapters).pack(side="left",padx=5)
  f=row("Saved profile")
  self.combo=ttk.Combobox(f,textvariable=self.profile,state="readonly")
  self.combo.pack(side="left",fill="x",expand=True)
  self.combo.bind("<<ComboboxSelected>>",lambda e:self.load())
  ttk.Button(f,text="+ New Profile",command=self.new).pack(side="left",padx=5)
  ttk.Button(f,text="Delete",command=self.delete).pack(side="left")
  f=row("IP mode")
  ttk.Radiobutton(f,text="Static IPv4",variable=self.mode,value="static",command=self.toggle).pack(side="left")
  ttk.Radiobutton(f,text="DHCP",variable=self.mode,value="dhcp",command=self.toggle).pack(side="left",padx=15)
  self.entries={}
  for label,k in [("Profile name","name"),("IP address","ip"),("Subnet mask","mask"),("Gateway (optional)","gateway"),("Primary DNS (optional)","dns1"),("Secondary DNS (optional)","dns2")]:
   f=row(label);v=self.name if k=="name" else self.values[k]
   e=ttk.Entry(f,textvariable=v);e.pack(side="left",fill="x",expand=True);self.entries[k]=e
  f=ttk.Frame(frame);f.pack(fill="x",pady=15)
  for title,fn in [("Save / Update Profile",self.save),("Apply Static IP",self.static),("Switch to DHCP",self.dhcp),("Show Current IP",self.current)]:
   ttk.Button(f,text=title,command=fn).pack(side="left",padx=(0,7))
  f=row("Public IPv4")
  ttk.Label(f,textvariable=self.public).pack(side="left",fill="x",expand=True)
  self.publicbutton=ttk.Button(f,text="Show Public IP",command=self.getpublic)
  self.publicbutton.pack(side="left",padx=5)
  ttk.Button(f,text="Copy IP",command=self.copy).pack(side="left")
  ttk.Label(frame,text="Public IP is checked via HTTPS. CGNAT/VPN may change the observed address.").pack(anchor="w")
  ttk.Label(frame,textvariable=self.status).pack(anchor="w",pady=8)
  self.log=tk.Text(frame,height=10,bg="#19263a",fg="#edf3fa",font=("Consolas",9),wrap="word")
  self.log.pack(fill="both",expand=True)
  self.refresh_adapters();self.refresh_profiles();root.after(100,self.current)
 def output(self,msg):
  self.log.insert("end",msg+"\n");self.log.see("end")
 def refresh_adapters(self):
  try:
   items=adapters();self.adapterbox["values"]=items
   if items and self.adapter.get() not in items:self.adapter.set(items[0])
  except Exception as e:self.output(str(e))
 def refresh_profiles(self):
  names=sorted(self.profiles);self.combo["values"]=names
  if self.profile.get() not in self.profiles and names:self.profile.set(names[0]);self.load()
 def load(self):
  d=self.profiles.get(self.profile.get())
  if not isinstance(d,dict):return
  self.name.set(self.profile.get())
  for k,v in self.values.items():v.set(d.get(k,""))
  self.mode.set("static");self.toggle()
 def new(self):
  self.profile.set("");self.name.set("")
  for v in self.values.values():v.set("")
  self.values["mask"].set("255.255.255.0");self.mode.set("static");self.toggle()
  self.status.set("New profile: enter a unique name, then Save")
 def toggle(self):
  for k in self.values:self.entries[k].configure(state="disabled" if self.mode.get()=="dhcp" else "normal")
 def data(self):return {k:v.get().strip() for k,v in self.values.items()}
 def persist(self):
  APPDIR.mkdir(parents=True,exist_ok=True)
  temp=STORE.with_suffix(".tmp")
  temp.write_text(json.dumps(self.profiles,indent=2,ensure_ascii=False),encoding="utf-8")
  temp.replace(STORE)
 def save(self):
  name=self.name.get().strip()
  if not name or len(name)>80:messagebox.showerror("Profile","Enter a name (max 80 characters)");return
  try:d=check(self.data())
  except Exception as e:messagebox.showerror("Invalid settings",str(e));return
  if name in self.profiles and not messagebox.askyesno("Overwrite?",f"Update existing profile '{name}'?"):return
  try:self.profiles[name]=d;self.persist()
  except Exception as e:messagebox.showerror("Save failed",str(e));return
  self.profile.set(name);self.refresh_profiles();self.status.set("Saved: "+name)
 def delete(self):
  name=self.profile.get()
  if name not in self.profiles:return
  if not messagebox.askyesno("Delete profile",f"Delete '{name}'?"):return
  del self.profiles[name]
  try:self.persist()
  except Exception as e:messagebox.showerror("Save failed",str(e));return
  self.profile.set("");self.refresh_profiles()
 def require_adapter(self):
  name=self.adapter.get()
  if name not in adapters():raise ValueError("Select an available adapter and Refresh")
  return name
 def execute(self,commands,message):
  if not elevated():messagebox.showerror("Administrator required","Run as Administrator");return
  for cmd in commands:
   try:p=command(cmd)
   except Exception as e:messagebox.showerror("Command failed",str(e));return
   self.output("> "+subprocess.list2cmdline(cmd))
   self.output((p.stdout or p.stderr or "").strip())
   if p.returncode:messagebox.showerror("Error","Network update failed or partially applied. See log.");return
  self.status.set(message);self.current();messagebox.showinfo("IP Switcher",message)
 def static(self):
  try:a=self.require_adapter();d=check(self.data())
  except Exception as e:messagebox.showerror("Invalid settings",str(e));return
  if not messagebox.askyesno("Apply Static IP",f"Adapter: {a}\nIP: {d['ip']}\nMask: {d['mask']}\nGateway: {d['gateway'] or 'none'}\nApply?"):return
  b=["netsh","interface","ipv4"]
  address=b+["set","address",f"name={a}","source=static",f"address={d['ip']}",f"mask={d['mask']}",f"gateway={d['gateway'] or 'none'}"]
  if d["dns1"]:
   dns=[b+["set","dnsservers",f"name={a}","source=static",f"address={d['dns1']}","register=primary","validate=no"]]
   if d["dns2"]:dns.append(b+["add","dnsservers",f"name={a}",f"address={d['dns2']}","index=2","validate=no"])
  else:dns=[b+["set","dnsservers",f"name={a}","source=dhcp"]]
  self.execute([address]+dns,"Static IPv4 applied")
 def dhcp(self):
  try:a=self.require_adapter()
  except Exception as e:messagebox.showerror("Adapter",str(e));return
  if not messagebox.askyesno("DHCP",f"Enable automatic IP and DNS on {a}?"):return
  b=["netsh","interface","ipv4"]
  self.execute([b+["set","address",f"name={a}","source=dhcp"],b+["set","dnsservers",f"name={a}","source=dhcp"]],"DHCP enabled")
 def current(self):
  if not self.adapter.get():return
  try:
   p=command(["netsh","interface","ipv4","show","config",f"name={self.adapter.get()}"])
   self.output("--- Current configuration ---\n"+(p.stdout or p.stderr))
  except Exception as e:self.output(str(e))
 def getpublic(self):
  if self.busy:return
  self.busy=True;self.public.set("Checking...");self.publicbutton.configure(state="disabled")
  def job():
   for url in ("https://api.ipify.org","https://ipv4.icanhazip.com"):
    try:
     with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Windows-IP-Switcher/3.0"}),timeout=6) as r:
      ip=str(ipaddress.IPv4Address(r.read(100).decode("ascii").strip()))
     if not ipaddress.IPv4Address(ip).is_global:raise ValueError("Not a public IPv4")
     self.root.after(0,lambda ip=ip:self.publicdone(ip));return
    except Exception:pass
   self.root.after(0,lambda:self.publicdone("Unavailable"))
  threading.Thread(target=job,daemon=True).start()
 def publicdone(self,value):
  self.public.set(value);self.busy=False;self.publicbutton.configure(state="normal")
  self.output("Public IPv4: "+value)
 def copy(self):
  try:ip=ipaddress.IPv4Address(self.public.get())
  except ValueError:messagebox.showinfo("Public IP","Check public IP first");return
  if not ip.is_global:return
  self.root.clipboard_clear();self.root.clipboard_append(str(ip))
  self.status.set("Copied: "+str(ip))
if __name__=="__main__":
 if sys.platform!="win32":raise SystemExit("Windows only")
 admins()
 root=tk.Tk();App(root);root.mainloop()
