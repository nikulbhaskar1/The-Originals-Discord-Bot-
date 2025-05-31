#!/usr/bin/env python3
"""
Multi-purpose Discord Bot
A Discord bot with music, moderation, and owner privilege features.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
import discord
from discord.ext import commands

# Load environment variables
load_dotenv()

# Import bot modules
from bot.config import Config
from bot.music import Music
from bot.moderation import Moderation
from bot.owner import Owner
from bot.utils import Utils

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MultiPurposeBot(commands.Bot):
    """Main bot class with all functionality."""
    
    def __init__(self):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix=Config.PREFIX,
            intents=intents,
            help_command=None  # We'll create our own help command
        )
        
        # Store configuration
        self.config = Config()
        self.utils = Utils(self)
        
    async def setup_hook(self):
        """Set up the bot with cogs."""
        try:
            # Add cogs
            await self.add_cog(Music(self))
            await self.add_cog(Moderation(self))
            await self.add_cog(Owner(self))
            
            # Sync slash commands
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
            logger.info("All cogs loaded successfully")
        except Exception as e:
            logger.error(f"Error loading cogs: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set bot activity
        activity = discord.Activity(
            type=discord.ActivityType.listening,
            name=f"{Config.PREFIX}help | Music & Moderation"
        )
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """Global error handler."""
        if isinstance(error, commands.CommandNotFound):
            embed = discord.Embed(
                title="❌ Command Not Found",
                description=f"Command `{ctx.invoked_with}` not found. Use `{Config.PREFIX}help` for available commands.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Missing Permissions",
                description="You don't have permission to use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Missing Arguments",
                description=f"Missing required argument: `{error.param.name}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            logger.error(f"Unhandled error: {error}")
            embed = discord.Embed(
                title="❌ An Error Occurred",
                description="An unexpected error occurred. Please try again later.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

# Custom help command
@commands.command(name='help')
async def help_command(ctx, category=None):
    """Custom help command."""
    bot = ctx.bot
    
    if category is None:
        # Main help embed
        embed = discord.Embed(
            title="🤖 Multi-Purpose Bot Help",
            description="A feature-rich Discord bot with music, moderation, and owner features.",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📂 Categories",
            value=f"`{Config.PREFIX}help music` - Music commands\n"
                  f"`{Config.PREFIX}help mod` - Moderation commands\n"
                  f"`{Config.PREFIX}help owner` - Owner commands",
            inline=False
        )
        
        embed.add_field(
            name="🔗 Quick Commands",
            value=f"`{Config.PREFIX}play <song>` - Play music\n"
                  f"`{Config.PREFIX}kick <user>` - Kick user\n"
                  f"`{Config.PREFIX}ban <user>` - Ban user",
            inline=False
        )
        
        embed.set_footer(text=f"Use {Config.PREFIX}help <category> for detailed commands")
        
    elif category.lower() in ['music', 'm']:
        embed = discord.Embed(
            title="🎵 Music Commands",
            color=discord.Color.green()
        )
        
        commands_list = [
            f"`{Config.PREFIX}play <song>` - Play a song or add to queue",
            f"`{Config.PREFIX}pause` - Pause current song",
            f"`{Config.PREFIX}resume` - Resume paused song",
            f"`{Config.PREFIX}stop` - Stop music and clear queue",
            f"`{Config.PREFIX}skip` - Skip current song",
            f"`{Config.PREFIX}queue` - Show current queue",
            f"`{Config.PREFIX}np` - Show now playing",
            f"`{Config.PREFIX}volume <1-100>` - Set volume",
            f"`{Config.PREFIX}join` - Join voice channel",
            f"`{Config.PREFIX}leave` - Leave voice channel"
        ]
        
        embed.description = "\n".join(commands_list)
        
    elif category.lower() in ['moderation', 'mod']:
        embed = discord.Embed(
            title="🛡️ Moderation Commands",
            color=discord.Color.orange()
        )
        
        commands_list = [
            f"`{Config.PREFIX}kick <user> [reason]` - Kick a user",
            f"`{Config.PREFIX}ban <user> [reason]` - Ban a user",
            f"`{Config.PREFIX}unban <user>` - Unban a user",
            f"`{Config.PREFIX}mute <user> [reason]` - Mute a user",
            f"`{Config.PREFIX}unmute <user>` - Unmute a user",
            f"`{Config.PREFIX}clear <amount>` - Delete messages",
            f"`{Config.PREFIX}warn <user> [reason]` - Warn a user"
        ]
        
        embed.description = "\n".join(commands_list)
        embed.add_field(
            name="⚠️ Note",
            value="Moderation commands cannot be used on the bot owner.",
            inline=False
        )
        
    elif category.lower() in ['owner', 'o']:
        if ctx.author.id != Config.OWNER_ID:
            embed = discord.Embed(
                title="❌ Access Denied",
                description="Only the bot owner can view these commands.",
                color=discord.Color.red()
            )
        else:
            embed = discord.Embed(
                title="👑 Owner Commands",
                color=discord.Color.purple()
            )
            
            commands_list = [
                f"`{Config.PREFIX}gban <user> [reason]` - Globally ban user",
                f"`{Config.PREFIX}gkick <user> [reason]` - Globally kick user",
                f"`{Config.PREFIX}gmute <user> [reason]` - Globally mute user",
                f"`{Config.PREFIX}leaveserver <server_id>` - Leave a server",
                f"`{Config.PREFIX}servers` - List all servers",
                f"`{Config.PREFIX}shutdown` - Shutdown the bot"
            ]
            
            embed.description = "\n".join(commands_list)
    
    else:
        embed = discord.Embed(
            title="❌ Invalid Category",
            description=f"Category `{category}` not found. Available: `music`, `mod`, `owner`",
            color=discord.Color.red()
        )
    
    await ctx.send(embed=embed)

async def main():
    """Main function to run the bot."""
    bot = MultiPurposeBot()
    bot.add_command(help_command)
    
    try:
        await bot.start(Config.TOKEN)
    except discord.LoginFailure:
        logger.error("Invalid bot token provided")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
