import argparse, json
from pathlib import Path
from typing import List, Tuple

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from tqdm import tqdm


# ─────────────────────── dataset ────────────────────────────────────────────
class TrackDataset(Dataset):
    """
    Loads every `track.json` under DemoData/<label>/** and returns
        sequence   — (seq_len, 2) float32 tensor   [lat, lon]
        label_idx  — int in {0,1,2}
    """
    LABEL2IDX = {"Hydropgraphic": 0, "Malicious": 1, "Normal": 2}

    def __init__(self, root_dir: str | Path):
        self.samples: List[Tuple[torch.Tensor, int]] = []
        root = Path(root_dir)

        for class_dir in root.iterdir():
            if not class_dir.is_dir() or class_dir.name not in self.LABEL2IDX:
                continue
            y = self.LABEL2IDX[class_dir.name]

            for track_file in class_dir.rglob("track.json"):
                seq = self._load_track(track_file)          # (L, 2)
                if len(seq):                                # skip empty files
                    self.samples.append((seq, y))

        if not self.samples:
            raise RuntimeError(f"No tracks found under {root}")

    @staticmethod
    def _load_track(path: Path) -> torch.Tensor:
        with open(path) as f:
            fixes = json.load(f)
        coords = [[fix["lat"], fix["lon"]] for fix in fixes]
        return torch.tensor(coords, dtype=torch.float32)

    def __len__(self) -> int:          return len(self.samples)
    def __getitem__(self, i):          return self.samples[i]


def pad_collate(batch):
    """Pads variable-length tracks to (B, L_max, 2) and returns a mask."""
    seqs, labels = zip(*batch)
    lengths = [s.size(0) for s in seqs]
    L = max(lengths)

    x = torch.zeros(len(batch), L, 2)
    mask = torch.zeros(len(batch), L, dtype=torch.bool)      # True = real token
    for i, s in enumerate(seqs):
        x[i, : s.size(0)] = s
        mask[i, : s.size(0)] = True
    return x, torch.tensor(labels), mask

