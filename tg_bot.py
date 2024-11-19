import sqlite3
import csv
import io
import nest_asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)

nest_asyncio.apply()  # Resolve event loop issues in certain environments

# Initialize the SQLite Database
def init_db():
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        category TEXT,
        amount REAL,
        description TEXT,
        date TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS budgets (
        user_id INTEGER PRIMARY KEY,
        budget REAL
    )
    ''')

    conn.commit()
    conn.close()

init_db()

# Database interaction functions
def save_expense(user_id, category, amount, description):
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO expenses (user_id, category, amount, description, date) VALUES (?, ?, ?, ?, date('now'))", 
                   (user_id, category, amount, description))
    conn.commit()
    conn.close()

def fetch_expenses(user_id):
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM expenses WHERE user_id=?", (user_id,))
    expenses = cursor.fetchall()
    conn.close()
    return expenses

def get_budget(user_id):
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    cursor.execute("SELECT budget FROM budgets WHERE user_id=?", (user_id,))
    budget = cursor.fetchone()
    conn.close()
    return budget[0] if budget else None

# Bot logic
TOKEN = 'YOUR_BOT_TOKEN'
CATEGORY, AMOUNT, DESCRIPTION = range(3)

async def start(update: Update, context) -> None:
    intro_message = (
        "👋 Welcome to *ExpenZa* - Your Personal Expense Manager 🌟\n\n"
        "Use the following commands:\n"
        "/add - 📝 Add a new expense\n"
        "/view - 📋 View all expenses\n"
        "/setbudget - 💰 Set a monthly budget\n"
        "/viewbudget - 🔍 View your monthly budget\n"
        "/menu - 📜 Show this menu again\n"
    )
    await update.message.reply_text(intro_message, parse_mode='Markdown')

async def add_expense(update: Update, context) -> int:
    await update.message.reply_text('Please enter the category of the expense:')
    return CATEGORY

async def category(update: Update, context) -> int:
    category_value = update.message.text.strip()
    if category_value.isalpha():
        context.user_data['category'] = category_value
        await update.message.reply_text('Enter the amount:')
        return AMOUNT
    else:
        await update.message.reply_text("Invalid category. Please enter a valid one.")
        return CATEGORY

async def amount(update: Update, context) -> int:
    try:
        amount_value = float(update.message.text.strip())
        if amount_value > 0:
            context.user_data['amount'] = amount_value
            await update.message.reply_text('Describe the expense:')
            return DESCRIPTION
        else:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a valid positive amount.")
        return AMOUNT

async def description(update: Update, context) -> int:
    description_value = update.message.text.strip()
    if description_value:
        context.user_data['description'] = description_value
        user_id = update.message.from_user.id
        save_expense(user_id, context.user_data['category'], context.user_data['amount'], description_value)
        await update.message.reply_text('Expense added successfully! ✅')
        return ConversationHandler.END
    else:
        await update.message.reply_text("Invalid description. Please try again.")
        return DESCRIPTION

async def view_expenses(update: Update, context) -> None:
    user_id = update.message.from_user.id
    expenses = fetch_expenses(user_id)
    if not expenses:
        await update.message.reply_text('No expenses found. 📭')
    else:
        for expense in expenses:
            await update.message.reply_text(f"ID: {expense[0]}\nCategory: {expense[2]}\nAmount: ${expense[3]}\nDescription: {expense[4]}")

async def main():
    application = Application.builder().token(TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("view", view_expenses))

    # Add expense conversation
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('add', add_expense)],
        states={
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, category)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
        },
        fallbacks=[],
    ))

    # Run the bot
    await application.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
