"""
Moderation functionality for the Discord bot.
"""

import logging
from typing import Optional
import discord
from discord.ext import commands
from .config import Config
from .utils import Utils

logger = logging.getLogger(__name__)

class Moderation(commands.Cog):
    """Moderation commands cog."""
    
    def __init__(self, bot):
        self.bot = bot
        self.utils = Utils(bot)
    
    def cog_check(self, ctx):
        """Check if commands can be used in this context."""
        return ctx.guild is not None
    
    @commands.command(name='kick')
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member from the server."""
        await self._kick_member(ctx, member, reason)
    
    @discord.app_commands.command(name='kick', description='Kick a member from the server')
    @discord.app_commands.describe(member='The member to kick', reason='Reason for the kick')
    async def slash_kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        """Slash command: Kick a member."""
        await self._kick_member(interaction, member, reason)
    
    async def _kick_member(self, ctx_or_interaction, member: discord.Member, reason: str):
        """Helper method for kicking members."""
        if isinstance(ctx_or_interaction, discord.Interaction):
            author = ctx_or_interaction.user
            guild = ctx_or_interaction.guild
            respond = ctx_or_interaction.response.send_message
        else:
            author = ctx_or_interaction.author
            guild = ctx_or_interaction.guild
            respond = lambda **kwargs: self.utils.safe_send(ctx_or_interaction, **kwargs)
        
        # Check if target is the owner
        if self.utils.is_owner_protected(member):
            embed = self.utils.create_embed(
                "❌ Cannot Kick Owner",
                "You cannot kick the bot owner.",
                "error"
            )
            return await respond(embed=embed)
        
        # Check if target is higher role than executor
        if member.top_role >= author.top_role and author != guild.owner:
            embed = self.utils.create_embed(
                "❌ Insufficient Role",
                "You cannot kick someone with a higher or equal role.",
                "error"
            )
            return await respond(embed=embed)
        
        # Check if bot can kick the member
        if member.top_role >= guild.me.top_role:
            embed = self.utils.create_embed(
                "❌ Cannot Kick",
                "I cannot kick someone with a higher or equal role than me.",
                "error"
            )
            return await respond(embed=embed)
        
        try:
            # Try to DM the user before kicking
            try:
                dm_embed = self.utils.create_embed(
                    f"👢 Kicked from {guild.name}",
                    f"**Reason:** {reason}\n**Moderator:** {author.mention}",
                    "warning"
                )
                await member.send(embed=
