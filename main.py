import os
import json
import logging
import pytz
from datetime import datetime
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)

# --- Configuration ---
TOKEN = "Telegram Bot Token"
USERS_FILE = "users.json"
REMINDERS_FILE = "reminders.json"
BD_TIMEZONE = "Asia/Dhaka"

# --- Setup Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Conversation States ---
EVENT, DATE, TIME = range(3)


# --- Persistence Functions (for Users and Reminders) ---

def load_from_json(filename: str) -> list | dict:
    """Generic function to load data from a JSON file."""
    if not os.path.exists(filename):
        return []  # Return empty list for users or reminders
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading {filename}: {e}")
        return []


def save_to_json(data: list | dict, filename: str):
    """Generic function to save data to a JSON file."""
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        logger.error(f"Error saving to {filename}: {e}")


def save_user(user_id: int):
    """Saves a new user ID if it's not already in the list."""
    users = load_from_json(USERS_FILE)
    if user_id not in users:
        users.append(user_id)
        save_to_json(users, USERS_FILE)
        logger.info(f"New user saved: {user_id}")


# --- Reminder and Job Queue Functions ---

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Sends the reminder message and removes it from the file."""
    job = context.job
    chat_id = job.chat_id
    event_name = job.data['event']

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"⏰ **Reminder:**\n\n{event_name}",
        parse_mode='Markdown'
    )

    # Remove the reminder from the JSON file after it has been sent
    reminders = load_from_json(REMINDERS_FILE)
    # The job name is the unique identifier for the reminder
    updated_reminders = [r for r in reminders if r['job_name'] != job.name]
    save_to_json(updated_reminders, REMINDERS_FILE)
    logger.info(f"Sent and removed reminder: {job.name}")


def schedule_reminder_job(context: ContextTypes.DEFAULT_TYPE, reminder: dict):
    """Schedules a single reminder job in the job queue."""
    chat_id = reminder['chat_id']
    event_name = reminder['event']
    job_name = reminder['job_name']

    # Convert the ISO format string back to a datetime object
    utc_datetime = datetime.fromisoformat(reminder['utc_time'])

    context.job_queue.run_once(
        send_reminder,
        utc_datetime,
        chat_id=chat_id,
        name=job_name,
        data={'event': event_name}
    )
    logger.info(f"Scheduled job: {job_name} for {utc_datetime}")


def load_and_schedule_reminders(application: ApplicationBuilder.build):
    """Loads reminders from the JSON file and schedules them on bot startup."""
    reminders = load_from_json(REMINDERS_FILE)
    if not reminders:
        logger.info("No pending reminders to load.")
        return

    logger.info(f"Loading {len(reminders)} pending reminders...")
    utc_now = datetime.now(pytz.utc)

    valid_reminders = []
    for reminder in reminders:
        utc_datetime = datetime.fromisoformat(reminder['utc_time'])
        # Only schedule reminders that are in the future
        if utc_datetime > utc_now:
            schedule_reminder_job(application, reminder)
            valid_reminders.append(reminder)
        else:
            logger.warning(f"Skipping past reminder: {reminder['job_name']}")

    # Clean up the file by removing past reminders
    save_to_json(valid_reminders, REMINDERS_FILE)


# --- Bot Command and Message Handlers ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    user = update.effective_user
    save_user(user.id)

    keyboard = [
        [KeyboardButton("🗓️ Schedule Manager"), KeyboardButton("ℹ️ Learn About us")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_message = f"👋 Hello, {user.first_name}!\n\nWelcome to my bot. Please choose an option from the menu."
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)


async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Learn About us' button."""
    await update.message.reply_text(
        "🤖 I am a personal assistant bot.\n"
        "Created by IT Shikkha.\n\n"
        "I can help you set reminders and perform other small tasks."
    )


# --- Conversation Handler for Schedule Manager ---

async def schedule_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation for setting a reminder."""
    await update.message.reply_text(
        "🗓️ Let's set a new reminder!\n\n"
        "First, what is the name of the event? (e.g., 'Meet with friend')\n\n"
        "Type /cancel at any time to stop."
    )
    return EVENT


async def get_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the event name and asks for the date."""
    context.user_data['event'] = update.message.text
    await update.message.reply_text(
        f"Great! Event: '{context.user_data['event']}'\n\n"
        "Now, please provide the date in `YYYY-MM-DD` format (e.g., 2025-12-31)."
    )
    return DATE


async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves the date and asks for the time."""
    try:
        datetime.strptime(update.message.text, '%Y-%m-%d')
        context.user_data['date'] = update.message.text
        await update.message.reply_text(
            f"Date saved: {context.user_data['date']}\n\n"
            "Now, provide the time in 24-hour `HH:MM` format (e.g., 14:30)."
        )
        return TIME
    except ValueError:
        await update.message.reply_text("Incorrect format. Please use `YYYY-MM-DD` format for the date.")
        return DATE


async def get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Saves time, schedules the reminder, and ends the conversation."""
    try:
        context.user_data['time'] = update.message.text
        event_datetime_str = f"{context.user_data['date']} {context.user_data['time']}"

        local_tz = pytz.timezone(BD_TIMEZONE)
        naive_datetime = datetime.strptime(event_datetime_str, '%Y-%m-%d %H:%M')
        local_datetime = local_tz.localize(naive_datetime)

        # Check if the time is in the past
        if local_datetime < datetime.now(local_tz):
            await update.message.reply_text(
                "❌ You cannot set a reminder for a past time.\n\nPlease try again with a future time."
            )
            return TIME

        # Convert to UTC for the job queue
        utc_datetime = local_datetime.astimezone(pytz.utc)

        # Create a unique name for the job
        chat_id = update.effective_chat.id
        job_name = f"reminder_{chat_id}_{int(utc_datetime.timestamp())}"

        # --- Save reminder to JSON file ---
        new_reminder = {
            'chat_id': chat_id,
            'event': context.user_data['event'],
            'utc_time': utc_datetime.isoformat(),  # Save in standard ISO format
            'job_name': job_name
        }
        reminders = load_from_json(REMINDERS_FILE)
        reminders.append(new_reminder)
        save_to_json(reminders, REMINDERS_FILE)

        # --- Schedule the job ---
        schedule_reminder_job(context, new_reminder)

        formatted_datetime = local_datetime.strftime('%A, %d %B %Y, %I:%M %p')
        await update.message.reply_text(
            "✅ Your reminder has been set successfully!\n\n"
            f"**Event:** {context.user_data['event']}\n"
            f"**Time:** {formatted_datetime}",
            parse_mode='Markdown'
        )
        context.user_data.clear()
        return ConversationHandler.END
    except (ValueError, KeyError):
        await update.message.reply_text("Incorrect format. Please use `HH:MM` for the time.")
        return TIME


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the conversation."""
    await update.message.reply_text("Reminder setup has been canceled.")
    context.user_data.clear()
    return ConversationHandler.END


# --- Main Function ---
def main():
    """Sets up and runs the bot."""
    application = ApplicationBuilder().token(TOKEN).build()

    # --- Load and schedule pending reminders on startup ---
    # We pass the application object to the function so it can access the job_queue
    load_and_schedule_reminders(application)

    # --- Handlers ---
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^🗓️ Schedule Manager$'), schedule_start)],
        states={
            EVENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_event)],
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.Regex(r'^ℹ️ Learn About us$'), about_us))
    application.add_handler(conv_handler)

    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
