<p align="center">
  <img src="assets/logo.png" alt="Time Forge Logo" width="180"/>
</p>

<h1 align="center">Time Forge</h1>

<p align="center">
  <strong>A sleek, privacy-first desktop application that automatically tracks how you spend time on your Windows PC.</strong>
</p>

<p align="center">
  <a href="https://github.com/master-redevil/Time-Forge/releases/latest">
    <img src="https://img.shields.io/github/v/release/master-redevil/Time-Forge?style=for-the-badge&color=6366F1&labelColor=1E2430" alt="Latest Release"/>
  </a>
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?style=for-the-badge&logo=windows&labelColor=1E2430" alt="Platform"/>
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=1E2430" alt="Python"/>
  <img src="https://img.shields.io/github/license/master-redevil/Time-Forge?style=for-the-badge&color=a6e3a1&labelColor=1E2430" alt="License"/>
</p>

<p align="center">
  <a href="#features">Features</a> &bull;
  <a href="#installation">Installation</a> &bull;
  <a href="#development">Development</a> &bull;
  <a href="#architecture">Architecture</a> &bull;
  <a href="#contributing">Contributing</a>
</p>

---

## Features

### Intelligent Tracking
- **Automatic Focus Detection** — Tracks the active foreground application in real-time using native Win32 APIs.
- **Idle Detection** — Automatically pauses tracking when you step away from your computer, preventing inflated usage stats.
- **Session Tracking** — Records individual usage sessions per application with start times and durations.
- **System Process Filtering** — Smart blocklist automatically hides Windows system processes from the management view.

### Rich Analytics
- **Daily Usage Breakdown** — Pie charts showing proportional app usage and bar charts for trend analysis.
- **7-Day Usage Trends** — Stacked bar charts visualizing your usage patterns over the past week.
- **Session Timeline** — A visual swimlane timeline plotting every session across a 24-hour axis with a live "now" indicator.
- **Date Navigation** — Navigate to any historical date to review past activity.

### Data Export
- **CSV** — Raw data export for spreadsheets and external analysis.
- **JSON** — Structured data export for developers and integrations.
- **PDF Reports** — Professionally styled reports with summary statistics and detailed activity tables.

### Configurable Settings
- **Poll Interval** — Control how frequently the tracker checks the focused window (1–60s).
- **Idle Threshold** — Set how long before inactivity pauses tracking (10–3600s).
- **Scan Interval** — Adjust background process scanning frequency (5–300s).
- **Data Retention** — Choose how many days of history to keep (1–3650 days).

### Privacy First
- **100% Local** — All data stays on your machine in a local SQLite database. No cloud. No telemetry. No accounts.
- **Your Data, Your Control** — Export or delete your data at any time.

### System Integration
- **System Tray** — Runs quietly in the background with a custom tray icon and context menu.
- **Global Hotkey** — Press `Ctrl+Shift+T` from anywhere to instantly toggle the dashboard.
- **Single Instance** — Enforced via Windows Mutex to prevent duplicate processes.
- **Update Notifications** — Checks GitHub for new releases on startup and prompts you to download.

---

## Installation

1. Go to the [**Latest Release**](https://github.com/master-redevil/Time-Forge/releases/latest) page.
2. Download **`TimeForge_Setup.exe`**.
3. Run the installer and follow the setup wizard.
4. Launch Time Forge from the Start Menu or Desktop shortcut.

> [!NOTE]
> **Windows SmartScreen:** Since this app is not code-signed with a paid certificate, Windows may show a "Windows protected your PC" warning. Click **"More info"** then **"Run anyway"** to proceed. This is standard for independent open-source software.

---

## Development

### Prerequisites

- **Python 3.11+**
- **Windows 10/11** (required for Win32 API integration)

### Setup

```bash
# Clone the repository
git clone https://github.com/master-redevil/Time-Forge.git
cd Time-Forge

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

### Building from Source

```bash
# Build the standalone executable
pyinstaller TimeForge.spec

# Build the Windows installer (requires Inno Setup 6)
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

The built installer will be output to the `dist/` directory.

---

## Architecture

```
Time-Forge/
├── main.py              # Entry point, tray icon, hotkey registration
├── tracker.py           # Background tracking daemon (QThread)
├── database.py          # SQLite layer with WAL mode & versioned migrations
├── config.py            # JSON-based configuration management
├── updater.py           # GitHub release version checker
├── ui/
│   └── dashboard.py     # All UI views (Dashboard, Analytics, Settings, etc.)
├── assets/
│   ├── logo.png         # Application logo
│   ├── logo.ico         # Windows icon (multi-size)
│   └── icons/           # SVG icons for the UI
├── TimeForge.spec       # PyInstaller build configuration
├── installer.iss        # Inno Setup installer script
└── .github/
    └── workflows/
        └── release.yml  # CI/CD pipeline for automated releases
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11+ |
| GUI Framework | PySide6 (Qt 6) |
| Database | SQLite with WAL journaling |
| Process Monitoring | psutil |
| Win32 Integration | ctypes (native Windows APIs) |
| Charts | QtCharts |
| PDF Generation | QtPrintSupport |
| Packaging | PyInstaller |
| Installer | Inno Setup |
| CI/CD | GitHub Actions |

### Database Schema

Time Forge uses a versioned migration system (`SchemaVersion` table) to safely evolve the database schema across updates.

| Table | Purpose |
|-------|---------|
| `TrackedApps` | Apps selected for tracking, with optional exe paths |
| `UsageLogs` | Daily aggregated focus-time per app |
| `Sessions` | Individual session records with start time and duration |
| `DeviceActivity` | Total device active time per day |
| `SchemaVersion` | Tracks current database schema version |

---

## Contributing

Contributions are welcome. To get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## Releasing

Releases are fully automated via GitHub Actions. To publish a new version:

```bash
# 1. Update APP_VERSION in config.py
# 2. Commit and push
git add .
git commit -m "Release v1.x.x"
git push origin main

# 3. Tag and push
git tag v1.x.x
git push origin v1.x.x
```

GitHub Actions will build `TimeForge_Setup.exe` and attach it to the release automatically.

---

## License

This project is open source.

---

<p align="center">
  <sub>Developed and maintained by <a href="https://github.com/master-redevil">master-redevil</a></sub>
</p>
