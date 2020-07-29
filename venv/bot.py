import discord
from discord.ext import commands
from discord.ext.commands import Bot
from discord.utils import get

from cogs.GeneralCog import GeneralCog
from cogs.MusicCog import MusicCog
from cogs.SoundCog import SoundCog

################ GLOBAL VARIABLES ################

TOKEN = '' # Bot token here
PREFIX = 't!'
IMAGE_FOLDER = 'images/'

bot = commands.Bot(command_prefix=PREFIX)
bot.remove_command('connect')
bot.remove_command('help')

@bot.command()
async def jerry(ctx):  # Test command. May remove later
    await ctx.send('jERry', file=discord.File(IMAGE_FOLDER + 'jerry.jpg'))

@bot.command()
async def guildid(ctx):
    await ctx.send(f"Guild id = {ctx.message.guild.id}")

def setup(bot):
    bot.add_cog(MusicCog(bot))
    bot.add_cog(SoundCog(bot))
    bot.add_cog(GeneralCog(bot))
setup(bot)
bot.run(TOKEN)
