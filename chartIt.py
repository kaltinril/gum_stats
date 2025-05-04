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
    """Plot a series of bar charts (one for each metric) with small inset sparklines
    and annotate each sparkline with the total percent change from the first to the last
    data point in the time series.
    """
    fig, axs = plt.subplots(
        len(metrics), 
        1, 
        figsize=(12, 3 * len(metrics)), 
        constrained_layout=True
    )
    
    for ax, metric in zip(axs, metrics):
        # Calculate the average value of the metric for each repository
        averages = [
            data[f'{metric}_{prefix}'].mean() for prefix in repositories.values()
        ]
        
        # Create the bar chart
        x = np.arange(len(repositories))  # Label locations
        bars = ax.bar(x, averages, color='lightblue', edgecolor='black', label=f'Average {metric}')
        
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
                percent_change = 0.0  # or np.nan or a custom placeholder
            
            # Get bar height for sparkline vertical placement
            bar_height = bars[i].get_height()
            
            # Create inset axes for the sparkline
            ax_inset = ax.inset_axes([
                i / len(repositories),   # x-position in the parent axis
                bar_height / max(averages) + 0.05,  # y-position in the parent axis
                0.1,                     # width of the inset
                0.1                      # height of the inset
            ])
            ax_inset.plot(dates, time_series, color='black', linewidth=1)
            ax_inset.xaxis.set_visible(False)
            ax_inset.yaxis.set_visible(False)
            ax_inset.set_xlim(dates.min(), dates.max())
            ax_inset.yaxis.set_major_locator(MaxNLocator(2))
            
            # Place the percent change text inside the sparkline area
            # Here, we're placing it in the top-right corner of the inset
            ax_inset.text(
                0.95, 
                0.95, 
                f"{percent_change:.2f}%", 
                transform=ax_inset.transAxes,
                ha="right", 
                va="top", 
                fontsize=8, 
                color="darkred"
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
