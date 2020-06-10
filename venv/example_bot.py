import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get

import youtube_dl
import os
import random

TOKEN = '' # Bot token here
BOT_PREFIX = 't!'
IMAGE_FOLDER = 'images/'
playlist = []

bot = commands.Bot(command_prefix=BOT_PREFIX)

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
    isConnected = ctx.message.author.voice is not None
    if isConnected:
        channel = ctx.message.author.voice.channel
        await channel.connect()
        print(f'Joined {channel}')
        await ctx.send(f"Joined \'{channel}\' channel.")
    else:
        await ctx.send("You're not in a voice channel")


@bot.command()
async def leave(ctx):
    server = ctx.message.guild.voice_client
    await ctx.send(f"Left {server}")
    await server.disconnect()

@bot.command(name="id")
async def getID(ctx):
    await ctx.send(ctx.author.id)


##############################     AUDIO COMMANDS    ##############################

@bot.command()
async def connected(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice is None:
        await ctx.send("Not connected")
    elif voice.is_connected():
        await ctx.send("Connected...")

@bot.command(pass_context=True, aliases=['p'])
async def play(ctx, url: str):

    ###### Setup ######

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
        info_dict = ydl.extract_info(url, download=False)
        video_id = info_dict.get("id", None)
        video_title = info_dict.get('title', None)
        print(f"\nVideo Info:\nID: {video_id}\nTitle: {video_title}\n") # DEBUG

    ###### Play ######

    fileName = musicFolder + '\\' + video_title + '-' + video_id + ".mp3"
    playlist.append(fileName)
    if not os.path.exists(fileName):
        print("DEBUG: File doesn't exist. Downloading...")
        ydl.download([url])

    if voice is None:
        if ctx.message.author.voice is not None:
            channel = ctx.message.author.voice.channel
            await channel.connect()
            voice = get(bot.voice_clients, guild=ctx.guild)
        else:
            await ctx.send("Either me or you are not in a voice channel")
            return
    voice.play(discord.FFmpegPCMAudio(fileName), after=lambda e: print(f"{fileName} finished playing."))
    voice.source = discord.PCMVolumeTransformer(voice.source)
    voice.source.volume = 0.2

    await bot.change_presence(status=discord.Status.idle, activity=discord.Game(video_title))
    await ctx.send(f"Playing: {video_title}")
    print("Playing...")

@bot.command()
async def pause(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice is not None and voice.is_playing():
        voice.pause()
        await ctx.send("Paused")

@bot.command()
async def resume(ctx):
    voice = get(bot.voice_clients, guild=ctx.guild)
    if voice is not None and voice.is_paused():
        voice.resume()
        await ctx.send(f"Resumed playing {voice.source}")

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