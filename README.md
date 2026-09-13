# 🎬 Apple Music To Video (macOS) `v1.0.1`

[![macOS](https://img.shields.io/badge/Platform-macOS%20Sonoma%20%7C%20Sequoia-black?style=flat-square&logo=apple)](https://www.apple.com/macos/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/Framework-PyQt6-green?style=flat-square&logo=qt)](https://riverbankcomputing.com/software/pyqt/)
[![Version](https://img.shields.io/badge/Version-v1.0.1-red?style=flat-square)](https://github.com/)

A sleek, native macOS desktop application built with **Python** and **PyQt6** that seamlessly converts your existing **Apple Music** audio playlists into dedicated **Music Video (Clips Vidéo)** playlists.

It automatically queries Apple Music's catalog and your local library, matches official music videos with extreme accuracy, eliminates false positives, guarantees **100% music video exclusivity**, and injects them directly into your Music.app without requiring a paid Apple Developer subscription.

---

## 🌟 Key Features

### 🎯 High-Fidelity Precision Matching (Zero False Positives)
- **Multi-Strategy Verification**: Combines primary artist matching, full sequence ratio, and collaborator token sets (Jaccard similarity).
- **Strict Anti-False-Positive Filter**: Requiring both `title_sim >= 0.80` and `artist_sim >= 0.78` (default tolerance: **0.85**).
- **Faux-Video Exclusion**: Automatically identifies and rejects static audio tracks, visualizers, karaoke, and lyric videos (`(Official Audio)`, `(Visualizer)`, etc.) to guarantee only real, official music video clips.

### 🎬 100% Music Video Exclusivity
- **Strict Format Enforcement**: All duplicated tracks are verified against `media kind is music video`.
- **Zero Audio Track Leakage**: Audio songs are strictly barred from the final video playlist.
- **Automated Safety Sweep**: Any residual non-video tracks from previous operations are purged automatically.

### 🛡️ Zero Duplicates Guarantee
- **Local Library First**: Automatically queries `library playlist 1` before attempting any network streaming.
- If a music video is already saved in your library, it is directly duplicated into the destination playlist in **0.02 seconds** without re-downloading or duplicating files in your library.
- Tracks already present in the target playlist are detected and preserved without duplication.

### 🖥️ Background Window Operation (No Full-Screen Hijacking)
- Eliminates intrusive full-screen video playback during conversion.
- Automatically mutes audio and pauses video stream playback within 250ms of detection, keeping Music.app in standard windowed mode without disrupting your workflow.

### 🎨 Fluid, Modern macOS Dark Interface
- **Refined Dark Palette**: Curated `#121318` background, glassmorphic cards, subtle borders, and vivid Apple Music red accents (`#FC3C44`).
- **Compact Base Size & Fully Responsive**: Starts at a comfortable **840 x 640 px** base size, while all components dynamically adapt to any window dimensions with a built-in resize handle (`QSizeGrip`).
- **Live Activity Stream**: Real-time list of all analyzed tracks with interactive tabs (`All`, `Converted`, `Skipped`), direct *"▶ Watch video"* links, instant search filter, and report export (`.json` / `.txt`).
- **Instant Demo Mode**: Test the interface, animations, and pipeline immediately with rich offline sample playlists without touching Music.app.

---

## 🚀 Installation & Getting Started

### 1. Prerequisites
- **Operating System**: macOS (tested on macOS Monterey, Ventura, Sonoma, and Sequoia).
- **Python**: Version 3.10 or later (`python3 --version`).
- **Apple Music**: Native **Music.app** installed and signed in.

### 2. Clone & Install Dependencies

```bash
git clone https://github.com/ifulymoon/apple-music-to-video.git
cd apple-music-to-video

# Install Python requirements
pip3 install -r requirements.txt
```

### 3. Launch the Application

```bash
# Using the executable launcher script
./run.sh

# Or directly via Python
python3 main.py

# Launch directly in offline Demo Mode
python3 main.py --demo
```

---

## 🔒 macOS Automation Permissions (Apple Events / TCC)

Because Apple Music To Video communicates with Apple's native Music app via AppleScript (`osascript`), macOS security requires your one-time permission:

1. **First Launch**: macOS will display a permission prompt:
   > *"Terminal" (or "Python") would like to control "Music".*  
   > **Click "OK" (Allow).**

2. **If Permissions Were Refused or Missing**:
   - The app will display an integrated yellow banner: *"Action Requise : Autorisation macOS"*.
   - Click **"Ouvrir Réglages Système"** (or manually navigate to `System Settings` > `Privacy & Security` > `Automation`).
   - Under your terminal/IDE app (e.g., Terminal, iTerm2, Python, VS Code), enable the toggle for **Music**.
   - Return to the app and click the refresh button (`⟳`).

3. **Explore Without Permissions**:
   - You can click **"Passer en Mode Démo"** at any time to explore the complete UI and simulated conversion process offline.

---

## ⚙️ Settings & Configuration

Click the **⚙️ (Settings)** icon in the top-right corner to customize:
- **Search Tolerance**: Adjustable slider (75% to 98%, default **85%**).
- **Apple Music Storefront**: Country catalog selection (`fr`, `us`, `gb`, `ca`, `de`, `jp`, etc.).
- **MusicKit API (Optional)**: Provide your own Developer Token (JWT) and Music User Token for optional cloud sync.
- **Offline Demo Mode**: Toggle anytime.

Preferences are automatically stored in `~/.apple_music_to_video/config.json`.

---

## 📁 Architecture & Codebase Structure

```
Apple Music To Video/
├── main.py                         # Application entry point
├── run.sh                          # Quick-start bash launcher
├── requirements.txt                # Python dependencies (PyQt6, requests)
├── README.md                       # Comprehensive English documentation
├── .gitignore                      # Git ignore file for macOS & Python
├── app/
│   ├── __init__.py                 # Version definitions (__version__ = "1.0.0")
│   ├── config.py                   # Persistent configuration & auto-migration
│   ├── backend/
│   │   ├── bridge_interface.py     # Base abstract bridge & data models (TrackInfo, VideoMatch)
│   │   ├── applescript_bridge.py   # High-speed native AppleScript bridge with zero-duplicate logic
│   │   ├── catalog_search.py       # High-precision Apple Music catalog search & similarity engine
│   │   ├── musickit_bridge.py      # Optional Apple Music MusicKit API bridge
│   │   ├── mock_bridge.py          # Offline demonstration bridge with realistic mock data
│   │   └── converter_worker.py     # Multi-threaded QThread worker with progress & cancellation
│   └── ui/
│       ├── styles.py               # Modern macOS dark QSS stylesheet & palette tokens
│       ├── main_window.py          # Responsive frameless window with native resize grip
│       ├── components/
│       │   ├── title_bar.py        # Custom macOS title bar with traffic lights & version badge
│       │   ├── playlist_card.py    # Source -> Destination playlist selector
│       │   ├── monitor_card.py     # Compact real-time scanning & artwork preview card
│       │   ├── progress_bar.py     # Animated progress bar with dual counters
│       │   ├── live_processing_panel.py # Full responsive live activity stream with tabs & search
│       │   └── permission_banner.py# macOS TCC permission detection & helper banner
│       └── dialogs/
│           └── settings_dialog.py  # User settings dialog with tolerance slider
```

---

## 🏷️ Versioning & Changelog

### `v1.0.1` (Current Release)
- **Internationalization (English)**:
  - Translated all user interface elements, dialogue boxes, status indicators, and notification badges into English.
- **Spacious Processed Tracks List**:
  - Restructured track row cards with dedicated vertical spacing (80px height hint + 8px separation).
  - Clearly partitioned Track Title, Artist Name, and Match Details to prevent crammed or overlapping text.
  - Eliminated Qt list widget item padding conflicts for crystal-clear readability.

### `v1.0.0`
- **High-Precision Matching**:
  - Implemented multi-strategy artist comparison (primary artist + token set Jaccard matching).
  - Raised default similarity tolerance to 0.85 with automated configuration migration.
  - Added filter to eliminate faux-videos (`(Audio)`, `(Visualizer)`, `(Karaoke)`, `(Lyric Video)`).
- **100% Video Exclusivity**:
  - Hard verification of `media kind is music video` on all added tracks.
  - Removal of ambiguous fallbacks that previously allowed audio tracks into video playlists.
  - Added automated `clean_playlist_non_videos` safety sweep.
- **Zero-Duplicate Engine**:
  - Direct fast-path lookup in `library playlist 1` before attempting any network load.
  - Tracks already in the target playlist are detected and preserved.
- **Background Playback & Normal Window**:
  - Instant pause within 250ms of stream opening to prevent full-screen takeover.
  - Automatic muting during metadata sync.
- **Responsive UI Overhaul**:
  - Compact base window geometry (840 x 640 px).
  - Built-in `QSizeGrip` handle for frameless window resizing.
  - Resizing mode `Adjust` on all lists with dynamic row expansion.

---

## 📄 License

This project is released under the **MIT License**.
Distributed freely for personal use.
