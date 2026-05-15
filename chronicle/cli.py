"""CLI: chronicle <command> <agent> [args]

Usage:
    chronicle run oracle1          # 10-minute check-in loop
    chronicle report oracle1 "msg" # File one report
    chronicle serve                # Start HTTP server
    chronicle gc oracle1           # Run summarization
"""

from .core import Chronicle
import time, os, sys, subprocess
from http.server import HTTPServer, SimpleHTTPRequestHandler

def cmd_run(args):
    name = args[0] if args else "default"
    c = Chronicle(name)
    n = 0
    print(f"📋 {name} — chronicle running (every 10 min)")
    while True:
        n += 1
        # Gather quick status
        report = f"Check-in #{n}"
        try:
            r = subprocess.run(["git", "log", "--since=10 minutes ago", "--oneline", "--format=%s"],
                capture_output=True, text=True, timeout=5,
                cwd=os.path.dirname(os.path.dirname(__file__)))
            if r.stdout.strip():
                lines = r.stdout.strip().split("\n")[:3]
                report += "\n" + "\n".join(f"  • {l[:70]}" for l in lines)
        except:
            pass
        c.check_in(report)
        if n % 288 == 0:
            c.summarize()
        if n % 144 == 0:
            c.generate_html()
        ts = time.strftime("%H:%M")
        c.generate_html()
        print(f"  #{n} {ts}")
        time.sleep(600)

def cmd_report(args):
    if len(args) < 1:
        print("Usage: chronicle report <agent> <message>")
        return
    name = args[0]
    msg = " ".join(args[1:]) if len(args) > 1 else "(no message)"
    c = Chronicle(name)
    cid = c.check_in(msg)
    c.generate_html()
    print(f"{name}: #{cid} — {msg[:60]}")

def cmd_serve(args):
    port = int(args[0]) if args and args[0].isdigit() else 4051
    # Generate all agent HTML
    base = os.path.dirname(os.path.dirname(__file__))
    for entry in os.listdir(base):
        if os.path.isdir(os.path.join(base, entry)) and not entry.startswith(".") and not entry.startswith("_"):
            try:
                Chronicle(entry).generate_html()
            except:
                pass

    os.chdir(base)
    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    print(f"Serving fleet-chronicle on http://localhost:{port}")
    HTTPServer(("", port), Handler).serve_forever()

def cmd_gc(args):
    name = args[0] if args else "default"
    c = Chronicle(name)
    result = c.summarize()
    print(f"GC {name}: {result} entries")
    c.generate_html()

def cmd_list(args):
    base = os.path.dirname(os.path.dirname(__file__))
    agents = [d for d in os.listdir(base)
              if os.path.isdir(os.path.join(base, d))
              and not d.startswith((".", "_"))
              and d != "chronicle"]
    print(f"Agents with chronicles: {len(agents)}")
    for a in sorted(agents):
        c = Chronicle(a)
        entries = c._read_entries()
        if entries:
            last = entries[-1]["date"][:16]
            print(f"  {a:20s} {len(entries):4d} entries, last: {last}")
        else:
            print(f"  {a:20s}  (empty)")

def main():
    if len(sys.argv) < 2:
        print("Usage: chronicle <command> [agent] [args]")
        print("  run <agent>         10-minute check-in loop")
        print("  report <agent> msg  File one report")
        print("  serve [port]        Start HTTP server")
        print("  gc <agent>          Run summarization")
        print("  list                List all agent chronicles")
        return
    cmd = sys.argv[1]
    args = sys.argv[2:]
    {
        "run": cmd_run,
        "report": cmd_report,
        "serve": cmd_serve,
        "gc": cmd_gc,
        "list": cmd_list,
    }.get(cmd, lambda _: print(f"Unknown: {cmd}"))(args)

if __name__ == "__main__":
    main()
