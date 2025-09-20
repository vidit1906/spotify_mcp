# 🎵 Spotify MCP Server

A Model Context Protocol (MCP) server that enables Claude Desktop to control Spotify directly. This project allows you to search for music, control playback, create playlists, and manage your Spotify experience through natural language conversations with Claude.

## ✨ Features

- 🎵 **Play Songs**: Search and play any song by name and/or artist
- 🔍 **Search Music**: Find songs, albums, and artists without playing them
- ⏯️ **Playback Control**: Play, pause, skip tracks, and go to previous songs
- 📱 **Device Management**: View and manage your Spotify-connected devices
- 📋 **Playlist Management**: Create playlists and add songs to existing ones
- 🔄 **Token Management**: Automatic refresh of Spotify access tokens
- 💬 **Natural Language Interface**: Control everything through conversational commands

## 🛠️ How It Works

This project uses the Model Context Protocol (MCP) to create a bridge between Claude Desktop and the Spotify Web API. The MCP server provides tools that Claude can use to:

1. **Authenticate with Spotify** using OAuth 2.0 flow
2. **Store credentials securely** in MongoDB with automatic token refresh
3. **Interact with Spotify API** for music control and playlist management
4. **Provide real-time feedback** about playback status and errors

## 📋 Prerequisites

- **Claude Desktop** (macOS/Windows)
- **Spotify Premium Account** (required for playback control)
- **Python 3.8+**
- **MongoDB** (local or cloud instance)
- **Spotify Developer App** (for API credentials)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/vidit1906/spotify_mcp.git
cd spotify_mcp
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click "Create App"
3. Fill in app details:
   - **App Name**: "Claude Spotify Control" (or any name)
   - **App Description**: "MCP server for Claude Desktop"
   - **Redirect URI**: `http://127.0.0.1:5001/callback`
4. Save your **Client ID** and **Client Secret**

### 3. Setup MongoDB

Choose one option:

**Option A: MongoDB Atlas (Cloud - Recommended)**
1. Create free account at [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Create a new cluster
3. Get your connection string

**Option B: Local MongoDB**
```bash
# Install MongoDB locally
brew install mongodb/brew/mongodb-community  # macOS
# or follow instructions for your OS
mongod --dbpath /path/to/data/directory
```

### 4. Environment Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/claude_dj
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
ANTHROPIC_API_KEY=your_anthropic_api_key  # Optional, only needed for Flask app
```

### 5. Initial Spotify Authentication

Run the Flask app to complete OAuth flow:

```bash
python app.py
```

1. Open http://127.0.0.1:5001/login in your browser
2. Log in with your Spotify account
3. Authorize the application
4. You should see "✅ Successfully connected to Spotify!"

### 6. Configure Claude Desktop

**macOS:**
```bash
# Create config directory if it doesn't exist
mkdir -p ~/Library/Application\ Support/Claude/

# Edit the Claude Desktop config
nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```bash
# Create config directory if it doesn't exist
mkdir "%APPDATA%\Claude"

# Edit the Claude Desktop config
notepad "%APPDATA%\Claude\claude_desktop_config.json"
```

Add this configuration (update paths to match your system):

```json
{
  "mcpServers": {
    "spotify-control": {
      "command": "/path/to/your/project/venv/bin/python",
      "args": ["/path/to/your/project/mcp_server.py"]
    }
  }
}
```

For example on macOS:
```json
{
  "mcpServers": {
    "spotify-control": {
      "command": "/Users/yourusername/spotify_mcp/venv/bin/python",
      "args": ["/Users/yourusername/spotify_mcp/mcp_server.py"]
    }
  }
}
```

### 7. Restart Claude Desktop

Close and reopen Claude Desktop to load the new MCP server.

## 🎯 Usage Examples

Once set up, you can use natural language commands in Claude Desktop:

### Basic Playback
- "Play Bohemian Rhapsody by Queen"
- "Play some Taylor Swift"
- "What song is currently playing?"
- "Pause the music"
- "Skip to the next song"
- "Go back to the previous track"

### Search and Discovery
- "Search for songs by The Beatles"
- "Find songs with 'love' in the title"
- "Look up albums by Pink Floyd"

### Playlist Management
- "Create a playlist called 'Study Music'"
- "Add 'Clair de Lune' and 'Moonlight Sonata' to my Classical playlist"
- "Make a new playlist with these songs: [list of songs]"

### Device Management
- "Show my Spotify devices"
- "Which devices can play music?"

## 🔧 Available Tools

The MCP server provides these tools to Claude:

| Tool | Description | Parameters |
|------|-------------|------------|
| `play_song` | Search and play a specific song | `song_name` (required), `artist_name` (optional) |
| `search_songs` | Search for songs without playing | `query` (search terms) |
| `get_current_song` | Get currently playing track info | None |
| `control_playback` | Control playback | `action` (play/pause/next/previous) |
| `get_devices` | List available Spotify devices | None |
| `create_playlist` | Create new playlist with optional songs | `playlist_name`, `description`, `public`, `songs` |
| `add_songs_to_playlist` | Add songs to existing playlist | `playlist_name`, `songs` |

## 🔒 Security & Privacy

- **OAuth 2.0**: Secure authentication with Spotify
- **Token Storage**: Access tokens stored securely in MongoDB
- **Automatic Refresh**: Tokens refreshed automatically when expired
- **Local Processing**: All requests processed locally, no data sent to third parties
- **Environment Variables**: Sensitive credentials stored in `.env` file

## 🐛 Troubleshooting

### MCP Server Not Connecting
- ✅ Verify Claude Desktop config file location and syntax
- ✅ Check Python paths are correct in config
- ✅ Ensure virtual environment has all dependencies
- ✅ Look at Claude Desktop developer console for errors

### Spotify Commands Not Working
- ✅ Complete initial OAuth flow via Flask app
- ✅ Ensure you have Spotify Premium (required for playback control)
- ✅ Have an active Spotify session (app open on a device)
- ✅ Check MongoDB connection and stored tokens
- ✅ Verify Spotify app credentials in `.env`

### Common Error Messages

**"No authenticated user found"**
- Run `python app.py` and complete authentication flow

**"Spotify Premium is required"**
- Upgrade to Spotify Premium for remote playback control

**"No active Spotify device found"**
- Open Spotify on phone/computer and start playing any song

**"MongoDB connection failed"**
- Check your `MONGO_URI` in `.env` file
- Ensure MongoDB is running (if local) or accessible (if cloud)

## 🏗️ Project Structure

```
spotify_mcp/
├── mcp_server.py           # Main MCP server implementation
├── app.py                  # Flask app for initial OAuth
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .gitignore             # Git ignore file
├── claude_desktop_config.json  # Claude Desktop configuration
└── setup_instructions.md  # Detailed setup guide
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

### Development Setup

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🔗 Related Links

- [Spotify Web API Documentation](https://developer.spotify.com/documentation/web-api/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Claude Desktop](https://claude.ai/desktop)
- [MongoDB Documentation](https://docs.mongodb.com/)

## ⚠️ Disclaimer

This project is not affiliated with Spotify Technology S.A. It uses the official Spotify Web API and follows their terms of service. Make sure to comply with Spotify's API terms and rate limits.

## 🆘 Support

If you encounter any issues or have questions:

1. Check the [Troubleshooting](#🐛-troubleshooting) section
2. Look through existing [GitHub Issues](https://github.com/vidit1906/spotify_mcp/issues)
3. Create a new issue with detailed information about your problem

---

**Made with ❤️ for the Claude Desktop and Spotify communities**
