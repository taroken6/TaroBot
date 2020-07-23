import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get

import time
import os
from SoundObj import Sound
import requests
from lxml import html
from bs4 import BeautifulSoup
import re

import pickle
import json

sound_folder = os.getcwd() + '\sounds\\'
help_param = ['help', 'h']
dl_param = ['download', 'dl']
del_param = ['delete', 'del', 'd']
reserved_names = help_param + dl_param

class SoundCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.json_file = "soundlist.txt"
        self.soundlist = {}

        self.deserialize()  # Get existing sounds in JSON file
        for file in os.listdir(sound_folder):  # Get other mp3 files in folder that aren't in JSON file
            file_name = file.split('.mp3')[0]
            if file_name not in self.soundlist.keys():
                self.soundlist[file_name] = Sound(
                    file_name,
                    f"{sound_folder}{file}",
                    'Description missing', 'URL missing')

    def serialize(self):
        '''
        Writes all Sound objects in dict to JSON
        '''
        data = {}
        for s in self.soundlist.keys():
            sound = self.soundlist[s]
            data[sound.name] = {
                'name': sound.name,
                'file': sound.file,
                'desc': sound.desc,
                'url': sound.url
            }

        with open(self.json_file, 'w') as sl:
            json.dump(data, sl, indent=2)
            sl.close()

    def deserialize(self):
        '''
        Unloads JSON to sound dict
        '''
        with open(self.json_file) as f:
            payload = json.load(f)
            for key, value in payload.items():
                if not key in self.soundlist:
                    self.soundlist[key] = Sound(value['name'], value['file'], value['desc'], value['url'])

    async def _help(self, ctx):
        MAX_FIELDS = 25  # Max fields is 25 per embed
        pages = (int)(len(self.soundlist) / MAX_FIELDS + 1)
        embeds = []
        for i in range(1, pages + 1):
            embeds.append(discord.Embed(
                title=f"Sounds commands, Page {i} of {pages}",
                description="t!s [sound name] [volume (0 - 200)]\n"
                            "t!s dl [myinstants.com URL] [name] [description]\n"
                            "example: t!s dl https://www.myinstants.com/instant/crickets/ cricket \"cricket noises\"",
                color=discord.Colour.teal()
            ))
        for idx, (key, value) in enumerate(self.soundlist.items()):
            page = (int)(idx / MAX_FIELDS)
            embeds[page].add_field(name=self.soundlist[key].name,
                                   value=self.soundlist[key].desc,
                                   inline=True)
        message = await ctx.send(embed=embeds[0])

        left_arrow = '⬅'
        right_arrow = '➡'
        await message.add_reaction(left_arrow)
        await message.add_reaction(right_arrow)
        page = 0
        reaction = ''

        message_timeout = time.time() + 60
        while time.time() < message_timeout:
            if reaction and reaction.member.id != self.bot.user.id:
                if reaction.emoji.name == left_arrow:
                    page = page - 1 if page > 0 else pages - 1
                    await message.edit(embed=embeds[page])
                if reaction.emoji.name == right_arrow:
                    page = page + 1 if page < pages - 1 else 0
                    await message.edit(embed=embeds[page])
            try:
                reaction = await self.bot.wait_for('raw_reaction_add', timeout=60.0)
            except:
                return print("Timed out")

    async def _download(self, ctx, url, name, desc):

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

        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")
        dl_url = ''
        for link in soup.find_all('a', {'class': "instant-page-extra-button"}):
            search = re.search('/media.*\.mp3', link.get('href'))
            if search:
                href = search.group(0)
                dl_url = 'https://www.myinstants.com' + href
                break
        mp3_file = requests.get(dl_url, allow_redirects=True)
        mp3_file_name = f"{sound_folder}{name}.mp3"
        with open(mp3_file_name, 'wb') as f:
            f.write(mp3_file.content)

        sound = Sound(name, mp3_file_name, desc, dl_url)
        self.soundlist[name] = sound
        self.serialize()
        self.deserialize()
        await ctx.send("Download complete!")

    async def _play(self, ctx, sound, vol=20):
        vol = (float)(vol) / 100
        voice = ctx.voice_client
        if not voice:
            if ctx.message.author.voice:
                channel = ctx.message.author.voice.channel
                await channel.connect()
                voice = get(self.bot.voice_clients, guild=ctx.guild)
            else:
                return await ctx.send("Either me or you are not in a voice channel")
        voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.soundlist[sound].file), vol), after=None)

    async def _delete(self, ctx, name):
        '''
        Remove sound from dict and then resets it
        '''
        self.soundlist.pop(name, None)
        self.serialize()
        self.deserialize()
        await ctx.send(f"'{name}' deleted successfully!")

    @commands.command(name='sound', aliases=['s'])
    async def _sound(self, ctx, *args):
        try:
            sound = args[0]
        except:
            sound = 'h'

        if not sound or sound in help_param:  ###### Help request ######
            return await self._help(ctx)
        if sound in del_param:
            try: name = args[1]
            except: return await ctx.send("Please specify a sound to delete")
            return await self._delete(ctx, name)
        if sound in dl_param:
            try:
                url, name, desc = args[1], args[2], args[3]
            except:
                return await ctx.send("Bad input: 't!s dl [url] [name] [desc]'")
            await self._download(ctx, url, name, desc)
        if sound in self.soundlist.keys():  ###### Play sound ######
            try: vol = args[1]
            except: vol = 20
            return await self._play(ctx, sound, vol)
        else:
            return await ctx.send("Sound does not exist")

