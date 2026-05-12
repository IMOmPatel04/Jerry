"""
Jerry AI Assistant — Main Entry Point
Wires together the brain, tools, memory, and UI into one cohesive assistant.
"""

import os
import sys
# Force UTF-8 output on Windows to prevent UnicodeEncodeError in logs/print
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    # stdout/stderr might be redirected or not support reconfigure (e.g. in some IDEs)
    pass

import yaml
import logging
from pathlib import Path

from jerry.brain.llm_engine import LLMEngine
from jerry.brain.memory import Memory
from jerry.brain.personality import get_greeting, get_system_prompt
from jerry.tools.base import ToolRegistry
from jerry.tools.system_cmd import OpenAppTool, RunCommandTool, SystemControlTool
from jerry.tools.system_info import SystemInfoTool
from jerry.tools.file_ops import SearchFilesTool, ReadFileTool, ListDirectoryTool, CopyFileTool, MoveFileTool, DeleteFileTool, CreateFileTool, WriteFileTool
from jerry.tools.web_search import WebSearchTool
from jerry.ui.terminal import TerminalUI

# Set up logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "jerry.log", encoding='utf-8'),
    ],
    force=True,
)
logger = logging.getLogger("jerry")


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    if not config_path.exists():
        logger.warning(f"Config not found at {config_path}, using defaults")
        return {
            "user": {"name": "Boss"},
            "llm": {
                "provider": "ollama",
                "model": "llama3.2",
                "temperature": 0.8,
                "max_tokens": 2048,
                "ollama_host": "http://localhost:11434",
            },
            "memory": {
                "database_path": "jerry_memory.db",
                "short_term_limit": 20,
            },
            "ui": {
                "show_tool_outputs": False,
                "show_system_messages": True,
            },
        }
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


class Jerry:
    """
    Jerry — Your Personal AI Assistant.
    The main class that ties everything together.
    """

    def __init__(self):
        """Initialize Jerry and all his subsystems."""
        self.config = load_config()
        self.user_name = self.config.get("user", {}).get("name", "Boss")
        self.show_tool_outputs = self.config.get("ui", {}).get("show_tool_outputs", False)
        self.show_system_messages = self.config.get("ui", {}).get("show_system_messages", True)
        
        # Initialize UI first so we can show errors nicely
        self.ui = TerminalUI()
        
        # Initialize the brain
        try:
            self.engine = LLMEngine(self.config.get("llm", {}))
        except (ImportError, ConnectionError) as e:
            self.ui.show_error(str(e))
            self.ui.show_error(
                "Jerry needs Ollama running to work! "
                "Install from https://ollama.com then run 'ollama serve'"
            )
            sys.exit(1)
        
        # Initialize memory
        db_path = self.config.get("memory", {}).get("database_path", "jerry_memory.db")
        short_term = self.config.get("memory", {}).get("short_term_limit", 20)
        self.memory = Memory(db_path=db_path, short_term_limit=short_term)
        
        # Initialize tools
        self.tools = ToolRegistry()
        self._register_tools()
        
        logger.info("Jerry initialized successfully!")

    def _register_tools(self):
        """Register all available tools."""
        # Resolve sandbox directory for write-restricted tools
        sandbox_rel = self.config.get("safety", {}).get("sandbox_directory", "testFile")
        sandbox_dir = str((Path(__file__).parent.parent / sandbox_rel).resolve())
        Path(sandbox_dir).mkdir(parents=True, exist_ok=True)
        logger.info(f"Sandbox directory: {sandbox_dir}")

        self.tools.register(OpenAppTool())
        self.tools.register(RunCommandTool())
        self.tools.register(SystemControlTool())
        self.tools.register(SystemInfoTool())
        self.tools.register(SearchFilesTool())
        self.tools.register(ReadFileTool())
        self.tools.register(ListDirectoryTool())
        self.tools.register(CopyFileTool(sandbox_dir=sandbox_dir))
        self.tools.register(MoveFileTool(sandbox_dir=sandbox_dir))
        self.tools.register(DeleteFileTool(sandbox_dir=sandbox_dir))
        self.tools.register(CreateFileTool(sandbox_dir=sandbox_dir))
        self.tools.register(WriteFileTool(sandbox_dir=sandbox_dir))
        self.tools.register(WebSearchTool())
        
        logger.info(f"Registered {len(self.tools.list_tools())} tools")

    def _handle_special_commands(self, user_input: str) -> bool:
        """
        Handle special UI commands.
        
        Returns:
            True if the command was handled (don't send to LLM)
        """
        cmd = user_input.lower().strip()
        
        if cmd in ("quit", "exit", "bye", "goodbye"):
            # Save session before exiting
            if len(self.memory.current_messages) > 2:
                self.memory.save_session_summary(
                    f"Conversation with {len(self.memory.current_messages)} messages."
                )
            self.ui.show_goodbye()
            sys.exit(0)
        
        elif cmd == "help":
            self.ui.show_help()
            return True
        
        elif cmd == "status":
            stats = self.memory.get_stats()
            tools = self.tools.list_tools()
            stats["available_tools"] = len(tools)
            stats["llm_model"] = self.config.get("llm", {}).get("model", "unknown")
            self.ui.show_status_panel(stats)
            return True
        
        elif cmd == "memory":
            facts = self.memory.get_user_facts()
            if facts:
                self.ui.show_jerry_message(
                    "Here's what I remember about you:\n\n"
                    + "\n".join(f"- **{f['category']}**: {f['fact']}" for f in facts)
                )
            else:
                self.ui.show_jerry_message(
                    "I don't have any saved facts about you yet. "
                    "As we chat more, I'll start remembering things! 🧠"
                )
            return True
        
        elif cmd == "tools":
            tools_list = self.tools.list_tools()
            msg = "Here are my current capabilities:\n\n"
            for t in tools_list:
                msg += f"- **{t['name']}**: {t['description']}\n"
            self.ui.show_jerry_message(msg)
            return True
        
        elif cmd == "clear":
            self.ui.console.clear()
            return True
        
        return False

    def chat(self, user_input: str):
        """
        Process a user message and generate Jerry's response.
        This is the main conversation loop logic.
        """
        # Add user message to memory
        self.memory.add_message("user", user_input)
        
        # Build context with memory
        messages = self.memory.get_context_messages()
        
        # Add memory context (user facts, past summaries) to the first message
        memory_context = self.memory.get_memory_context()
        if memory_context:
            # Prepend memory context as a system-like user message
            context_msg = {
                "role": "system",
                "content": f"[Memory Context]\n{memory_context}"
            }
            messages = [context_msg] + messages
        
        # Get tool definitions
        tool_defs = self.tools.get_all_tool_definitions()
        
        # Show thinking indicator
        self.ui.show_thinking()
        
        # Send to LLM with tool support
        response = self.engine.chat(
            messages=messages,
            user_name=self.user_name,
            tools=tool_defs if tool_defs else None,
        )
        
        # Handle tool calls
        if response.get("tool_calls"):
            tool_results = []
            for tool_call in response["tool_calls"]:
                tool_name = tool_call["name"]
                tool_args = tool_call.get("arguments", {})
                
                if self.show_system_messages:
                    self.ui.show_system_message(f"Using tool: {tool_name}...")
                
                result = self.tools.execute_tool(tool_name, tool_args)
                
                if self.show_tool_outputs:
                    self.ui.show_tool_execution(tool_name, result)
                
                tool_results.append({
                    "role": "tool",
                    "content": f"[Tool: {tool_name}] Result:\n{result}",
                })
            
            # Send tool results back to LLM for a natural response
            follow_up_messages = messages + [
                {"role": "assistant", "content": response.get("content", "")},
            ] + tool_results
            
            follow_up = self.engine.chat(
                messages=follow_up_messages,
                user_name=self.user_name,
            )
            
            jerry_response = follow_up.get("content", "Done!")
        else:
            jerry_response = response.get("content", "...")
        
        # Display Jerry's response
        if jerry_response.strip():
            self.ui.show_jerry_message(jerry_response)
        
        # Save to memory
        self.memory.add_message("assistant", jerry_response)

    def run(self):
        """Main loop — start Jerry and begin the conversation."""
        # Show startup
        greeting = get_greeting(self.user_name)
        self.ui.show_startup(greeting, version="0.1.0")
        
        # Main conversation loop
        while True:
            try:
                user_input = self.ui.get_user_input()
                
                if not user_input:
                    continue
                
                # Check for special commands
                if self._handle_special_commands(user_input):
                    continue
                
                # Normal conversation
                self.chat(user_input)
                
            except KeyboardInterrupt:
                self.ui.show_system_message("\nInterrupted! Type 'quit' to exit.")
            except Exception as e:
                logger.exception("Unexpected error")
                self.ui.show_error(f"Something went wrong: {e}")
                self.ui.show_system_message("Don't worry, I'm still here. Try again!")


def main():
    """Entry point for Jerry."""
    jerry = Jerry()
    jerry.run()


if __name__ == "__main__":
    main()
