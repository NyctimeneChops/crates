from __future__ import annotations

import os
import time
import tempfile
import requests

from soundcloud.client import SoundCloudClient


class AudioAnalyzer:
    def __init__(self, sc_client: SoundCloudClient) -> None:
        self.sc_client = sc_client

    def analyze_track(self, track) -> dict | None:
        stream_url = self.sc_client.get_stream_url(track.soundcloud_id)
        if not stream_url:
            return None

        tmp_path: str | None = None
        try:
            response = requests.get(stream_url, timeout=30, stream=True)
            response.raise_for_status()

            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                for chunk in response.iter_content(chunk_size=8192):
                    tmp.write(chunk)
                tmp_path = tmp.name
        except Exception as e:
            print(f"[analyzer] download failed for {track.soundcloud_id}: {e}", flush=True)
            return None

        try:
            import essentia.standard as es

            extractor = es.MusicExtractor(
                lowlevelStats=["mean", "stdev"],
                rhythmStats=["mean", "stdev"],
                tonalStats=["mean", "stdev"],
            )
            features, features_frames = extractor(tmp_path)

            names = features.descriptorNames()

            def f(key, default=0.0):
                try:
                    return float(features[key]) if key in names else default
                except Exception:
                    return default

            def fs(key, default="unknown"):
                try:
                    return str(features[key]) if key in names else default
                except Exception:
                    return default

            def fmfcc(idx, default=0.0):
                try:
                    return float(features["lowlevel.mfcc.mean"][idx]) if "lowlevel.mfcc.mean" in names else default
                except Exception:
                    return default

            return {
                "bpm": f("rhythm.bpm"),
                "danceability": f("rhythm.danceability"),
                "beat_loudness": f("rhythm.beats_loudness.mean"),
                "energy": f("lowlevel.average_loudness"),
                "loudness": f("lowlevel.average_loudness"),
                "dynamic_complexity": f("lowlevel.dynamic_complexity"),
                "spectral_centroid": f("lowlevel.spectral_centroid.mean"),
                "spectral_rolloff": f("lowlevel.spectral_rolloff.mean"),
                "spectral_flux": f("lowlevel.spectral_flux.mean"),
                "zero_crossing_rate": f("lowlevel.zerocrossingrate.mean"),
                "key": fs("tonal.key_krumhansl.key"),
                "scale": fs("tonal.key_krumhansl.scale"),
                "key_strength": f("tonal.key_krumhansl.strength"),
                "tuning_frequency": f("tonal.tuning_frequency"),
                "chords_strength": f("tonal.chords_strength.mean"),
                "mfcc_1": fmfcc(1),
                "mfcc_2": fmfcc(2),
                "mfcc_3": fmfcc(3),
                "mfcc_4": fmfcc(4),
                "mfcc_5": fmfcc(5),
                "instrumental_probability": 0.5,
                "mood_aggressive": 0.5,
                "mood_happy": 0.5,
                "mood_relaxed": 0.5,
                "mood_sad": 0.5,
                "valence": 0.5,
                "arousal": f("lowlevel.average_loudness"),
            }

        except Exception as e:
            print(f"[analyzer] essentia failed for {track.soundcloud_id}: {e}", flush=True)
            return None
        finally:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    def run(self, batch_size: int = 50, max_tracks: int = 2000) -> int:
        import psycopg
        import json

        db_url = os.environ["DATABASE_URL"]
        conn_str = db_url.replace("postgresql+psycopg://", "postgresql://")

        with psycopg.connect(conn_str, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, soundcloud_id, title, artist
                    FROM tracks
                    WHERE audio_features IS NULL
                    AND streamable = TRUE
                    LIMIT %s
                """, (max_tracks,))
                rows = cur.fetchall()

        total = len(rows)
        print(f"[analyzer] {total} tracks to analyze", flush=True)

        analyzed = 0
        failed = 0

        for i, (track_id, soundcloud_id, title, artist) in enumerate(rows):
            print(f"[analyzer] {i+1}/{total}: {artist} - {title}", flush=True)

            class TrackProxy:
                pass
            track = TrackProxy()
            track.soundcloud_id = soundcloud_id
            track.id = track_id

            features = self.analyze_track(track)

            if features:
                with psycopg.connect(conn_str, autocommit=True) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE tracks SET audio_features = %s WHERE id = %s",
                            (json.dumps(features), track_id)
                        )
                analyzed += 1
            else:
                failed += 1

            time.sleep(0.5)

        print(f"[analyzer] done. {analyzed} analyzed, {failed} failed.", flush=True)
        return analyzed
