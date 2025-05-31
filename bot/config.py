"""
Configuration module for the Discord bot.
"""

import os
from typing import List

class Config:
    """Configuration class for bot settings."""
    
    # Bot configuration
    TOKEN = os.getenv("DISCORD_TOKEN", "your_bot_token_here")
    PREFIX = os.getenv("BOT_PREFIX", "!")
    OWNER_ID = int(os.getenv("OWNER_ID", "123456789012345678"))
    
    # Spotify configuration
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "your_spotify_client_id")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "your_spotify_client_secret")
    
    # Music configuration
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    
    # Voice settings
    DEFAULT_VOLUME = 50
    MAX_VOLUME = 100
    
    # Moderation settings
    MAX_BULK_DELETE = 100
    
    # Owner privileges
    OWNER_GUILDS: List[int] = []
    
    # Embed colors
    COLOR_SUCCESS = 0x00ff00
    COLOR_ERROR = 0xff0000
    COLOR_WARNING = 0xffaa00
    COLOR_INFO = 0x0099ff
    COLOR_MUSIC = 0x9932cc
    
    # Rate limiting
    COMMAND_COOLDOWN = 3
    
    @classmethod
    def is_owner(cls, user_id: int) -> bool:
        """Check if user is the bot owner."""
        return user_id == cls.OWNER_ID
    
    @classmethod
    def get_embed_color(cls, type: str) -> int:
        """Get embed color by type."""
        colors = {
            'success': cls.COLOR_SUCCESS,
            'error': cls.COLOR_ERROR,
            'warning': cls.COLOR_WARNING,
            'info': cls.COLOR_INFO,
            'music': cls.COLOR_MUSIC
        }
        return colors.get(type, cls.COLOR_INFO)
