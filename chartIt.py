import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load data
data = pd.read_csv('data.csv')  # Replace with your file path
data.columns = data.columns.str.strip()
data['DATE'] = pd.to_datetime(data['DATE'])

repositories = {
    "Gum": "gum",
    "GeonBit.UI": "geonbit",
    "Myra": "myra",
    "ImGui": "imgui",
    "MLEM": "mlem.ui"
}

metrics = ['STARS', 'SUBS', 'FORKS', 'ISSUES']
excluded_repositories = ["ImGui"]  
filtered_repositories = {
    repo: prefix
    for repo, prefix in repositories.items()
    if repo not in excluded_repositories
}

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
        
        # === Sparklines ===
        max_bar_height = max(np.array(originals) + np.array(changes))
        
        for i, (repo, prefix) in enumerate(repositories.items()):
            # Full time series
            time_series = data[f"{metric}_{prefix}"]
            dates = data['DATE']
            first_val = time_series.iloc[0]
            last_val = time_series.iloc[-1]
            
            # % change
            if first_val != 0:
                pct_change = (last_val - first_val) / first_val * 100
            else:
                pct_change = 0.0
            
            total_bar_height = originals[i] + changes[i]
            
            # Inset axes just above the top of the stacked bar
            ax_inset = ax.inset_axes([
                i / len(repositories),
                total_bar_height / max_bar_height + 0.05,
                0.1,
                0.1
            ])
            
            # Plot sparkline
            ax_inset.plot(dates, time_series, color='black', linewidth=1, zorder=2)
            ax_inset.fill_between(dates, time_series, color='gray', alpha=0.2, zorder=1)
            
            # Highlight first & last
            ax_inset.scatter(dates.iloc[0], first_val, color='red', s=10, zorder=3)
            ax_inset.scatter(dates.iloc[-1], last_val, color='red', s=10, zorder=3)
            
            # Ensure we don't squash the sparkline
            y_min, y_max = time_series.min(), time_series.max()
            if y_min == y_max:
                y_min -= 0.5
                y_max += 0.5
            else:
                margin = 0.1 * (y_max - y_min)
                y_min -= margin
                y_max += margin
            ax_inset.set_ylim(y_min, y_max)
            ax_inset.set_xlim(dates.min(), dates.max())
            
            # Remove ticks/spines for "sparkline" style
            ax_inset.set_xticks([])
            ax_inset.set_yticks([])
            for spine in ax_inset.spines.values():
                spine.set_visible(False)
            
            # Show % change
            ax_inset.text(
                0.95,
                0.95,
                f"{pct_change:.1f}%",
                transform=ax_inset.transAxes,
                ha="right",
                va="top",
                fontsize=8,
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
