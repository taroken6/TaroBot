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

sound_folder = os.getcwd() + '\sounds\\'

class SoundCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.soundlist = {
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
                reaction = await bot.wait_for('raw_reaction_add', timeout=60.0)
            except:
                await ctx.send("Wait for reaction timed out")

    async def _download(self, ctx, url):
        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")
        dl_url = ''
        for link in soup.find_all('a', {'class': "instant-page-extra-button"}):
            search = re.search('/media.*\.mp3', link.get('href'))
            if search:
                href = search.group(0)
                dl_url = 'https://www.myinstants.com' + href
                break
        print(dl_url)
        mp3_file = requests.get(dl_url, allow_redirects=True)
        print(mp3_file.raw)
        with open('sound.mp3', 'wb') as f:
            f.write(mp3_file.content)

    @commands.command(name='sound', aliases=['s'])
    async def sound(self, ctx, *args):
        try:
            sound = args[0]
        except:
            sound = 'h'

        help_param = ['help', 'h']
        dl_param = ['download', 'dl']

        if not sound or sound in help_param:  ###### Help request ######
            await self._help(ctx)
            return
        elif sound in dl_param:
            try:
                url = args[1]
            except:
                return await ctx.send("Please specify a URL")
            await self._download(ctx, url)
        else:  ###### Play sound ######
            default_vol = 0.20
            try:
                vol = (float)(args[1]) / 100
                print(f"DEBUG: set volume to {vol}")
            except IndexError:
                print(f"DEBUG: set volume to default - {default_vol}")
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