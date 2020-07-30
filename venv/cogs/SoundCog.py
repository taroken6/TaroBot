import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get

from SoundObj import Sound
import requests
from lxml import html
from bs4 import BeautifulSoup
import re
import shutil
import time
import os

import pickle
import json

sound_folder = os.getcwd() + '\sounds\\'
default_sound_folder = sound_folder + 'default\\'
help_param = ['help', 'h']
dl_param = ['download', 'dl']
del_param = ['delete', 'del']
reserved_names = help_param + dl_param + del_param

##############################     SOUND PLAYER    ##############################

class SoundPlayer():
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild

        self.folder = self.get_folder()
        self.json_file = self.folder + "soundlist.txt"
        self.volume = 0.2
        self.soundlist = {}
        self.deserialize()

    def get_folder(self):
        folder = sound_folder + str(self.guild.id) + "\\"
        if not os.path.isdir(folder):
            shutil.copytree(default_sound_folder, folder)
        return folder

    def serialize(self):
        data = {}
        for s in self.soundlist.keys():
            sound = self.soundlist[s]
            data[sound.name] = {'name': sound.name, 'file': sound.file, 'desc': sound.desc, 'url': sound.url}

        with open(self.json_file, 'w') as sl:
            json.dump(data, sl, indent=2)
            sl.close()

    def deserialize(self):
        if os.path.isfile(self.json_file):
            f = open(self.json_file)
            payload = json.load(f)
            for key, value in payload.items():
                if not key in self.soundlist:
                    self.soundlist[key] = Sound(value['name'], value['file'], value['desc'], value['url'])

    async def _help(self, ctx):
        embeds = []
        MAX_FIELDS = 25  # Max fields is 25 per embed
        pages = (int)(len(self.soundlist) / MAX_FIELDS + 1)

        # Embed's header
        for i in range(1, pages + 1):
            embeds.append(discord.Embed(
                title=f"Sounds commands, Page {i} of {pages}",
                description="t!s [sound name] [volume (0 - 200)]\n"
                            "t!s dl [myinstants.com URL] [name] [description]\n"
                            "example: t!s dl https://www.myinstants.com/instant/crickets/ cricket \"cricket noises\"\n"
                            "t!s del [sound name]",
                color=discord.Colour.teal()
            ))

        # Soundlist
        for idx, (key, value) in enumerate(self.soundlist.items()):
            page = (int)(idx / MAX_FIELDS)
            embeds[page].add_field(name=self.soundlist[key].name,
                                   value=self.soundlist[key].desc,
                                   inline=True)

        left_arrow, right_arrow = '⬅', '➡'
        message = await ctx.send(embed=embeds[0])
        await message.add_reaction(left_arrow)
        await message.add_reaction(right_arrow)
        page = 0
        reaction = ''
        message_timeout = time.time() + 60
        while time.time() < message_timeout:
            if reaction and reaction.member.id != self.bot.user.id:
                if reaction.emoji.name == left_arrow:
                    page -= 1 if page > 0 else 1 - pages
                if reaction.emoji.name == right_arrow:
                    page += 1 if page < pages - 1 else 1 - pages
                await message.edit(embed=embeds[page])
            try:
                reaction = await self.bot.wait_for('raw_reaction_add', timeout=60.0)
            except:
                return print("Timed out")


    async def _download(self, ctx, url, name, desc):  # TODO: Make it so JSON saves onto guild IDs
        # Error handler
        if name in reserved_names:
            return await ctx.send(f"'{name}' is reserved for a command! Please retry with a different name.")
        if 'myinstants.com/instant/' not in url:
            return await ctx.send("URL must contain 'myinstants.com/instant/'")
        if name in self.soundlist.keys():
            msg = await ctx.send(f"The sound '{name}' already exists! Would you like to overwrite?")
            check = '✅'
            x = '❌'
            await msg.add_reaction(check)
            await msg.add_reaction(x)

            # Prompt to overwrite
            reaction = ''
            message_timeout = time.time() + 60
            while time.time() < message_timeout:
                if reaction and reaction.member.id != self.bot.user.id:
                    if reaction.emoji.name == check:
                        break
                    if reaction.emoji.name == x:
                        return await ctx.send("Download cancelled.")
                try:
                    reaction = await self.bot.wait_for('raw_reaction_add', timeout=60.0)
                except:
                    return await ctx.send("Timed out. Sound not downloaded.")

        # Scrape HTML for .mp3 file and write
        soup = BeautifulSoup(requests.get(url).text, "html.parser")
        dl_url = ''
        for link in soup.find_all('a', {'class': "instant-page-extra-button"}):
            search = re.search('/media.*\.mp3', link.get('href'))
            if search:
                href = search.group(0)
                dl_url = 'https://www.myinstants.com' + href
                break

        file = f"{self.folder}{name}.mp3"
        f = open(file, 'wb')
        f.write(requests.get(dl_url, allow_redirects=True).content)

        self.soundlist[name] = Sound(name, file, desc, dl_url)
        self.serialize()
        await ctx.send(f"'{name}' downloaded successfully!")

    async def _play(self, ctx, sound, vol=20):
        if not sound in self.soundlist:
            return await ctx.send("That sound doesn't exist!\n Please use t!s help to view all available sounds")

        vol = (float)(vol) / 100
        voice = ctx.voice_client
        if not voice:
            if ctx.message.author.voice:
                channel = ctx.message.author.voice.channel
                await channel.connect()
                voice = get(self.bot.voice_clients, guild=ctx.guild)
            else:
                return await ctx.send("Please join a voice channel")
        voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.soundlist[sound].file), vol), after=None)

    async def _delete(self, ctx, name):
        try:
            file = self.soundlist.pop(name, None).name + ".mp3"
        except:
            return await ctx.send("That sound doesn't exist!")

        os.remove(self.folder + file)
        self.serialize()
        await ctx.send(f"'{name}' deleted successfully!")

##############################     SOUND COMMANDS    ##############################

class SoundCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    async def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except KeyError:
            print(f"DEBUG: No sound player for guild {ctx.guild.id}. Creating new.")
            player = SoundPlayer(ctx)
            self.players[ctx.guild.id] = player
        return player

    @commands.command(name='sound', aliases=['s'])
    async def _sound(self, ctx, *args):
        try:
            sound = args[0]
        except:
            sound = 'h'
        player = await self.get_player(ctx)

        if not sound or sound in help_param: # Help
            return await player._help(ctx)
        elif sound in del_param: # Delete
            try: name = args[1]
            except: return await ctx.send("Please specify a sound to delete")
            return await player._delete(ctx, name)
        elif sound in dl_param: # Download
            if len(args) > 4:
                return await ctx.send("Invalid Input: Too many arguments passed!\n"
                                      "Make sure to put names & descriptions within quotes if they have spaces.\n"
                                      "Ex.) t!s dl https://www.myinstants.com/instant/mission-failed/ "
                                      "\"mission failed\" \"Mission failed. We'll get 'em next time.\"")
            desc = args[3] if len(args) > 3 else 'DESC_HERE'
            try: url, name = args[1], args[2]
            except: return await ctx.send("Bad input. Ex.) 't!s dl [url] [name] [desc]'")
            return await player._download(ctx, url, name, desc)
        else:
            try: vol = int(args[1])
            except: vol = 20
            return await player._play(ctx, sound, vol)

