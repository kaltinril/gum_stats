import matplotlib.pyplot as plt
import numpy as np
from starcounts import load_chart_data, parse_years_arg

years = parse_years_arg()
data, filtered_repositories, metrics = load_chart_data(years)


def plot_bar_with_sparklines(data, repositories, metrics):
    """
    Creates stacked bars with sparklines, laid out for many repos.
    - Gray portion = the original value (first data point).
    - Blue portion = the absolute change (final - original).
    - Sparklines sit in a dedicated row above each metric's bar chart.
    """
    n_repos = len(repositories)
    n_metrics = len(metrics)

    # Two rows per metric: one for sparklines, one for bars
    fig, all_axs = plt.subplots(
        n_metrics * 2, 1,
        figsize=(max(14, n_repos * 1.5), 3.5 * n_metrics),
        gridspec_kw={'height_ratios': [1, 3] * n_metrics},
        constrained_layout=True
    )

    for m_idx, metric in enumerate(metrics):
        ax_spark = all_axs[m_idx * 2]      # sparkline row
        ax_bar = all_axs[m_idx * 2 + 1]    # bar chart row

        # Compute originals and changes
        originals = []
        changes = []
        for prefix in repositories.values():
            ts = data[f"{metric}_{prefix}"]
            first_val = ts.iloc[0]
            last_val = ts.iloc[-1]
            originals.append(first_val)
            changes.append(last_val - first_val)

        x = np.arange(n_repos)

        # === Bar chart ===
        bars_original = ax_bar.bar(
            x, originals,
            color='lightgray', edgecolor='black', label='Original'
        )
        bars_change = ax_bar.bar(
            x, changes, bottom=originals,
            color='lightblue', edgecolor='black', label='Change'
        )

        # Label inside each bar portion
        for i, (barO, barC) in enumerate(zip(bars_original, bars_change)):
            orig_val = barO.get_height()
            orig_x = barO.get_x() + barO.get_width() / 2

            # Original label
            if orig_val > 0:
                ax_bar.text(
                    orig_x, orig_val / 2.0, f"{orig_val:.0f}",
                    ha='center', va='center', color='white', fontsize=8
                )

            # Change label
            change_val = barC.get_height()
            if abs(change_val) > 0:
                change_y = orig_val + change_val / 2.0
                ax_bar.text(
                    orig_x, change_y, f"{change_val:+.0f}",
                    ha='center', va='center', color='black', fontsize=8
                )

        # Final total on top
        for i in range(n_repos):
            final_val = originals[i] + changes[i]
            ax_bar.text(
                x[i], final_val * 1.01, f"{final_val:.0f}",
                ha='center', va='bottom', fontsize=8, color='black'
            )

        ax_bar.set_title(f'{metric}: Original vs. Change', fontsize=13)
        ax_bar.set_xticks(x)
        ax_bar.set_xticklabels(repositories.keys(), rotation=30, ha='right', fontsize=9)
        ax_bar.set_ylabel(metric)
        ax_bar.grid(axis='y', linestyle='--', alpha=0.7)
        ax_bar.legend(fontsize=8)

        # === Sparklines row (normalized to % change so slopes are comparable) ===
        ax_spark.axis('off')
        dates = data['DATE']

        spark_height = 0.85

        # Compute all % change series first to find a shared y range
        pct_series_list = []
        pct_changes = []
        for prefix in repositories.values():
            ts = data[f"{metric}_{prefix}"]
            first_val = ts.iloc[0]
            if first_val != 0:
                pct_ts = (ts - first_val) / first_val * 100
            else:
                pct_ts = ts * 0  # all zeros
            pct_series_list.append(pct_ts)
            pct_changes.append(pct_ts.iloc[-1])

        # Shared y range across all sparklines for this metric
        all_pct_min = min(s.min() for s in pct_series_list)
        all_pct_max = max(s.max() for s in pct_series_list)
        if all_pct_min == all_pct_max:
            all_pct_min -= 1
            all_pct_max += 1
        margin = 0.1 * (all_pct_max - all_pct_min)

        # Set explicit xlim so sparkline positions map cleanly
        ax_bar.set_xlim(-0.5, n_repos - 0.5)
        spark_width = 0.7 / n_repos

        for i, (repo, prefix) in enumerate(repositories.items()):
            pct_ts = pct_series_list[i]
            pct_change = pct_changes[i]

            center_ax = (i + 0.5) / n_repos
            left = center_ax - spark_width / 2
            ax_inset = ax_spark.inset_axes([left, 0.05, spark_width, spark_height])

            ax_inset.plot(dates, pct_ts, color='black', linewidth=1, zorder=2)
            ax_inset.fill_between(dates, pct_ts, color='gray', alpha=0.2, zorder=1)
            ax_inset.scatter(dates.iloc[0], pct_ts.iloc[0], color='red', s=8, zorder=3)
            ax_inset.scatter(dates.iloc[-1], pct_ts.iloc[-1], color='red', s=8, zorder=3)

            # Shared y scale so slopes are visually comparable
            ax_inset.set_ylim(all_pct_min - margin, all_pct_max + margin)
            ax_inset.set_xlim(dates.min(), dates.max())

            ax_inset.set_xticks([])
            ax_inset.set_yticks([])
            for spine in ax_inset.spines.values():
                spine.set_visible(False)

            ax_inset.text(
                0.95, 0.95, f"{pct_change:+.1f}%",
                transform=ax_inset.transAxes,
                ha="right", va="top", fontsize=7,
                color="darkred",
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'),
                zorder=5
            )

    plt.show()


plot_bar_with_sparklines(data, filtered_repositories, metrics)
