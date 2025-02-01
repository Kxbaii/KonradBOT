import discord
import random
import os
import yt_dlp as youtube_dl
import asyncio
from collections import deque
from discord import app_commands
import re

# Token
TOKEN = os.getenv('TOKEN')

# Set folder paths
IMAGES_FOLDER = os.path.join(os.path.dirname(__file__), 'images')
VIDEOS_FOLDER = os.path.join(os.path.dirname(__file__), 'videos')

# Setup youtube_dl options for search
ytdl_format_options = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'noplaylist': True,
    'default_search': 'ytsearch',  # Enables search functionality for song names
    'quiet': True,  # Suppress verbose output
    'cookiefile': 'cookies.txt',  # Use authenticated cookies
}

# Check if cookies.txt exists
if not os.path.exists("cookies.txt"):
    print("⚠️ Warning: cookies.txt not found! Some videos may not play.")

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Regular expression to check if a string is a URL
URL_REGEX = re.compile(
    r'^(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/.+$'
)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data

    @classmethod
    async def from_query(cls, query, *, loop=None, volume=0.5):
        """Handles both URLs and search queries."""
        loop = loop or asyncio.get_event_loop()
        
        # Determine if query is a URL
        is_url = URL_REGEX.match(query)
        
        # Extract info based on URL or search
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        if 'entries' in data:  # For search queries, take the first result
            data = data['entries'][0]
        
        filename = data['url']
        source = discord.FFmpegPCMAudio(filename)
        return cls(source, data=data, volume=volume)

# Bot class
class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Enable the message content intent
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)  # Initialize the command tree correctly
        self.song_queue = deque()  # Initialize the song queue
        self.loop_song = False  # Add a loop flag
        self.current_song = None  # Track the currently playing song

    async def on_ready(self):
        print(f'Logged in as {self.user}')
        await self.tree.sync()  # Synchronize commands with Discord
        print("Commands synchronized!")

# Initialize bot
bot = MyBot()

@bot.tree.command(name="play", description="Puść jakiegoś umca umca")
async def Brzdęknij(interaction: discord.Interaction, query: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("Musisz być na kanale głosowym, żeby puścić muzykę.")

    await interaction.response.defer(thinking=True)

    voice_client = interaction.guild.voice_client
    if voice_client is None:
        channel = interaction.user.voice.channel
        voice_client = await channel.connect()

    bot.song_queue.append(query)
    await interaction.followup.send(f'Dodano do kolejki: {query}')

    if not voice_client.is_playing() and not voice_client.is_paused():
        await play_next(voice_client)

async def play_next(voice_client):
    if bot.loop_song and bot.current_song:
        player = await YTDLSource.from_query(bot.current_song, loop=bot.loop)
    elif len(bot.song_queue) > 0:
        bot.current_song = bot.song_queue.popleft()
        player = await YTDLSource.from_query(bot.current_song, loop=bot.loop)
    else:
        bot.current_song = None
        bot.loop_song = False
        await voice_client.disconnect()
        return

    voice_client.play(player, after=lambda e: bot.loop.create_task(play_next(voice_client)))
    print(f'Now playing: **{player.data["title"]}**')

bot.run(TOKEN)
