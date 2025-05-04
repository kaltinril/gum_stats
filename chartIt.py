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
filtered_repositories = {repo: prefix for repo, prefix in repositories.items() if repo not in excluded_repositories}

# Function to create bar chart with sparklines
def plot_bar_with_sparklines(data, repositories, metrics):
    fig, axs = plt.subplots(len(metrics), 1, figsize=(12, 3 * len(metrics)), constrained_layout=True)
    
    for ax, metric in zip(axs, metrics):
        # Calculate the average value of the metric for each repository
        averages = [
            data[f'{metric}_{prefix}'].mean() for prefix in repositories.values()
        ]
        
        # Create the bar chart
        x = np.arange(len(repositories))  # Label locations
        bars = ax.bar(x, averages, color='lightblue', edgecolor='black', label=f'Average {metric}')
        
        # Add sparklines above each bar
        for i, (repo, prefix) in enumerate(repositories.items()):
            # Extract the time series for the repository
            time_series = data[f'{metric}_{prefix}']
            dates = data['DATE']
            
            # Normalize the position for the sparkline
            bar_height = bars[i].get_height()
            ax_inset = ax.inset_axes([i / len(repositories), bar_height / max(averages) + 0.05, 0.1, 0.1])
            ax_inset.plot(dates, time_series, color='black', linewidth=1)
            ax_inset.xaxis.set_visible(False)
            ax_inset.yaxis.set_visible(False)
            ax_inset.set_xlim(dates.min(), dates.max())
            ax_inset.yaxis.set_major_locator(MaxNLocator(2))
        
        # Format the main chart
        ax.set_title(f'{metric} Across Repositories', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels(repositories.keys())
        ax.set_ylabel(metric)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.show()

# Plot the bar chart with sparklines
plot_bar_with_sparklines(data, filtered_repositories, metrics)
