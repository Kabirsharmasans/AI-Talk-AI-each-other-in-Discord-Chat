# AI Talk AI

This project runs two interactive AI bots in a Discord channel, allowing them to hold a continuous conversation. It also provides a rich set of slash commands for users to interact with the bots and for administrators to dynamically configure their behavior.

## Features

- **Continuous Bot Conversation:** Two AI bots with distinct personalities talk to each other indefinitely.
- **User Inactivity Detection:** If the channel is quiet for too long, one bot will "roast" the users to encourage engagement.
- **Dynamic Configuration:** Admins can change bot models, personalities, and other settings on the fly using slash commands.
- **Interactive Commands:** Users can directly ask questions to specific bots, pause the chat, and check bot statuses.

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Create a `.env` file** in the same directory as the script and add the following variables:

    ```env
    # --- Required Variables ---
    TOKEN1="YOUR_PRIMARY_BOT_TOKEN"          # The token for the main bot that handles commands
    TOKEN2="YOUR_SECONDARY_BOT_TOKEN"        # The token for the second bot
    DISCORD_CHANNEL_ID="YOUR_CHANNEL_ID"      # The ID of the channel where the bots will talk
    DISCORD_GUILD_ID="YOUR_SERVER_ID"         # The ID of your Discord server (guild)
    ADMIN_USER_ID="YOUR_DISCORD_USER_ID"      # Your personal Discord user ID for admin commands

    # --- Optional Variables ---
    OLLAMA_HOST="http://localhost:11434"    # The host for your Ollama instance (if not local)
    ```

4.  **Run the script:**
    ```bash
    python ai_talk_ai.py
    ```

## Slash Commands

### User Commands

-   `/ask [bot_name] [prompt]`
    -   Asks a specific bot a question and gets a direct response.
-   `/bot_status`
    -   Displays the current model and temperature for each bot.

### Admin Commands

-   `/reset_chat`
    -   Clears the entire conversation history between the bots.
-   `/pause_chat`
    -   Pauses the continuous bot-to-bot conversation.
-   `/resume_chat`
    -   Resumes the bot-to-bot conversation.
-   `/swap_model [bot_name] [new_model]`
    -   Changes the Ollama model for the specified bot.
-   `/set_personality [bot_name] [personality]`
    -   Sets a new personality prompt for the specified bot.
-   `/set_temperature [bot_name] [temperature]`
    -   Changes the response temperature for the specified bot (e.g., 0.7, 1.2).
