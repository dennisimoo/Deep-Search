#!/usr/bin/env python3
"""
YouTube Transcript Web Viewer

A Flask web application that accepts YouTube video IDs and displays transcripts.
"""

import os
from flask import Flask, request, render_template, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
import re

app = Flask(__name__)

def extract_video_id(url_or_id):
    """Extract video ID from YouTube URL or return if already an ID"""
    # If it's already an 11-character ID, return it
    if len(url_or_id) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    
    # Extract from URL patterns
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/.*[?&]v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)
    
    return None

def get_transcript(video_id):
    """Download transcript for given video ID with fallback mechanisms"""
    proxy = os.getenv('YOUTUBE_PROXY')
    
    # Try with proxy first if configured
    if proxy:
        try:
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, proxies=proxies)
            return format_transcript(transcript_list)
        except Exception as e:
            print(f"Proxy failed ({proxy}): {str(e)}")
    
    # Fallback to direct connection
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return format_transcript(transcript_list)
    except Exception as e:
        # Try getting available transcripts to provide better error messages
        try:
            available = YouTubeTranscriptApi.list_transcripts(video_id)
            available_languages = [t.language_code for t in available]
            raise Exception(f"Could not get transcript. Available languages: {', '.join(available_languages)}")
        except:
            raise Exception(f"No transcript available for video {video_id}: {str(e)}")

def format_transcript(transcript_list):
    """Format transcript entries"""
    formatted_transcript = []
    for entry in transcript_list:
        formatted_transcript.append({
            'time': entry['start'],
            'text': entry['text'],
            'formatted_time': f"{int(entry['start'] // 60):02d}:{int(entry['start'] % 60):02d}"
        })
    return formatted_transcript

@app.route('/')
def index():
    """Home page with instructions"""
    return render_template('index.html')

@app.route('/watch')
def watch():
    """Display transcript for YouTube video"""
    video_id_param = request.args.get('v')
    
    if not video_id_param:
        return render_template('error.html', 
                             error_message="No video ID provided. Please use /watch?v=VIDEO_ID"), 400
    
    video_id = extract_video_id(video_id_param)
    
    if not video_id:
        return render_template('error.html', 
                             error_message="Invalid video ID format"), 400
    
    try:
        transcript = get_transcript(video_id)
        proxy_used = os.getenv('YOUTUBE_PROXY', 'None')
        
        return render_template('transcript.html', 
                             video_id=video_id,
                             transcript=transcript,
                             proxy_used=proxy_used)
        
    except Exception as e:
        return render_template('error.html', 
                             error_message=str(e)), 500

@app.route('/api/transcript/<video_id>')
def api_transcript(video_id):
    """API endpoint to get transcript as JSON"""
    try:
        transcript = get_transcript(video_id)
        return jsonify({
            'success': True,
            'video_id': video_id,
            'transcript': transcript,
            'proxy_used': os.getenv('YOUTUBE_PROXY', None)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Get proxy from environment variable  
    proxy = os.getenv('YOUTUBE_PROXY', '45.76.97.117:3128')  # Try different proxy
    if proxy:
        print(f"Using proxy: {proxy}")
    else:
        print("No proxy configured - using direct connection")
    
    app.run(host='0.0.0.0', port=33079, debug=True)