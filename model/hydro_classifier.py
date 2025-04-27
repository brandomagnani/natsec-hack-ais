#!/usr/bin/env python3
"""
Minimal demo: Transformer-based classifier on dummy data.
"""

import torch
import torch.nn as nn

# ─────────────────────── model ──────────────────────────────────────────────
class SelfAttentionPooling(nn.Module):
    """Soft-attention over time; ignores padding via mask."""
    def __init__(self, hidden_dim: int):
        super().__init__()
        self.att = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, h, mask=None):
        # h: (B,L,D)   mask: (B,L) bool
        scores = self.att(h)                        # (B,L,1)
        if mask is not None:
            scores = scores.masked_fill(~mask.unsqueeze(-1), -1e9)
        α = torch.softmax(scores, dim=1)            # attention weights
        return torch.sum(α * h, dim=1)              # (B,D)


class TransformerClassifier(nn.Module):
    def __init__(
        self,
        input_dim: int = 2,
        hidden_dim: int = 128,
        num_heads: int = 4,
        num_layers: int = 2,
        num_classes: int = 3,
        max_len: int = 2000,
    ):
        super().__init__()
        self.embedding = nn.Linear(input_dim, hidden_dim)
        self.pos = nn.Parameter(torch.randn(1, max_len, hidden_dim))  # learned PE

        enc_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim, nhead=num_heads, batch_first=True
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=num_layers)

        self.pool = SelfAttentionPooling(hidden_dim)
        self.fc = nn.Linear(hidden_dim, num_classes)

    def forward(self, x, mask=None):                 # x: (B,L,2)
        B, L, _ = x.shape
        x = self.embedding(x) + self.pos[:, :L]      # add position enc.
        h = self.encoder(x, src_key_padding_mask=~mask if mask is not None else None)
        z = self.pool(h, mask)                       # (B,D)
        return self.fc(z)                            # raw logits (B,C)
