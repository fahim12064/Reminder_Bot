Personal Assistant Telegram Bot
A versatile and persistent Telegram bot designed to act as a personal assistant. It can manage user-specific reminders, provide information, and is built to be easily extensible. The bot ensures that reminders are never lost, even if it restarts, by saving them to a file.

✨ Features
👋 Welcome Message: Greets new users and saves their ID for future interactions.
🗓️ Schedule Manager: A user-friendly, multi-step conversation to set reminders for specific events, dates, and times.
🔔 Persistent Reminders:
Reminders are saved to a reminders.json file.
The bot automatically re-schedules all pending reminders upon restart, ensuring no reminder is ever missed.
All time calculations are handled in the Bangladesh (Asia/Dhaka) timezone.
ℹ️ About Us: A simple, informative section about the bot.
🔐 Secure: Keeps the Telegram Bot Token safe using an environment variable file (.env).
Extensible: Built with a clean and modular structure, making it easy to add new features.
🛠️ Tech Stack
Language: Python 3.x
Core Library: python-telegram-bot
Timezone Handling: pytz
Environment Variables: python-dotenv
🚀 Getting Started
Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.
Prerequisites
Make sure you have Python 3.8+ installed on your system.
Installation
Clone the repository:
Bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
Create a virtual environment (recommended ):
This keeps your project dependencies isolated.
Bash
python -m venv venv
Activate it:
On Windows:
Bash
.\venv\Scripts\activate
On macOS/Linux:
Bash
source venv/bin/activate
Install the required packages:
A requirements.txt file makes this easy. First, create it:
Plain Text
pip freeze > requirements.txt
Then, anyone can install the dependencies using:
Bash
pip install -r requirements.txt
(Note: The required packages are python-telegram-bot, pytz, and python-dotenv)
Set up the environment variables:
Create a file named .env in the root directory of your project.
Open the file and add your Telegram Bot Token like this:
env
TELEGRAM_BOT_TOKEN="8326534479:AAHnlfv7m_6_uVZRg8J5mDqD2Wg8gTvf8Yw"
(Replace the token with your actual bot token from BotFather)
Running the Bot
Once the setup is complete, you can start the bot with a single command:
Bash
python bot.py
The bot will start, load any pending reminders, and begin listening for messages on Telegram.
📂 Project Structure
Plain Text
.
├── .env                  # Stores environment variables (like the bot token)
├── bot.py                # The main application script for the bot
├── reminders.json        # Stores pending reminders (auto-generated)
├── users.json            # Stores user IDs (auto-generated)
├── requirements.txt      # Lists all Python dependencies
└── README.md             # You are here!
🔧 How It Works
User Interaction
The bot greets users on /start and presents a main menu with ReplyKeyboardMarkup.
The Schedule Manager uses a ConversationHandler to guide the user through a series of questions (event name, date, time).
Reminder Persistence
When a user sets a reminder, the details (chat ID, event name, UTC time) are saved as an object in the reminders.json file.
The reminder is also scheduled in the JobQueue in memory.
When the bot starts, the load_and_schedule_reminders function reads reminders.json.
It iterates through all saved reminders, checks if they are still in the future, and re-schedules them in the JobQueue.
Once a reminder is sent, it is removed from reminders.json to prevent re-scheduling.
