"""
Owner-only functionality for the Discord bot.
"""

import logging
from typing import Optional
import discord
from discord.ext import commands
from .config import Config
from .utils import Utils

logger = logging.getLogger(__name__)

class Owner(commands.Cog):
    """Owner-only commands cog."""
    
    def __init__(self, bot):
        self.bot = bot
        self.utils = Utils(bot)
    
    def cog_check(self, ctx):
        """Check if user is the bot owner."""
        return Config.is_owner(ctx.author.id)
    
    @commands.command(name='gban', aliases=['globalban'])
    async def global_ban(self, ctx, user_id: int, *, reason: str = "No reason provided"):
        """Globally ban a user from all servers the bot is in."""
        await self._global_ban(ctx, user_id, reason)
    
    @discord.app_commands.command(name='gban', description='Globally ban a user from all servers')
    @discord.app_commands.describe(user_id='User ID to ban globally', reason='Reason for the ban')
    async def slash_global_ban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
        """Slash command: Globally ban a user."""
        try:
            user_id_int = int(user_id)
            await self._global_ban(interaction, user_id_int, reason)
        except ValueError:
            embed = self.utils.create_embed(
                "❌ Invalid User ID",
                "Please provide a valid numeric user ID.",
                "error"
            )
            await interaction.response.send_message(embed=embed)
    
    async def _global_ban(self, ctx_or_interaction, user_id: int, reason: str):
        """Helper method for global ban."""
        if isinstance(ctx_or_interaction, discord.Interaction):
            respond = ctx_or_interaction.response.send_message
            edit_response = ctx_or_interaction.edit_original_response
        else:
            respond = lambda **kwargs: self.utils.safe_send(ctx_or_interaction, **kwargs)
            edit_response = lambda **kwargs: None
        
        try:
            user = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            embed = self.utils.create_embed(
                "❌ User Not Found",
                f"Could not find user with ID: {user_id}",
                "error"
            )
            return await respond(embed=embed)
        
        if Config.is_owner(user.id):
            embed = self.utils.create_embed(
                "❌ Cannot Ban Owner",
                "You cannot globally ban yourself.",
                "error"
            )
            return await respond(embed=embed)
        
        banned_count = 0
        failed_count = 0
        
        status_embed = self.utils.create_embed(
            "🔨 Global Ban in Progress",
            f"Attempting to ban **{user.name}** from all servers...",
            "warning"
        )
        await respond(embed=status_embed)
        
        for guild in self.bot.guilds:
            try:
                member = guild.get_member(user.id)
                if member:
                    if guild.me.guild_permissions.ban_members and member.top_role < guild.me.top_role:
                        await guild.ban(user, reason=f"Global ban by owner - {reason}")
                        banned_count += 1
                    else:
                        failed_count += 1
                else:
                    if guild.me.guild_permissions.ban_members:
                        try:
                            await guild.ban(user, reason=f"Global ban by owner - {reason}")
                            banned_count += 1
                        except discord.NotFound:
                            pass
                        except discord.Forbidden:
                            failed_count += 1
            except Exception as e:
                logger.error(f"Error banning {user.name} from {guild.name}: {e}")
                failed_count += 1
        
        embed = self.utils.create_embed(
            "✅ Global Ban Complete",
            f"**{user.name}** globally banned.\n"
            f"**Reason:** {reason}\n"
            f"**Banned from:** {banned_count} servers\n"
            f"**Failed:** {failed_count} servers",
            "success"
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        if isinstance(ctx_or_interaction, discord.Interaction):
            await edit_response(embed=embed)
        else:
            await respond(embed=embed)
    
    @commands.command(name='servers', aliases=['guilds'])
    async def list_servers(self, ctx):
        """List all servers the bot is in."""
        await self._list_servers(ctx)
    
    @discord.app_commands.command(name='servers', description='List all servers the bot is in')
    async def slash_list_servers(self, interaction: discord.Interaction):
        """Slash command: List servers."""
        await self._list_servers(interaction)
    
    async def _list_servers(self, ctx_or_interaction):
        """Helper method for listing servers."""
        if isinstance(ctx_or_interaction, discord.Interaction):
            respond = ctx_or_interaction.response.send_message
        else:
            respond = lambda **kwargs: self.utils.safe_send(ctx_or_interaction, **kwargs)
        
        guilds = self.bot.guilds
        
        if not guilds:
            embed = self.utils.create_embed(
                "📋 Server List",
                "Bot is not in any servers.",
                "info"
            )
            return await respond(embed=embed)
        
        sorted_guilds = sorted(guilds, key=lambda g: g.member_count, reverse=True)
        
        embed = self.utils.create_embed(
            "📋 Server List",
            f"Bot is in {len(guilds)} servers",
            "info"
        )
        
        server_list = []
        for i, guild in enumerate(sorted_guilds[:20], 1):
            server_list.append(
                f"`{i}.` **{guild.name}** (ID: {guild.id})\n"
                f"    Members: {guild.member_count} | Owner: {guild.owner}"
            )
        
        embed.description = "\n\n".join(server_list)
        
        if len(guilds) > 20:
            embed.add_field(
                name="📊 Note",
                value=f"Showing 20 of {len(guilds)} servers",
                inline=False
            )
        
        await respond(embed=embed)
    
    @commands.command(name='shutdown')
    async def shutdown(self, ctx):
        """Shutdown the bot."""
        await self._shutdown(ctx)
    
    @discord.app_commands.command(name='shutdown', description='Shutdown the bot')
    async def slash_shutdown(self, interaction: discord.Interaction):
        """Slash command: Shutdown the bot."""
        await self._shutdown(interaction)
    
    async def _shutdown(self, ctx_or_interaction):
        """Helper method for shutting down the bot."""
        if isinstance(ctx_or_interaction, discord.Interaction):
            author = ctx_or_interaction.user
            respond = ctx_or_interaction.response.send_message
        else:
            author = ctx_or_interaction.author
            respond = lambda **kwargs: self.utils.safe_send(ctx_or_interaction, **kwargs)
        
        embed = self.utils.create_embed(
            "🔄 Shutting Down",
            "Bot is shutting down...",
            "warning"
        )
        await respond(embed=embed)
        
        logger.info(f"Bot shutdown initiated by owner {author}")
        await self.bot.close()
