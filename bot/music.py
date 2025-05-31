"""
Music functionality for the Discord bot.
"""

import asyncio
import logging
from typing import Dict, List, Optional
import discord
from discord.ext import commands
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import youtube_dl
from .config import Config
from .utils import Utils

logger = logging.getLogger(__name__)

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

# Initialize Spotify client
try:
    spotify_client = spotipy.Spotify(
        client_credentials_manager=SpotifyClientCredentials(
            client_id=Config.SPOTIFY_CLIENT_ID,
            client_secret=Config.SPOTIFY_CLIENT_SECRET
        )
    )
except Exception as e:
    logger.warning(f"Failed to initialize Spotify client: {e}")
    spotify_client = None

class YTDLSource(discord.PCMVolumeTransformer):
    """Audio source using youtube-dl."""
    
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
        self.uploader = data.get('uploader')
    
    @classmethod
    async def create_source(cls, search: str, *, loop=None):
        """Create audio source from search query."""
        loop = loop or asyncio.get_event_loop()
        
        try:
            # Check if it's a Spotify URL/URI
            if 'spotify.com' in search or 'spotify:' in search:
                if spotify_client:
                    # Extract track info from Spotify
                    track_info = await cls._get_spotify_track_info(search, loop)
                    if track_info:
                        # Search for the track on YouTube
                        search_query = f"{track_info['artist']} {track_info['name']}"
                        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{search_query}", download=False))
                    else:
                        return None
                else:
                    logger.warning("Spotify client not available")
                    return None
            else:
                # Regular YouTube search
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(search, download=False))
            
            if data and 'entries' in data and data['entries']:
                # Take first item from a playlist or search results
                data = data['entries'][0]
            
            if data and 'url' in data:
                filename = data['url']
                return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
            else:
                return None
        except Exception as e:
            logger.error(f"Error creating audio source: {e}")
            return None
    
    @classmethod
    async def _get_spotify_track_info(cls, spotify_url: str, loop):
        """Extract track information from Spotify URL."""
        try:
            # Extract track ID from Spotify URL
            if 'track/' in spotify_url:
                track_id = spotify_url.split('track/')[-1].split('?')[0]
            elif 'spotify:track:' in spotify_url:
                track_id = spotify_url.split('spotify:track:')[-1]
            else:
                return None
            
            # Get track info from Spotify
            if spotify_client:
                track_info = await loop.run_in_executor(None, lambda: spotify_client.track(track_id))
                
                return {
                    'name': track_info['name'],
                    'artist': track_info['artists'][0]['name'],
                    'album': track_info['album']['name'],
                    'duration': track_info['duration_ms'] // 1000,
                    'external_url': track_info['external_urls']['spotify']
                }
            return None
        except Exception as e:
            logger.error(f"Error getting Spotify track info: {e}")
            return None

class MusicQueue:
    """Music queue management."""
    
    def __init__(self):
        self.queue: List[YTDLSource] = []
        self.current: Optional[YTDLSource] = None
        self.loop_song = False
        self.loop_queue = False
    
    def add(self, source: YTDLSource):
        """Add song to queue."""
        self.queue.append(source)
    
    def get_next(self) -> Optional[YTDLSource]:
        """Get next song from queue."""
        if self.loop_song and self.current:
            return self.current
        
        if not self.queue:
            return None
        
        next_song = self.queue.pop(0)
        
        if self.loop_queue and self.current:
            self.queue.append(self.current)
        
        self.current = next_song
        return next_song
    
    def clear(self):
        """Clear the queue."""
        self.queue.clear()
        self.current = None
    
    def skip(self) -> Optional[YTDLSource]:
        """Skip current song."""
        return self.get_next()

class Music(commands.Cog):
    """Music commands cog."""
    
    def __init__(self, bot):
        self.bot = bot
        self.utils = Utils(bot)
        self.queues: Dict[int, MusicQueue] = {}
        self.voice_clients: Dict[int, discord.VoiceClient] = {}
    
    def get_queue(self, guild_id: int) -> MusicQueue:
        """Get or create queue for guild."""
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]
    
    async def play_next(self, guild_id: int):
        """Play next song in queue."""
        queue = self.get_queue(guild_id)
        voice_client = self.voice_clients.get(guild_id)
        
        if not voice_client or not voice_client.is_connected():
            return
        
        next_source = queue.get_next()
        if next_source:
            voice_client.play(
                next_source,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(guild_id), self.bot.loop
                ) if not e else logger.error(f"Player error: {e}")
            )
    
    @commands.command(name='join')
    async def join(self, ctx):
        """Join the user's voice channel."""
        await self._join_voice(ctx)
    
    @discord.app_commands.command(name='join', description='Join your voice channel')
    async def slash_join(self, interaction: discord.Interaction):
        """Slash command: Join the user's voice channel."""
        await self._join_voice(interaction)
    
    async def _join_voice(self, ctx_or_interaction):
        """Helper method for joining voice channel."""
        if isinstance(ctx_or_interaction, discord.Interaction):
            user = ctx_or_interaction.user
            guild = ctx_or_interaction.guild
            voice_client = guild.voice_client if guild else None
            respond = ctx_or_interaction.response.send_message
        else:
            user = ctx_or_interaction.author
            guild = ctx_or_interaction.guild
            voice_client = ctx_or_interaction.voice_client
            respond = lambda **kwargs: self.utils.safe_send(ctx_or_interaction, **kwargs)
        
        if not hasattr(user, 'voice') or not user.voice:
            embed = self.utils.create_embed(
                "❌ Not in Voice Channel",
                "You need to be in a voice channel to use this command.",
                "error"
            )
            return await respond(embed=embed)
        
        channel = user.voice.channel
        
        if voice_client:
            await voice_client.move_to(channel)
        else:
            voice_client = await channel.connect()
            if guild:
                self.voice_clients[guild.id] = voice_client
        
        embed = self.utils.create_embed(
            "✅ Joined Voice Channel",
            f"Connected to {channel.name}",
            "success"
        )
        await respond(embed=embed)
    
    @commands.command(name='play', aliases=['p'])
    async def play(self, ctx, *, search: str):
        """Play a song or add to queue."""
        await self._play_music(ctx, search)
    
    @discord.app_commands.command(name='play', description='Play music from YouTube or Spotify')
    async def slash_play(self, interaction: discord.Interaction, search: str):
        """Slash command: Play music."""
        await self._play_music(interaction, search)
    
    async def _play_music(self, ctx_or_interaction, search: str):
        """Helper method for playing music."""
        if isinstance(ctx_or_interaction, discord.Interaction):
            user = ctx_or_interaction.user
            guild = ctx_or_interaction.guild
            voice_client = guild.voice_client if guild else None
            respond = ctx_or_interaction.response.send_message
        else:
            user = ctx_or_interaction.author
            guild = ctx_or_interaction.guild
            voice_client = ctx_or_interaction.voice_client
            respond = lambda **kwargs: self.utils.safe_send(ctx_or_interaction, **kwargs)
        
        if not hasattr(user, 'voice') or not user.voice:
            embed = self.utils.create_embed(
                "❌ Not in Voice Channel",
                "You need to be in a voice channel to play music.",
                "error"
            )
            return await respond(embed=embed)
        
        # Join voice channel if not connected
        if not voice_client:
            await self._join_voice(ctx_or_interaction)
            if guild:
                voice_client = self.voice_clients.get(guild.id)
        
        # Create loading message
        loading_embed = self.utils.create_embed(
            "🔍 Searching...",
            f"Searching for: `{search}`",
            "music"
        )
        
        if isinstance(ctx_or_interaction, discord.Interaction):
            await respond(embed=loading_embed)
            loading_msg = await ctx_or_interaction.original_response()
        else:
            loading_msg = await respond(embed=loading_embed)
        
        # Create audio source
        source = await YTDLSource.create_source(search, loop=self.bot.loop)
        
        if not source:
            embed = self.utils.create_embed(
                "❌ Not Found",
                f"Could not find: `{search}`",
                "error"
            )
            if loading_msg:
                await loading_msg.edit(embed=embed)
            return
        
        if guild:
            queue = self.get_queue(guild.id)
            
            # If nothing is playing, start playing immediately
            if voice_client and not voice_client.is_playing():
                queue.current = source
                voice_client.play(
                    source,
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self.play_next(guild.id), self.bot.loop
                    ) if not e else logger.error(f"Player error: {e}")
                )
                
                embed = self.utils.create_embed(
                    "🎵 Now Playing",
                    f"**{source.title}**",
                    "music"
                )
                if source.thumbnail:
                    embed.set_thumbnail(url=source.thumbnail)
                if source.duration:
                    embed.add_field(
                        name="Duration",
                        value=self.utils.format_duration(source.duration),
                        inline=True
                    )
                if source.uploader:
                    embed.add_field(name="Uploader", value=source.uploader, inline=True)
            else:
                # Add to queue
                queue.add(source)
                embed = self.utils.create_embed(
                    "✅ Added to Queue",
                    f"**{source.title}**\nPosition in queue: {len(queue.queue)}",
                    "music"
                )
            
            if loading_msg:
                await loading_msg.edit(embed=embed)
