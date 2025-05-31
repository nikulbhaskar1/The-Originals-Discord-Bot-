"""
Utility functions for the Discord bot.
"""

import asyncio
import logging
from typing import Optional, Union
import discord
from discord.ext import commands
from .config import Config

logger = logging.getLogger(__name__)

class Utils:
    """Utility class for common bot functions."""
    
    def __init__(self, bot):
        self.bot = bot
    
    def create_embed(self, title: str, description: str = None, color_type: str = "info") -> discord.Embed:
        """Create a standardized embed."""
        embed = discord.Embed(
            title=title,
            description=description,
            color=Config.get_embed_color(color_type)
        )
        return embed
    
    def is_owner_protected(self, user: discord.Member) -> bool:
        """Check if user is protected (is the owner)."""
        return Config.is_owner(user.id)
    
    async def safe_send(self, ctx, content=None, embed=None):
        """Safely send a message with error handling."""
        try:
            return await ctx.send(content=content, embed=embed)
        except discord.Forbidden:
            logger.warning(f"Missing permissions to send message in {ctx.guild.name}")
        except discord.HTTPException as e:
            logger.error(f"HTTP error sending message: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")
    
    async def get_member_from_mention(self, ctx, user_input: str) -> Optional[discord.Member]:
        """Get member from mention, ID, or username."""
        if user_input.startswith('<@') and user_input.endswith('>'):
            user_id = user_input[2:-1]
            if user_id.startswith('!'):
                user_id = user_id[1:]
            try:
                return ctx.guild.get_member(int(user_id))
            except ValueError:
                pass
        
        try:
            user_id = int(user_input)
            return ctx.guild.get_member(user_id)
        except ValueError:
            pass
        
        return discord.utils.get(ctx.guild.members, name=user_input)
    
    def format_duration(self, seconds: int) -> str:
        """Format duration in seconds to MM:SS format."""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    async def log_action(self, guild: discord.Guild, action: str, moderator: discord.User, 
                        target: discord.User = None, reason: str = None):
        """Log moderation actions."""
        log_message = f"[{guild.name}] {action} by {moderator.name}"
        if target:
            log_message += f" on {target.name}"
        if reason:
            log_message += f" - Reason: {reason}"
        
        logger.info(log_message)
    
    def has_permissions(self, member: discord.Member, **permissions) -> bool:
        """Check if member has required permissions."""
        member_perms = member.guild_permissions
        return all(getattr(member_perms, perm, False) for perm in permissions)
