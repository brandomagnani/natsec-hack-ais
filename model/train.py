from hydro_classifier import TransformerClassifier
from trajectory_dataset import TrackDataset, pad_collate

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from pathlib import Path

from tqdm import tqdm

import argparse


def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ds = TrackDataset(args.data)
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True, collate_fn=pad_collate)

    model = TransformerClassifier().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = correct = total = 0

        for x, y, mask in tqdm(dl, desc=f"Epoch {epoch}/{args.epochs}"):
            x, y, mask = x.to(device), y.to(device), mask.to(device)
            opt.zero_grad()
            logits = model(x, mask)
            loss = criterion(logits, y)
            loss.backward()
            opt.step()

            running_loss += loss.item() * y.size(0)
            pred = logits.argmax(dim=1)
            correct += (pred == y).sum().item()
            total += y.size(0)

        print(f"Epoch {epoch:02d}  "
              f"loss {running_loss/total:.4f}  "
              f"acc {correct/total:.3f}")

        if args.ckpt_dir:
            Path(args.ckpt_dir).mkdir(exist_ok=True, parents=True)
            torch.save(model.state_dict(), f"{args.ckpt_dir}/epoch{epoch:02d}.pt")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="DemoData", help="root folder with tracks")
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--ckpt-dir", default="checkpoints",
                   help="where to save *.pt (omit to skip saving)")
    train(p.parse_args())