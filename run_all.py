import subprocess
import sys
import time
import signal

processes = []

def stop_all():
    for process in processes:
        if process.poll() is None:
            process.terminate()

def main():
    jobs = [
        [sys.executable, "-u", "bot.py"],
        [sys.executable, "-u", "niro/self_panel.py"],
    ]

    try:
        for job in jobs:
            processes.append(subprocess.Popen(job))
            print("Started:", " ".join(job), flush=True)

        while True:
            for process in processes:
                code = process.poll()
                if code is not None:
                    print("A process stopped:", code, flush=True)
                    stop_all()
                    return code
            time.sleep(2)

    except KeyboardInterrupt:
        stop_all()
        return 0
    finally:
        stop_all()

if __name__ == "__main__":
    sys.exit(main())
