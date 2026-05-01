import discord
from discord.ext import commands, tasks
import asyncio
import os

# ── Config ──────────────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN")          # set in your environment
TARGET_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID", "0"))  # voice channel ID

# ── Bot setup ────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ── Helpers ──────────────────────────────────────────────────────────────────
async def join_target_channel():
    """Connect (or move) to the target voice channel."""
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel is None or not isinstance(channel, discord.VoiceChannel):
        print(f"[!] Channel {TARGET_CHANNEL_ID} not found or is not a voice channel.")
        return

    guild = channel.guild
    vc = guild.voice_client

    if vc is None:
        await channel.connect(reconnect=True)
        print(f"[+] Joined '{channel.name}'")
    elif vc.channel != channel:
        await vc.move_to(channel)
        print(f"[+] Moved to '{channel.name}'")

# ── Events ───────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"[✓] Logged in as {bot.user} ({bot.user.id})")
    await join_target_channel()
    watchdog.start()

@bot.event
async def on_voice_state_update(member, before, after):
    """Rejoin immediately if the bot is disconnected."""
    if member != bot.user:
        return
    if before.channel is not None and after.channel is None:
        print("[!] Disconnected — rejoining in 3 s...")
        await asyncio.sleep(3)
        await join_target_channel()

# ── Watchdog loop ────────────────────────────────────────────────────────────
@tasks.loop(seconds=30)
async def watchdog():
    """Periodic check — reconnects if the voice client silently died."""
    for guild in bot.guilds:
        vc = guild.voice_client
        if vc is None or not vc.is_connected():
            print("[watchdog] Not connected — rejoining...")
            await join_target_channel()

# ── Commands ─────────────────────────────────────────────────────────────────
@bot.command(name="join")
@commands.has_permissions(administrator=True)
async def join_cmd(ctx):
    """!join — force the bot into the target channel."""
    await join_target_channel()
    await ctx.send("✅ Joining voice channel!")

@bot.command(name="leave")
@commands.has_permissions(administrator=True)
async def leave_cmd(ctx):
    """!leave — temporarily disconnect (watchdog will rejoin in ~30 s)."""
    vc = ctx.guild.voice_client
    if vc:
        watchdog.stop()
        await vc.disconnect()
        await ctx.send("👋 Left the channel. (watchdog paused — use `!join` to re-enable)")
    else:
        await ctx.send("I'm not in a voice channel.")

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("Set the DISCORD_TOKEN environment variable.")
    if TARGET_CHANNEL_ID == 0:
        raise ValueError("Set the VOICE_CHANNEL_ID environment variable.")
    bot.run(TOKEN)
