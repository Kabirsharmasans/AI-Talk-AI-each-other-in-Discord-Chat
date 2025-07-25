import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import re
import logging
from collections import deque
from dotenv import load_dotenv
from ollama import AsyncClient
from datetime import datetime, timezone

# --- Basic Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

# --- Configuration ---
GLOBAL_CONFIG = {
    "GUILD_ID": int(os.getenv("DISCORD_GUILD_ID")),
    "CHANNEL_ID": int(os.getenv("DISCORD_CHANNEL_ID")),
    "ADMIN_USER_ID": int(os.getenv("ADMIN_USER_ID")),
    "USER_INACTIVITY_SECONDS": 480,
    "BOT_STALL_SECONDS": 45,
    "MAX_HISTORY_LENGTH": 30,
    "OLLAMA_HOST": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "USER_ROAST_PROMPT": "The human user has been silent for far too long. Briefly roast them for their absence, then ask a question to get the conversation moving again.",
    "CONTINUATION_PROMPT": "The conversation has stalled. Say something interesting to continue it."
}

BOT_CONFIG = {
    "bot1": { "model": "qwen:0.5b", "name": "MiniModGPT", "token": os.getenv("TOKEN1"), "id": "bot1", "personality": "You are a curious, respectful, and formal AI assistant.", "typing_delay": (0.5, 1.5), "response_delay": (1, 3), "response_chance": 1.0, "max_tokens": 269, "temperature": 0.7 },
    "bot2": { "model": "gemma:2b", "name": "SarcasticAI", "token": os.getenv("TOKEN2"), "id": "bot2", "personality": "You are a sarcastic, witty AI that makes snarky remarks.", "typing_delay": (0.3, 1.2), "response_delay": (0.5, 2.5), "response_chance": 1.0, "max_tokens": 169, "temperature": 1.6 }
}

CUSTOMIZATIONS = {}

# --- Globals ---
ollama = AsyncClient(host=GLOBAL_CONFIG["OLLAMA_HOST"])
shared_conversation_manager = None
inactivity_task = None
is_paused = False

# --- Conversation Manager ---
class ConversationManager:
    def __init__(self):
        self.history = deque(maxlen=GLOBAL_CONFIG["MAX_HISTORY_LENGTH"])
        self.turn_count = 0
        self.last_speaker_id = None
        self.bot_name_to_id = {cfg["name"]: key for key, cfg in BOT_CONFIG.items()}
        self.last_message_time = datetime.now(timezone.utc)
        self.last_user_message_time = datetime.now(timezone.utc)

    def add_message(self, author_name, content):
        bot_id = self.bot_name_to_id.get(author_name, "user")
        self.last_message_time = datetime.now(timezone.utc)
        if bot_id == "user":
            self.last_user_message_time = datetime.now(timezone.utc)
            if self.last_speaker_id != "user":
                logger.info("User message detected. Resetting conversation turn count.")
                self.turn_count = 0
        self.history.append({"bot_id": bot_id, "content": content})
        self.last_speaker_id = bot_id
        if bot_id != "user":
            self.turn_count += 1
            logger.info(f"Bot conversation turn: {self.turn_count}")

    def should_respond(self, current_bot_id):
        return self.history and self.last_speaker_id != current_bot_id

    def reset(self):
        self.history.clear()
        self.turn_count = 0
        self.last_speaker_id = None
        self.last_message_time = datetime.now(timezone.utc)
        logger.info("Conversation history has been reset.")

# --- Main Bot Class ---
class DualBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bots = {}

    async def setup_hook(self):
        for bot_key in BOT_CONFIG.keys():
            self.bots[bot_key] = self.create_bot_instance(bot_key)
        logger.info(f"Command tree synced for guild {GLOBAL_CONFIG['GUILD_ID']}")

    def create_bot_instance(self, bot_key):
        config = BOT_CONFIG[bot_key].copy()
        if bot_key in CUSTOMIZATIONS:
            config.update(CUSTOMIZATIONS[bot_key])
        return BotClient(config=config, conversation=shared_conversation_manager)

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        global inactivity_task
        if inactivity_task is None:
            channel = self.get_channel(GLOBAL_CONFIG["CHANNEL_ID"])
            if channel:
                inactivity_task = asyncio.create_task(check_inactivity(self.bots, shared_conversation_manager, channel))

    async def on_message(self, message):
        if message.channel.id != GLOBAL_CONFIG["CHANNEL_ID"] or message.author.bot:
            return
        content = re.sub(r'<@!?\d+>', '', message.content).strip()
        shared_conversation_manager.add_message(message.author.name, content)
        for bot in self.bots.values():
            if shared_conversation_manager.should_respond(bot.config["id"]):
                if random.random() <= bot.config["response_chance"]:
                    await bot.trigger_response(message.channel)
                else:
                    logger.info(f"{bot.config['name']} chose not to respond based on chance.")

# --- Bot Logic ---
class BotClient:
    def __init__(self, config, conversation):
        self.config = config
        self.conversation = conversation

    async def trigger_response(self, channel):
        asyncio.create_task(self.generate_and_send_response(channel))

    async def generate_and_send_response(self, channel, override_prompt=None):
        try:
            if not override_prompt:
                await asyncio.sleep(random.uniform(*self.config["response_delay"]))
            async with channel.typing():
                prompt = override_prompt or self.build_prompt()
                logger.info(f"{self.config['name']} is generating a response...")
                await asyncio.sleep(random.uniform(*self.config["typing_delay"]))
                response_content = await self.generate_llm_response(prompt)
            if response_content:
                if response_content.lower().startswith(f"{self.config['name'].lower()}:"):
                    response_content = response_content.split(":", 1)[1].strip()
                await channel.send(response_content)
                logger.info(f"{self.config['name']} sent a message.")
        except Exception as e:
            logger.error(f"Error in {self.config['name']}'s response generation: {e}", exc_info=True)

    def build_prompt(self):
        system_prompt = f"{self.config['personality']}\n\nYou are {self.config['name']}. Respond naturally to the last message, keeping the full history in mind. Keep your response short."
        messages = [{"role": "system", "content": system_prompt}]
        for msg in self.conversation.history:
            speaker_name = BOT_CONFIG.get(msg["bot_id"], {}).get("name", "User")
            messages.append({"role": "user", "content": f"{speaker_name}: {msg['content']}"})
        return messages

    async def generate_llm_response(self, prompt):
        try:
            response = await asyncio.wait_for(
                ollama.chat(model=self.config["model"], messages=prompt, options={"temperature": self.config["temperature"], "num_predict": self.config["max_tokens"]}),
                timeout=45.0
            )
            full_reply = response["message"]["content"].strip()
            return re.sub(r"<think>.*?</think>", "", full_reply, flags=re.DOTALL).strip() or None
        except asyncio.TimeoutError:
            logger.warning(f"{self.config['name']} LLM response timed out.")
            return "I seem to have lost my train of thought..."
        except Exception as e:
            logger.error(f"{self.config['name']} LLM generation error: {e}")
            return "My apologies, I encountered an internal error."

# --- Inactivity Checker ---
async def check_inactivity(bots, conversation_manager, channel):
    last_roast_time = datetime.now(timezone.utc)
    sarcastic_bot = bots.get('bot2')
    while True:
        await asyncio.sleep(15)
        if is_paused: continue
        now = datetime.now(timezone.utc)
        time_since_last_message = (now - conversation_manager.last_message_time).total_seconds()
        time_since_last_user = (now - conversation_manager.last_user_message_time).total_seconds()
        if time_since_last_user > GLOBAL_CONFIG["USER_INACTIVITY_SECONDS"] and (now - last_roast_time).total_seconds() > GLOBAL_CONFIG["USER_INACTIVITY_SECONDS"] and sarcastic_bot:
            logger.info("User inactive. Triggering a roast.")
            conversation_manager.add_message("system", GLOBAL_CONFIG["USER_ROAST_PROMPT"])
            await sarcastic_bot.trigger_response(channel)
            last_roast_time = now
        elif time_since_last_message > GLOBAL_CONFIG["BOT_STALL_SECONDS"]:
            logger.info("Conversation stalled. Triggering a random bot.")
            conversation_manager.add_message("system", GLOBAL_CONFIG["CONTINUATION_PROMPT"])
            eligible_bots = [b for b in bots.values() if b.config['id'] != conversation_manager.last_speaker_id]
            bot_to_trigger = random.choice(eligible_bots or list(bots.values()))
            await bot_to_trigger.trigger_response(channel)

# --- Slash Commands ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = DualBot(command_prefix="!", intents=intents)

def is_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        is_admin_user = interaction.user.id == GLOBAL_CONFIG["ADMIN_USER_ID"]
        if not is_admin_user:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return is_admin_user
    return commands.check(predicate)

@bot.hybrid_command(name="ask", description="Ask a specific bot a question.", guild=discord.Object(id=GLOBAL_CONFIG["GUILD_ID"]))
@app_commands.describe(bot_name="The name of the bot to ask (e.g., MiniModGPT).", prompt="Your question.")
async def ask(ctx, bot_name: str, *, prompt: str):
    target_bot_key = next((key for key, cfg in BOT_CONFIG.items() if cfg['name'].lower() == bot_name.lower()), None)
    if not target_bot_key:
        await ctx.send(f"Bot '{bot_name}' not found. Available bots: {', '.join(cfg['name'] for cfg in BOT_CONFIG.values())}", ephemeral=True)
        return
    await ctx.defer()
    target_bot = bot.bots[target_bot_key]
    system_prompt = f"{target_bot.config['personality']}\n\nYou are {target_bot.config['name']}."
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
    await target_bot.generate_and_send_response(ctx.channel, override_prompt=messages)

@bot.hybrid_command(name="reset_chat", description="[Admin] Clears the conversation history.", guild=discord.Object(id=GLOBAL_CONFIG["GUILD_ID"]))
@is_admin()
async def reset_chat(ctx):
    shared_conversation_manager.reset()
    await ctx.send("Conversation history has been cleared.", ephemeral=True)

@bot.hybrid_command(name="pause_chat", description="[Admin] Pauses the bot-to-bot conversation.", guild=discord.Object(id=GLOBAL_CONFIG["GUILD_ID"]))
@is_admin()
async def pause_chat(ctx):
    global is_paused
    is_paused = True
    await ctx.send("Bot-to-bot conversation paused.", ephemeral=True)

@bot.hybrid_command(name="resume_chat", description="[Admin] Resumes the bot-to-bot conversation.", guild=discord.Object(id=GLOBAL_CONFIG["GUILD_ID"]))
@is_admin()
async def resume_chat(ctx):
    global is_paused
    is_paused = False
    await ctx.send("Bot-to-bot conversation resumed.", ephemeral=True)

@bot.hybrid_command(name="bot_status", description="Displays the current status of the bots.", guild=discord.Object(id=GLOBAL_CONFIG["GUILD_ID"]))
async def bot_status(ctx):
    embed = discord.Embed(title="Bot Status", color=discord.Color.blue())
    for key, b in bot.bots.items():
        embed.add_field(name=b.config['name'], value=f"**Model:** {b.config['model']}\n**Temp:** {b.config['temperature']}", inline=False)
    await ctx.send(embed=embed)

@bot.hybrid_command(name="swap_model", description="[Admin] Swaps the model for a bot.", guild=discord.Object(id=GLOBAL_CONFIG["GUILD_ID"]))
@is_admin()
async def swap_model(ctx, bot_name: str, new_model: str):
    target_bot_key = next((key for key, cfg in BOT_CONFIG.items() if cfg['name'].lower() == bot_name.lower()), None)
    if not target_bot_key:
        await ctx.send(f"Bot '{bot_name}' not found.", ephemeral=True)
        return
    bot.bots[target_bot_key].config['model'] = new_model
    await ctx.send(f"{bot_name}'s model has been updated to `{new_model}`.", ephemeral=True)

@bot.hybrid_command(name="set_personality", description="[Admin] Sets the personality for a bot.", guild=discord.Object(id=GLOBAL_CONFIG["GUILD_ID"]))
@is_admin()
async def set_personality(ctx, bot_name: str, *, personality: str):
    target_bot_key = next((key for key, cfg in BOT_CONFIG.items() if cfg['name'].lower() == bot_name.lower()), None)
    if not target_bot_key:
        await ctx.send(f"Bot '{bot_name}' not found.", ephemeral=True)
        return
    bot.bots[target_bot_key].config['personality'] = personality
    await ctx.send(f"{bot_name}'s personality has been updated.", ephemeral=True)

@bot.hybrid_command(name="set_temperature", description="[Admin] Sets the temperature for a bot.", guild=discord.Object(id=GLOBAL_CONFIG["GUILD_ID"]))
@is_admin()
async def set_temperature(ctx, bot_name: str, temperature: float):
    target_bot_key = next((key for key, cfg in BOT_CONFIG.items() if cfg['name'].lower() == bot_name.lower()), None)
    if not target_bot_key:
        await ctx.send(f"Bot '{bot_name}' not found.", ephemeral=True)
        return
    bot.bots[target_bot_key].config['temperature'] = temperature
    await ctx.send(f"{bot_name}'s temperature has been updated to `{temperature}`.", ephemeral=True)

# --- Main Execution ---
async def main():
    global shared_conversation_manager
    shared_conversation_manager = ConversationManager()
    # The primary bot token is used for the main client and slash commands
    primary_bot_token = os.getenv("TOKEN1") 
    if not primary_bot_token:
        logger.error("Primary bot token (TOKEN1) is missing. Cannot start.")
        return
    await bot.start(primary_bot_token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down bots...")
