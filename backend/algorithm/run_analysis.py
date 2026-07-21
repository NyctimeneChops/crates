#!/usr/bin/env python3
"""
Run audio analysis on Vast.ai.
Usage: python run_analysis.py

Requirements (Linux):
  pip install essentia requests sqlalchemy psycopg python-dotenv
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from soundcloud.client import SoundCloudClient
from algorithm.audio_analyzer import AudioAnalyzer

print("Starting audio analysis pipeline...")
print(f"Database: {os.environ.get('DATABASE_URL', 'NOT SET')[:30]}...")

with SoundCloudClient() as sc:
    analyzer = AudioAnalyzer(sc)
    total = analyzer.run(max_tracks=2000)
    print(f"Analysis complete. {total} tracks analyzed.")
