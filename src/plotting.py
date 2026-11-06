"""Plot helpers (matplotlib only)."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_before_after(
    raw: pd.DataFrame,
    clean: pd.DataFrame,
    channels: list[str],
    start: str,
    end: str,
    labels: dict[str, str] | None = None,
    save_path: str | Path | None = None,
):
    """Left column = raw readings, right column = cleaned 1-minute series, one row per channel.
    Shaded red bands on the right mark minutes flagged as aggregate outage."""
    labels = labels or {}
    fig, axes = plt.subplots(len(channels), 2, figsize=(13, 3 * len(channels)), sharex="col")
    if len(channels) == 1:
        axes = axes.reshape(1, 2)

    r = raw.loc[start:end]
    c = clean.loc[start:end]
    for i, ch in enumerate(channels):
        name = labels.get(ch, ch)
        axes[i, 0].plot(r.index, r[ch], lw=0.7, color="tab:gray")
        axes[i, 1].plot(c.index, c[ch], lw=0.9, color="tab:blue")
        axes[i, 0].set_ylabel(f"{name} (W)")
        # Each side gets its own y-range so a raw spike does not flatten the cleaned plot.
        for ax, series in ((axes[i, 0], r[ch]), (axes[i, 1], c[ch])):
            top = series.max()
            ax.set_ylim(bottom=0, top=(top * 1.05 if pd.notna(top) and top > 0 else 1))
            ax.grid(alpha=0.3)
        if "agg_outage" in c.columns and c["agg_outage"].any():
            out_idx = c.index[c["agg_outage"]]
            for ts in out_idx:
                axes[i, 1].axvspan(ts, ts + pd.Timedelta("1min"), color="tab:red", alpha=0.15, lw=0)

    axes[0, 0].set_title("Before: raw readings")
    axes[0, 1].set_title("After: cleaned, 1-minute (red = long outage, not filled)")
    fig.autofmt_xdate()
    fig.tight_layout()
    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150)
    return fig