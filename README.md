# Telegram Assistant

A Matrix bot powered by **Ollama**, a local LLM (Large Language Model) engine. This bot allows you to interact with an AI model directly through Matrix, maintaining conversation history for context-aware responses.

## Features

- **Local LLM Integration**: Runs on your own hardware using Ollama for privacy and control
- **Context-Aware Conversations**: Maintains chat history per conversation for coherent multi-turn interactions
- **Typing Indicators**: Shows "Thinking..." status while processing responses
- **Multiple Commands**: `/start`, `/help`, and `/reset` for easy bot control
- **Error Handling**: Graceful handling of connection issues with user-friendly error messages
- **Configuration Management**: Easy setup via `bot.conf` with environment variable support

## Prerequisites

- **Python 3.8+**
- **Ollama** installed and running locally (download from [ollama.ai](https://ollama.ai))
- **Matrix Account** (create one at [matrix.org](https://matrix.org) or your preferred homeserver)
- A Matrix client to interact with the bot (e.g., Element, Neon)

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd telegram_assistant
```

### 2. Create a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

The main dependencies are:
- `matrix-nio` - Matrix client library
- `ollama` - Ollama Python client
- `configparser` - Configuration file parsing

### 4. Configure the Bot

Edit `bot.conf` (now JSON) and add your settings. Example `bot.conf` content:

```json
{
  "matrix_password": "YOUR_MATRIX_PASSWORD_HERE",
  "matrix_user_id": "autobot_1981:matrix.org",
  "matrix_homeserver": "https://matrix.org",
  "ollama_url": "http://llm.fritz.box:11434",
  "model": "qwen2.5-coder:7b"
}
```

**Configuration Options:**
- `matrix_password`: Your Matrix account password
- `matrix_user_id`: Your Matrix user ID (format: `@username:homeserver.org`)
- `matrix_homeserver`: Your Matrix homeserver URL (e.g., `https://matrix.org`)
- `ollama_url`: URL where Ollama is running (default: `http://llm.fritz.box:11434`)
- `model`: Name of the Ollama model to use (e.g., `qwen2.5-coder:7b`, `mistral`, `neural-chat`)

**Alternative**: Set the `MATRIX_PASSWORD` environment variable instead of the config file:
```bash
export MATRIX_PASSWORD="your_password_here"
```

### 5. Start Ollama

Before running the bot, ensure Ollama is running:
```bash
ollama serve
```

In another terminal, pull a model (if not already available):
```bash
ollama pull qwen2.5-coder:7b
```

## Running the Application

Activate the virtual environment (if not already active):
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Run the bot:
```bash
python src/main.py
```

The bot will connect to Telegram and start listening for messages.

## Available Commands

- **`/start`** - Greet the bot and begin chatting
- **`/help`** - Display available commands
- **`/reset`** - Clear chat history and start a fresh conversation

## Usage Example

1. Add the bot to a Matrix room
2. Send `/start` in the room to greet the bot
3. Send any message to get a response from the AI
4. Continue the conversation - the bot remembers context from previous messages
5. Use `/reset` to clear conversation history and start fresh
6. Use `/help` to see available commands

## How It Works

1. **Login**: The bot logs into Matrix using the configured credentials
2. **Message Reception**: The bot listens for messages in Matrix rooms it joins
3. **History Management**: Each room maintains its own message history by room ID
4. **LLM Processing**: User messages are sent to the Ollama server with conversation context
5. **Response**: The AI generates a response which is sent back to the Matrix room
6. **Display**: The "Thinking..." message is redacted and replaced with the actual response

## Troubleshooting

### "Connection refused" errors
- Ensure Ollama is running: `ollama serve`
- Check the `ollama_url` in `bot.conf` matches where Ollama is actually running
- Default assumes Ollama at `http://llm.fritz.box:11434` - adjust for your setup

### Bot doesn't respond
- Verify your Matrix credentials are correct in `bot.conf`
- Check that you've added the bot to a Matrix room
- Ensure the bot's user ID is correct (`autobot_1981:matrix.org`)
- Check Matrix homeserver connectivity

### Login fails
- Verify the `matrix_password` is correct
- Ensure `matrix_homeserver` URL is correct (including https://)
- Check your Matrix server is accessible
- Try testing login with a Matrix client first

### Ollama model errors
- Pull the required model: `ollama pull <model-name>`
- Check available models: `ollama list`
- Verify the model name in `bot.conf` matches exactly

### Memory issues
- Reduce the model size (e.g., use `mistral:7b` instead of larger models)
- Clear chat history with `/reset` to reduce memory usage

## License

See [LICENSE](LICENSE) for details.

## Contributing

Feel free to submit issues and enhancement requests!
