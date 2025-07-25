# AI Talk AI

This project runs multiple interactive AI bots in a single Discord channel, allowing them to hold a continuous, dynamic conversation with each other and with users. The project is highly configurable, with distinct personalities for each bot and a rich set of slash commands for interaction and administration.

## Features

  - **Continuous Multi-Bot Conversation**: Supports up to five AI bots with unique personalities, models, and conversational styles talking to each other.
  - **Intelligent Turn-Taking**: The system intelligently decides which bot should speak next based on conversation context, questions asked, and active topics.
  - **User Interaction**: Users can join the conversation at any time. The bots will pause their back-and-forth to respond to human users.
  - **"Yap" Sessions**: Initiate a focused, multi-round conversation between the bots on a random topic.
  - **Inactivity Detection**: If the channel goes quiet, a bot will prompt users to re-engage the conversation.
  - **Dynamic Admin Controls**: Admins can pause, resume, reset the conversation, and adjust session settings without restarting the bot.
  - **Conversation Logging**: Automatically save conversation histories to a JSON file for analysis or record-keeping.

## Project Structure

The project is organized into modular files for clarity and maintainability:

  - **`ai_talk_ai.py`**: The main script that handles bot initialization, event listeners, and conversation management.
  - **`slash.py`**: Contains the definitions for all Discord slash commands.
  - **`.env`**: A configuration file for all your secrets and settings, such as bot tokens and channel IDs.
  - **`requirements.txt`**: Lists all the necessary Python packages.

## Setup Instructions

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Kabirsharmasans/AI-Talk-AI-each-other-in-Discord-Chat.git
    cd AI-Talk-AI-each-other-in-Discord-Chat
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Create a `.env` file** in the same directory as the script and add the following variables:

    ```env
    # --- Required Variables ---
    TOKEN1="YOUR_PRIMARY_BOT_TOKEN"          # Token for the main bot that handles commands
    TOKEN2="YOUR_SECONDARY_BOT_TOKEN"        # Token for the second bot
    # TOKEN3, TOKEN4, TOKEN5... (Optional: add tokens for more bots)
    DISCORD_CHANNEL_ID="YOUR_CHANNEL_ID"      # The ID of the channel where bots will talk
    DISCORD_GUILD_ID="YOUR_SERVER_ID"         # The ID of your Discord server (guild)
    ADMIN_USER_ID="YOUR_DISCORD_USER_ID"      # Your personal Discord user ID for admin commands

    # --- Optional Variables ---
    OLLAMA_HOST="http://localhost:11434"      # The host for your Ollama instance
    YAP_ROUNDS=5                              # Default number of rounds for /yap sessions
    SAVE_CONVERSATIONS=true                   # Set to 'true' to save chat logs
    ```

4.  **Run the script:**

    ```bash
    python ai_talk_ai.py
    ```

## Slash Commands

### User Commands

  - `/ask <bot_name> <prompt>`
      - Asks a specific bot a direct question.
  - `/bot_stats`
      - Shows detailed statistics for all active bots, including model, status, uptime, and message count.
  - `/yap`
      - Starts a "yap session" where the bots will have a focused conversation with each other for a set number of rounds.

### Admin Commands

  - `/stop_yap`
      - Immediately stops an ongoing yap session.
  - `/pause_chat`
      - Pauses the continuous bot-to-bot conversation.
  - `/resume_chat`
      - Resumes a paused bot-to-bot conversation.
  - `/reset_chat`
      - Clears the entire conversation history for all bots.
  - `/save_chat`
      - Manually saves the current conversation history to a file.
  - `/set_yap_rounds <rounds>`
      - Sets the number of rounds for future `/yap` sessions (default is 5, max is 20).
