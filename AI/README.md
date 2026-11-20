# AI Music Manager

A lightweight local music library manager with a terminal interface (TUI) and a
desktop interface (GUI). The app is implemented in Python's standard library;
the PowerShell and Bash scripts are launchers for the same app.

## Requirements

- Python 3
- Tkinter for the GUI (often included with Python; some Linux distributions
  package it separately)

## Run

From PowerShell:

```powershell
.\music-manager.ps1
.\music-manager.ps1 --tui
```

From Bash:

```bash
./music-manager.sh
./music-manager.sh --tui
```

The GUI is the default. In either mode, scan one or more folders to add common
audio formats to the library. Search matches track names and folder paths.
Opening a track uses the operating system's default audio application; this
manager does not include an audio decoder or player.

The library is stored in `.music-manager/library.json` alongside the app.
