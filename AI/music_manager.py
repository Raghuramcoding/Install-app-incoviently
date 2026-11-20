#!/usr/bin/env python3
"""A small cross-platform local music library manager."""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    tk = None
    filedialog = None
    messagebox = None
    ttk = None

APP_DIR = Path(__file__).resolve().parent
LIBRARY_FILE = APP_DIR / ".music-manager" / "library.json"
AUDIO_EXTENSIONS = {
    ".aac", ".aif", ".aiff", ".alac", ".flac", ".m4a", ".mp3",
    ".ogg", ".opus", ".wav", ".wma",
}


def load_library() -> list[str]:
    if not LIBRARY_FILE.exists():
        return []
    try:
        data = json.loads(LIBRARY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read library at {LIBRARY_FILE}: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("tracks"), list):
        raise RuntimeError(f"Library file has an invalid format: {LIBRARY_FILE}")
    if not all(isinstance(path, str) for path in data["tracks"]):
        raise RuntimeError(f"Library file has an invalid format: {LIBRARY_FILE}")
    return sorted({str(Path(path).resolve()) for path in data["tracks"] if Path(path).is_file()})


def save_library(tracks: list[str]) -> None:
    LIBRARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"tracks": sorted(set(tracks))}, indent=2)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=LIBRARY_FILE.parent, delete=False
        ) as temporary_file:
            temporary_file.write(payload + "\n")
            temporary_path = temporary_file.name
        os.replace(temporary_path, LIBRARY_FILE)
    except OSError as error:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)
        raise RuntimeError(f"Could not save library at {LIBRARY_FILE}: {error}") from error


def scan_folder(folder: Path) -> int:
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        raise ValueError(f"Not a folder: {folder}")
    tracks = set(load_library())
    added = 0
    for path in folder.rglob("*"):
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
            resolved_path = str(path.resolve())
            if resolved_path not in tracks:
                tracks.add(resolved_path)
                added += 1
    save_library(list(tracks))
    return added


def filtered_tracks(query: str = "") -> list[str]:
    tracks = load_library()
    normalized_query = query.casefold().strip()
    if normalized_query:
        tracks = [
            path for path in tracks
            if normalized_query in Path(path).name.casefold()
            or normalized_query in str(Path(path).parent).casefold()
        ]
    return tracks


def open_location(path: str) -> None:
    system = platform.system()
    if system == "Windows":
        os.startfile(path)  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def open_track(path: str) -> None:
    if not Path(path).is_file():
        raise FileNotFoundError(f"Track is no longer available: {path}")
    open_location(path)


def show_tui() -> None:
    print("AI Music Manager - terminal mode")
    while True:
        tracks = load_library()
        print(f"\n{len(tracks)} track(s) in your library")
        print("[S]can folder  [L]ist/search  [P]lay/open track  [Q]uit")
        try:
            choice = input("> ").strip().casefold()
        except EOFError:
            return
        try:
            if choice in {"q", "quit"}:
                return
            if choice in {"s", "scan"}:
                folder = input("Folder to scan: ").strip().strip('"')
                if folder:
                    added = scan_folder(Path(folder))
                    print(f"Added {added} track(s).")
            elif choice in {"l", "list"}:
                query = input("Search (leave blank for all): ").strip()
                matches = filtered_tracks(query)
                for index, path in enumerate(matches, start=1):
                    print(f"{index:>3}. {Path(path).name} - {Path(path).parent}")
                if not matches:
                    print("No matching tracks.")
            elif choice in {"p", "play"}:
                matches = filtered_tracks(input("Track name search: ").strip())
                for index, path in enumerate(matches, start=1):
                    print(f"{index:>3}. {Path(path).name}")
                if matches:
                    selection = input("Track number (blank to cancel): ").strip()
                    if selection:
                        index = int(selection) - 1
                        if index < 0 or index >= len(matches):
                            print("That track number is out of range.")
                        else:
                            open_track(matches[index])
            else:
                print("Choose S, L, P, or Q.")
        except (OSError, RuntimeError, ValueError) as error:
            print(f"Error: {error}", file=sys.stderr)


class MusicManagerWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AI Music Manager")
        self.root.geometry("900x560")
        self.search_text = tk.StringVar()
        self.status_text = tk.StringVar()

        toolbar = ttk.Frame(root, padding=12)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text="Scan folder...", command=self.scan).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Play selected", command=self.play_selected).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Button(toolbar, text="Open containing folder", command=self.open_folder).pack(
            side=tk.LEFT, padx=(8, 0)
        )
        ttk.Label(toolbar, text="Search").pack(side=tk.LEFT, padx=(20, 6))
        search = ttk.Entry(toolbar, textvariable=self.search_text)
        search.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_text.trace_add("write", lambda *_: self.refresh())

        columns = ("title", "location")
        self.table = ttk.Treeview(root, columns=columns, show="headings", selectmode="browse")
        self.table.heading("title", text="Track")
        self.table.heading("location", text="Folder")
        self.table.column("title", width=300)
        self.table.column("location", width=540)
        self.table.pack(fill=tk.BOTH, expand=True, padx=12)
        self.table.bind("<Double-1>", lambda _event: self.play_selected())

        ttk.Label(root, textvariable=self.status_text, anchor=tk.W, padding=(12, 8)).pack(
            fill=tk.X
        )
        self.refresh()
        search.focus_set()

    def refresh(self) -> None:
        self.table.delete(*self.table.get_children())
        try:
            tracks = filtered_tracks(self.search_text.get())
        except (OSError, RuntimeError) as error:
            messagebox.showerror("Library error", str(error), parent=self.root)
            tracks = []
        for path in tracks:
            self.table.insert("", tk.END, iid=path, values=(Path(path).name, str(Path(path).parent)))
        self.status_text.set(f"{len(tracks)} track(s) shown")

    def selected_path(self) -> str | None:
        selection = self.table.selection()
        return selection[0] if selection else None

    def scan(self) -> None:
        folder = filedialog.askdirectory(title="Choose a music folder", parent=self.root)
        if not folder:
            return
        try:
            added = scan_folder(Path(folder))
        except (OSError, RuntimeError, ValueError) as error:
            messagebox.showerror("Scan failed", str(error), parent=self.root)
            return
        self.refresh()
        self.status_text.set(f"Added {added} track(s)")

    def play_selected(self) -> None:
        path = self.selected_path()
        if path is None:
            self.status_text.set("Select a track first")
            return
        try:
            open_track(path)
        except (OSError, FileNotFoundError) as error:
            messagebox.showerror("Could not open track", str(error), parent=self.root)

    def open_folder(self) -> None:
        path = self.selected_path()
        if path is None:
            self.status_text.set("Select a track first")
            return
        try:
            open_location(str(Path(path).parent))
        except OSError as error:
            messagebox.showerror("Could not open folder", str(error), parent=self.root)


def show_gui() -> None:
    if tk is None:
        raise RuntimeError("Tkinter is not installed; use --tui or install Tkinter for the GUI.")
    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise RuntimeError(f"Could not start the desktop interface: {error}") from error
    MusicManagerWindow(root)
    root.mainloop()


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage a local music library.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--tui", action="store_true", help="open the terminal interface")
    mode.add_argument("--gui", action="store_true", help="open the desktop interface (default)")
    args = parser.parse_args()
    try:
        if args.tui:
            show_tui()
        else:
            show_gui()
    except (OSError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
