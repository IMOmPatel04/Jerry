"""
Jerry's System Command Tool
Lets Jerry open apps, run commands, and control the computer.
"""

import subprocess
import os
import logging
import shutil
from typing import Optional

from jerry.tools.base import Tool

logger = logging.getLogger("jerry.tools.system_cmd")

# Common Windows applications and their paths/commands
KNOWN_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "task manager": "taskmgr.exe",
    "control panel": "control.exe",
    "settings": "ms-settings:",
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "code": "code",
    "vs code": "code",
    "visual studio code": "code",
    "spotify": "spotify",
    "discord": "discord",
    "slack": "slack",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "teams": "teams",
}

# Dangerous commands that should be blocked or confirmed
DANGEROUS_PATTERNS = [
    "format", "del /s", "rmdir /s", "rm -rf",
    "shutdown", "restart", "logoff",
    "reg delete", "regedit",
    "net user", "net localgroup",
    "cipher /w",
]


class OpenAppTool(Tool):
    """Tool to open applications by name."""

    name = "open_application"
    description = "Open an application on the computer by its name. Examples: 'Chrome', 'Notepad', 'VS Code', 'Calculator'"

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the application to open (e.g., 'Chrome', 'Notepad', 'VS Code')",
                },
            },
            "required": ["app_name"],
        }

    def execute(self, app_name: str) -> str:
        app_lower = app_name.lower().strip()
        
        # Check known apps first
        command = KNOWN_APPS.get(app_lower)
        
        if command:
            try:
                if command.startswith("ms-"):
                    # Windows URI scheme
                    os.startfile(command)
                else:
                    subprocess.Popen(
                        command,
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                return f"✅ Opened {app_name} successfully."
            except Exception as e:
                return f"❌ Couldn't open {app_name}: {e}"
        
        # Try to find the app via `where` command (Windows)
        try:
            result = subprocess.run(
                ["where", app_lower],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                app_path = result.stdout.strip().split("\n")[0]
                subprocess.Popen(app_path, shell=True)
                return f"✅ Found and opened {app_name} at {app_path}."
        except Exception:
            pass
        
        # Last resort: try start command
        try:
            subprocess.Popen(
                f'start "" "{app_lower}"',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return f"✅ Attempted to open {app_name}. If it doesn't open, the app might not be installed."
        except Exception as e:
            return f"❌ I couldn't find {app_name} on your system. Is it installed? Error: {e}"


class RunCommandTool(Tool):
    """Tool to run shell commands."""

    name = "run_command"
    description = "Run a shell command on the computer. Use for quick system tasks like checking the date, listing files, etc. DO NOT use for dangerous operations without user confirmation."

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The command to execute in PowerShell",
                },
            },
            "required": ["command"],
        }

    def execute(self, command: str) -> str:
        # Safety check
        cmd_lower = command.lower()
        for pattern in DANGEROUS_PATTERNS:
            if pattern in cmd_lower:
                return (
                    f"⚠️ BLOCKED: The command '{command}' looks dangerous (matches pattern: '{pattern}'). "
                    f"I won't run this without explicit confirmation. "
                    f"If you really want to run this, tell me and I'll reconsider."
                )
        
        try:
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.expanduser("~"),
            )
            
            output = result.stdout.strip()
            error = result.stderr.strip()
            
            if result.returncode == 0:
                if output:
                    # Truncate very long outputs
                    if len(output) > 2000:
                        output = output[:2000] + "\n... (output truncated)"
                    return f"✅ Command executed successfully:\n{output}"
                else:
                    return "✅ Command executed successfully (no output)."
            else:
                return f"❌ Command failed (exit code {result.returncode}):\n{error or output}"

        except subprocess.TimeoutExpired:
            return "⏰ Command timed out after 30 seconds. It might still be running in the background."
        except Exception as e:
            return f"❌ Error running command: {e}"


class SystemControlTool(Tool):
    """Tool for system-level operations like lock, volume, etc."""

    name = "system_control"
    description = "Control system functions: lock screen, adjust volume, take a screenshot, get current time, etc."

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action to perform: 'lock', 'screenshot', 'time', 'date', 'volume_up', 'volume_down', 'volume_mute'",
                    "enum": ["lock", "screenshot", "time", "date", "volume_up", "volume_down", "volume_mute"],
                },
            },
            "required": ["action"],
        }

    def execute(self, action: str) -> str:
        import datetime

        action = action.lower().strip()
        
        if action == "time":
            now = datetime.datetime.now()
            return f"🕐 Current time: {now.strftime('%I:%M %p')} ({now.strftime('%H:%M:%S')})"
        
        elif action == "date":
            now = datetime.datetime.now()
            return f"📅 Today is {now.strftime('%A, %B %d, %Y')}"
        
        elif action == "lock":
            try:
                subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
                return "🔒 Locking your computer now."
            except Exception as e:
                return f"❌ Couldn't lock: {e}"
        
        elif action == "screenshot":
            try:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshots_dir = os.path.join(os.path.expanduser("~"), "Pictures", "Jerry_Screenshots")
                os.makedirs(screenshots_dir, exist_ok=True)
                filepath = os.path.join(screenshots_dir, f"jerry_screenshot_{timestamp}.png")
                
                # Use PowerShell to take screenshot
                ps_script = f"""
                Add-Type -AssemblyName System.Windows.Forms
                [System.Windows.Forms.Screen]::PrimaryScreen | ForEach-Object {{
                    $bitmap = New-Object System.Drawing.Bitmap($_.Bounds.Width, $_.Bounds.Height)
                    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                    $graphics.CopyFromScreen($_.Bounds.Location, [System.Drawing.Point]::Empty, $_.Bounds.Size)
                    $bitmap.Save('{filepath}')
                    $graphics.Dispose()
                    $bitmap.Dispose()
                }}
                """
                subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=10)
                return f"📸 Screenshot saved to: {filepath}"
            except Exception as e:
                return f"❌ Screenshot failed: {e}"
        
        elif action in ("volume_up", "volume_down", "volume_mute"):
            try:
                key_map = {
                    "volume_up": "0xAF",
                    "volume_down": "0xAE",
                    "volume_mute": "0xAD",
                }
                vk_code = key_map[action]
                ps_cmd = f"""
                $wshell = New-Object -ComObject wscript.shell
                $wshell.SendKeys([char]{vk_code})
                """
                # Use nircmd approach for reliability
                if action == "volume_up":
                    subprocess.run(
                        ["powershell", "-Command",
                         "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"],
                        capture_output=True, timeout=5
                    )
                    return "🔊 Volume up!"
                elif action == "volume_down":
                    subprocess.run(
                        ["powershell", "-Command",
                         "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"],
                        capture_output=True, timeout=5
                    )
                    return "🔉 Volume down!"
                elif action == "volume_mute":
                    subprocess.run(
                        ["powershell", "-Command",
                         "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"],
                        capture_output=True, timeout=5
                    )
                    return "🔇 Volume toggled mute!"
            except Exception as e:
                return f"❌ Volume control error: {e}"
        
        return f"❓ Unknown action: {action}"
