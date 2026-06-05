"""
Visualization utilities for Meta-CART
======================================

Functions for visualizing Meta-CART results, including:
- Tree structure diagrams
- Treatment effect plots
- Subgroup comparisons
- Bootstrap stability plots
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend: safe for headless import/use
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, List
from meta_cart import MetaCART, Node, BootstrapStability


def plot_tree_structure(
    meta_cart: MetaCART,
    figsize: tuple = (14, 10),
    show_honest: bool = True
) -> plt.Figure:
    """
    Create a visualization of the tree structure.

    Parameters
    ----------
    meta_cart : MetaCART
        Fitted Meta-CART model
    figsize : tuple
        Figure size
    show_honest : bool
        Whether to show honest estimates

    Returns
    -------
    fig : matplotlib Figure
    """

    fig, ax = plt.subplots(figsize=figsize)
    ax.axis('off')

    if meta_cart.tree_ is None:
        ax.text(0.5, 0.5, 'No tree available', ha='center', va='center')
        return fig

    # Calculate tree layout
    positions = {}
    _calculate_positions(meta_cart.tree_, positions, x=0.5, y=1.0, dx=0.25)

    # Draw edges
    _draw_edges(meta_cart.tree_, positions, ax)

    # Draw nodes
    _draw_nodes(meta_cart.tree_, positions, ax, show_honest)

    plt.tight_layout()
    return fig


def _calculate_positions(
    node: Node,
    positions: dict,
    x: float,
    y: float,
    dx: float
) -> None:
    """Calculate x, y positions for each node."""

    if node is None:
        return

    positions[node.node_id] = (x, y)

    if not node.is_leaf:
        dy = 0.15
        new_dx = dx / 2

        _calculate_positions(node.left_child, positions, x - dx, y - dy, new_dx)
        _calculate_positions(node.right_child, positions, x + dx, y - dy, new_dx)


def _draw_edges(node: Node, positions: dict, ax: plt.Axes) -> None:
    """Draw edges between nodes."""

    if node is None or node.is_leaf:
        return

    x, y = positions[node.node_id]

    # Left edge
    if node.left_child:
        x_left, y_left = positions[node.left_child.node_id]
        ax.plot([x, x_left], [y, y_left], 'k-', alpha=0.3, linewidth=1.5)

        # Add label
        mid_x, mid_y = (x + x_left) / 2, (y + y_left) / 2
        ax.text(mid_x, mid_y, '≤', fontsize=8, ha='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    # Right edge
    if node.right_child:
        x_right, y_right = positions[node.right_child.node_id]
        ax.plot([x, x_right], [y, y_right], 'k-', alpha=0.3, linewidth=1.5)

        # Add label
        mid_x, mid_y = (x + x_right) / 2, (y + y_right) / 2
        ax.text(mid_x, mid_y, '>', fontsize=8, ha='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    # Recurse
    _draw_edges(node.left_child, positions, ax)
    _draw_edges(node.right_child, positions, ax)


def _draw_nodes(
    node: Node,
    positions: dict,
    ax: plt.Axes,
    show_honest: bool
) -> None:
    """Draw node boxes."""

    if node is None:
        return

    x, y = positions[node.node_id]

    # Determine node color based on treatment effect
    if show_honest and node.honest_effect is not None:
        effect = node.honest_effect
    else:
        effect = node.treatment_effect

    # Color by effect size
    if effect > 0.5:
        color = '#d4edda'  # Green
    elif effect < -0.5:
        color = '#f8d7da'  # Red
    else:
        color = '#fff3cd'  # Yellow

    # Create label
    if node.is_leaf:
        # Leaf node
        label = f"Subgroup {node.node_id}\n"
        label += f"n = {node.n_samples}\n"

        if show_honest and node.honest_effect is not None:
            label += f"TE = {node.honest_effect:.3f}\n"
            label += f"95% CI: [{node.honest_ci_lower:.3f}, {node.honest_ci_upper:.3f}]"
        else:
            label += f"TE = {node.treatment_effect:.3f}\n"
            ci_l = node.treatment_effect - 1.96 * node.treatment_effect_se
            ci_u = node.treatment_effect + 1.96 * node.treatment_effect_se
            label += f"95% CI: [{ci_l:.3f}, {ci_u:.3f}]"

        box_style = 'round,pad=0.5'
        width = 0.12
        height = 0.08
    else:
        # Internal node
        label = f"{node.split_variable}\n≤ {node.split_value:.3f}\n"
        label += f"n = {node.n_samples}"
        box_style = 'round,pad=0.3'
        color = '#e7f3ff'  # Light blue
        width = 0.1
        height = 0.06

    # Draw box
    bbox = dict(
        boxstyle=box_style,
        facecolor=color,
        edgecolor='black',
        linewidth=1.5 if node.is_leaf else 1
    )

    ax.text(x, y, label, ha='center', va='center',
            fontsize=9 if node.is_leaf else 8,
            bbox=bbox, fontweight='bold' if node.is_leaf else 'normal')

    # Recurse
    if not node.is_leaf:
        _draw_nodes(node.left_child, positions, ax, show_honest)
        _draw_nodes(node.right_child, positions, ax, show_honest)


def plot_subgroup_effects(
    meta_cart: MetaCART,
    figsize: tuple = (10, 6),
    use_honest: bool = True
) -> plt.Figure:
    """
    Plot treatment effects for each subgroup with confidence intervals.

    Parameters
    ----------
    meta_cart : MetaCART
        Fitted Meta-CART model
    figsize : tuple
        Figure size
    use_honest : bool
        Whether to use honest estimates

    Returns
    -------
    fig : matplotlib Figure
    """

    effects_df = meta_cart.get_subgroup_effects()

    fig, ax = plt.subplots(figsize=figsize)

    n_groups = len(effects_df)
    x_pos = np.arange(n_groups)

    if use_honest and 'honest_effect' in effects_df.columns:
        effects = effects_df['honest_effect'].values
        ci_lower = effects_df['honest_ci_lower'].values
        ci_upper = effects_df['honest_ci_upper'].values
        title_suffix = '(Honest Estimates)'
    else:
        effects = effects_df['treatment_effect'].values
        ci_lower = effects_df['ci_lower'].values
        ci_upper = effects_df['ci_upper'].values
        title_suffix = '(Training Estimates)'

    # Plot error bars
    colors = ['green' if e > 0 else 'red' for e in effects]
    ax.errorbar(x_pos, effects,
                yerr=[effects - ci_lower, ci_upper - effects],
                fmt='o', markersize=10, capsize=5, capthick=2,
                ecolor='gray', markerfacecolor=colors, markeredgecolor='black',
                markeredgewidth=1.5)

    # Add horizontal line at 0
    ax.axhline(y=0, color='black', linestyle='--', alpha=0.3, linewidth=1)

    # Customize
    ax.set_xlabel('Subgroup ID', fontsize=12, fontweight='bold')
    ax.set_ylabel('Treatment Effect', fontsize=12, fontweight='bold')
    ax.set_title(f'Treatment Effects by Subgroup {title_suffix}',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels([f"Subgroup {i}" for i in effects_df['subgroup_id']])
    ax.grid(axis='y', alpha=0.3)

    # Add sample sizes as text
    for i, (idx, row) in enumerate(effects_df.iterrows()):
        y_offset = 0.1 * (ci_upper[i] - ci_lower[i])
        ax.text(i, ci_upper[i] + y_offset, f"n={row['n_samples']}",
                ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    return fig


def plot_comparison_forest(
    meta_cart: MetaCART,
    figsize: tuple = (10, 8),
    use_honest: bool = True
) -> plt.Figure:
    """
    Create a forest plot comparing subgroups.

    Parameters
    ----------
    meta_cart : MetaCART
        Fitted Meta-CART model
    figsize : tuple
        Figure size
    use_honest : bool
        Whether to use honest estimates

    Returns
    -------
    fig : matplotlib Figure
    """

    effects_df = meta_cart.get_subgroup_effects()
    rules = meta_cart.get_splitting_rules()

    # Merge effects with rules
    rules_df = pd.DataFrame(rules)
    merged = effects_df.merge(rules_df, on='subgroup_id')

    # Sort by effect size
    if use_honest and 'honest_effect' in merged.columns:
        merged = merged.sort_values('honest_effect')
        effect_col = 'honest_effect'
        ci_lower_col = 'honest_ci_lower'
        ci_upper_col = 'honest_ci_upper'
    else:
        merged = merged.sort_values('treatment_effect')
        effect_col = 'treatment_effect'
        ci_lower_col = 'ci_lower'
        ci_upper_col = 'ci_upper'

    fig, ax = plt.subplots(figsize=figsize)

    n_groups = len(merged)
    y_pos = np.arange(n_groups)

    effects = merged[effect_col].values
    ci_lower = merged[ci_lower_col].values
    ci_upper = merged[ci_upper_col].values

    # Plot
    colors = ['green' if e > 0 else 'red' for e in effects]

    for i, (idx, row) in enumerate(merged.iterrows()):
        # Point estimate
        ax.plot(effects[i], y_pos[i], 'o', markersize=10,
                color=colors[i], markeredgecolor='black', markeredgewidth=1.5)

        # Confidence interval
        ax.plot([ci_lower[i], ci_upper[i]], [y_pos[i], y_pos[i]],
                '-', linewidth=2, color='gray')

    # Add vertical line at 0
    ax.axvline(x=0, color='black', linestyle='--', alpha=0.5)

    # Labels
    labels = []
    for _, row in merged.iterrows():
        rule_str = row['rule_string']
        if len(rule_str) > 40:
            rule_str = rule_str[:37] + '...'
        labels.append(f"{rule_str}\n(n={row['n_samples']})")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel('Treatment Effect (95% CI)', fontsize=12, fontweight='bold')
    ax.set_title('Forest Plot: Treatment Effects by Subgroup',
                 fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    return fig


def plot_variable_importance(
    bootstrap: BootstrapStability,
    figsize: tuple = (10, 6)
) -> plt.Figure:
    """
    Plot variable importance from bootstrap analysis.

    Parameters
    ----------
    bootstrap : BootstrapStability
        Fitted bootstrap stability analysis
    figsize : tuple
        Figure size

    Returns
    -------
    fig : matplotlib Figure
    """

    importance_df = bootstrap.get_variable_importance()

    fig, ax = plt.subplots(figsize=figsize)

    # Sort by importance
    importance_df = importance_df.sort_values('importance', ascending=True)

    # Plot
    ax.barh(range(len(importance_df)), importance_df['importance'],
            color='steelblue', alpha=0.7, edgecolor='black')

    # Labels
    ax.set_yticks(range(len(importance_df)))
    ax.set_yticklabels(importance_df['variable'])
    ax.set_xlabel('Importance (Proportion of Bootstrap Trees)',
                   fontsize=12, fontweight='bold')
    ax.set_title('Variable Importance from Bootstrap Analysis',
                 fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    # Add values as text
    for i, (idx, row) in enumerate(importance_df.iterrows()):
        ax.text(row['importance'] + 0.01, i, f"{row['importance']:.3f}",
                va='center', fontsize=9)

    plt.tight_layout()
    return fig


def plot_diagnostic_panel(
    meta_cart: MetaCART,
    X: np.ndarray,
    y: np.ndarray,
    treatment: np.ndarray,
    figsize: tuple = (16, 12)
) -> plt.Figure:
    """
    Create a comprehensive diagnostic panel.

    Parameters
    ----------
    meta_cart : MetaCART
        Fitted Meta-CART model
    X : array-like
        Covariates
    y : array-like
        Outcomes
    treatment : array-like
        Treatment indicators
    figsize : tuple
        Figure size

    Returns
    -------
    fig : matplotlib Figure
    """

    fig = plt.figure(figsize=figsize)
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # 1. Subgroup effects
    ax1 = fig.add_subplot(gs[0, :])
    effects_df = meta_cart.get_subgroup_effects()
    n_groups = len(effects_df)
    x_pos = np.arange(n_groups)

    use_honest = 'honest_effect' in effects_df.columns
    if use_honest:
        effects = effects_df['honest_effect'].values
        ci_lower = effects_df['honest_ci_lower'].values
        ci_upper = effects_df['honest_ci_upper'].values
    else:
        effects = effects_df['treatment_effect'].values
        ci_lower = effects_df['ci_lower'].values
        ci_upper = effects_df['ci_upper'].values

    colors = ['green' if e > 0 else 'red' for e in effects]
    ax1.errorbar(x_pos, effects,
                yerr=[effects - ci_lower, ci_upper - effects],
                fmt='o', markersize=8, capsize=5,
                ecolor='gray', markerfacecolor=colors)
    ax1.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax1.set_xlabel('Subgroup')
    ax1.set_ylabel('Treatment Effect')
    ax1.set_title('Treatment Effects by Subgroup')
    ax1.grid(alpha=0.3)

    # 2. Sample sizes
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.bar(x_pos, effects_df['n_samples'], color='steelblue', alpha=0.7)
    ax2.set_xlabel('Subgroup')
    ax2.set_ylabel('Sample Size')
    ax2.set_title('Sample Sizes by Subgroup')
    ax2.grid(axis='y', alpha=0.3)

    # 3. Treatment/Control balance
    ax3 = fig.add_subplot(gs[1, 1])
    width = 0.35
    ax3.bar(x_pos - width/2, effects_df['n_treated'], width,
            label='Treated', color='green', alpha=0.7)
    ax3.bar(x_pos + width/2, effects_df['n_control'], width,
            label='Control', color='gray', alpha=0.7)
    ax3.set_xlabel('Subgroup')
    ax3.set_ylabel('Count')
    ax3.set_title('Treatment/Control Balance')
    ax3.legend()
    ax3.grid(axis='y', alpha=0.3)

    # 4. Effect heterogeneity
    ax4 = fig.add_subplot(gs[2, 0])
    if use_honest:
        se_values = effects_df['honest_se'].values
    else:
        se_values = effects_df['std_error'].values

    ax4.scatter(effects, se_values, s=100, alpha=0.6, c=colors)
    ax4.set_xlabel('Treatment Effect')
    ax4.set_ylabel('Standard Error')
    ax4.set_title('Effect Size vs. Precision')
    ax4.grid(alpha=0.3)

    # 5. P-value distribution
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.bar(x_pos, effects_df['p_value'], color='steelblue', alpha=0.7)
    ax5.axhline(y=0.05, color='red', linestyle='--', label='α = 0.05')
    ax5.set_xlabel('Subgroup')
    ax5.set_ylabel('P-value')
    ax5.set_title('Statistical Significance')
    ax5.legend()
    ax5.grid(axis='y', alpha=0.3)

    return fig
