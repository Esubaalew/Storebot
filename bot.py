import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, Application, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
import logging
import os
import json
from dotenv import load_dotenv
from tools import add_product_to_api

# Constants for ConversationHandler states
NAME, DESCRIPTION, IMAGE_URL = range(3)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)



# Helper function to check if a product exists using the API
def product_exists(product_id):
    try:
        response = requests.get(f"{os.getenv("PRODUCT_API_URL")}{product_id}/")
        response.raise_for_status()  # Raise an error for non-2xx responses
        return response.json()  # Return the product data
    except requests.RequestException as e:
        logger.error(f"Error fetching product from API: {e}")
        return None

# Helper function to add an order to the API
def add_order_to_api(order_data):
    try:
        response = requests.post(os.getenv("ORDER_API_URL"), json=order_data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Error adding order to API: {e}")
        return None

# Bot command: Start order process
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0].startswith('order_'):
        product_id = context.args[0].split('_')[1]
        product = product_exists(product_id)

        if product:
            keyboard = [[InlineKeyboardButton("Proceed with Purchase", callback_data=f"order_{product_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_photo(
                photo=product["image"],
                caption=f"*{product['name']}*\n{product['description']}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("Sorry, the product does not exist.")
    else:
        await update.message.reply_text("Welcome to the ordering bot!")

# Handle the order confirmation flow
async def handle_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = query.data.split('_')[1]
    product = product_exists(product_id)

    if not product:
        await query.edit_message_text("Sorry, the product does not exist.")
        return

    # Prepare order confirmation details
    order_text = (
        f"Order Confirmation:\n\n"
        f"*Product:* {product['name']}\n"
        f"*Description:* {product['description']}\n\n"
        f"Would you like to confirm this order?"
    )

    keyboard = [[InlineKeyboardButton("Confirm Order", callback_data=f"confirm_order_{product_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query.message.photo:
        await query.edit_message_caption(caption=order_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        await query.edit_message_text(text=order_text, parse_mode='Markdown', reply_markup=reply_markup)

# Handle order confirmation
async def handle_confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split('_')
    if len(parts) != 3 or parts[0] != 'confirm' or parts[1] != 'order':
        await query.message.reply_text("Invalid confirmation data.")
        return

    product_id = parts[2]
    product = product_exists(product_id)

    if not product:
        await query.message.reply_text("Sorry, the product does not exist.")
        return

    order_data = {

        "product": product_id,
        "ordered_by": query.from_user.id,
    }

    response = add_order_to_api(order_data)

    if response:
        await query.message.delete()
        await query.message.reply_text(f"Thank you, {query.from_user.first_name}! Your order for *{product['name']}* has been confirmed.", parse_mode='Markdown')
    else:
        await query.message.reply_text("There was a problem confirming your order. Please try again later.")

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
    product_data = {
        "name": context.user_data['name'],
        "description": context.user_data['description'],
        "image": context.user_data['image_url'],
        "price": 0  # Default price, or could ask for it
    }

    response = add_product_to_api(product_data)

    if response:
        product_id = response.get('id')
        channel_id = "-1002437698028"  # Your Telegram channel ID
        keyboard = [[InlineKeyboardButton("Order", url=f"https://t.me/{context.bot.username}?start=order_{product_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_photo(
            chat_id=channel_id,
            photo=context.user_data['image_url'],
            caption=f"*{context.user_data['name']}*\n{context.user_data['description']}",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

        await update.message.reply_text("Product has been added and posted to the channel!")
    else:
        await update.message.reply_text("Failed to add the product to the API.")

    return ConversationHandler.END

# Main function to run the bot
def main():
    load_dotenv()
    application = Application.builder().token(os.getenv("TOKEN")).build()

    add_product_handler = ConversationHandler(
        entry_points=[CommandHandler('add_product', add_product)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_name)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_description)],
            IMAGE_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_image_url)]
        },
        fallbacks=[]
    )

    application.add_handler(CommandHandler('start', start))
    application.add_handler(add_product_handler)
    application.add_handler(CallbackQueryHandler(handle_order, pattern=r'^order_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_confirm_order, pattern=r'^confirm_order_\d+$'))

    application.run_polling()

if __name__ == '__main__':
    main()
