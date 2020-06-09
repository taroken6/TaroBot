import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get

import youtube_dl
import os
import random

TOKEN = '' # BOT TOKEN HERE
BOT_PREFIX = 't!'
IMAGE_FOLDER = 'images/'

bot = commands.Bot(command_prefix=BOT_PREFIX)

players = {}

##############################     GENERAL COMMANDS     ##############################

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("Yeet"))
    print('We have logged in as {0.user}'.format(bot))

@bot.command(pass_context=True, aliases=['r'])
async def reply(ctx, *, question):
    responses = ["Yes", "Maybe", "No"]
    await ctx.send(f"question: {question}\nanswer: {random.choice(responses)}")

@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! {round(bot.latency * 1000)} ms')

@bot.command()
async def join(ctx):
    channel = ctx.message.author.voice.channel
    await channel.connect()
    print(f'Joined {channel}')
    await ctx.send(f"Joined \'{channel}\' channel.")


@bot.command()
async def leave(ctx):
    server = ctx.message.guild.voice_client
    await ctx.send(f"Left {server}")
    await server.disconnect()

##############################     AUDIO COMMANDS    ##############################

@bot.command()
async def connected(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice.is_connected():
        await ctx.send("Connected...")

@bot.command(pass_context=True, aliases=['p'])
async def play(ctx, url: str):

    musicFolder = os.getcwd() + '\music'
    name = ''

    await ctx.send("Loading song...")
    print(f"Music folder is: {musicFolder}")

    voice = get(bot.voice_clients, guild=ctx.guild)
    ydl_opts = {
        'outtmpl': 'music/%(title)s-%(id)s.%(ext)s',  # TODO: Fix this
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        print("Downloading song...")
        ydl.download([url])
        info_dict = ydl.extract_info(url, download=False)
        video_url = info_dict.get("url", None)  # Temp google video file
        video_id = info_dict.get("id", None)
        video_title = info_dict.get('title', None)
        print(f"\nVideo Info:\nURL: {video_url}\nID: {video_id}\nTitle: {video_title}\n") # DEBUG

    fileName = musicFolder + '\\' + video_title + '-' + video_id + ".mp3"
    print(f"Path found: {os.path.isdir(musicFolder)}")

    voice.play(discord.FFmpegPCMAudio(fileName), after=lambda e: print(f"{fileName} finished downloading."))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 0.2

    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(video_title))
    await ctx.send(f"Playing: {video_title}")
    print("Playing")

@bot.command(pass_context=True, aliases=['vol'])
async def volume(ctx, vol: int):
    voice = get(bot.voice_clients, guild=ctx.guild)
    vol = 200 if vol > 200 else vol
    voice.source.volume = vol / 100
    await ctx.send(f"Volume set to {vol}%")

##############################     MEME COMMANDS    ##############################

@bot.command()
async def jerry(ctx):
    await ctx.send('jERry', file=discord.File(IMAGE_FOLDER + 'jerry.jpg'))

bot.run(TOKEN)