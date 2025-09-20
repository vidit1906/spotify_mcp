# Setup Instructions for Claude Desktop + Spotify MCP Server

## Overview
This setup allows you to control Spotify directly from Claude Desktop without using API credits. The MCP (Model Context Protocol) server provides tools for playing songs, controlling playback, and searching music.

## Prerequisites
1. Claude Desktop app installed on macOS
2. Spotify Premium account (required for playback control)
3. Python 3.8+ with virtual environment

## Setup Steps

### 1. Install Dependencies
```bash
cd /Users/vidit/Desktop/dev/mcp_spotify
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Initial Spotify Authentication
You still need to authenticate with Spotify once using the Flask app:

```bash
# Make sure your .env file has the Spotify credentials
python app.py
```

Then visit http://127.0.0.1:5001/login and complete the Spotify OAuth flow. This stores your credentials in MongoDB.

### 3. Configure Claude Desktop

Copy the configuration to Claude Desktop's config directory:

```bash
# Create the config directory if it doesn't exist
mkdir -p ~/Library/Application\ Support/Claude/

# Copy the configuration
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Important**: The config file needs to use the full path to your Python executable and script. If your paths are different, update the config file:

```json
{
  "mcpServers": {
    "spotify-control": {
      "command": "/Users/vidit/Desktop/dev/mcp_spotify/venv/bin/python",
      "args": ["/Users/vidit/Desktop/dev/mcp_spotify/mcp_server.py"]
    }
  }
}
```

### 4. Restart Claude Desktop
Close and reopen Claude Desktop for the configuration to take effect.

### 5. Test the Connection
In Claude Desktop, you should now be able to use commands like:
- "Play Bohemian Rhapsody by Queen"
- "What song is currently playing?"
- "Pause the music"
- "Skip to the next song"
- "Search for songs by The Beatles"

## Available Tools

The MCP server provides these tools:

1. **play_song**: Search and play a specific song
   - Parameters: song_name (required), artist_name (optional)

2. **search_songs**: Search for songs without playing them
   - Parameters: query (song name, artist, album, etc.)

3. **get_current_song**: Get info about currently playing song
   - No parameters required

4. **control_playback**: Control playback (play/pause/next/previous)
   - Parameters: action (play, pause, next, previous)

## Troubleshooting

### MCP Server Not Connecting
1. Check that Claude Desktop config file is in the right location
2. Verify Python paths in the config file are correct
3. Make sure the virtual environment has all dependencies installed
4. Check Claude Desktop's developer console for error messages

### Spotify Commands Not Working
1. Ensure you've completed the initial OAuth flow via the Flask app
2. Make sure you have an active Spotify session (app open on some device)
3. Verify your Spotify account has Premium (required for playback control)
4. Check your MongoDB connection and stored tokens

### Token Refresh Issues
The MCP server automatically refreshes expired tokens, but if you get authentication errors:
1. Re-run the Flask app and re-authenticate
2. Check your Spotify app credentials in the .env file

## Environment Variables Required

Make sure your `.env` file contains:
```
MONGO_URI=your_mongodb_connection_string
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
```

Note: You no longer need `ANTHROPIC_API_KEY` since we're using Claude Desktop directly!
