import discord
import random
import os
from discord import app_commands

# Token
TOKEN = ''

# Set folder paths
IMAGES_FOLDER = os.path.join(os.path.dirname(__file__), 'images')
VIDEOS_FOLDER = os.path.join(os.path.dirname(__file__), 'videos')

# Bot class
class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

# Initialize bot
bot = MyBot()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

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

# Run bot
bot.run(TOKEN)
