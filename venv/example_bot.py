import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get

import youtube_dl
from youtube_dl import YoutubeDL
import os
import random
import concurrent.futures
import asyncio

from SongObj import Song
from SoundObj import Sound

################ GLOBAL VARIABLES ################

TOKEN = '' # Bot token here
BOT_PREFIX = 't!'
IMAGE_FOLDER = 'images/'
playlist = []
playing = False
song_playing = None
music_folder = os.getcwd() + '\music'
sound_folder = os.getcwd() + '\sounds\\'

################ YTDL VARIABLES ################

ydl_opts = {
    'outtmpl': 'music/%(title)s-%(id)s.%(ext)s',  # TODO: Fix this
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

ydl = YoutubeDL(ydl_opts)

################  ################


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

@bot.command(name="id")
async def getID(ctx):
    await ctx.send(ctx.author.id)


##############################     MUSIC PLAYER / YTDL    ##############################

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

    @classmethod
    async def create_source(cls, ctx, url: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        data_to_run = partial(ydl.extract_info, url=url, download=download)
        data = await loop.run_in_executor(None, data_to_run)

        if 'entries' in data:
            data = data['entries'][0]

        await ctx.send(f"Added {data['title']} to queue.")

        if download:
            source = ydl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

    @classmethod
    async def prepare_stream(cls, data, *, loop):
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        data_to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, data_to_run)
        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)

class MusicPlayer:
    '''
    Music player assigned to each guild that it connects
    '''
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.cog = ctx.cog  # Note: Cogs are a collection of commands and listeners

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.playing = None
        self.volume = 0.2
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            try:
                async with timeout(300):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return self.destroy(self.guild)  # Disconnects from guild

        if not isinstance(source, YTDLSource):
            try:
                source = await YTDLSource.prepare_stream(source, loop=self.bot.loop)
            except Exception as e:
                await self.channel.send(f"Error processing song. Exception: {e}")

        source.volume = self.volume
        self.current = source

        self.guild.voice_client.play(source, after=lambda e: print("Done playing song..."))
        self.np = await self.channel.send(f"Now playing: {source.title}. Requested by {source.requester}")

        await self.next.wait()

        source.cleanup()
        self.current = None

        try:
            await self.np.delete()
        except discord.HTTPException:
            pass

    def destroy(self, guild):
        return self.bot.loop.create_task(self.cog.cleanup(guild))

##############################     AUDIO COMMANDS    ##############################
class Voice:
    def __init__(self, bot):
        self.bot = bot
        self.guilds = {}

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del(self.guilds[guild.id])
        except KeyError:
            pass

    @bot.command(name='connect', aliases=['join'])
    async def connect(ctx):
        isConnected = ctx.message.author.voice is not None
        if isConnected:
            channel = ctx.message.author.voice.channel
            await channel.connect()
            print(f'Joined {channel}')
            await ctx.send(f"Joined \'{channel}\' channel.")
        else:
            await ctx.send("You're not in a voice channel")

    @bot.command(name='disconnect', aliases=['leave'])
    async def disconnect(ctx):
        server = ctx.message.guild.voice_client
        await ctx.send(f"Left {server}")  # Prints out object for now
        await server.disconnect()

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
        await ctx.send("Loading song...")

        with ydl:
            print("Downloading song...")
            info_dict = ydl.extract_info(url, download=False)
            video_id = info_dict.get("id", None)
            video_title = info_dict.get('title', None)

        ###### Play ######

        fileName = music_folder + '\\' + video_title + '-' + video_id + ".mp3"
        playlist.append(Song(video_title, video_id, url, fileName))
        if not os.path.exists(fileName):
            print("DEBUG: File doesn't exist. Downloading...")
            ydl.download([url])

        voice = get(bot.voice_clients, guild=ctx.guild)
        if not voice:
            try:
                channel = ctx.message.author.voice.channel
                await channel.connect()
                voice = get(bot.voice_clients, guild=ctx.guild)
            except AttributeError:
                await ctx.send("No channel to join. Please join one.")
                raise Exception("No channel to join. Please join one.")

        voice.play(discord.FFmpegPCMAudio(playlist[0].file), after=lambda e: print(f"{video_title} finished playing."))
        voice.source = discord.PCMVolumeTransformer(voice.source)
        voice.source.volume = 0.2

        await bot.change_presence(status=discord.Status.idle, activity=discord.Game(video_title))
        await ctx.send(f"Playing: {video_title}")
        print("Playing...")

    @bot.command()
    async def queue(ctx, url: str):
        with ydl:
            info_dict = ydl.extract_info(url, download=False)
            video_id = info_dict.get("id", None)
            video_title = info_dict.get('title', None)
            print(f"\n### Queued ### \nVideo Info:\nID: {video_id}\nTitle: {video_title}\n") # DEBUG

        ###### Queue ######

        file_name = music_folder + '\\' + video_title + '-' + video_id + ".mp3"
        playlist.append(Song(video_title, video_id, url, file_name))

    @bot.command(pass_context=True, aliases=['np'])
    async def current(ctx):
        index = 1
        if len(playlist) == 0:
            await ctx.send("No songs in playlist")
        else:
            for index, song in enumerate(playlist):
                await ctx.send(f"{index}. {song.title}")

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

@bot.command(pass_context=True, aliases=['s'])
async def sound(ctx, *args):
    soundlist = {
        "horn": Sound("horn", sound_folder + "airhorn.mp3", "MLG airhorn - Once"),
        "wow": Sound("wow", sound_folder + "anime_wow.mp3", "Japanese wow~"),
        "bullyme": Sound("bullyme", sound_folder + "bully_me.mp3", "Why you bully me"),
        "clench": Sound("clech", sound_folder + "clench.mp3", "Clench the butt cheeks"),
        "deez": Sound("deez", sound_folder + "deez_nuts.mp3", "Deez Nuts"),
        "discnotif": Sound("discnotif", sound_folder + "disc_notif.mp3", "Discord notification sound"),
        "nope": Sound("nope", sound_folder + "engi_nope.mp3", "engineer's nope.avi"),
        "fastaf": Sound("fastaf", sound_folder + "fast_af.mp3", "I'm fast AF boi"),
        "grapefruit": Sound("grapefruit", sound_folder + "grapefruit.mp3", "KWWHEKEWWHKWHKWHE"),
        "hourlater": Sound("hourlater", sound_folder + "hour_later.mp3", "One hour later..."),
        "mlghorn": Sound("mlghorn", sound_folder + "mlg_horn.mp3", "MLG airhorn"),
        "notfunny": Sound("notfunny", sound_folder + "not_funny.mp3", "Not funny, didn't laugh"),
        "ohmygah": Sound("ohmygah", sound_folder + "oh_my_gah.mp3", "Oh my gah"),
        "oof": Sound("oof", sound_folder + "oof.mp3", "OOF"),
        "pbb": Sound("pbb", sound_folder + "pbb.mp3", "\"Does that feel good?\""),
        "pika": Sound("pika", sound_folder + "pika.mp3", "Pika pika~~~"),
        "prettygood": Sound("prettygood", sound_folder + "pretty_good.mp3", "Hey, thta's pretty good."),
        "risitas": Sound("risitas", sound_folder + "risitas.mp3", "JESUS, AHHHH AH AH AH"),
        "skype": Sound("skype", sound_folder + "skype_call.mp3", "Skype call tone"),
        "snort": Sound("snort", sound_folder + "snort.mp3", "The Spy's mating call"),
        "succ": Sound("succ", sound_folder + "succ.mp3", "SUCC"),
        "tidus": Sound("tidus", sound_folder + "tidus.mp3", "AH HAH HAH HAH"),
        "triple": Sound("triple", sound_folder + "triple.mp3", "Oh baby a triple"),
        "typing": Sound("typing", sound_folder + "typing.mp3", "*type noises intesify*"),
        "weakhorn": Sound("weakhorn", sound_folder + "weak_horn.mp3", "Sad air horn"),
        "whoa": Sound("whoa", sound_folder + "woah.mp3", "Whoa? whoa... WHOA WHOA WHOA WHOA"),
        "wow": Sound("wow", sound_folder + "wow.mp3", "Wow."),
        "wronghouse": Sound("wronghouse", sound_folder + "wrong_house.mp3", "You came to the wrong house foo!"),
        "yeahboi": Sound("yeahboi", sound_folder + "yeah_boi.mp3", "Yeah boiiiiiiiiiiiiiiiiii"),
        "yeet": Sound("yeet", sound_folder + "yeet.mp3", "Swaggersoul's yeet"),
        "subaluwa": Sound("subaluwa", sound_folder + "subaluwa.mp3", "Iconic Ed, Edd, n Eddy sumo noise"),
        "dude": Sound("dude", sound_folder + "dude.mp3", "How's it goin' dude?")
    }
    default_vol = 0.20
    sound = args[0]
    try:
        vol = (float)(args[1]) / 100
        print(f"DEBUG: set volume to {vol}")
    except IndexError:
        print(f"DEBUG: set volume to {default_vol}")
        vol = default_vol

    if sound == 'help' or sound == 'h':
        embed = discord.Embed(
            title="Sound commands:",
            description="t!s [sound] [volume (0 - 200)]",
            color=discord.Colour.teal()
        )
        for key, value in soundlist.items():
            embed.add_field(name=soundlist[key].name, value=soundlist[key].desc, inline=False)
        await ctx.send(embed=embed)
    else:
        voice = get(bot.voice_clients, guild=ctx.guild)
        if voice is None:
            if ctx.message.author.voice is not None:
                channel = ctx.message.author.voice.channel
                await channel.connect()
                voice = get(bot.voice_clients, guild=ctx.guild)
            else:
                await ctx.send("Either me or you are not in a voice channel")
                return
        voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(soundlist[sound].file), vol), after=None)

bot.run(TOKEN)