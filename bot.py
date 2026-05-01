import discord
from discord.ext import commands, tasks
import asyncio
import os

# ── Config ──────────────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID", "0"))
SOUND_FILE = "Chouni Laugh.wav"  # name of your audio file — must be in the same folder

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

async def play_sound():
    """Play the sound file in the current voice channel."""
    for guild in bot.guilds:
        vc = guild.voice_client
        if vc and vc.is_connected():
            if vc.is_playing():
                vc.stop()
            source = discord.FFmpegPCMAudio(SOUND_FILE)
            vc.play(source)
            print("[♪] Playing sound!")

# ── Events ───────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"[✓] Logged in as {bot.user} ({bot.user.id})")
    await join_target_channel()
    watchdog.start()
    sound_loop.start()

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

# ── Sound loop ───────────────────────────────────────────────────────────────
@tasks.loop(hours=3)
async def sound_loop():
    """Play the sound every 3 hours."""
    await play_sound()

@sound_loop.before_loop
async def before_sound_loop():
    await bot.wait_until_ready()

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

@bot.command(name="play")
async def play_cmd(ctx):
    """!play — manually trigger the sound."""
    await play_sound()
    await ctx.send("🔊 Playing sound!")

# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not TOKEN:
        raise ValueError("Set the DISCORD_TOKEN environment variable.")
    if TARGET_CHANNEL_ID == 0:
        raise ValueError("Set the VOICE_CHANNEL_ID environment variable.")
    bot.run(TOKEN)
