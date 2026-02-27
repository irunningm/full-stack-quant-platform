# -*- coding: utf-8 -*-
# main.py
import subprocess
import sys
import os
env = os.environ.copy()

def main():
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    cmd = ["uv", "run", "streamlit", "run", app_path]

    print("启动命令：", " ".join(cmd))
    subprocess.run(cmd, env=env, check=True)

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        env["PYTHONUTF8"] = "1"
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    main()