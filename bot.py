import discord
import random
import os
import yt_dlp as youtube_dl
import asyncio
from collections import deque
from discord import app_commands

# Token
TOKEN = os.getenv('TOKEN')

# Set folder paths
IMAGES_FOLDER = os.path.join(os.path.dirname(__file__), 'images')
VIDEOS_FOLDER = os.path.join(os.path.dirname(__file__), 'videos')

# Setup youtube_dl options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',  # Ensure you have FFmpeg installed
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'noplaylist': True,
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data

    @classmethod
    async def from_url(cls, url, *, loop=None, volume=0.5):
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
            if 'entries' in data:
                data = data['entries'][0]
            filename = data['url']
            source = discord.FFmpegPCMAudio(filename)
            return cls(source, data=data, volume=volume)
        except Exception as e:
            print(f"Error extracting info: {e}")
            return None

# Bot class
class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Enable the message content intent
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)  # Initialize the command tree correctly
        self.song_queue = deque()  # Initialize the song queue
        self.activity_check_task = None  # Task for checking inactivity

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        await self.tree.sync()  # Synchronize commands with Discord
        print("Commands synchronized!")

    async def check_inactivity(self, voice_client):
        await asyncio.sleep(600)  # Wait for 10 minutes
        if not voice_client.is_playing():
            await voice_client.disconnect()
            self.activity_check_task = None  # Clear the task after disconnecting

# Initialize bot
bot = MyBot()

# Command: /zdjecie
@bot.tree.command(name="zdjecie", description="Send a random image")
async def zdjecie(interaction: discord.Interaction):
    images = os.listdir(IMAGES_FOLDER)
    random_image = random.choice(images)
    with open(os.path.join(IMAGES_FOLDER, random_image), 'rb') as file:
        await interaction.response.send_message(file=discord.File(file))

# Command: /filmik
@bot.tree.command(name="filmik", description="Send a random video")
async def filmik(interaction: discord.Interaction):
    videos = os.listdir(VIDEOS_FOLDER)
    random_video = random.choice(videos)
    with open(os.path.join(VIDEOS_FOLDER, random_video), 'rb') as file:
        await interaction.response.send_message(file=discord.File(file))

@bot.tree.command(name="join", description="Join a voice channel")
async def join(interaction: discord.Interaction):
    if interaction.user.voice:
        channel = interaction.user.voice.channel
        await channel.connect()
        await interaction.response.send_message(f"Joined {channel}")
    else:
        await interaction.response.send_message("You need to be in a voice channel to use this command.")

@bot.tree.command(name="leave", description="Leave the voice channel")
async def leave(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        bot.song_queue.clear()  # Clear the queue on leave
        bot.activity_check_task = None  # Clear the task
        await interaction.response.send_message("Disconnected from the voice channel.")
    else:
        await interaction.response.send_message("I'm not in a voice channel.")

@bot.tree.command(name="play", description="Play a song from a YouTube link")
async def play(interaction: discord.Interaction, url: str):
    # Check if the user is in a voice channel
    if not interaction.user.voice:
        return await interaction.response.send_message("You need to be in a voice channel to play music.")

    # Get the current voice client
    voice_client = interaction.guild.voice_client

    # Check if the bot is already in a voice channel
    if voice_client is None:
        channel = interaction.user.voice.channel
        voice_client = await channel.connect()

    # Add the song to the queue
    bot.song_queue.append(url)
    await interaction.response.send_message(f'Added to queue: {url}')

    # Play if not already playing
    if not voice_client.is_playing() and len(bot.song_queue) > 0:
        await play_next(voice_client)

    # Start the inactivity check if it's not already running
    if bot.activity_check_task is None:
        bot.activity_check_task = bot.loop.create_task(bot.check_inactivity(voice_client))

async def play_next(voice_client):
    if len(bot.song_queue) > 0:
        url = bot.song_queue.popleft()  # Get the next song from the queue
        player = await YTDLSource.from_url(url, loop=bot.loop)
        if player is None:
            print("Failed to load player, trying next song.")
            await play_next(voice_client)
            return
        voice_client.play(player, after=lambda e: bot.loop.create_task(play_next(voice_client)))
        print(f'Now playing: **{player.data["title"]}**')
    else:
        await voice_client.disconnect()  # Disconnect if the queue is empty

@bot.tree.command(name="stop", description="Stop the music")
async def stop(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Music stopped.")
    else:
        await interaction.response.send_message("No music is currently playing.")

@bot.tree.command(name="pause", description="Pause the music")
async def pause(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        await interaction.response.send_message("Music paused.")
    else:
        await interaction.response.send_message("No music is currently playing.")

@bot.tree.command(name="resume", description="Resume the music")
async def resume(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        await interaction.response.send_message("Music resumed.")
    else:
        await interaction.response.send_message("Music is not paused.")

@bot.tree.command(name="skip", description="Skip the currently playing song")
async def skip(interaction: discord.Interaction):
    if interaction.guild.voice_client and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Skipped the currently playing song.")
    else:
        await interaction.response.send_message("No music is currently playing.")

@bot.tree.command(name="queue", description="Show the current music queue")
async def queue(interaction: discord.Interaction):
    if bot.song_queue:
        queue_list = "\n".join(bot.song_queue)
        await interaction.response.send_message(f"Current queue:\n{queue_list}")
    else:
        await interaction.response.send_message("The queue is currently empty.")

# Run bot
bot.run(TOKEN)
