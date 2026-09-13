"""
Service de recherche haute fidélité dans le catalogue Apple Music.
Interroge directement l'API de catalogue Apple Music (amp-api.music.apple.com)
avec jeton d'accès officiel intégré et rafraîchissement dynamique,
garantissant un taux de détection maximal pour les clips vidéo officiels.
"""

import difflib
import re
import unicodedata
from typing import Optional, List, Dict, Any
import requests

from .bridge_interface import TrackInfo, VideoMatch


class CatalogSearchService:
    """Moteur de recherche de clips vidéo dans le catalogue Apple Music."""

    # Jeton officiel Apple WebKit (valide et automatiquement actualisé si nécessaire)
    DEFAULT_AMP_TOKEN = (
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IldlYlBsYXlLaWQifQ."
        "eyJpc3MiOiJBTVBXZWJQbGF5IiwiaWF0IjoxNzg2NjMyOTI0LCJleHAiOjE3OTI2ODA5MjQs"
        "InJvb3RfaHR0cHNfb3JpZ2luIjpbImFwcGxlLmNvbSJdfQ."
        "hBgj61sZf-y7bmuvT-joXAUAcf7TVJ51732xnH5vFkLHOmsQHxVqGMYUuI4h8c0-RX3fRY3moylhLW8fewFJyw"
    )

    AMP_API_BASE = "https://amp-api.music.apple.com/v1"
    ITUNES_BASE = "https://itunes.apple.com/search"

    def __init__(self, storefront: str = "fr", tolerance: float = 0.85):
        self.storefront = storefront.lower()
        self.tolerance = tolerance
        self._amp_token = self.DEFAULT_AMP_TOKEN
        self._cache: Dict[str, Optional[VideoMatch]] = {}

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._amp_token}",
            "Origin": "https://music.apple.com",
            "Referer": "https://music.apple.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)",
            "Accept": "application/json"
        }

    def _is_faux_video(self, title: str) -> bool:
        """
        Détecte si la vidéo est un faux clip vidéo (simple audio statique, visualizer, karaoké ou lyric video).
        Ces vidéos sont rejetées pour garantir exclusivement de vrais clips vidéo musicaux.
        """
        if not title:
            return False
        faux_patterns = [
            r"\b(official\s+)?audio\b",
            r"\bvisualizer\b",
            r"\baudio\s+visualizer\b",
            r"\bkaraoke\b",
            r"\blyric\s+video\b",
            r"\blyrics\b",
        ]
        for pat in faux_patterns:
            if re.search(pat, title, re.IGNORECASE):
                return True
        return False

    def _normalize(self, text: str) -> str:
        """Normalise une chaîne pour comparaison insensible aux accents, casse et ponctuation."""
        if not text:
            return ""
        text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")
        text = text.lower()
        # Retrait des mentions parasites récurrentes dans les clips
        parasites = [
            r"\(official music video\)",
            r"\(official video\)",
            r"\[official music video\]",
            r"\[official video\]",
            r"\(clip officiel\)",
            r"\[clip officiel\]",
            r"\(video\)",
            r"\(visualizer\)",
            r"\(audio\)",
            r"\(live[^\)]*\)",
            r"\[live[^\]]*\]",
            r"\(explicit\)",
            r"\(4k\)",
            r"\[4k\]",
            r"\(hd\)",
            r"\[hd\]",
        ]
        for p in parasites:
            text = re.sub(p, "", text, flags=re.IGNORECASE)
        # Retrait de la ponctuation
        text = re.sub(r"[^\w\s]", " ", text)
        return " ".join(text.split())

    def _primary_artist(self, artist: str) -> str:
        """Extrait le nom de l'artiste principal (avant feat, &, with, virgule)."""
        if not artist:
            return ""
        separators = [",", "&", " feat.", " ft.", " feat ", " ft ", " with ", " / ", " x "]
        lower_art = artist
        cut_pos = len(lower_art)
        for sep in separators:
            idx = lower_art.lower().find(sep)
            if idx != -1 and idx < cut_pos:
                cut_pos = idx
        return artist[:cut_pos].strip()

    def _compute_similarity(self, a: str, b: str) -> float:
        """Calcule le ratio de similarité textuelle."""
        norm_a = self._normalize(a)
        norm_b = self._normalize(b)
        if not norm_a or not norm_b:
            return 0.0
        if norm_a == norm_b:
            return 1.0
        if norm_a in norm_b or norm_b in norm_a:
            return 0.90
        return difflib.SequenceMatcher(None, norm_a, norm_b).ratio()

    def _compute_artist_similarity(self, track_art: str, video_art: str) -> float:
        """
        Calcule une similarité d'artiste haute précision pour éliminer tout faux positif.
        Combine comparaison d'artiste principal, correspondance de tokens et inclusion stricte.
        """
        norm_trk = self._normalize(track_art)
        norm_vid = self._normalize(video_art)
        if not norm_trk or not norm_vid:
            return 0.0
        if norm_trk == norm_vid:
            return 1.0

        prim_trk = self._normalize(self._primary_artist(track_art))
        prim_vid = self._normalize(self._primary_artist(video_art))

        # 1. Similarité entre les artistes principaux
        prim_ratio = difflib.SequenceMatcher(None, prim_trk, prim_vid).ratio() if prim_trk and prim_vid else 0.0
        full_ratio = difflib.SequenceMatcher(None, norm_trk, norm_vid).ratio()

        # Si les artistes principaux sont quasi identiques (ex: "The Weeknd" == "The Weeknd")
        if prim_trk and prim_vid and (prim_trk == prim_vid or prim_ratio >= 0.88):
            return max(0.95, full_ratio)

        # 2. Inclusion de l'artiste principal (ex: "Freddie Dredd" dans "Freddie Dredd & Doom Shop")
        if (prim_trk and prim_trk in norm_vid) or (prim_vid and prim_vid in norm_trk):
            return max(0.90, full_ratio)

        # 3. Correspondance d'ensemble de tokens d'artistes (gestion des featurings et ordres inversés)
        stop = {"feat", "ft", "and", "the", "with", "by", "x"}
        toks_a = {w for w in norm_trk.split() if w not in stop and len(w) > 1}
        toks_b = {w for w in norm_vid.split() if w not in stop and len(w) > 1}
        if toks_a and toks_b:
            overlap = len(toks_a & toks_b) / min(len(toks_a), len(toks_b))
            jaccard = len(toks_a & toks_b) / len(toks_a | toks_b)
            if overlap >= 0.80 and prim_ratio >= 0.60:
                return max(0.92, full_ratio)
            if jaccard >= 0.60:
                return max(0.88, full_ratio)

        # Artistes sans aucun lien probant -> Score très bas pour forcer le rejet
        return max(prim_ratio * 0.7, full_ratio * 0.7)

    def search_music_video(self, track: TrackInfo) -> Optional[VideoMatch]:
        """
        Recherche s'il existe une version clip vidéo pour le morceau donné.
        Retourne l'objet VideoMatch ou None.
        """
        clean_title = track.clean_name()
        clean_artist = self._primary_artist(track.artist)
        cache_key = f"{self._normalize(clean_title)}___{self._normalize(clean_artist)}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # 1. Recherche ciblée avec titre épuré et artiste
        match = self._search_via_amp_api(clean_title, clean_artist, track.artist)

        # 2. Si non trouvé, tentative avec le titre d'origine exact et artiste complet
        if not match and track.name != clean_title:
            match = self._search_via_amp_api(track.name, clean_artist, track.artist)

        self._cache[cache_key] = match
        return match

    def _search_via_amp_api(self, title: str, artist: str, full_artist: str) -> Optional[VideoMatch]:
        """Effectue la requête auprès de l'API de catalogue Apple Music."""
        query = f"{title} {artist}".strip()
        url = f"{self.AMP_API_BASE}/catalog/{self.storefront}/search"
        params = {
            "term": query,
            "types": "music-videos",
            "limit": 8
        }

        try:
            resp = requests.get(url, headers=self._get_headers(), params=params, timeout=5.0)

            # Si le jeton est expiré (401), tenter de rafraîchir
            if resp.status_code == 401:
                if self._refresh_amp_token():
                    resp = requests.get(url, headers=self._get_headers(), params=params, timeout=5.0)

            if resp.status_code != 200:
                return None

            data = resp.json()
            items = data.get("results", {}).get("music-videos", {}).get("data", [])
            if not items:
                return None

            best_match: Optional[VideoMatch] = None
            best_score = 0.0

            for it in items:
                # Vérification stricte : doit être explicitement un clip vidéo
                if it.get("type") != "music-videos":
                    continue

                attr = it.get("attributes", {})
                item_title = attr.get("name", "")
                item_artist = attr.get("artistName", "")

                # 1. EXCLUSION DES FAUX CLIPS (Audio, Visualizers, Karaoké, Lyrics)
                if self._is_faux_video(item_title):
                    continue

                # 2. VÉRIFICATION STRICTE TITRE ET ARTISTE
                title_sim = self._compute_similarity(title, item_title)
                artist_sim = self._compute_artist_similarity(full_artist or artist, item_artist)

                # FILTRE ANTI-FAUX POSITIFS ABSOLU :
                # Titre >= 0.80 et Artiste >= 0.78
                if title_sim < 0.80 or artist_sim < 0.78:
                    continue

                combined = (title_sim * 0.50) + (artist_sim * 0.50)

                # Pénalité légère pour les enregistrements Live si le morceau initial ne mentionne pas Live
                is_video_live = bool(re.search(r"\blive\b", item_title, re.IGNORECASE))
                is_track_live = bool(re.search(r"\blive\b", title, re.IGNORECASE))
                if is_video_live and not is_track_live:
                    combined -= 0.06

                if combined > best_score and combined >= self.tolerance:
                    best_score = combined
                    raw_art = attr.get("artwork", {}).get("url", "")
                    if raw_art:
                        art_url = raw_art.replace("{w}x{h}", "600x600").replace("{f}", "jpg")
                    else:
                        art_url = ""

                    preview_list = attr.get("previews", [])
                    preview_url = preview_list[0].get("hlsUrl", "") if preview_list else ""

                    best_match = VideoMatch(
                        track_name=item_title,
                        artist_name=item_artist,
                        video_url=attr.get("url", ""),
                        preview_url=preview_url,
                        artwork_url=art_url,
                        track_id=str(it.get("id", "")),
                        source="apple_music_catalog",
                        confidence_score=round(combined, 2),
                        extra_metadata={
                            "genre": ", ".join(attr.get("genreNames", [])),
                            "durationMillis": attr.get("durationInMillis", 0),
                            "releaseDate": attr.get("releaseDate", ""),
                            "isrc": attr.get("isrc", "")
                        }
                    )

            return best_match

        except Exception as e:
            print(f"[CatalogSearch] Erreur recherche amp-api pour '{query}': {e}")
            return None

    def _search_via_itunes_fallback(self, title: str, artist: str) -> Optional[VideoMatch]:
        """Recherche de secours via l'iTunes Search API avec même rigueur anti-faux positifs."""
        query = f"{title} {artist}".strip()
        params = {
            "term": query,
            "entity": "musicVideo",
            "country": self.storefront,
            "limit": 5
        }
        try:
            resp = requests.get(
                self.ITUNES_BASE,
                params=params,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
                timeout=4.0
            )
            if resp.status_code != 200:
                return None

            data = resp.json()
            for it in data.get("results", []):
                if it.get("kind") == "music-video":
                    item_title = it.get("trackName", "")
                    item_artist = it.get("artistName", "")

                    if self._is_faux_video(item_title):
                        continue

                    title_sim = self._compute_similarity(title, item_title)
                    artist_sim = self._compute_artist_similarity(artist, item_artist)
                    if title_sim < 0.80 or artist_sim < 0.78:
                        continue

                    combined = (title_sim * 0.50) + (artist_sim * 0.50)
                    if combined >= self.tolerance:
                        raw_art = it.get("artworkUrl100", "")
                        high_art = raw_art.replace("100x100bb.jpg", "600x600bb.jpg") if raw_art else ""
                        return VideoMatch(
                            track_name=item_title,
                            artist_name=item_artist,
                            video_url=it.get("trackViewUrl", ""),
                            preview_url=it.get("previewUrl", ""),
                            artwork_url=high_art or raw_art,
                            track_id=str(it.get("trackId", "")),
                            source="itunes_catalog",
                            confidence_score=round(combined, 2)
                        )
        except Exception:
            pass
        return None

    def _refresh_amp_token(self) -> bool:
        """Tente d'extraire dynamiquement un nouveau jeton Apple WebKit."""
        try:
            r = requests.get("https://music.apple.com/us/browse", timeout=4.0)
            scripts = re.findall(r"src=[\"\x27](/[^\"\x27]+\.js)[\"\x27]", r.text)
            for s in scripts:
                if "index" in s:
                    txt = requests.get("https://music.apple.com" + s, timeout=4.0).text
                    m = re.findall(r"\$c\s*=\s*\"(eyJh[^\"]+)\"", txt)
                    if m:
                        self._amp_token = m[0]
                        return True
        except Exception as e:
            print(f"[CatalogSearch] Échec rafraîchissement token: {e}")
        return False
