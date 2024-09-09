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

# Load orders from JSON file
def load_orders():
    try:
        with open('orders.json', 'r') as file:
            data = file.read().strip()
            if data:
                return json.loads(data)
            return []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Save orders to JSON file
def save_orders(orders):
    with open('orders.json', 'w') as file:
        json.dump(orders, file, indent=4)

products = load_products()
orders = load_orders()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if this is an order start command
    if context.args and context.args[0].startswith('order_'):
        product_id = context.args[0].split('_')[1]
        product = next((p for p in products if p["id"] == product_id), None)

        if product:
            keyboard = [[InlineKeyboardButton("Proceed with Purchase", callback_data=f"order_{product['id']}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Display the product image and details with an inline button
            await update.message.reply_photo(
                photo=product["image_url"],
                caption=f"*{product['name']}*\n{product['description']}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("Sorry, the product does not exist.")
    else:
        await update.message.reply_text("Welcome to the ordering bot!")

async def handle_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = query.data.split('_')[1]
    logger.info(f"Handle Order Callback - Extracted Product ID: '{product_id}'")

    product = next((p for p in products if p["id"] == product_id), None)
    logger.info(f"Product Found: {product}")

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

    # Inline button for confirming the order
    keyboard = [[InlineKeyboardButton("Confirm Order", callback_data=f"confirm_order_{product_id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Check if the original message contains text or an image
    if update.callback_query.message.photo:
        # If the message contains a photo, edit the caption
        await query.edit_message_caption(
            caption=order_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        # If the message contains text, edit the message text
        await query.edit_message_text(
            text=order_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

async def handle_confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    logger.info(f"Callback Data Received: '{query.data}'")

    # Split the data correctly
    parts = query.data.split('_')
    if len(parts) != 3 or parts[0] != 'confirm' or parts[1] != 'order':
        await query.message.reply_text("Invalid confirmation data.")
        return

    product_id = parts[2]
    logger.info(f"Extracted Product ID: '{product_id}'")

    product = next((p for p in products if p["id"] == product_id), None)
    logger.info(f"Product Found: {product}")

    if not product:
        await query.message.reply_text("Sorry, the product does not exist.")
        return

    # Save order details to orders.json
    order = {
        "user_id": query.from_user.id,
        "username": query.from_user.username,
        "product_id": product["id"],
        "product_name": product["name"]
    }

    orders.append(order)
    save_orders(orders)

    # Delete the original message
    await query.message.delete()

    # Send a confirmation message
    await query.message.reply_text(
        f"Thank you, {query.from_user.first_name}! Your order for *{product['name']}* has been confirmed.",
        parse_mode='Markdown'
    )






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
        "price": 0  # Set default price or get from user if needed
    }

    response = add_product_to_api(product_data)
    print(response)

    if response:
        # Assuming the API returns the product with ID
        product_id = response.get('id')
        channel_id = "-1002437698028"  # Your channel ID
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
    application.add_handler(CallbackQueryHandler(handle_order, pattern=r'^order_\d+$'))
    application.add_handler(CallbackQueryHandler(handle_confirm_order, pattern=r'^confirm_order_\d+$'))

    application.run_polling()

if __name__ == '__main__':
    main()
