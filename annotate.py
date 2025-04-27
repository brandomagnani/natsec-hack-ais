#!/usr/bin/env python3
"""
track_browser.py  –  quick annotation-by-moving tool
─────────────────────────────────────────────────────
Usage:
    python track_browser.py /path/to/data [--demo DemoData]

• Recursively collects every  …/<MMSI>/track.png  under <data root>.
• Shows one image at a time (← / → to browse).
• Buttons "Normal", "Malicious", "Hydro" move the *whole* MMSI folder
  into DemoData/<Category>/ and advance to the next track.
"""

from __future__ import annotations
import argparse, shutil
from pathlib import Path
from typing import List

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk


# ── helpers ────────────────────────────────────────────────────────────────
def collect_tracks(root: Path) -> List[Path]:
    """Return sorted list of .../MMSI/track.png paths."""
    return sorted(p for p in root.rglob("track.png") if p.is_file())


def ensure_demo_dirs(demo_root: Path):
    for sub in ("Normal", "Malicious", "Hydro"):
        (demo_root / sub).mkdir(parents=True, exist_ok=True)


# ── GUI ────────────────────────────────────────────────────────────────────
class TrackViewer(tk.Tk):
    def __init__(self, images: List[Path], demo_root: Path):
        super().__init__()
        self.title("Track browser / annotator")
        self.images = images          # list of track.png paths
        self.demo_root = demo_root
        self.idx = 0

        # --- image label ---------------------------------------------------
        self.pic_label = ttk.Label(self)
        self.pic_label.grid(row=0, column=0, columnspan=5, padx=6, pady=6)

        # --- nav buttons ---------------------------------------------------
        ttk.Button(self, text="◀", width=3, command=self.prev_img) \
            .grid(row=1, column=0, padx=4)
        ttk.Button(self, text="▶", width=3, command=self.next_img) \
            .grid(row=1, column=4, padx=4)

        self.counter = ttk.Label(self, text="")
        self.counter.grid(row=1, column=2)

        # --- category buttons ---------------------------------------------
        ttk.Separator(self, orient="horizontal").grid(row=2, columnspan=5,
                                                      sticky="ew", pady=3)
        ttk.Button(self, text="Normal",   width=11,
                   command=lambda: self.move_current("Normal"))   \
            .grid(row=3, column=0, columnspan=1, pady=3)
        ttk.Button(self, text="Malicious", width=11,
                   command=lambda: self.move_current("Malicious")) \
            .grid(row=3, column=2, columnspan=1, pady=3)
        ttk.Button(self, text="Hydro",    width=11,
                   command=lambda: self.move_current("Hydro"))     \
            .grid(row=3, column=4, columnspan=1, pady=3)

        # key bindings
        self.bind("<Right>", lambda e: self.next_img())
        self.bind("<Left>",  lambda e: self.prev_img())

        self.show_img()

    # ---------- navigation -------------------------------------------------
    def next_img(self):
        if self.images:
            self.idx = (self.idx + 1) % len(self.images)
            self.show_img()

    def prev_img(self):
        if self.images:
            self.idx = (self.idx - 1) % len(self.images)
            self.show_img()

    # ---------- rendering --------------------------------------------------
    def show_img(self):
        if not self.images:
            messagebox.showinfo("Done", "No more images to label!")
            self.destroy(); return

        img_path = self.images[self.idx]
        pil_img  = Image.open(img_path)

        # resize to fit current window (or first image size)
        win_w = self.winfo_width()  or pil_img.width
        win_h = self.winfo_height() or pil_img.height
        scale = min(win_w/pil_img.width, win_h/pil_img.height, 1.0)
        if scale < 1.0:
            pil_img = pil_img.resize((int(pil_img.width*scale),
                                      int(pil_img.height*scale)),
                                     Image.LANCZOS)

        self.tk_img = ImageTk.PhotoImage(pil_img)  # keep reference
        self.pic_label.configure(image=self.tk_img)

        self.counter.configure(
            text=f"{self.idx+1}/{len(self.images)}\n{img_path.parent.name}"
        )

    # ---------- annotation -------------------------------------------------
    def move_current(self, category: str):
        """Move MMSI folder of current image into DemoData/<category>/."""
        if not self.images:
            return

        img_path = self.images[self.idx]
        mmsi_dir = img_path.parent
        dest_dir = self.demo_root / category / mmsi_dir.name

        try:
            shutil.move(str(mmsi_dir), dest_dir)
        except shutil.Error as e:
            messagebox.showerror("Move error", str(e))
            return

        # remove from list and adjust index
        del self.images[self.idx]
        if self.idx >= len(self.images):
            self.idx = 0
        self.show_img()


# ── entry point ────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, help="Root directory with MMSI folders")
    ap.add_argument("--demo", type=Path, default=Path("DemoData"),
                    help="Destination root for DemoData (default ./DemoData)")
    args = ap.parse_args()

    tracks = collect_tracks(args.root.expanduser())
    if not tracks:
        print("No track.png files found under", args.root)
        return

    ensure_demo_dirs(args.demo.expanduser())
    app = TrackViewer(tracks, args.demo.expanduser())
    app.mainloop()


if __name__ == "__main__":
    main()
