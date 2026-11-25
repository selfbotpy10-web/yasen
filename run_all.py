import os
import sys
import time
import signal
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))

processes = []

def start_process(name, command):
    print(f"Starting {name}...", flush=True)
    p = subprocess.Popen(command, cwd=ROOT)
    processes.append((name, p))
    return p

def stop_all():
    for name, p in processes:
        if p.poll() is None:
            print(f"Stopping {name}...", flush=True)
            p.terminate()

    for name, p in processes:
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()

def shutdown(signum, frame):
    stop_all()
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

try:
    bot = start_process("YASEN BOT", [sys.executable, "bot.py"])
    niro = start_process("NIRO SELF PANEL", [sys.executable, "niro/self_panel.py"])

    print("Both processes started.", flush=True)

    while True:
        for name, p in processes:
            code = p.poll()

            if code is not None:
                print(f"{name} stopped with exit code {code}", flush=True)
                stop_all()
                sys.exit(code if code else 1)

        time.sleep(3)

except KeyboardInterrupt:
    stop_all()

except Exception as e:
    print("ERROR:", e, flush=True)
    stop_all()
    sys.exit(1)
