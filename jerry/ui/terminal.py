"""
Jerry's Terminal UI
Beautiful, colorful terminal interface using the Rich library.
"""

import time
import logging
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.live import Live
    from rich.layout import Layout
    from rich.align import Align
    from rich import box
except ImportError:
    raise ImportError("Rich library is required. Run: pip install rich")

logger = logging.getLogger("jerry.ui")

# Jerry's color scheme
JERRY_COLOR = "cyan"
USER_COLOR = "green"
SYSTEM_COLOR = "yellow"
ERROR_COLOR = "red"
TOOL_COLOR = "magenta"

JERRY_LOGO = r"""
       ██╗███████╗██████╗ ██████╗ ██╗   ██╗
       ██║██╔════╝██╔══██╗██╔══██╗╚██╗ ██╔╝
       ██║█████╗  ██████╔╝██████╔╝ ╚████╔╝ 
  ██   ██║██╔══╝  ██╔══██╗██╔══██╗  ╚██╔╝  
  ╚█████╔╝███████╗██║  ██║██║  ██║   ██║   
   ╚════╝ ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   
"""

JERRY_MINI = "🤖"


class TerminalUI:
    """Rich terminal interface for Jerry."""

    def __init__(self):
        self.console = Console()

    def show_startup(self, greeting: str, version: str = "0.1.0"):
        """Display Jerry's startup screen."""
        self.console.clear()
        
        # Logo
        logo_text = Text(JERRY_LOGO, style=f"bold {JERRY_COLOR}")
        self.console.print(Align.center(logo_text))
        
        # Subtitle
        subtitle = Text("Your Personal AI Assistant", style="italic dim")
        self.console.print(Align.center(subtitle))
        self.console.print(Align.center(Text(f"v{version}", style="dim")))
        self.console.print()
        
        # Greeting panel
        self.console.print(
            Panel(
                Text(greeting, style=JERRY_COLOR),
                title=f"{JERRY_MINI} Jerry",
                title_align="left",
                border_style=JERRY_COLOR,
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        self.console.print()
        
        # Help hint
        self.console.print(
            Text(
                "  💡 Type your message, or try: 'help', 'status', 'quit'",
                style="dim",
            )
        )
        self.console.print()

    def get_user_input(self) -> str:
        """Get input from the user with a styled prompt."""
        try:
            self.console.print(Text(f"  You ", style=f"bold {USER_COLOR}"), end="")
            user_input = self.console.input(Text("› ", style=f"bold {USER_COLOR}"))
            return user_input.strip()
        except (EOFError, KeyboardInterrupt):
            return "quit"

    def show_jerry_message(self, message: str):
        """Display a message from Jerry."""
        self.console.print()
        self.console.print(
            Panel(
                Markdown(message),
                title=f"{JERRY_MINI} Jerry",
                title_align="left",
                border_style=JERRY_COLOR,
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )
        self.console.print()

    def show_jerry_streaming(self, token_generator):
        """
        Display Jerry's response as it streams in, token by token.
        
        Args:
            token_generator: Generator yielding tokens
            
        Returns:
            str: Complete response text
        """
        self.console.print()
        full_response = ""
        
        self.console.print(
            Text(f"  {JERRY_MINI} Jerry › ", style=f"bold {JERRY_COLOR}"),
            end="",
        )
        
        for token in token_generator:
            full_response += token
            self.console.print(token, end="", highlight=False)
        
        self.console.print()  # Newline after streaming
        self.console.print()
        
        return full_response

    def show_tool_execution(self, tool_name: str, result: str):
        """Show a tool execution result."""
        self.console.print(
            Panel(
                Text(result),
                title=f"⚡ {tool_name}",
                title_align="left",
                border_style=TOOL_COLOR,
                box=box.SIMPLE,
                padding=(0, 1),
            )
        )

    def show_system_message(self, message: str):
        """Display a system/info message."""
        self.console.print(
            Text(f"  ℹ️  {message}", style=f"dim {SYSTEM_COLOR}")
        )

    def show_error(self, message: str):
        """Display an error message."""
        self.console.print(
            Text(f"  ❌ {message}", style=f"bold {ERROR_COLOR}")
        )

    def show_thinking(self):
        """Show a thinking indicator."""
        self.console.print(
            Text(f"  {JERRY_MINI} Thinking...", style=f"dim {JERRY_COLOR}"),
            end="\r",
        )

    def show_status_panel(self, stats: dict):
        """Show a status panel with memory/system stats."""
        table = Table(
            title="📊 Jerry Status",
            box=box.ROUNDED,
            border_style=JERRY_COLOR,
            show_header=True,
            header_style=f"bold {JERRY_COLOR}",
        )
        
        table.add_column("Metric", style="bold")
        table.add_column("Value", style=JERRY_COLOR)
        
        for key, value in stats.items():
            # Make key human readable
            display_key = key.replace("_", " ").title()
            table.add_row(display_key, str(value))
        
        self.console.print()
        self.console.print(table)
        self.console.print()

    def show_help(self):
        """Display help information."""
        help_text = """
**Commands:**
• Just type naturally to chat with Jerry
• `status` — Show Jerry's current stats
• `memory` — Show what Jerry remembers about you
• `tools` — List available tools
• `clear` — Clear the screen
• `quit` or `exit` — Say goodbye to Jerry

**Things you can ask Jerry to do:**
• "Open Chrome" — Launch applications
• "What's my CPU usage?" — System monitoring
• "Search for files named report" — Find files
• "What time is it?" — Quick info
• "Take a screenshot" — Capture screen
• "Tell me a joke" — Just hang out! 😄
"""
        self.console.print(
            Panel(
                Markdown(help_text),
                title="📖 Help",
                title_align="left",
                border_style="blue",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    def show_goodbye(self):
        """Display goodbye message."""
        self.console.print()
        self.console.print(
            Panel(
                Text(
                    "Catch you later, Boss! Stay awesome. 🫡",
                    style=f"bold {JERRY_COLOR}",
                    justify="center",
                ),
                border_style=JERRY_COLOR,
                box=box.DOUBLE,
                padding=(1, 2),
            )
        )
        self.console.print()
