import os
import logging
import ollama
import configparser
import asyncio
from nio import AsyncClient, MatrixRoom, RoomMessage, RoomMessageText, Api
from nio.responses import SyncResponse

# Configuration defaults
DEFAULT_CONFIG = {
    'matrix_password': os.environ.get("MATRIX_PASSWORD", ""),
    'matrix_user_id': 'autobot_1981:matrix.org',
    'matrix_homeserver': 'https://matrix.org',
    'ollama_url': 'http://llm.fritz.box:11434',
    'model': 'qwen2.5-coder:7b'
}

def load_config():
    """Load configuration from JSON file `bot.conf` (keeps INI fallback).

    The file `bot.conf` is now expected to be JSON, e.g.:
    {
      "matrix_password": "your_matrix_password_here",
      "matrix_user_id": "autobot_1981:matrix.org",
      "matrix_homeserver": "https://matrix.org",
      "ollama_url": "http://llm.fritz.box:11434",
      "model": "qwen2.5-coder:7b"
    }
    """
    bot_config = DEFAULT_CONFIG.copy()
    path = 'bot.conf'

    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                data = json.load(f) or {}
            for key in DEFAULT_CONFIG:
                if key in data:
                    bot_config[key] = data[key]
        except json.JSONDecodeError:
            # Backwards-compat: try INI format if file isn't valid JSON
            try:
                config = configparser.ConfigParser()
                config.read(path)
                if 'bot' in config:
                    for key in DEFAULT_CONFIG:
                        if key in config['bot']:
                            bot_config[key] = config['bot'][key]
            except Exception as e:
                print(f"Failed to parse INI fallback from {path}: {e}")
        except Exception as e:
            print(f"Failed to load JSON config from {path}: {e}")

    return bot_config

# Load config once
CONFIG = load_config()

# Chat history storage: room_id -> list of messages
CHAT_HISTORY = {}

# Matrix client instance
matrix_client = None

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(room: MatrixRoom):
    """Handle /start command"""
    await matrix_client.room_send(
        room_id=room.room_id,
        message_type="m.room.message",
        content={
            "msgtype": "m.text",
            "body": "I'm a bot, please talk to me!"
        }
    )

async def help_command(room: MatrixRoom):
    """Handle /help command"""
    await matrix_client.room_send(
        room_id=room.room_id,
        message_type="m.room.message",
        content={
            "msgtype": "m.text",
            "body": "Use /start to begin, /reset to clear history."
        }
    )

async def reset_command(room: MatrixRoom):
    """Handle /reset command"""
    if room.room_id in CHAT_HISTORY:
        CHAT_HISTORY[room.room_id] = []
    await matrix_client.room_send(
        room_id=room.room_id,
        message_type="m.room.message",
        content={
            "msgtype": "m.text",
            "body": "Chat context has been reset."
        }
    )

async def handle_message(room: MatrixRoom, user_text: str):
    """Handle regular messages"""
    room_id = room.room_id
    
    # Send a "thinking..." message
    thinking_response = await matrix_client.room_send(
        room_id=room_id,
        message_type="m.room.message",
        content={
            "msgtype": "m.text",
            "body": "Thinking..."
        }
    )
    
    # Initialize history for room if not exists
    if room_id not in CHAT_HISTORY:
        CHAT_HISTORY[room_id] = []
    
    # Add user message to history
    CHAT_HISTORY[room_id].append({'role': 'user', 'content': user_text})

    try:
        client = ollama.AsyncClient(host=CONFIG['ollama_url'])
        response = await client.chat(model=CONFIG['model'], messages=CHAT_HISTORY[room_id])
        response_text = response['message']['content']
        
        # Add bot response to history
        CHAT_HISTORY[room_id].append({'role': 'assistant', 'content': response_text})
        
        # Delete the thinking message and send the actual response
        await matrix_client.room_redact(
            room_id=room_id,
            event_id=thinking_response.event_id
        )
        
        # Send the actual response
        await matrix_client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": response_text
            }
        )
    except Exception as e:
        logging.error(f"Error calling Ollama: {e}")
        error_text = "Sorry, I'm having trouble connecting to my brain right now."
        
        # Delete the thinking message and send error
        await matrix_client.room_redact(
            room_id=room_id,
            event_id=thinking_response.event_id
        )
        
        await matrix_client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": error_text
            }
        )

async def message_callback(room: MatrixRoom, event: RoomMessageText):
    """Callback for incoming messages"""
    # Ignore own messages
    if event.sender == matrix_client.user_id:
        return
    
    user_text = event.body
    
    # Handle commands
    if user_text.startswith('/start'):
        await start(room)
    elif user_text.startswith('/help'):
        await help_command(room)
    elif user_text.startswith('/reset'):
        await reset_command(room)
    else:
        # Regular message
        await handle_message(room, user_text)

async def sync_callback(response: SyncResponse):
    """Callback for sync responses"""
    if not isinstance(response, SyncResponse):
        return

async def main():
    """Main function to run the Matrix bot"""
    global matrix_client
    
    password = CONFIG['matrix_password']
    user_id = CONFIG['matrix_user_id']
    homeserver = CONFIG['matrix_homeserver']
    
    if not password or password == "your_matrix_password_here":
        print("Error: Matrix password not found in bot.conf or environment variable.")
        exit(1)
    
    # Create the client
    matrix_client = AsyncClient(homeserver, user_id)
    
    try:
        # Login
        login_response = await matrix_client.login(password)
        if not login_response.user_id:
            print(f"Failed to login: {login_response}")
            exit(1)
        
        print(f"Logged in as {login_response.user_id}")
        print(f"Bot started with model: {CONFIG['model']} at {CONFIG['ollama_url']}")
        
        # Set up callbacks
        matrix_client.add_event_callback(message_callback, RoomMessageText)
        
        # Start syncing
        await matrix_client.sync_forever(timeout=30000)
    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        await matrix_client.close()

if __name__ == '__main__':
    asyncio.run(main())
