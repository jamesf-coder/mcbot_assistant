import os
import logging
import ollama
import configparser
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Configuration defaults
DEFAULT_CONFIG = {
    'telegram_api': os.environ.get("TELEGRAM_API", ""),
    'ollama_url': 'http://llm.fritz.box:11434',
    'model': 'qwen2.5-coder:7b'
}

def load_config():
    config = configparser.ConfigParser()
    config.read('bot.conf')
    
    bot_config = DEFAULT_CONFIG.copy()
    if 'bot' in config:
        for key in DEFAULT_CONFIG:
            if key in config['bot']:
                bot_config[key] = config['bot'][key]
    
    return bot_config

# Load config once
CONFIG = load_config()

# Chat history storage: chat_id -> list of messages
CHAT_HISTORY = {}

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I'm a bot, please talk to me!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Use /start to begin, /reset to clear history."
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = []
    await context.bot.send_message(
        chat_id=chat_id,
        text="Chat context has been reset."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text
    
    # Send typing action to show the bot is "thinking" in the chat header
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # Send an initial "thinking..." message
    thinking_message = await context.bot.send_message(
        chat_id=chat_id,
        text="Thinking..."
    )

    # Initialize history for chat if not exists
    if chat_id not in CHAT_HISTORY:
        CHAT_HISTORY[chat_id] = []
    
    # Add user message to history
    CHAT_HISTORY[chat_id].append({'role': 'user', 'content': user_text})

    try:
        client = ollama.AsyncClient(host=CONFIG['ollama_url'])
        response = await client.chat(model=CONFIG['model'], messages=CHAT_HISTORY[chat_id])
        response_text = response['message']['content']
        
        # Add bot response to history
        CHAT_HISTORY[chat_id].append({'role': 'assistant', 'content': response_text})
        
        # Edit the thinking message with the actual response
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=thinking_message.message_id,
            text=response_text
        )
    except Exception as e:
        logging.error(f"Error calling Ollama: {e}")
        error_text = "Sorry, I'm having trouble connecting to my brain right now."
        
        # Update the thinking message with the error
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=thinking_message.message_id,
            text=error_text
        )

if __name__ == '__main__':
    token = CONFIG['telegram_api']
    
    if not token or token == "your_telegram_token_here":
        print("Error: Telegram API token not found in bot.conf or environment variable.")
        exit(1)

    application = ApplicationBuilder().token(token).build()
    
    start_handler = CommandHandler('start', start)
    help_handler = CommandHandler('help', help_command)
    reset_handler = CommandHandler('reset', reset_command)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(help_handler)
    application.add_handler(reset_handler)
    application.add_handler(message_handler)
    
    print(f"Bot started with model: {CONFIG['model']} at {CONFIG['ollama_url']}")
    application.run_polling()
