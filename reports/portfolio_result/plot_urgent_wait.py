"""Render the README figure from saved results; no simulation or data changes."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
data = pd.read_csv(HERE / "results.csv")
summary = data.loc[
    (data.record_type == "summary")
    & (data.scenario == "Moderate Congestion")
    & (data.metric == "urgent_wait_minutes")
].set_index("method").loc[["FCFS", "CTAS"]]
means = summary.value.to_numpy()
low, high = summary.ci95_low.to_numpy(), summary.ci95_high.to_numpy()
reduction = 100 * (1 - means[1] / means[0])
assert np.allclose(means, [185.6, 11.8], atol=0.05)
assert round(reduction, 1) == 93.6

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 15})
fig, ax = plt.subplots(figsize=(9, 4.8), facecolor="white")
fig.subplots_adjust(left=0.23, right=0.97, top=0.66, bottom=0.26)
fig.text(0.06, 0.91, "Waiting time for high-acuity patients", fontsize=21,
         weight="semibold", color="#20364B")
fig.text(0.06, 0.83, "CTAS 1–2 · Moderate Congestion", fontsize=15, color="#52616B")
fig.text(0.06, 0.73, f"{reduction:.1f}% lower mean wait with CTAS Priority",
         fontsize=17, weight="semibold", color="#32796F")
ax.barh([1, 0], means, height=0.43, color=["#243F58", "#508D82"], zorder=3)
ax.errorbar(means, [1, 0], xerr=np.vstack([means-low, high-means]),
            fmt="none", ecolor="#192D3B", capsize=5, elinewidth=1.4, zorder=4)
for y, mean, upper in zip([1, 0], means, high):
    ax.text(upper + 4, y, f"{mean:.1f}", va="center", fontsize=17,
            weight="semibold", color="#20364B")
ax.set_yticks([1, 0], ["FCFS", "CTAS Priority"])
ax.set_xlim(0, 230)
ax.set_xticks([0, 50, 100, 150, 200])
ax.set_xlabel("Mean waiting time (minutes)", labelpad=10)
ax.set_ylim(-0.5, 1.5)
ax.tick_params(axis="y", length=0, pad=12)
ax.tick_params(axis="x", length=0, colors="#52616B")
ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
ax.grid(axis="x", color="#E5E9EC", linewidth=0.8, zorder=0)
fig.text(0.06, 0.08, "Synthetic simulations · 10 paired seeds · Error bars: 95% confidence intervals",
         fontsize=11.5, color="#52616B")
fig.text(0.06, 0.035, "Source: portfolio_result/results.csv · 21 measured days after 7-day warm-up",
         fontsize=10.5, color="#687680")
fig.savefig(HERE / "urgent_wait_reduction.png", dpi=220, facecolor="white")
plt.close(fig)
