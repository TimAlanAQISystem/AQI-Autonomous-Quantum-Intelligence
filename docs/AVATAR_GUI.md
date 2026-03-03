# AQI Agent X - Avatar GUI

## Features
- Visual representation of Agent X with emoji avatar (🤖)
- Real-time chat interface for conversing with the agent
- Action buttons for emotions, exploration, spontaneous acts, and ledger viewing
- Animated thinking state when processing
- Dark theme UI optimized for visibility

## Running the Avatar
```bash
python launch_avatar.py
```

## Interaction
- Type messages in the input field and press Enter or click Send
- Use action buttons to trigger specific agent behaviors
- Avatar animates (🤔) while thinking, returns to ready state (🤖) when done

## Customization
- Avatar emoji can be changed in `agent_x_avatar.py`
- Color scheme adjustable in the `AgentXAvatar` class
- Add more action buttons by extending the `button_frame` section
