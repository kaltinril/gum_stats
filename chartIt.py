import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the data
data = pd.read_csv('data.csv')  # Replace 'data.csv' with your actual CSV path
data.columns = data.columns.str.strip()  
data['DATE'] = pd.to_datetime(data['DATE'])

repositories = {
    "Gum": "gum",
    "GeonBit.UI": "geonbit",
    "Myra": "myra",
    "ImGui": "imgui"
}

metrics = ['STARS', 'SUBS', 'FORKS', 'ISSUES']

# Exclude any repos you don't want
excluded_repositories = ["ImGui"]  
filtered_repositories = {
    repo: prefix
    for repo, prefix in repositories.items()
    if repo not in excluded_repositories
}

def plot_bar_with_sparklines(data, repositories, metrics):
    """
    Creates stacked bars:
      - Gray portion = the original value (first data point)
      - Blue portion = the change from the first to the last data point
    The total stacked height is the final value.
    Each bar also has a mini sparkline showing the time series and percent change.
    """
    fig, axs = plt.subplots(len(metrics), 1, figsize=(12, 3 * len(metrics)), constrained_layout=True)
    
    for ax, metric in zip(axs, metrics):
        
        # Collect 'original' and 'change' values for each repository
        # original = first data point
        # change   = final - original
        originals = []
        changes   = []
        
        for prefix in repositories.values():
            ts = data[f"{metric}_{prefix}"]
            first_val = ts.iloc[0]
            last_val = ts.iloc[-1]
            originals.append(first_val)
            changes.append(last_val - first_val)
        
        x = np.arange(len(repositories))  # x positions for bars
        
        # STACKED BARS
        # 1) Bottom portion (gray) = 'original'
        bars_original = ax.bar(
            x, 
            originals, 
            color='lightgray', 
            edgecolor='black', 
            label='Original'
        )
        
        # 2) Top portion (blue) = 'change' (stacked on top of the original)
        bars_change = ax.bar(
            x, 
            changes, 
            bottom=originals, 
            color='lightblue', 
            edgecolor='black', 
            label='Change'
        )
        
        # Add numeric labels at the very top (final = original + change)
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
        
        # Add sparklines for each repository
        for i, (repo, prefix) in enumerate(repositories.items()):
            # Full time series
            time_series = data[f"{metric}_{prefix}"]
            dates = data['DATE']
            first_val = time_series.iloc[0]
            last_val = time_series.iloc[-1]
            
            # Percent change
            if first_val != 0:
                pct_change = (last_val - first_val) / first_val * 100
            else:
                pct_change = 0.0
            
            # Create inset axes for sparkline
            final_val = originals[i] + changes[i]  # total bar height
            ax_inset = ax.inset_axes([
                i / len(repositories),             # x-position in parent axis
                final_val / max(originals + np.array(changes)) + 0.05,  # y-position above the total bar
                0.1,                               # width of inset
                0.1                                # height of inset
            ])
            
            # Plot time series (sparkline)
            ax_inset.plot(dates, time_series, color='black', linewidth=1, zorder=2)
            ax_inset.fill_between(dates, time_series, color='gray', alpha=0.2, zorder=1)
            
            # Highlight first and last points
            ax_inset.scatter(dates.iloc[0],  first_val, color='red', s=10, zorder=3)
            ax_inset.scatter(dates.iloc[-1], last_val,   color='red', s=10, zorder=3)
            
            # Make sure the sparkline isn't squashed
            y_min, y_max = time_series.min(), time_series.max()
            if y_min == y_max:
                # If truly flat, give a small buffer
                y_min -= 0.5
                y_max += 0.5
            else:
                margin = 0.1 * (y_max - y_min)
                y_min -= margin
                y_max += margin
            ax_inset.set_ylim(y_min, y_max)
            ax_inset.set_xlim(dates.min(), dates.max())
            
            # Remove tick labels/spines
            ax_inset.set_xticks([])
            ax_inset.set_yticks([])
            for spine in ax_inset.spines.values():
                spine.set_visible(False)
            
            # Place percent change text in top-right with bounding box
            ax_inset.text(
                0.95, 
                0.95, 
                f"{pct_change:.2f}%", 
                transform=ax_inset.transAxes,
                ha="right", 
                va="top", 
                fontsize=8, 
                color="darkred",
                zorder=5,
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none')
            )
        
        # Format the main chart
        ax.set_title(f'{metric}: Original vs. Change', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(repositories.keys())
        ax.set_ylabel(metric)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        # Optionally add a legend if you like
        ax.legend()
    
    plt.show()

# Run the plotting function
plot_bar_with_sparklines(data, filtered_repositories, metrics)
