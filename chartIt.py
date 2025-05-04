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
        
        # Add sparklines above each bar and show percent change
        for i, (repo, prefix) in enumerate(repositories.items()):
            # Extract the time series for the repository
            time_series = data[f'{metric}_{prefix}']
            dates = data['DATE']
            
            # -- Compute percent change from first to last data point --
            # Check for division by zero in case the first value is 0
            first_value = time_series.iloc[0]
            last_value = time_series.iloc[-1]
            if first_value != 0:
                percent_change = (last_value - first_value) / first_value * 100
            else:
                percent_change = np.nan  # or handle differently if desired
            
            # Place the percent change text on top of the bar
            bar_height = bars[i].get_height()
            ax.text(
                x[i], 
                bar_height * 1.01,  # small offset above the bar
                f"{percent_change:.2f}%",
                ha='center',
                va='bottom',
                fontsize=9
            )
            
            # Normalize the position for the sparkline
            ax_inset = ax.inset_axes([
                i / len(repositories),   # x-position of the inset
                bar_height / max(averages) + 0.05,  # y-position of the inset
                0.1,                     # width of the inset
                0.1                      # height of the inset
            ])
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

# Plot the bar chart with sparklines and percent change
plot_bar_with_sparklines(data, filtered_repositories, metrics)
