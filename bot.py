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
}

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

# Command: /zdjecie
@bot.tree.command(name="zdjecie", description="Wyślij śmieszne zdjęcie konrad")
async def zdjecie(interaction: discord.Interaction):
    images = os.listdir(IMAGES_FOLDER)
    random_image = random.choice(images)
    with open(os.path.join(IMAGES_FOLDER, random_image), 'rb') as file:
        await interaction.response.send_message(file=discord.File(file))

# Command: /filmik
@bot.tree.command(name="filmik", description="Wyślij śmieszny filmik konrad")
async def filmik(interaction: discord.Interaction):
    videos = os.listdir(VIDEOS_FOLDER)
    random_video = random.choice(videos)
    with open(os.path.join(VIDEOS_FOLDER, random_video), 'rb') as file:
        await interaction.response.send_message(file=discord.File(file))

@bot.tree.command(name="leave", description="Wypierdalaj z kanału")
async def wyjazd(interaction: discord.Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        bot.song_queue.clear()  # Clear the queue on leave
        bot.loop_song = False  # Turn off looping when leaving
        await interaction.response.send_message("Już poszedłem.")
    else:
        await interaction.response.send_message("Przecież nigdzie mnie nie ma, odpierdolisz się?.")

@bot.tree.command(name="play", description="Puść jakiegoś umca umca")
async def Brzdęknij(interaction: discord.Interaction, query: str):
    # Check if the user is in a voice channel
    if not interaction.user.voice:
        return await interaction.response.send_message("Musisz być na kanale głosowym, żeby puścić muzykę.")

    # Acknowledge the interaction immediately
    await interaction.response.defer(thinking=True)

    # Get the current voice client
    voice_client = interaction.guild.voice_client

    # Check if the bot is already in a voice channel
    if voice_client is None:
        channel = interaction.user.voice.channel
        voice_client = await channel.connect()

    # Add the song to the queue
    bot.song_queue.append(query)
    await interaction.followup.send(f'Dodano do kolejki: {query}')

    # If the bot is not playing, start playing immediately
    if not voice_client.is_playing() and not voice_client.is_paused():
        await play_next(voice_client)

async def play_next(voice_client):
    if bot.loop_song and bot.current_song:
        player = await YTDLSource.from_query(bot.current_song, loop=bot.loop)
    elif len(bot.song_queue) > 0:
        bot.current_song = bot.song_queue.popleft()  # Get the next song from the queue
        player = await YTDLSource.from_query(bot.current_song, loop=bot.loop)
    else:
        bot.current_song = None  # Clear the current song if no songs are left
        bot.loop_song = False  # Disable loop if there are no more songs
        await voice_client.disconnect()  # Disconnect if the queue is empty
        return

    # Play the audio
    voice_client.play(player, after=lambda e: bot.loop.create_task(play_next(voice_client)))
    print(f'Now playing: **{player.data["title"]}**')

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

@bot.tree.command(name="loop", description="Toggle looping for the current song")
async def loop(interaction: discord.Interaction):
    bot.loop_song = not bot.loop_song  # Toggle loop mode
    status = "enabled" if bot.loop_song else "disabled"
    await interaction.response.send_message(f"Looping is now {status}.")

# Run bot
bot.run(TOKEN)
