#!/usr/bin/env python3
"""
MCP Spotify Server - A Model Context Protocol server that provides Spotify control tools.
This replaces the Flask app + Anthropic API approach with direct Claude Desktop integration.
"""

import asyncio
import os
import sys
import time
import urllib.parse
import requests
import json
from typing import Any, Sequence
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)
import mcp.types as types

# Load environment variables
load_dotenv()

# Configuration
MONGO_URI = os.getenv("MONGO_URI")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = "http://127.0.0.1:5001/callback"
SCOPE = "user-modify-playback-state user-read-playback-state playlist-modify-public playlist-modify-private"

# Database setup
try:
    client = MongoClient(MONGO_URI)
    db = client.claude_dj
    users_collection = db.users
    client.admin.command('ping')
    print("✅ Connected to MongoDB!", file=sys.stderr)
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}", file=sys.stderr)
    exit()

# Create the server instance
server = Server("spotify-mcp-server")

def get_user_token():
    """Get the access token for the authenticated user."""
    user_data = users_collection.find_one()
    if not user_data:
        raise Exception("No authenticated user found. Please run the Flask app first to authenticate with Spotify.")
    
    # Check if token needs refresh
    if user_data['expires_at'] <= int(time.time()):
        # Token expired, refresh it
        refresh_token = user_data['refresh_token']
        token_url = "https://accounts.spotify.com/api/token"
        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': SPOTIFY_CLIENT_ID,
            'client_secret': SPOTIFY_CLIENT_SECRET,
        }
        response = requests.post(token_url, data=token_data)
        token_info = response.json()
        
        if 'access_token' in token_info:
            # Update the stored token
            expires_at = int(time.time()) + token_info['expires_in']
            users_collection.update_one(
                {'spotify_user_id': user_data['spotify_user_id']},
                {'$set': {
                    'access_token': token_info['access_token'],
                    'expires_at': expires_at
                }}
            )
            return token_info['access_token']
        else:
            raise Exception("Failed to refresh token. Please re-authenticate.")
    
    return user_data['access_token']

def search_spotify_track(access_token: str, song_name: str, artist_name: str = ""):
    """Search for a track on Spotify."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    if artist_name:
        query = f"track:{song_name} artist:{artist_name}"
    else:
        query = song_name
    
    search_url = "https://api.spotify.com/v1/search"
    search_params = {
        "q": query,
        "type": "track",
        "limit": 5
    }
    
    response = requests.get(search_url, headers=headers, params=search_params)
    return response.json()

def play_spotify_track(access_token: str, track_uri: str):
    """Play a specific track on Spotify."""
    headers = {"Authorization": f"Bearer {access_token}"}
    play_url = "https://api.spotify.com/v1/me/player/play"
    play_data = {"uris": [track_uri]}
    
    response = requests.put(play_url, headers=headers, json=play_data)
    return response

def get_current_playback(access_token: str):
    """Get current playback information."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://api.spotify.com/v1/me/player", headers=headers)
    return response.json() if response.status_code == 200 else None

def get_available_devices(access_token: str):
    """Get list of available Spotify devices."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://api.spotify.com/v1/me/player/devices", headers=headers)
    return response.json() if response.status_code == 200 else None

def control_playback(access_token: str, action: str):
    """Control Spotify playback (play, pause, next, previous)."""
    headers = {"Authorization": f"Bearer {access_token}"}
    base_url = "https://api.spotify.com/v1/me/player"
    
    if action == "play":
        response = requests.put(f"{base_url}/play", headers=headers)
    elif action == "pause":
        response = requests.put(f"{base_url}/pause", headers=headers)
    elif action == "next":
        response = requests.post(f"{base_url}/next", headers=headers)
    elif action == "previous":
        response = requests.post(f"{base_url}/previous", headers=headers)
    else:
        return {"error": f"Unknown action: {action}"}
    
    return {"status": "success" if response.status_code == 204 else "error", "response_code": response.status_code}

def create_playlist(access_token: str, playlist_name: str, description: str = "", public: bool = True):
    """Create a new Spotify playlist."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Get user ID first
    user_response = requests.get("https://api.spotify.com/v1/me", headers=headers)
    if user_response.status_code != 200:
        return {"error": "Could not get user information"}
    
    user_id = user_response.json()["id"]
    
    # Create playlist
    playlist_url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
    playlist_data = {
        "name": playlist_name,
        "description": description,
        "public": public
    }
    
    response = requests.post(playlist_url, headers=headers, json=playlist_data)
    return response

def add_tracks_to_playlist(access_token: str, playlist_id: str, track_uris: list):
    """Add tracks to an existing playlist."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    add_tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    add_tracks_data = {"uris": track_uris}
    
    response = requests.post(add_tracks_url, headers=headers, json=add_tracks_data)
    return response

def search_multiple_tracks(access_token: str, song_queries: list):
    """Search for multiple tracks and return their URIs."""
    headers = {"Authorization": f"Bearer {access_token}"}
    track_uris = []
    found_tracks = []
    
    for query in song_queries:
        search_url = "https://api.spotify.com/v1/search"
        search_params = {
            "q": query,
            "type": "track",
            "limit": 1
        }
        
        response = requests.get(search_url, headers=headers, params=search_params)
        search_results = response.json()
        
        tracks = search_results.get("tracks", {}).get("items", [])
        if tracks:
            track = tracks[0]
            track_uris.append(track["uri"])
            found_tracks.append({
                "name": track["name"],
                "artists": [artist["name"] for artist in track["artists"]],
                "uri": track["uri"]
            })
    
    return track_uris, found_tracks

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="play_song",
            description="Search for a song and play it on Spotify. Provide song name and optionally artist name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "song_name": {
                        "type": "string",
                        "description": "The name of the song to play"
                    },
                    "artist_name": {
                        "type": "string",
                        "description": "The name of the artist (optional, helps with search accuracy)"
                    }
                },
                "required": ["song_name"]
            }
        ),
        Tool(
            name="search_songs",
            description="Search for songs on Spotify without playing them. Returns a list of matching tracks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for songs (can include song name, artist, album, etc.)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_current_song",
            description="Get information about the currently playing song on Spotify.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="control_playback",
            description="Control Spotify playback with basic commands.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["play", "pause", "next", "previous"],
                        "description": "The playback action to perform"
                    }
                },
                "required": ["action"]
            }
        ),
        Tool(
            name="get_devices",
            description="Get list of available Spotify devices to help troubleshoot playback issues.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="create_playlist",
            description="Create a new Spotify playlist with optional songs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "playlist_name": {
                        "type": "string",
                        "description": "The name of the playlist to create"
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description for the playlist"
                    },
                    "public": {
                        "type": "boolean",
                        "description": "Whether the playlist should be public (default: true)"
                    },
                    "songs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of songs to add (format: 'Song Name by Artist' or just 'Song Name')"
                    }
                },
                "required": ["playlist_name"]
            }
        ),
        Tool(
            name="add_songs_to_playlist",
            description="Add songs to an existing playlist by searching for them.",
            inputSchema={
                "type": "object",
                "properties": {
                    "playlist_name": {
                        "type": "string",
                        "description": "The name of the existing playlist to add songs to"
                    },
                    "songs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of songs to add (format: 'Song Name by Artist' or just 'Song Name')"
                    }
                },
                "required": ["playlist_name", "songs"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    """Handle tool calls."""
    try:
        access_token = get_user_token()
        
        if name == "play_song":
            song_name = arguments.get("song_name", "")
            artist_name = arguments.get("artist_name", "")
            
            if not song_name:
                return [types.TextContent(
                    type="text",
                    text="Error: Song name is required."
                )]
            
            # Search for the track
            search_results = search_spotify_track(access_token, song_name, artist_name)
            tracks = search_results.get("tracks", {}).get("items", [])
            
            if not tracks:
                return [types.TextContent(
                    type="text",
                    text=f"No songs found for '{song_name}' by '{artist_name}'" if artist_name else f"No songs found for '{song_name}'"
                )]
            
            # Play the first track
            track = tracks[0]
            track_uri = track["uri"]
            response = play_spotify_track(access_token, track_uri)
            
            if response.status_code == 204:
                return [types.TextContent(
                    type="text",
                    text=f"✅ Now playing: '{track['name']}' by {', '.join(artist['name'] for artist in track['artists'])}"
                )]
            elif response.status_code == 403:
                # Premium required error
                return [types.TextContent(
                    type="text",
                    text=f"❌ Spotify Premium is required to control playback remotely.\n\n"
                         f"However, I found the song you're looking for:\n"
                         f"🎵 **{track['name']}** by {', '.join(artist['name'] for artist in track['artists'])}\n"
                         f"📀 Album: {track['album']['name']}\n"
                         f"🔗 You can play it manually in Spotify or upgrade to Premium for remote control."
                )]
            elif response.status_code == 404:
                # Check available devices to provide better guidance
                devices_info = get_available_devices(access_token)
                if devices_info and devices_info.get('devices'):
                    devices = devices_info['devices']
                    active_devices = [d for d in devices if d.get('is_active')]
                    if not active_devices:
                        device_list = '\n'.join([f"- {d['name']} ({d['type']})" for d in devices])
                        return [types.TextContent(
                            type="text",
                            text=f"❌ No active Spotify device found. You have these devices available:\n{device_list}\n\nPlease start playing music on one of these devices first, then try again."
                        )]
                    else:
                        return [types.TextContent(
                            type="text",
                            text="❌ Could not play song. Try refreshing your Spotify app or restarting playback manually."
                        )]
                else:
                    return [types.TextContent(
                        type="text",
                        text="❌ No Spotify devices found. Please open Spotify on your phone, computer, or another device and make sure you're logged in."
                    )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"❌ Could not play song (Error {response.status_code}). Make sure Spotify is active on one of your devices."
                )]
        
        elif name == "search_songs":
            query = arguments.get("query", "")
            if not query:
                return [types.TextContent(
                    type="text",
                    text="Error: Search query is required."
                )]
            
            search_results = search_spotify_track(access_token, query)
            tracks = search_results.get("tracks", {}).get("items", [])
            
            if not tracks:
                return [types.TextContent(
                    type="text",
                    text=f"No songs found for '{query}'"
                )]
            
            result_text = f"Found {len(tracks)} songs for '{query}':\n\n"
            for i, track in enumerate(tracks, 1):
                artists = ", ".join(artist['name'] for artist in track['artists'])
                album = track['album']['name']
                result_text += f"{i}. **{track['name']}** by {artists}\n   Album: {album}\n   Spotify URI: {track['uri']}\n\n"
            
            return [types.TextContent(
                type="text",
                text=result_text
            )]
        
        elif name == "get_current_song":
            playback_info = get_current_playback(access_token)
            
            if not playback_info or not playback_info.get('item'):
                return [types.TextContent(
                    type="text",
                    text="No song is currently playing on Spotify."
                )]
            
            track = playback_info['item']
            artists = ", ".join(artist['name'] for artist in track['artists'])
            album = track['album']['name']
            is_playing = playback_info.get('is_playing', False)
            progress_ms = playback_info.get('progress_ms', 0)
            duration_ms = track.get('duration_ms', 0)
            
            progress_min = progress_ms // 60000
            progress_sec = (progress_ms % 60000) // 1000
            duration_min = duration_ms // 60000
            duration_sec = (duration_ms % 60000) // 1000
            
            status = "Playing" if is_playing else "Paused"
            
            return [types.TextContent(
                type="text",
                text=f"🎵 **Currently {status}**: '{track['name']}' by {artists}\n"
                     f"📀 Album: {album}\n"
                     f"⏱️ Progress: {progress_min}:{progress_sec:02d} / {duration_min}:{duration_sec:02d}"
            )]
        
        elif name == "control_playback":
            action = arguments.get("action", "")
            if action not in ["play", "pause", "next", "previous"]:
                return [types.TextContent(
                    type="text",
                    text="Error: Action must be one of: play, pause, next, previous"
                )]
            
            result = control_playback(access_token, action)
            
            if result.get("status") == "success":
                action_messages = {
                    "play": "▶️ Resumed playback",
                    "pause": "⏸️ Paused playback", 
                    "next": "⏭️ Skipped to next track",
                    "previous": "⏮️ Went to previous track"
                }
                return [types.TextContent(
                    type="text",
                    text=action_messages.get(action, f"Performed action: {action}")
                )]
            elif result.get("response_code") == 403:
                return [types.TextContent(
                    type="text",
                    text=f"❌ Spotify Premium is required for playback control ('{action}').\nYou can manually control playback in your Spotify app or upgrade to Premium."
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"❌ Could not perform action '{action}'. Make sure Spotify is active and you have Premium."
                )]
        
        elif name == "get_devices":
            devices_info = get_available_devices(access_token)
            
            if not devices_info or not devices_info.get('devices'):
                return [types.TextContent(
                    type="text",
                    text="❌ No Spotify devices found. Please open Spotify on your phone, computer, or another device and make sure you're logged in."
                )]
            
            devices = devices_info['devices']
            if not devices:
                return [types.TextContent(
                    type="text",
                    text="❌ No Spotify devices available. Please open Spotify on a device and make sure you're logged in."
                )]
            
            device_list = "📱 **Available Spotify Devices:**\n\n"
            for device in devices:
                status = "🟢 Active" if device.get('is_active') else "⚪ Inactive"
                volume = device.get('volume_percent', 0)
                device_list += f"• **{device['name']}** ({device['type']})\n"
                device_list += f"  Status: {status} | Volume: {volume}%\n\n"
            
            active_count = len([d for d in devices if d.get('is_active')])
            if active_count == 0:
                device_list += "⚠️ **No active devices found.** To play music:\n"
                device_list += "1. Open Spotify on one of the devices above\n"
                device_list += "2. Start playing any song (you can pause it after)\n"
                device_list += "3. Then try your music request again"
            
            return [types.TextContent(
                type="text",
                text=device_list
            )]
        
        elif name == "create_playlist":
            playlist_name = arguments.get("playlist_name", "")
            description = arguments.get("description", "")
            public = arguments.get("public", True)
            songs = arguments.get("songs", [])
            
            if not playlist_name:
                return [types.TextContent(
                    type="text",
                    text="Error: Playlist name is required."
                )]
            
            # Create the playlist
            playlist_response = create_playlist(access_token, playlist_name, description, public)
            
            if playlist_response.status_code == 201:
                playlist_data = playlist_response.json()
                playlist_id = playlist_data["id"]
                playlist_url = playlist_data["external_urls"]["spotify"]
                
                result_text = f"✅ Created playlist: **{playlist_name}**\n"
                result_text += f"🔗 URL: {playlist_url}\n"
                
                # Add songs if provided
                if songs:
                    track_uris, found_tracks = search_multiple_tracks(access_token, songs)
                    
                    if track_uris:
                        add_response = add_tracks_to_playlist(access_token, playlist_id, track_uris)
                        
                        if add_response.status_code == 201:
                            result_text += f"\n🎵 Added {len(found_tracks)} songs:\n"
                            for track in found_tracks:
                                result_text += f"• {track['name']} by {', '.join(track['artists'])}\n"
                        else:
                            result_text += f"\n⚠️ Playlist created but failed to add songs (Error {add_response.status_code})"
                    else:
                        result_text += f"\n⚠️ Playlist created but no songs were found to add"
                
                return [types.TextContent(
                    type="text",
                    text=result_text
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"❌ Failed to create playlist (Error {playlist_response.status_code}). Make sure you have proper permissions."
                )]
        
        elif name == "add_songs_to_playlist":
            playlist_name = arguments.get("playlist_name", "")
            songs = arguments.get("songs", [])
            
            if not playlist_name or not songs:
                return [types.TextContent(
                    type="text",
                    text="Error: Both playlist name and songs are required."
                )]
            
            # First, find the playlist by name
            headers = {"Authorization": f"Bearer {access_token}"}
            playlists_response = requests.get("https://api.spotify.com/v1/me/playlists", headers=headers)
            
            if playlists_response.status_code != 200:
                return [types.TextContent(
                    type="text",
                    text="❌ Failed to get your playlists."
                )]
            
            playlists_data = playlists_response.json()
            target_playlist = None
            
            for playlist in playlists_data.get("items", []):
                if playlist["name"].lower() == playlist_name.lower():
                    target_playlist = playlist
                    break
            
            if not target_playlist:
                return [types.TextContent(
                    type="text",
                    text=f"❌ Playlist '{playlist_name}' not found in your library."
                )]
            
            # Search for songs and add them
            track_uris, found_tracks = search_multiple_tracks(access_token, songs)
            
            if not track_uris:
                return [types.TextContent(
                    type="text",
                    text="❌ None of the requested songs were found."
                )]
            
            # Add tracks to playlist
            add_response = add_tracks_to_playlist(access_token, target_playlist["id"], track_uris)
            
            if add_response.status_code == 201:
                result_text = f"✅ Added {len(found_tracks)} songs to **{playlist_name}**:\n\n"
                for track in found_tracks:
                    result_text += f"• {track['name']} by {', '.join(track['artists'])}\n"
                
                if len(found_tracks) < len(songs):
                    result_text += f"\n⚠️ {len(songs) - len(found_tracks)} song(s) could not be found and were skipped."
                
                return [types.TextContent(
                    type="text",
                    text=result_text
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"❌ Failed to add songs to playlist (Error {add_response.status_code})."
                )]
        
        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]
            
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

async def main():
    # Import here to avoid issues with event loop
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="spotify-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())
