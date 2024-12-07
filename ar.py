import subprocess
import time
import sys
from rich.console import Console
from rich.text import Text
from datetime import datetime

# Rich console for styled output
console = Console()

# Define the banner text
banner = """\
  ('-.      .-')    ('-. .-.             
  ( OO ).-. ( OO ). ( OO )  /             
  / . --. /(_)---\_),--. ,--. ,--. ,--.  
  | \-.  \ /    _ | |  | |  | |  | |  |  
.-'-'  |  |\  :` `. |   .|  | |  | | .-')
 \| |_.'  | '..`''.)|       | |  |_|( OO )
  |  .-.  |.-._)   \|  .-.  | |  | | `-' /
  |  | |  |\       /|  | |  |('  '-'(_.-' 
  `--' `--' `-----' `--' `--'  `-----'   
"""

# Split the banner into lines for animated display
banner_lines = banner.splitlines()

def animate_banner():
    """Display the banner with animation."""
    for i in range(len(banner_lines) + 1):
        console.clear()  # Clear the console
        text = Text("\n".join(banner_lines[:i]), style="bold green")
        console.print(text)
        time.sleep(0.2)  # Add a delay for animation effect

def log(message):
    """Log messages with timestamps."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def run_script(target_script):
    """Run the target Python script."""
    try:
        process = subprocess.Popen([sys.executable, target_script])
        log(f"Started {target_script} with PID: {process.pid}")
        return process
    except Exception as e:
        log(f"Error running {target_script}: {e}")
        return None

def main():
    animate_banner()  # Display the animated banner

    target_script = str(input('Script name (e.g., grass.py): '))
    restart_time = int(input('Input restart time in minutes (min 1 minute): '))

    if not target_script.endswith(".py"):
        log("Please enter a valid Python script name ending with .py.")
        sys.exit(1)

    if restart_time < 1:
        log("Restart time must be at least 1 minute.")
        sys.exit(1)

    while True:
        process = run_script(target_script)
        if process:
            try:
                time.sleep(restart_time * 60)
            finally:
                log(f"Terminating {target_script} after {restart_time} minutes.")
                process.terminate()
                process.wait(timeout=5)
                if process.poll() is None:  # If still running, force kill
                    process.kill()
                    log(f"{target_script} was forcefully killed.")
        else:
            log("Failed to start the script. Retrying in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Script execution stopped by user.")
        sys.exit(0)
