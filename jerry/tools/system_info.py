"""
Jerry's System Info Tool
Monitors system resources — CPU, RAM, disk, battery, etc.
"""

import platform
import datetime
import logging

try:
    import psutil
except ImportError:
    psutil = None

from jerry.tools.base import Tool

logger = logging.getLogger("jerry.tools.system_info")


class SystemInfoTool(Tool):
    """Tool to get system information and resource usage."""

    name = "get_system_info"
    description = "Get information about the computer's current state: CPU usage, RAM, disk space, battery, running processes, network status, or a full system overview."

    def get_parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "info_type": {
                    "type": "string",
                    "description": "Type of info: 'overview', 'cpu', 'memory', 'disk', 'battery', 'network', 'processes', 'uptime'",
                    "enum": ["overview", "cpu", "memory", "disk", "battery", "network", "processes", "uptime"],
                },
            },
            "required": ["info_type"],
        }

    def execute(self, info_type: str) -> str:
        if psutil is None:
            return "❌ psutil is not installed. Run: pip install psutil"

        info_type = info_type.lower().strip()

        if info_type == "overview":
            return self._get_overview()
        elif info_type == "cpu":
            return self._get_cpu()
        elif info_type == "memory":
            return self._get_memory()
        elif info_type == "disk":
            return self._get_disk()
        elif info_type == "battery":
            return self._get_battery()
        elif info_type == "network":
            return self._get_network()
        elif info_type == "processes":
            return self._get_top_processes()
        elif info_type == "uptime":
            return self._get_uptime()
        else:
            return f"Unknown info type: {info_type}"

    def _get_overview(self) -> str:
        """Full system overview."""
        parts = [
            "📊 **System Overview**",
            f"  🖥️  OS: {platform.system()} {platform.release()} ({platform.version()})",
            f"  💻 Machine: {platform.machine()}",
            f"  🏷️  Hostname: {platform.node()}",
            "",
            self._get_cpu(),
            "",
            self._get_memory(),
            "",
            self._get_disk(),
            "",
            self._get_battery(),
            "",
            self._get_uptime(),
        ]
        return "\n".join(parts)

    def _get_cpu(self) -> str:
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        freq_str = f"{cpu_freq.current:.0f}MHz" if cpu_freq else "N/A"
        
        status = "😴 Idle" if cpu_percent < 20 else "🟢 Normal" if cpu_percent < 60 else "🟡 Busy" if cpu_percent < 85 else "🔴 Heavy load!"
        
        return f"🧠 CPU: {cpu_percent}% usage ({cpu_count} cores @ {freq_str}) — {status}"

    def _get_memory(self) -> str:
        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024 ** 3)
        total_gb = mem.total / (1024 ** 3)
        
        status = "🟢 Plenty free" if mem.percent < 50 else "🟡 Getting used" if mem.percent < 80 else "🔴 Running low!"
        
        return f"💾 RAM: {used_gb:.1f}GB / {total_gb:.1f}GB ({mem.percent}%) — {status}"

    def _get_disk(self) -> str:
        partitions = psutil.disk_partitions()
        parts = ["💿 Disk Usage:"]
        
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                used_gb = usage.used / (1024 ** 3)
                total_gb = usage.total / (1024 ** 3)
                free_gb = usage.free / (1024 ** 3)
                
                status = "🟢" if usage.percent < 70 else "🟡" if usage.percent < 90 else "🔴"
                
                parts.append(
                    f"  {status} {partition.mountpoint} — "
                    f"{used_gb:.1f}GB / {total_gb:.1f}GB ({usage.percent}%) "
                    f"[{free_gb:.1f}GB free]"
                )
            except PermissionError:
                continue
        
        return "\n".join(parts)

    def _get_battery(self) -> str:
        battery = psutil.sensors_battery()
        if battery is None:
            return "🔌 Battery: Desktop PC (no battery)"
        
        plugged = "🔌 Plugged in" if battery.power_plugged else "🔋 On battery"
        
        if battery.percent > 80:
            status = "🟢"
        elif battery.percent > 30:
            status = "🟡"
        else:
            status = "🔴 Low!"
        
        time_left = ""
        if battery.secsleft > 0 and not battery.power_plugged:
            hours = battery.secsleft // 3600
            mins = (battery.secsleft % 3600) // 60
            time_left = f" — ~{hours}h {mins}m remaining"
        
        return f"🔋 Battery: {battery.percent}% {status} ({plugged}){time_left}"

    def _get_network(self) -> str:
        net = psutil.net_io_counters()
        sent_mb = net.bytes_sent / (1024 ** 2)
        recv_mb = net.bytes_recv / (1024 ** 2)
        
        connections = len(psutil.net_connections())
        
        return (
            f"🌐 Network: {connections} active connections\n"
            f"  📤 Sent: {sent_mb:.1f} MB | 📥 Received: {recv_mb:.1f} MB (this session)"
        )

    def _get_top_processes(self, limit: int = 10) -> str:
        """Get top processes by CPU usage."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
        
        parts = [f"📋 Top {limit} Processes (by CPU):"]
        for i, proc in enumerate(processes[:limit], 1):
            cpu = proc.get('cpu_percent', 0) or 0
            mem = proc.get('memory_percent', 0) or 0
            name = proc.get('name', 'Unknown')
            parts.append(f"  {i:2}. {name:<30} CPU: {cpu:5.1f}%  RAM: {mem:5.1f}%")
        
        return "\n".join(parts)

    def _get_uptime(self) -> str:
        boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot_time
        
        days = uptime.days
        hours = uptime.seconds // 3600
        mins = (uptime.seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        parts.append(f"{hours}h {mins}m")
        
        return f"⏱️ Uptime: {' '.join(parts)} (booted: {boot_time.strftime('%b %d, %I:%M %p')})"
