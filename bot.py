from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CommandHandler, Application, MessageHandler, filters, ContextTypes
import logging
import os
from dotenv import load_dotenv

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
   
    keyboard = [
        [InlineKeyboardButton("Explore Products", web_app=WebAppInfo(url=os.getenv("WEB_APP_URL")))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    
    await update.message.reply_text(f"Hello {update.effective_user.first_name}! Welcome to the Bot!", reply_markup=reply_markup)



async def echo(update: Update, context):
    await update.message.reply_text(update.message.text)

def main():
    load_dotenv()
    application = Application.builder().token(os.getenv("TOKEN")).build()

   
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    
    application.run_polling()

if __name__ == '__main__':
    main()
