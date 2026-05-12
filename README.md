# 🤖 Jerry — Your Personal AI Assistant

> Inspired by Jarvis from Iron Man. Built for you.

Jerry is your personal AI companion that lives on your computer. He can chat with you, control your system, monitor resources, manage files, and keep you company — all with personality and humor.

## ⚡ Quick Start

### Prerequisites
1. **Python 3.10+** — [Download](https://python.org)
2. **Ollama** — [Download](https://ollama.com) (Jerry's brain runs locally!)

### Setup

```bash
# 1. Install Ollama and pull the Llama model
ollama pull llama3.2

# 2. Make sure Ollama is running
ollama serve

# 3. Install Jerry's dependencies
cd jerry
pip install -r requirements.txt

# 4. Launch Jerry!
python -m jerry
```

## 🎮 Usage

Just type naturally! Jerry understands conversational language.

```
You › Hey Jerry, what's my CPU usage?
🤖 Jerry › Let me check... Your CPU is at 23% — nice and chill! 😎

You › Open Chrome for me
🤖 Jerry › On it, Boss! ✅ Chrome is opening now.

You › Tell me a joke
🤖 Jerry › Why do programmers prefer dark mode? Because light attracts bugs! 🐛
```

### Special Commands
| Command | Description |
|---------|-------------|
| `help` | Show available commands |
| `status` | Jerry's current stats |
| `memory` | What Jerry remembers about you |
| `tools` | List Jerry's capabilities |
| `clear` | Clear the screen |
| `quit` | Say goodbye |

## 🧠 Architecture

```
jerry/
├── brain/           # Jerry's intelligence
│   ├── llm_engine.py    # Ollama/Llama integration
│   ├── personality.py   # Character & behavior
│   └── memory.py        # SQLite conversation memory
├── tools/           # Jerry's capabilities
│   ├── system_cmd.py    # Open apps, run commands
│   ├── system_info.py   # CPU, RAM, disk monitoring
│   └── file_ops.py      # File search & management
├── ui/              # Interface
│   └── terminal.py      # Rich terminal UI
└── main.py          # Entry point
```

## 🔮 Roadmap
- [x] Core AI brain with personality
- [x] Computer command integration
- [x] System monitoring
- [x] File operations
- [ ] Voice interface (for pocket device)
- [ ] Web search
- [ ] Email & calendar integration
- [ ] Pocket device hardware build

## 💡 Configuration

Edit `config.yaml` to customize Jerry:
- Change what Jerry calls you
- Adjust AI creativity level
- Configure safety settings
- Switch LLM models

---


