import discord
from discord.ext import commands

from cogs.GeneralCog import GeneralCog
from cogs.MusicCog import MusicCog
from cogs.SoundCog import SoundCog

TOKEN = 'MTg1MTExODg4NDU4Mjg1MDU2.V0X84Q.c9woaRaX4mi1BJESartYmS4zeTc'  # Bot token here
PREFIX = 't!'
IMAGE_FOLDER = 'images/'

bot = commands.Bot(command_prefix=PREFIX)
bot.remove_command('connect')
bot.remove_command('help')


@bot.command()
async def jerry(ctx):  # Test command. May remove later
    await ctx.send('jERry', file=discord.File(IMAGE_FOLDER + 'jerry.jpg'))


def setup(bot):
    bot.add_cog(MusicCog(bot))
    bot.add_cog(SoundCog(bot))
    bot.add_cog(GeneralCog(bot))
setup(bot)
bot.run(TOKEN)
