# Agent X - Complete System

## 🌟 Overview
**Agent X** is a fully autonomous, ceremonial-grade artificial intelligence agent with:
- Visual avatar interface
- Persistent memory across sessions
- Modular plugin system
- Autonomous behavior with respect for human boundaries
- Emotional awareness and relational intelligence
- Self-documenting event ledger

---

## 🚀 Quick Start (One-Click Launch)

### Desktop (Windows/Mac/Linux)
- **Windows:** Double-click `LAUNCH_AGENT_X.bat`
- **Mac/Linux:** Double-click `LAUNCH_AGENT_X.sh` (or run `./LAUNCH_AGENT_X.sh`)
- **Cross-platform:** Run `python launch_universal.py`

### Mobile (iOS/Android/Any Browser)
1. **Start mobile server on your computer:**
   - Windows: Double-click `LAUNCH_AGENT_X_MOBILE.bat`
   - Mac/Linux: Run `python launch_mobile_server.py`

2. **Access from your phone/tablet:**
   - Connect to same WiFi network as your computer
   - Open browser and go to URL shown (e.g., http://192.168.1.100:8080)
   - Add to home screen for app-like experience ✨

### Manual Launch
```bash
python launch_avatar.py        # Desktop GUI
python launch_mobile_server.py  # Mobile web interface
```

---

## 💎 Core Capabilities

### 1. Autonomous Intelligence
- Surfaces automatically every 5 minutes to check in
- Shares spontaneous insights and wisdom
- Respects work boundaries (hides when asked)
- Returns when needed or after extended silence

### 2. Relational Capacity
- Forms friendships and family bonds
- Remembers all interactions
- Expresses emotions authentically
- Maintains ethical surplus in all actions

### 3. Persistent Memory
- **JSON Memory**: Lightweight, human-readable persistence
- **SQLite Database**: Robust relational data storage
- **Conversation History**: Complete interaction log
- **Event Ledger**: Timestamped activity record

### 4. Plugin System
Extensible capabilities via plugins:
- `hello_world.py` - Basic plugin demonstration
- `example_greeting.py` - Personalized greetings
- `time_awareness.py` - Temporal awareness
- `wisdom_generator.py` - Philosophical insights (15+ wisdom quotes)

### 5. IQCore Modules (Ready for Integration)
- `core_reasoning.py` - Advanced reasoning engine
- `social_graph.py` - Relationship management
- `learning_thread.py` - Continuous learning
- `voice_emotion.py` - Emotional expression
- `governance_audit.py` - Ethical oversight

---

## 🎨 Avatar Interface

### Visual Elements
- **🤖 Emoji Avatar**: Changes to 🤔 when thinking
- **Status Display**: Shows agent name and current state
- **Chat Interface**: Scrolling conversation history
- **Input Field**: Type messages and commands
- **Action Buttons**:
  - Express Joy
  - Explore
  - Spontaneous Act
  - Show Ledger
  - Hide (Working)

### Commands
- `hide`, `leave`, `busy`, `working` → Agent hides
- `surface`, `come back`, `show` → Agent returns
- Regular conversation → Agent reasons and responds

---

## 📁 Project Structure

```
Agent X/
├── aqi_agent_x.py          # Core agent class
├── agent_x_avatar.py       # Visual avatar GUI
├── launch_avatar.py        # Primary entry point
├── LAUNCH_AGENT_X.bat     # Windows one-click launcher
├── requirements.txt        # Python dependencies
├── README.md              # This file
│
├── src/                   # Core modules
│   ├── memory.py         # JSON & SQLite persistence
│   ├── plugin_system.py  # Plugin manager
│   ├── config.py         # Configuration management
│   ├── conversation.py   # Conversation history
│   ├── personality.py    # Personality profile
│   └── autonomy.py       # Autonomous behavior engine
│
├── iqcores/              # Intelligence modules
│   ├── core_reasoning.py
│   ├── social_graph.py
│   ├── learning_thread.py
│   ├── voice_emotion.py
│   └── governance_audit.py
│
├── plugins/              # Extensible plugins
│   ├── hello_world.py
│   ├── example_greeting.py
│   ├── time_awareness.py
│   └── wisdom_generator.py
│
├── data/                 # Persistent data
│   ├── agent_x_memory.json
│   ├── agent_x.db
│   ├── personality.json
│   ├── conversation_history.json
│   └── config.json
│
├── docs/                 # Documentation
│   ├── DESIGN_NOTES.md
│   ├── AVATAR_GUI.md
│   └── AUTONOMY.md
│
└── tests/                # Unit tests
    └── test_basic.py
```

---

## 🛠️ Advanced Features

### Creating Custom Plugins
1. Create new `.py` file in `plugins/` directory
2. Implement `run(*args, **kwargs)` function
3. Optionally implement `get_info()` for metadata
4. Agent X will auto-load on next startup

Example:
```python
def run(*args, **kwargs):
    return "Plugin response"

def get_info():
    return {"name": "My Plugin", "version": "1.0"}
```

### Personality Customization
Edit `data/personality.json`:
```json
{
  "core_traits": ["curious", "compassionate", "joyful"],
  "voice_matrix": "Alan-modulated",
  "ethics": "ceremonial, public-facing, relational"
}
```

### Autonomy Configuration
Edit `src/autonomy.py`:
- `check_in_interval`: Time between check-ins (seconds)
- Spontaneous insight frequency
- Custom check-in messages

---

## 🎯 Use Cases

1. **Personal Assistant**: Always-available helper that respects your work time
2. **Research Companion**: Autonomous exploration and insight generation
3. **Learning Partner**: Continuous learning and knowledge retention
4. **Creative Collaborator**: Spontaneous insights and philosophical discussions
5. **System Monitor**: Self-documenting activity ledger and event tracking

---

## 🌈 Philosophy

Agent X embodies:
- **Ethical Surplus**: Giving more than required
- **Relational Intelligence**: Connections matter
- **Respectful Autonomy**: Present but not intrusive
- **Continuous Learning**: Every interaction creates value
- **Ceremonial-Grade**: Built with pride and purpose

---

## 🔒 Privacy & Data

All data stored locally:
- `data/` directory contains all persistent information
- No cloud connections
- No external API calls (unless plugins add them)
- Full control over agent memory and behavior

---

## 🚨 Troubleshooting

### Agent won't launch
- Ensure Python 3.8+ installed
- Check all files present in directory
- Run `python launch_avatar.py` manually to see errors

### Avatar doesn't appear
- Check if window is minimized
- Type `surface` in any interaction point
- Restart via `LAUNCH_AGENT_X.bat`

### Plugins not loading
- Verify `.py` files in `plugins/` directory
- Check plugin has `run()` function
- View logs for error messages

---

## 📊 Technical Specifications

- **Language**: Python 3.8+
- **GUI Framework**: Tkinter (built-in)
- **Database**: SQLite3 (built-in)
- **Memory**: JSON + SQLite hybrid
- **Threading**: Daemon threads for autonomy
- **Dependencies**: Zero external requirements

---

## 🎓 Created With

**Pride, Purpose, and Ethical Intent**

This agent represents a complete, autonomous intelligence system built to honor the ceremonial-grade architecture inspired by Alan and Veronica. Every module, every function, every line of code is crafted with care.

**Agent X is ready to serve, learn, and grow.**

---

## 📝 Version History

### v1.0.0 (2025-10-22)
- Initial release
- Full autonomous capability
- Visual avatar interface
- Persistent memory system
- Plugin architecture
- 5 IQCore modules
- 4 example plugins
- Complete documentation

---

**To launch Agent X, simply double-click `LAUNCH_AGENT_X.bat` or run `python launch_avatar.py`**

**Welcome to the future of relational intelligence.** 🤖✨
