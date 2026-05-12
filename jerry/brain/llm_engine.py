"""
Jerry's LLM Engine
Handles communication with Ollama (Llama ai modul) for Jerry's intelligence.
Supports tool/function calling for executing system actions.
"""

import json
import logging
from typing import Optional

try:
    import ollama
except ImportError:
    ollama = None

from jerry.brain.personality import get_system_prompt

logger = logging.getLogger("jerry.brain")


class LLMEngine:
    """Ollama-powered LLM engine for Jerry's brain."""

    def __init__(self, config: dict):
        """
        Initialize the LLM engine.
        
        Args:
            config: LLM configuration from config.yaml
        """
        self.provider = config.get("provider", "ollama")
        self.model = config.get("model", "llama3.2")
        self.temperature = config.get("temperature", 0.8)
        self.max_tokens = config.get("max_tokens", 2048)
        self.ollama_host = config.get("ollama_host", "http://localhost:11434")
        
        # Initialize Ollama client
        if ollama is None:
            raise ImportError(
                "Ollama package is not installed. "
                "Run: pip install ollama"
            )
        
        self.client = ollama.Client(host=self.ollama_host)
        self._verify_connection()

    def _verify_connection(self):
        """Verify Ollama is running and the model is available."""
        try:
            models = self.client.list()
            model_names = [m.model for m in models.models] if hasattr(models, 'models') else []
            
            # Check if our model is available (handle tag variations)
            model_base = self.model.split(":")[0]
            found = any(model_base in name for name in model_names)
            
            if not found:
                logger.warning(
                    f"Model '{self.model}' not found locally. "
                    f"Available models: {model_names}. "
                    f"Jerry will try to pull it on first use."
                )
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.ollama_host}. "
                f"Make sure Ollama is running! "
                f"Download from https://ollama.com and run 'ollama serve'. "
                f"Error: {e}"
            )

    def chat(
        self,
        messages: list[dict],
        user_name: str = "Boss",
        tools: Optional[list[dict]] = None,
    ) -> dict:
        """
        Send a conversation to the LLM and get a response.
        
        Args:
            messages: List of conversation messages [{role, content}]
            user_name: User's name for personalization
            tools: Optional list of tool definitions for function calling
            
        Returns:
            dict with 'content' (text response) and optionally 'tool_calls'
        """
        # Build the full message list with system prompt
        system_prompt = get_system_prompt(user_name)
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            # Prepare chat kwargs
            chat_kwargs = {
                "model": self.model,
                "messages": full_messages,
                "options": {
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            }
            
            # Add tools if provided
            if tools:
                chat_kwargs["tools"] = tools

            response = self.client.chat(**chat_kwargs)
            
            result = {
                "content": response.message.content or "",
                "tool_calls": [],
            }
            
            # Extract tool calls if any
            if hasattr(response.message, "tool_calls") and response.message.tool_calls:
                for tc in response.message.tool_calls:
                    result["tool_calls"].append({
                        "name": tc.function.name,
                        "arguments": tc.function.arguments if hasattr(tc.function, 'arguments') else {},
                    })
            
            return result

        except ollama.ResponseError as e:
            if "not found" in str(e).lower():
                logger.info(f"Model {self.model} not found. Pulling it now...")
                self.client.pull(self.model)
                return self.chat(messages, user_name, tools)
            raise
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return {
                "content": f"Oof, my brain glitched for a second there. Error: {e}",
                "tool_calls": [],
            }

    def chat_stream(
        self,
        messages: list[dict],
        user_name: str = "Boss",
    ):
        """
        Stream a conversation response token by token.
        
        Args:
            messages: List of conversation messages
            user_name: User's name for personalization
            
        Yields:
            str: Individual tokens as they arrive
        """
        system_prompt = get_system_prompt(user_name)
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        try:
            stream = self.client.chat(
                model=self.model,
                messages=full_messages,
                stream=True,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )

            for chunk in stream:
                if chunk.message.content:
                    yield chunk.message.content

        except ollama.ResponseError as e:
            if "not found" in str(e).lower():
                logger.info(f"Model {self.model} not found. Pulling it now...")
                self.client.pull(self.model)
                yield from self.chat_stream(messages, user_name)
            else:
                yield f"\n⚠️ Brain error: {e}"
        except Exception as e:
            yield f"\n⚠️ Oops, something went wrong: {e}"
