from __future__ import annotations

import base64
import os
import shlex
import time
from dataclasses import dataclass
from typing import Any, Generator

import httpx
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Track:
    id: int
    title: str
    artist: str
    artist_id: int
    duration_ms: int
    stream_url: str | None
    permalink_url: str
    artwork_url: str | None
    play_count: int
    likes_count: int
    tags_raw: list[str]
    genre: str | None
    streamable: bool
    access: str
    created_at: str

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Track:
        tag_str = data.get("tag_list", "") or ""
        try:
            tags = shlex.split(tag_str)
        except ValueError:
            tags = tag_str.split()

        return cls(
            id=data["id"],
            title=data.get("title", ""),
            artist=data.get("user", {}).get("username", ""),
            artist_id=data.get("user", {}).get("id", 0),
            duration_ms=data.get("duration", 0),
            stream_url=data.get("stream_url"),
            permalink_url=data.get("permalink_url", ""),
            artwork_url=data.get("artwork_url"),
            play_count=data.get("playback_count", 0) or 0,
            likes_count=data.get("likes_count", 0) or 0,
            tags_raw=tags,
            genre=data.get("genre") or None,
            streamable=bool(data.get("streamable", False)),
            access=data.get("access", "playable"),
            created_at=data.get("created_at", ""),
        )


@dataclass
class TokenCache:
    access_token: str
    expires_at: float

    def is_valid(self, buffer_seconds: int = 60) -> bool:
        return time.time() < self.expires_at - buffer_seconds


class SoundCloudClient:
    BASE_URL = "https://api.soundcloud.com"
    TOKEN_URL = "https://secure.soundcloud.com/oauth/token"

    def __init__(self) -> None:
        self.client_id = os.environ["SOUNDCLOUD_CLIENT_ID"]
        self.client_secret = os.environ["SOUNDCLOUD_CLIENT_SECRET"]
        self._token: TokenCache | None = None
        os.environ.pop("SSLKEYLOGFILE", None)
        self._http = httpx.Client(timeout=30.0, verify=False)

    def _fetch_token(self) -> TokenCache:
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        resp = self._http.post(
            self.TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"grant_type": "client_credentials"},
        )
        resp.raise_for_status()
        body = resp.json()
        return TokenCache(
            access_token=body["access_token"],
            expires_at=time.time() + body.get("expires_in", 3600),
        )

    def _ensure_token(self) -> str:
        if self._token is None or not self._token.is_valid():
            self._token = self._fetch_token()
        return self._token.access_token

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self.BASE_URL}{path}" if path.startswith("/") else path
        backoff = 1.0
        resp: httpx.Response | None = None
        for _ in range(5):
            token = self._ensure_token()
            resp = self._http.get(
                url,
                params=params,
                headers={"Authorization": f"OAuth {token}"},
            )
            if resp.status_code == 429:
                time.sleep(backoff)
                backoff = min(backoff * 2, 60.0)
                continue
            if resp.status_code == 401:
                self._token = None
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError(f"Exceeded retry limit for {url}")

    def get_track(self, track_id: int) -> Track:
        data = self._get(f"/tracks/{track_id}")
        return Track.from_api(data)

    def search_tracks(self, query: str, limit: int = 50, offset: int = 0) -> list[Track]:
        data = self._get("/tracks", params={"q": query, "limit": limit, "offset": offset})
        items = data if isinstance(data, list) else data.get("collection", [])
        return [Track.from_api(t) for t in items]

    def get_related_tracks(self, track_id: int, limit: int = 10) -> list[Track]:
        data = self._get(f"/tracks/{track_id}/related", params={"limit": limit})
        items = data if isinstance(data, list) else data.get("collection", [])
        return [Track.from_api(t) for t in items]

    def get_tracks_by_tag(self, tag: str, limit: int = 50, offset: int = 0) -> list[Track]:
        data = self._get("/tracks", params={"tags": tag, "limit": limit, "offset": offset})
        items = data if isinstance(data, list) else data.get("collection", [])
        return [Track.from_api(t) for t in items]

    def get_stream_url(self, track_id: int) -> str | None:
        try:
            token = self._ensure_token()
            data = self._get(f"/tracks/{track_id}/streams")
            url = (
                data.get("http_mp3_128_url") or
                data.get("hls_mp3_128_url") or
                data.get("preview_mp3_128_url")
            )
            if not url:
                return None
            # Follow redirects with auth to reach the final pre-signed CDN URL
            resp = self._http.get(
                url,
                headers={"Authorization": f"OAuth {token}"},
                follow_redirects=True,
            )
            return str(resp.url)
        except Exception:
            return None

    def resolve(self, url: str) -> dict[str, Any]:
        return self._get("/resolve", params={"url": url})

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        max_pages: int = 10,
    ) -> Generator[dict[str, Any], None, None]:
        params = dict(params or {})
        params.setdefault("limit", 50)
        url: str | None = f"{self.BASE_URL}{path}"
        page = 0
        while url and page < max_pages:
            data = self._get(url, params=params if page == 0 else None)
            if isinstance(data, list):
                yield from data
                break
            yield from data.get("collection", [])
            url = data.get("next_href")
            page += 1

    def __enter__(self) -> SoundCloudClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self._http.close()