import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get

import asyncio
from async_timeout import timeout
import youtube_dl
from youtube_dl import YoutubeDL
from functools import partial
import concurrent.futures
import itertools


################ YTDL VARIABLES ################

# music_folder = os.getcwd() + '\music'
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
            data = data['entries'][0]  # First entry in a playlist if given

        await ctx.send(f"Added {data['title']} to queue.")

        if download:
            source = ydl.prepare_filename(data).replace('.webm', '.mp3')  # Temp fix for download=True in '_play' function
            print(f"DEBUG: create_source, source = {source}")
        else:
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source), data=data, requester=ctx.author)

    @classmethod
    async def prepare_stream(cls, data, *, loop):
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        data_to_run = partial(ydl.extract_info, url=data['webpage_url'], download=True)
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
            self.next.clear()
            try:
                async with timeout(30):
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                print("DEBUG: Player has timed out due to no songs in queue.")
                return self.destroy(self.guild)  # Disconnects from guild

            if not isinstance(source, YTDLSource): # When download=False in '_play' function
                try:
                    source = await YTDLSource.prepare_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self.channel.send(f"Error processing song. Exception: {e}")

            source.volume = self.volume
            self.current = source

            self.guild.voice_client.play(source, after=lambda e: self.bot.loop.call_soon_threadsafe(self.next.set))
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

##############################     VOICE COMMANDS    ##############################

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del(self.guilds[guild.id])
        except KeyError:
            pass

    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            print("DEBUG: Music player not found... Creating new...")
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
        return player

    @commands.command(name='play', aliases=['p'])
    async def _play(self, ctx, url):
        bot_voice = ctx.voice_client
        if not bot_voice:
            try:
                user_channel = ctx.message.author.voice.channel
                await user_channel.connect()
            except:
                return await ctx.send("Please join a channel first then retry.")

        player = self.get_player(ctx)
        # If download=True, URL downloaded and queued as Discord.FFmpegPCMAudio object
        # If download=False, URL queued as dict to be streamed through bot (Doesn't work. Known streaming issue with YTDL as of 07/06/20)
        source = await YTDLSource.create_source(ctx, url, loop=self.bot.loop, download=True)
        await player.queue.put(source)
        print(f"DEBUG: Successfully queued!")

    @commands.command(name='queue', aliases=['q'])
    async def _queue(self, ctx):
        '''
        Shows a list of 10 requests in queue
        '''
        bot_voice = ctx.voice_client
        if not bot_voice:
            return await ctx.send("I'm currently not in a voice channel!")

        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send("There are no songs queued")

        queue = list(itertools.islice(player.queue._queue, 0, 10))  # Lists first 10 on queue
        queue_string = '\n'.join(f"{idx + 1}. '{entry.title}' from {entry.requester}"
                                 for idx, entry in enumerate(queue))
        embed = discord.Embed(title=f"Listing next {len(queue)} from queue", description=queue_string)

        await ctx.send(embed=embed)


    @commands.command(pass_context=True, name='current', aliases=['np'])
    async def _current(self, ctx):
        bot_voice = ctx.voice_client
        if not bot_voice:
            return await ctx.send("I'm currently not in a voice channel!")

        player = self.get_player(ctx)
        if not player.current:
            return await ctx.send("Currently not playing anything")

        player.np = await ctx.send(f"Currently playing '{bot_voice.source.title}' requested by "
                                          f"{bot_voice.source.requester}")

    @commands.command(name='pause')
    async def _pause(self, ctx):
        bot_voice = ctx.voice_client
        if not bot_voice: return await(ctx.send("I'm not in a voice channel"))

        try:
            user_channel = ctx.message.author.voice.channel
        except:
            return await ctx.send("You're not in a voice channel!")
        if bot_voice.channel != user_channel: return await ctx.send("We're not in the same voice channel!")

        if not bot_voice.is_playing():
            return await ctx.send("I'm not playing anything!")
        elif bot_voice.is_paused():
            return await ctx.send("Already paused!")

        bot_voice.pause()
        await ctx.send("Song paused.")

    @commands.command(name='resume')
    async def _resume(self, ctx):
        bot_voice = ctx.voice_client
        if not bot_voice: return await ctx.send("I'm not in a voice channel!")

        try:
            user_channel = ctx.message.author.voice.channel
        except:
            return await ctx.send("You're not in a voice channel!")
        if bot_voice.channel != user_channel: return await ctx.send("We're not in the same voice channel!")

        if bot_voice.is_paused():
            bot_voice.resume()
            return await ctx.send(f"Resumed playing {bot_voice.source.title}")
        else:
            return await ctx.send("I'm not playing anything!")

    @commands.command(name='volume', aliases=['vol'])
    async def _volume(self, ctx, vol: int):
        bot_voice = ctx.voice_client
        if not bot_voice:
            return await ctx.send("I'm not in a voice channel!")

        try:
            user_channel = ctx.message.author.voice.channel
        except:
            return await ctx.send("You're not in a voice channel!")
        if bot_voice.channel != user_channel: return await ctx.send("We're not in the same voice channel!")

        if not bot_voice.source:
            await ctx.send("I'm not playing anything!")
        else:
            vol = 200 if vol > 200 else vol
            bot_voice.source.volume = vol / 100
            await ctx.send(f"Volume set to {vol}%")