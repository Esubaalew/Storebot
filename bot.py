from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, Application, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
import logging
import os
import json
from dotenv import load_dotenv

# Constants for ConversationHandler states
NAME, DESCRIPTION, IMAGE_URL = range(3)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Load products from JSON file
def load_products():
    try:
        with open('products.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Save products to JSON file
def save_products(products):
    with open('products.json', 'w') as file:
        json.dump(products, file, indent=4)

products = load_products()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the ordering bot!")

# Admin command to add a new product
async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send the product name.")
    return NAME

async def get_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Please send the product description.")
    return DESCRIPTION

async def get_product_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Please send the product image URL.")
    return IMAGE_URL

async def get_product_image_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['image_url'] = update.message.text
    product = {
        "id": str(len(products) + 1),
        "name": context.user_data['name'],
        "description": context.user_data['description'],
        "image_url": context.user_data['image_url']
    }
    products.append(product)
    save_products(products)

    # Post the product to the channel
    channel_id = "-1002437698028"  # Your channel ID
    keyboard = [[InlineKeyboardButton("Order", url=f"https://t.me/{context.bot.username}?start=order_{product['id']}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_photo(
        chat_id=channel_id,
        photo=product["image_url"],
        caption=f"*{product['name']}*\n{product['description']}",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

    await update.message.reply_text("Product has been added and posted to the channel!")
    return ConversationHandler.END

async def handle_start_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        product_id = context.args[0].split('_')[1]
        product = next((p for p in products if p["id"] == product_id), None)

        if product:
            await update.message.reply_text(
                f"You have selected *{product['name']}*.\nDescription: {product['description']}\nWould you like to proceed with the purchase?",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("Sorry, the product does not exist.")
    else:
        await update.message.reply_text("Invalid command or product ID.")

def main():
    load_dotenv()
    application = Application.builder().token(os.getenv("TOKEN")).build()

    # Add product conversation handler
    add_product_handler = ConversationHandler(
        entry_points=[CommandHandler('add_product', add_product)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_name)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_description)],
            IMAGE_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_image_url)]
        },
        fallbacks=[]
    )

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(add_product_handler)
    application.add_handler(CommandHandler('start', handle_start_order))  # Removed pass_args

    application.run_polling()

if __name__ == '__main__':
    main()
