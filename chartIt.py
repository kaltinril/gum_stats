import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator

# Load the data
data = pd.read_csv('data.csv')  # Replace 'data.csv' with the path to your file
data.columns = data.columns.str.strip()  # Clean column names by stripping leading/trailing spaces
data['DATE'] = pd.to_datetime(data['DATE'])  # Convert DATE to datetime

# Define repositories and their corresponding prefixes in the dataset
repositories = {
    "Gum": "gum",
    "GeonBit.UI": "geonbit",
    "Myra": "myra",
    "ImGui": "imgui"
}

metrics = ['STARS', 'SUBS', 'FORKS', 'ISSUES']

# Specify repositories to exclude
excluded_repositories = ["ImGui"]  # Add repositories to exclude here

# Filter repositories based on exclusion
filtered_repositories = {
    repo: prefix 
    for repo, prefix in repositories.items() 
    if repo not in excluded_repositories
}

def plot_bar_with_sparklines(data, repositories, metrics):
    """
    Plot bar charts (average metric values) with small inset sparklines
    and annotate each sparkline with percent change (first to last).
    Also adds numeric labels on top of each bar.
    """
    fig, axs = plt.subplots(
        len(metrics), 
        1, 
        figsize=(12, 3 * len(metrics)), 
        constrained_layout=True
    )
    
    for ax, metric in zip(axs, metrics):
        # Calculate the average value of the metric for each repository
        averages = []
        for prefix in repositories.values():
            avg_val = data[f'{metric}_{prefix}'].mean()
            averages.append(avg_val)
        
        # Create the bar chart
        x = np.arange(len(repositories))  # Label locations
        bars = ax.bar(
            x, 
            averages, 
            color='lightblue', 
            edgecolor='black', 
            label=f'Average {metric}'
        )
        
        # Add numeric labels above each bar
        for i, bar in enumerate(bars):
            bar_height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width()/2,
                bar_height * 1.01,  # a little above the bar
                f"{bar_height:.1f}",  # or .0f if integers
                ha='center',
                va='bottom',
                fontsize=9,
                color='black'
            )
        
        # Add sparklines (mini-charts) above each bar and show percent change
        for i, (repo, prefix) in enumerate(repositories.items()):
            # Extract the time series for the repository
            time_series = data[f'{metric}_{prefix}']
            dates = data['DATE']
            
            # -- Compute percent change from first to last data point --
            first_value = time_series.iloc[0]
            last_value = time_series.iloc[-1]
            
            # Safely compute percent change, avoiding division by zero
            if first_value != 0:
                percent_change = (last_value - first_value) / first_value * 100
            else:
                percent_change = 0.0
            
            # Create inset axes for the sparkline
            bar_height = bars[i].get_height()
            ax_inset = ax.inset_axes([
                i / len(repositories),             # x-position in parent axis
                bar_height / max(averages) + 0.05, # y-position in parent axis
                0.1,                               # width of the inset
                0.1                                # height of the inset
            ])
            
            # Plot the sparkline
            ax_inset.plot(dates, time_series, color='black', linewidth=1)
            ax_inset.fill_between(dates, time_series, color='gray', alpha=0.2)
            
            # Highlight the first and last data points
            ax_inset.scatter(dates.iloc[0],  first_value,  color='red', s=10, zorder=3)
            ax_inset.scatter(dates.iloc[-1], last_value, color='red', s=10, zorder=3)
            
            # Ensure the sparkline isn't squashed: set y-limits
            y_min, y_max = time_series.min(), time_series.max()
            if y_min == y_max:
                # Handle the case where data is flat
                y_min -= 0.5
                y_max += 0.5
            else:
                # Add a small margin around min and max
                margin = 0.1 * (y_max - y_min)
                y_min -= margin
                y_max += margin
            ax_inset.set_ylim(y_min, y_max)
            
            # Keep x-limits consistent with the data range
            ax_inset.set_xlim(dates.min(), dates.max())
            
            # Remove tick labels and spines for a "sparkline" look
            ax_inset.set_xticks([])
            ax_inset.set_yticks([])
            for spine in ax_inset.spines.values():
                spine.set_visible(False)
            
            # Place the percent change text in the top-right corner
            # with a bounding box and higher zorder so it's visible.
            ax_inset.text(
                0.95, 
                0.95, 
                f"{percent_change:.2f}%", 
                transform=ax_inset.transAxes,
                ha="right", 
                va="top", 
                fontsize=8, 
                color="darkred",
                zorder=5,  # ensures it's drawn above the sparkline
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none')
            )
        
        # Format the main chart
        ax.set_title(f'{metric} Across Repositories', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(repositories.keys())
        ax.set_ylabel(metric)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.show()

# Plot the bar chart with sparklines and percent change
plot_bar_with_sparklines(data, filtered_repositories, metrics)
