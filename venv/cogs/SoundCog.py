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

class SoundCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.json_file = "soundlist.txt"
        self.soundlist = {}

        for file in os.listdir(sound_folder):
            file_name = file.split('.mp3')[0]
            self.soundlist[file_name] = Sound(file_name, f"{sound_folder}{file}", 'Description missing', 'URL missing')

    async def _help(self, ctx):
        MAX_FIELDS = 25  # Max fields is 25 per embed
        pages = (int)(len(self.soundlist) / MAX_FIELDS + 1)
        embeds = []
        for i in range(1, pages + 1):
            embeds.append(discord.Embed(
                title=f"Sounds commands, Page {i} of {pages}",
                description="t!s [sound] [volume (0 - 200)]",
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
        sound = Sound(name, mp3_file_name, desc, dl_url)

        with open(mp3_file_name, 'wb') as f:
            f.write(mp3_file.content)
        self.serialize(sound)

    def serialize(self, sound):
        name, file, desc, url = sound.name, sound.file, sound.desc, sound.url
        data = {name:
                 {'name': name,
                  'file': file,
                  'desc': desc,
                  'url': url
                  }}
        with open(self.json_file, 'w') as sl:
            json.dump(data, sl)
            sl.close()
            f = open(self.json_file)
            payload = json.load(f)
            print(payload)
        return

    def deserialize(self):
        return


    @commands.command(name='sound', aliases=['s'])
    async def sound(self, ctx, *args):
        try:
            sound = args[0]
        except:
            sound = 'h'

        help_param = ['help', 'h']
        dl_param = ['download', 'dl']

        if not sound or sound in help_param:  ###### Help request ######
            return await self._help(ctx)
        elif sound in dl_param:
            try:
                url, name, desc = args[1], args[2], args[3]
            except:
                return await ctx.send("Bad input: 't!s dl [url] [name] [desc]")
            await self._download(ctx, url, name, desc)
        else:  ###### Play sound ######
            default_vol = 0.20
            try:
                vol = (float)(args[1]) / 100
            except IndexError:
                vol = default_vol
            voice = ctx.voice_client
            if not voice:
                if ctx.message.author.voice:
                    channel = ctx.message.author.voice.channel
                    await channel.connect()
                    voice = get(self.bot.voice_clients, guild=ctx.guild)
                else:
                    return await ctx.send("Either me or you are not in a voice channel")
            voice.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.soundlist[sound].file), vol), after=None)

# TODO: Allow it so that users can create their own sound command 3rd