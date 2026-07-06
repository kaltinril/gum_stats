import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from repos_config import get_chart_repositories, METRICS

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Chart GitHub repository stats.')
parser.add_argument(
    '-y', '--years',
    type=float,
    default=None,
    help='Number of years back to include (e.g. -y 1). If omitted, shows everything.'
)
args = parser.parse_args()

# Load data
data = pd.read_csv('data.csv')
data.columns = data.columns.str.strip()
data['DATE'] = pd.to_datetime(data['DATE'])

# Filter to the requested lookback window (default: show everything)
if args.years is not None:
    cutoff = data['DATE'].max() - pd.DateOffset(days=round(args.years * 365.25))
    data = data[data['DATE'] >= cutoff].reset_index(drop=True)

filtered_repositories = get_chart_repositories()
metrics = METRICS

# Fill missing columns with 0 for repos added after data collection started
for prefix in filtered_repositories.values():
    for metric in metrics:
        col = f"{metric}_{prefix}"
        if col not in data.columns:
            data[col] = 0
        else:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)

def plot_bar_with_sparklines(data, repositories, metrics):
    """
    Creates stacked bars:
      - Gray portion = the original value (first data point).
      - Blue portion = the absolute change (final - original).
    Inside the bars, we label the original and change amounts.
    On top, we put the final total.
    Also includes sparklines with percent change.
    """
    fig, axs = plt.subplots(len(metrics), 1, figsize=(12, 3 * len(metrics)), constrained_layout=True)
    
    for ax, metric in zip(axs, metrics):
        
        # For each repo, find the original (first) and the change (last - first)
        originals = []
        changes   = []
        
        for prefix in repositories.values():
            ts = data[f"{metric}_{prefix}"]
            first_val = ts.iloc[0]
            last_val = ts.iloc[-1]
            originals.append(first_val)
            changes.append(last_val - first_val)
        
        x = np.arange(len(repositories))
        
        # Stacked bars
        bars_original = ax.bar(
            x, 
            originals, 
            color='lightgray', 
            edgecolor='black', 
            label='Original'
        )
        bars_change = ax.bar(
            x, 
            changes, 
            bottom=originals, 
            color='lightblue', 
            edgecolor='black', 
            label='Change'
        )
        
        # === Label inside each portion of the bar ===
        for i, (barO, barC) in enumerate(zip(bars_original, bars_change)):
            # Original portion
            orig_val = barO.get_height()
            orig_x   = barO.get_x() + barO.get_width()/2
            # Place label in the middle (vertically) of the gray portion
            ax.text(
                orig_x, 
                orig_val / 2.0, 
                f"{orig_val:.1f}", 
                ha='center', 
                va='center',
                color='white',      # White text stands out on gray
                fontsize=9
            )
            
            # Change portion
            change_val = barC.get_height()
            # Midpoint of the blue portion is original + half the change
            change_y = orig_val + change_val / 2.0
            
            ax.text(
                orig_x,
                change_y,
                f"{change_val:.1f}",
                ha='center',
                va='center',
                color='black',
                fontsize=9
            )
        
        # === Label the final total on top ===
        for i in range(len(x)):
            final_val = originals[i] + changes[i]
            ax.text(
                x[i], 
                final_val * 1.01, 
                f"{final_val:.1f}", 
                ha='center', 
                va='bottom',
                fontsize=9, 
                color='black'
            )
        
        # === Sparklines (normalized to % change, shared y-axis) ===
        max_bar_height = max(np.array(originals) + np.array(changes))
        n_repos = len(repositories)
        dates = data['DATE']

        # Compute all % change series first to find a shared y range
        pct_series_list = []
        pct_changes = []
        for prefix in repositories.values():
            ts = data[f"{metric}_{prefix}"]
            first_val = ts.iloc[0]
            if first_val != 0:
                pct_ts = (ts - first_val) / first_val * 100
            else:
                pct_ts = ts * 0
            pct_series_list.append(pct_ts)
            pct_changes.append(pct_ts.iloc[-1])

        all_pct_min = min(s.min() for s in pct_series_list)
        all_pct_max = max(s.max() for s in pct_series_list)
        if all_pct_min == all_pct_max:
            all_pct_min -= 1
            all_pct_max += 1
        pct_margin = 0.1 * (all_pct_max - all_pct_min)

        # Set explicit xlim so sparkline positions map cleanly
        ax.set_xlim(-0.5, n_repos - 0.5)
        spark_w = 0.7 / n_repos  # 0.7 data units out of n_repos total
        spark_h = 0.1

        for i, (repo, prefix) in enumerate(repositories.items()):
            pct_ts = pct_series_list[i]
            pct_change = pct_changes[i]
            total_bar_height = originals[i] + changes[i]

            # Center sparkline over bar i: bar center in axes coords = (i+0.5)/n_repos
            center_ax = (i + 0.5) / n_repos
            left = center_ax - spark_w / 2
            bottom = total_bar_height / max_bar_height + 0.05

            ax_inset = ax.inset_axes([left, bottom, spark_w, spark_h])

            ax_inset.plot(dates, pct_ts, color='black', linewidth=1, zorder=2)
            ax_inset.fill_between(dates, pct_ts, color='gray', alpha=0.2, zorder=1)
            ax_inset.scatter(dates.iloc[0], pct_ts.iloc[0], color='red', s=10, zorder=3)
            ax_inset.scatter(dates.iloc[-1], pct_ts.iloc[-1], color='red', s=10, zorder=3)

            # Shared y scale so slopes are visually comparable
            ax_inset.set_ylim(all_pct_min - pct_margin, all_pct_max + pct_margin)
            ax_inset.set_xlim(dates.min(), dates.max())

            ax_inset.set_xticks([])
            ax_inset.set_yticks([])
            for spine in ax_inset.spines.values():
                spine.set_visible(False)

            ax_inset.text(
                0.95, 0.95, f"{pct_change:+.1f}%",
                transform=ax_inset.transAxes,
                ha="right", va="top", fontsize=8,
                color="darkred",
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'),
                zorder=5
            )
        
        ax.set_title(f'{metric}: Original vs. Change', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(repositories.keys())
        ax.set_ylabel(metric)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        ax.legend()
    
    plt.show()

plot_bar_with_sparklines(data, filtered_repositories, metrics)
