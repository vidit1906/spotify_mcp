#!/usr/bin/env python3
"""
Debug script to help troubleshoot Spotify MCP server issues.
This script checks your setup and provides specific guidance.
"""

import os
import sys
import time
import requests
from pymongo.mongo_client import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment():
    """Check if all required environment variables are set."""
    print("🔍 Checking environment variables...")
    
    required_vars = ["MONGO_URI", "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"]
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
            print(f"❌ {var}: Not set")
        else:
            # Show partial value for security
            if "SECRET" in var or "URI" in var:
                display_value = value[:10] + "..." if len(value) > 10 else value
            else:
                display_value = value
            print(f"✅ {var}: {display_value}")
    
    if missing_vars:
        print(f"\n❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file with these variables.")
        return False
    
    return True

def check_mongodb():
    """Check MongoDB connection and stored tokens."""
    print("\n🔍 Checking MongoDB connection...")
    
    try:
        mongo_uri = os.getenv("MONGO_URI")
        client = MongoClient(mongo_uri)
        db = client.claude_dj
        users_collection = db.users
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
        
        # Check for stored user data
        user_data = users_collection.find_one()
        if not user_data:
            print("❌ No authenticated user found in database")
            print("Please run 'python app.py' and complete the Spotify OAuth flow at http://127.0.0.1:5001/login")
            return False
        
        print(f"✅ Found user: {user_data.get('spotify_user_id', 'Unknown')}")
        
        # Check token expiry
        expires_at = user_data.get('expires_at', 0)
        current_time = int(time.time())
        
        if expires_at <= current_time:
            print(f"⚠️ Access token expired (expired {current_time - expires_at} seconds ago)")
            print("The MCP server will attempt to refresh it automatically")
        else:
            print(f"✅ Access token valid (expires in {expires_at - current_time} seconds)")
        
        return True
        
    except Exception as e:
        print(f"❌ MongoDB error: {e}")
        return False

def check_spotify_api():
    """Check Spotify API access and available devices."""
    print("\n🔍 Checking Spotify API access...")
    
    try:
        # Get user token (simplified version of the MCP server logic)
        mongo_uri = os.getenv("MONGO_URI")
        client = MongoClient(mongo_uri)
        db = client.claude_dj
        users_collection = db.users
        
        user_data = users_collection.find_one()
        if not user_data:
            print("❌ No user data found")
            return False
        
        access_token = user_data['access_token']
        
        # Test API access
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Check user profile
        profile_response = requests.get("https://api.spotify.com/v1/me", headers=headers)
        if profile_response.status_code == 200:
            profile_data = profile_response.json()
            print(f"✅ Spotify API access successful")
            print(f"✅ Logged in as: {profile_data.get('display_name', 'Unknown')} ({profile_data.get('id', 'Unknown')})")
            
            # Check subscription type
            product = profile_data.get('product', 'Unknown')
            if product == 'premium':
                print("✅ Spotify Premium detected (required for playback control)")
            else:
                print(f"⚠️ Spotify subscription: {product} (Premium required for playback control)")
        else:
            print(f"❌ Spotify API access failed: {profile_response.status_code}")
            return False
        
        # Check available devices
        devices_response = requests.get("https://api.spotify.com/v1/me/player/devices", headers=headers)
        if devices_response.status_code == 200:
            devices_data = devices_response.json()
            devices = devices_data.get('devices', [])
            
            print(f"\n📱 Found {len(devices)} Spotify device(s):")
            
            if not devices:
                print("❌ No devices found")
                print("Please open Spotify on your phone, computer, or another device")
                return False
            
            active_devices = []
            for device in devices:
                status = "🟢 Active" if device.get('is_active') else "⚪ Inactive" 
                print(f"  • {device['name']} ({device['type']}) - {status}")
                if device.get('is_active'):
                    active_devices.append(device)
            
            if not active_devices:
                print("\n⚠️ No active devices found!")
                print("To fix this:")
                print("1. Open Spotify on one of the devices listed above")
                print("2. Start playing any song (you can pause it immediately)")
                print("3. The device will now be 'active' and ready for remote control")
                return False
            else:
                print(f"\n✅ {len(active_devices)} active device(s) ready for playback")
                return True
        else:
            print(f"❌ Could not get devices: {devices_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Spotify API error: {e}")
        return False

def test_playback():
    """Test basic playback functionality."""
    print("\n🔍 Testing playback functionality...")
    
    try:
        # Get user token
        mongo_uri = os.getenv("MONGO_URI")
        client = MongoClient(mongo_uri)
        db = client.claude_dj
        users_collection = db.users
        
        user_data = users_collection.find_one()
        access_token = user_data['access_token']
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get current playback state
        player_response = requests.get("https://api.spotify.com/v1/me/player", headers=headers)
        
        if player_response.status_code == 200:
            player_data = player_response.json()
            if player_data and player_data.get('item'):
                track = player_data['item']
                print(f"✅ Current playback state available")
                print(f"   Playing: {track['name']} by {', '.join(a['name'] for a in track['artists'])}")
            else:
                print("ℹ️ No current playback (this is normal if nothing is playing)")
        elif player_response.status_code == 204:
            print("ℹ️ No current playback (this is normal if nothing is playing)")
        else:
            print(f"⚠️ Could not get playback state: {player_response.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Playback test error: {e}")
        return False

def main():
    """Run all diagnostic checks."""
    print("🎵 Spotify MCP Server Diagnostic Tool")
    print("=" * 50)
    
    all_checks_passed = True
    
    # Run all checks
    all_checks_passed &= check_environment()
    all_checks_passed &= check_mongodb()
    all_checks_passed &= check_spotify_api()
    all_checks_passed &= test_playback()
    
    print("\n" + "=" * 50)
    
    if all_checks_passed:
        print("🎉 All checks passed! Your Spotify MCP server should work correctly.")
        print("\nTo use in Claude Desktop:")
        print("1. Make sure Claude Desktop is restarted")
        print("2. Try saying: 'Play Hotel California by Eagles'")
    else:
        print("❌ Some checks failed. Please fix the issues above and try again.")
        print("\nCommon solutions:")
        print("• Create a .env file with your Spotify credentials")
        print("• Run 'python app.py' to authenticate with Spotify")
        print("• Open Spotify on a device and start playing music")
        print("• Make sure you have Spotify Premium")

if __name__ == "__main__":
    main()
