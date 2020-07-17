import discord
from discord.ext import commands
from discord.ext.commands import Bot

import random

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.change_presence(status=discord.Status.online, activity=discord.Game("Yeet"))
        print('We have logged in as {0.user}'.format(self.bot))

    @commands.command(pass_context=True, aliases=['r'])
    async def reply(self, ctx, *, question):
        responses = ["Yes", "Maybe", "No"]
        await ctx.send(f"question: {question}\nanswer: {random.choice(responses)}")

    @commands.command()
    async def ping(self, ctx):
        await ctx.send(f'Pong! {round(self.bot.latency * 1000)} ms')

    @commands.command(name="id")
    async def getID(self, ctx):
        await ctx.send(f"Your ID: {ctx.author.id}")

    @commands.command(name='connect', aliases=['join'])
    async def _connect(self, ctx):
        bot_voice = ctx.voice_client
        try:
            user_channel = ctx.author.voice.channel
        except:
            return await ctx.send("You're currently not in a voice channel!")

        if not bot_voice:
            await user_channel.connect()
        elif bot_voice.channel != user_channel:
            await bot_voice.disconnect()
            await user_channel.connect()

    @commands.command(name='disconnect', aliases=['leave'])
    async def _disconnect(self, ctx: discord.ext.commands.Context):
        bot_voice = ctx.voice_client

        try:
            user_channel = ctx.author.voice.channel
        except:
            return await ctx.send("Please join a voice channel")

        if user_channel != bot_voice.channel: return await ctx.send("We're not in the same voice channel")

        try:
            await ctx.message.guild.voice_client.disconnect()
        except:
            return await ctx.send("I'm not in a server.")

    @commands.command(name="help")
    async def _help(self, ctx):
        embed = discord.Embed(title="Commands", color=discord.Color.light_grey())

        temp_general = GeneralCog.get_commands(bot.get_cog('GeneralCog'))
        general_text = ''
        for command in temp_general:
            general_text += f"{command}\n"
        embed.add_field(name="General commands:",
                        value= general_text,
                        inline=True)

        temp_music = MusicCog.get_commands(bot.get_cog('MusicCog'))
        music_text = ''
        for command in temp_music:
            music_text += f"{command}\n"
        embed.add_field(name="Music commands:",
                        value=music_text,
                        inline=True)

        temp_sound = SoundCog.get_commands(bot.get_cog('SoundCog'))
        sound_text = ''
        for command in temp_sound:
            sound_text += f"{command}\n"
        embed.add_field(name="Sound commands:",
                        value=sound_text,
                        inline=True)

        await ctx.send(embed=embed)

    @commands.command(name='connected')
    async def _connected(self, ctx):
        voice = get(bot.voice_clients, guild=ctx.guild)
        if voice is None:
            await ctx.send("Not connected")
        elif voice.is_connected():
            await ctx.send("Connected...")
