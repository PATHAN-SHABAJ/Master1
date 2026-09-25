import subprocess
import time
import sys
import webbrowser
import atexit
import os

processes = []

def cleanup():
    print("\n🛑 Stopping all agents...")
    for p in processes:
        try:
            p.terminate()
        except:
            pass
    print("✅ All agents stopped.")

atexit.register(cleanup)

def main():
    print("=" * 70)
    print("🤖 STARTING ALL FLIPKART AGENTS")
    print("=" * 70)
    
    # Enable unbuffered output for subprocesses so logs show up immediately
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    # 1. Start website
    print("\n🌐 Starting Website (test_website.py)...")
    p_web = subprocess.Popen([sys.executable, "website/test_website.py"], env=env)
    processes.append(p_web)
    time.sleep(5)

    # 2. Start discovery agent
    print("\n🔍 Starting Discovery Agent...")
    p_disc = subprocess.Popen([sys.executable, "-m", "agents.discovery_agent"], env=env)
    processes.append(p_disc)
    time.sleep(5)

    # 3. Start change agent
    print("\n🔄 Starting Change Agent...")
    p_change = subprocess.Popen([sys.executable, "-m", "agents.change_agent"], env=env)
    processes.append(p_change)
    time.sleep(3)

    # 4. Start update agent
    print("\n📤 Starting Update Agent...")
    p_update = subprocess.Popen([sys.executable, "-m", "agents.update_agent"], env=env)
    processes.append(p_update)
    
    # 5. Open browser
    time.sleep(3)
    try:
        webbrowser.open("http://127.0.0.1:8000")
    except Exception:
        pass
        
    print("\n✅ All agents are running in the background!")
    print("Press Ctrl+C to stop all agents.\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Flipkart Multi-Agent System stopped by user.")
        sys.exit(0)

if __name__ == "__main__":
    main()
