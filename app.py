import os
import time
import urllib.parse
import requests
import anthropic # <-- Import anthropic
from flask import Flask, request, redirect, jsonify
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv

# --- 1. INITIAL SETUP ---
load_dotenv()
app = Flask(__name__)

# Load credentials
MONGO_URI = os.getenv("MONGO_URI")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") # <-- Load Claude Key

# Spotify API constants
REDIRECT_URI = "http://127.0.0.1:5001/callback"
SCOPE = "user-modify-playback-state user-read-playback-state playlist-modify-public playlist-modify-private"

# --- 2. DATABASE & API CLIENTS ---
try:
    client = MongoClient(MONGO_URI)
    db = client.claude_dj
    users_collection = db.users
    client.admin.command('ping')
    print("✅ Connected to MongoDB!")
except Exception as e:
    print(e)
    exit()

# Initialize Claude client
try:
    claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    print("✅ Connected to Anthropic (Claude) API!")
except Exception as e:
    print(e)
    exit()

# --- 3. SPOTIFY HELPER FUNCTION ---

def play_song_on_spotify(access_token, song_name, artist_name):
    """Searches for a song and plays it on Spotify."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 1. Search for the track
    search_url = "https://api.spotify.com/v1/search"
    search_params = {
        "q": f"track:{song_name} artist:{artist_name}",
        "type": "track",
        "limit": 1
    }
    search_response = requests.get(search_url, headers=headers, params=search_params)
    search_results = search_response.json()

    tracks = search_results.get("tracks", {}).get("items", [])
    if not tracks:
        return {"status": "error", "message": "Song not found."}
    
    track_uri = tracks[0]["uri"]

    # 2. Play the track
    play_url = "https://api.spotify.com/v1/me/player/play"
    play_data = {"uris": [track_uri]}
    play_response = requests.put(play_url, headers=headers, json=play_data)

    if play_response.status_code == 204:
        return {"status": "success", "message": f"Now playing '{tracks[0]['name']}'."}
    else:
        return {"status": "error", "message": "Could not play song. Is Spotify active?"}


# --- 4. SPOTIFY AUTHENTICATION ROUTES (Unchanged) ---
@app.route('/')
def home():
    return '<a href="/login">Log in with Spotify</a>'

@app.route('/debug')
def debug():
    """Debug route to check configuration"""
    return f"""
    <h2>Debug Info</h2>
    <p>Client ID: {SPOTIFY_CLIENT_ID[:10]}...</p>
    <p>Redirect URI: {REDIRECT_URI}</p>
    <p>Scope: {SCOPE}</p>
    """

@app.route('/login')
def login():
    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        'response_type': 'code', 'client_id': SPOTIFY_CLIENT_ID, 'scope': SCOPE, 'redirect_uri': REDIRECT_URI,
    })
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "<h1>Error: No authorization code received</h1>", 400
    
    token_url = "https://accounts.spotify.com/api/token"
    token_data = {
        'grant_type': 'authorization_code', 
        'code': code, 
        'redirect_uri': REDIRECT_URI,
        'client_id': SPOTIFY_CLIENT_ID, 
        'client_secret': SPOTIFY_CLIENT_SECRET,
    }
    
    response = requests.post(token_url, data=token_data)
    token_info = response.json()
    
    # Debug: Print the response to see what we're getting
    print(f"Token response status: {response.status_code}")
    print(f"Token response: {token_info}")
    
    if 'access_token' not in token_info:
        error_msg = token_info.get('error_description', 'Unknown error')
        return f"<h1>Spotify Authentication Error</h1><p>{error_msg}</p><p>Response: {token_info}</p>", 400
    
    headers = {"Authorization": f"Bearer {token_info['access_token']}"}
    user_profile_response = requests.get("https://api.spotify.com/v1/me", headers=headers)
    user_profile_data = user_profile_response.json()
    
    if 'id' not in user_profile_data:
        return f"<h1>Error getting user profile</h1><p>{user_profile_data}</p>", 400
    
    spotify_user_id = user_profile_data['id']
    expires_at = int(time.time()) + token_info['expires_in']
    user_data = {
        'spotify_user_id': spotify_user_id, 
        'access_token': token_info['access_token'],
        'refresh_token': token_info['refresh_token'], 
        'expires_at': expires_at, 
        'scope': token_info['scope'],
    }
    users_collection.update_one({'spotify_user_id': spotify_user_id}, {'$set': user_data}, upsert=True)
    return "<h1>Login successful!</h1><p>You can now close this window.</p>"

# --- 5. THE NEW AI CHAT ENDPOINT ---

@app.route('/chat', methods=['POST'])
def chat():
    """Receives a command, processes it with Claude, and executes the action."""
    user_command = request.json.get('command')
    if not user_command:
        return jsonify({"error": "No command provided"}), 400

    # For this example, we'll just use the first user in the database.
    # In a real app, you'd identify the logged-in user.
    user_data = users_collection.find_one()
    if not user_data:
        return jsonify({"error": "No authenticated user found. Please log in first."}), 401

    access_token = user_data['access_token']

    # Define the tool(s) for Claude
    tools = [
        {
            "name": "play_song",
            "description": "Finds a song by its name and artist and plays it on Spotify.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "song_name": {"type": "string", "description": "The name of the song to play."},
                    "artist_name": {"type": "string", "description": "The name of the artist of the song."}
                },
                "required": ["song_name", "artist_name"]
            }
        }
    ]

    # Call Claude and ask it to use our tools
    try:
        response = claude_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1024,
            messages=[{"role": "user", "content": user_command}],
            tools=tools,
        )
    except Exception as e:
        return jsonify({"error": f"Claude API error: {e}"}), 500
    
    # Process Claude's response to find the tool it wants to use
    tool_use = next((block for block in response.content if block.type == 'tool_use'), None)

    if not tool_use:
        return jsonify({"message": "I'm not sure how to help with that."})

    tool_name = tool_use.name
    tool_input = tool_use.input

    if tool_name == "play_song":
        song_name = tool_input.get("song_name")
        artist_name = tool_input.get("artist_name")
        result = play_song_on_spotify(access_token, song_name, artist_name)
        return jsonify(result)

    return jsonify({"message": "Unknown command."})


if __name__ == '__main__':
    app.run(debug=True, port=5001, host="0.0.0.0")

