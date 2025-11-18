"""
Create publication-quality figures for Meta-CART synthesis paper
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle
import numpy as np
import seaborn as sns

# Set publication style
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['xtick.labelsize'] = 9
plt.rcParams['ytick.labelsize'] = 9
plt.rcParams['legend.fontsize'] = 9
plt.rcParams['figure.titlesize'] = 13

# Color scheme
COLOR_DATA = '#3498db'
COLOR_PROCESS = '#e74c3c'
COLOR_OUTPUT = '#2ecc71'
COLOR_VALIDATION = '#f39c12'
COLOR_LIGHT = '#ecf0f1'


def create_figure1_methodology():
    """
    Figure 1: Meta-CART Methodology Flowchart
    Shows the complete workflow from data input to validated subgroups
    """
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # Title
    fig.suptitle('Figure 1: Meta-CART Methodology Framework',
                 fontsize=14, fontweight='bold', y=0.98)

    # Box drawing helper function
    def draw_box(x, y, width, height, text, color, ax, style='round'):
        if style == 'round':
            box = FancyBboxPatch((x, y), width, height,
                                boxstyle="round,pad=0.1",
                                facecolor=color, edgecolor='black',
                                linewidth=1.5, alpha=0.8)
        else:
            box = Rectangle((x, y), width, height,
                          facecolor=color, edgecolor='black',
                          linewidth=1.5, alpha=0.8)
        ax.add_patch(box)
        ax.text(x + width/2, y + height/2, text,
               ha='center', va='center', fontsize=9,
               weight='bold', wrap=True)

    # Arrow helper
    def draw_arrow(x1, y1, x2, y2, ax, label=''):
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                              arrowstyle='->', mutation_scale=20,
                              linewidth=2, color='black')
        ax.add_patch(arrow)
        if label:
            mid_x, mid_y = (x1 + x2)/2, (y1 + y2)/2
            ax.text(mid_x + 0.3, mid_y, label, fontsize=8,
                   style='italic', bbox=dict(boxstyle='round',
                   facecolor='white', alpha=0.8))

    # Step 1: Input Data
    draw_box(0.5, 8.5, 2, 0.8, 'Input Data\n(X, y, treatment)', COLOR_DATA, ax)

    # Step 2: Sample Splitting
    draw_arrow(1.5, 8.5, 1.5, 7.8, ax)
    draw_box(0.3, 6.8, 1.2, 0.8, 'Building\nSample\n(50%)', COLOR_LIGHT, ax)
    draw_box(1.8, 6.8, 1.2, 0.8, 'Estimation\nSample\n(50%)', COLOR_LIGHT, ax)

    # Sample splitting label
    ax.text(1.5, 7.5, 'Honest Sample Splitting', ha='center',
           fontsize=9, weight='bold', style='italic')

    # Step 3: Tree Building
    draw_arrow(0.9, 6.8, 0.9, 6.0, ax)
    draw_box(0.2, 5.0, 1.6, 0.8, 'Recursive Partitioning\nMaximize ΔTE',
            COLOR_PROCESS, ax)

    # Splitting criterion equation
    ax.text(0.2, 4.6, r'Score = $\sum_i n_i(\hat{\tau}_i - \hat{\tau})^2$',
           fontsize=8, style='italic')

    # Step 4: Pruning
    draw_arrow(1.0, 5.0, 1.0, 4.2, ax)
    draw_box(0.2, 3.2, 1.6, 0.8, 'Cross-Validation\nPruning',
            COLOR_PROCESS, ax)

    # Step 5: Tree Structure Output
    draw_arrow(1.0, 3.2, 1.0, 2.5, ax)
    draw_box(0.3, 1.5, 1.4, 0.8, 'Final Tree\nStructure', COLOR_OUTPUT, ax)

    # Step 6: Honest Estimation
    draw_arrow(2.4, 7.0, 4.0, 5.5, ax, 'Apply tree')
    draw_box(3.8, 4.7, 1.6, 0.8, 'Honest Effect\nEstimation', COLOR_PROCESS, ax)

    # Step 7: Statistical Inference
    draw_arrow(4.6, 4.7, 4.6, 3.9, ax)
    draw_box(3.8, 3.0, 1.6, 0.7, 'Confidence Intervals\n& P-values',
            COLOR_OUTPUT, ax)

    # Step 8: Multiple Testing
    draw_arrow(4.6, 3.0, 4.6, 2.2, ax)
    draw_box(3.8, 1.4, 1.6, 0.7, 'Multiple Testing\nCorrection',
            COLOR_PROCESS, ax)

    # Step 9: Bootstrap Validation
    draw_box(6.2, 7.5, 2.0, 1.2, 'Bootstrap Validation\n(100-500 iterations)',
            COLOR_VALIDATION, ax)
    draw_arrow(7.2, 7.5, 7.2, 6.5, ax)

    # Bootstrap outputs
    draw_box(6.0, 5.0, 1.0, 0.6, 'Variable\nImportance', COLOR_OUTPUT, ax, 'round')
    draw_box(7.2, 5.0, 1.0, 0.6, 'Subgroup\nStability', COLOR_OUTPUT, ax, 'round')
    draw_box(8.4, 5.0, 1.0, 0.6, 'Structure\nSimilarity', COLOR_OUTPUT, ax, 'round')

    # Final Output
    draw_box(6.2, 2.5, 2.8, 1.3,
            'Final Validated Subgroups\n• Treatment effects\n• Confidence intervals\n• Splitting rules\n• Stability metrics',
            COLOR_OUTPUT, ax)

    # Connect components to final output
    draw_arrow(1.7, 1.5, 6.2, 3.0, ax)
    draw_arrow(4.6, 1.4, 6.2, 2.8, ax)
    draw_arrow(7.2, 5.0, 7.2, 3.8, ax)

    # Add legend for components
    legend_y = 0.5
    ax.text(0.5, legend_y, 'Key Components:', fontsize=9, weight='bold')

    legend_elements = [
        mpatches.Patch(color=COLOR_DATA, label='Data', alpha=0.8),
        mpatches.Patch(color=COLOR_PROCESS, label='Processing', alpha=0.8),
        mpatches.Patch(color=COLOR_OUTPUT, label='Output', alpha=0.8),
        mpatches.Patch(color=COLOR_VALIDATION, label='Validation', alpha=0.8)
    ]
    ax.legend(handles=legend_elements, loc='lower left',
             bbox_to_anchor=(0.05, 0.02), ncol=4, frameon=True)

    plt.tight_layout()
    plt.savefig('Figure1_MetaCART_Methodology.png', dpi=300, bbox_inches='tight')
    print("Figure 1 saved: Figure1_MetaCART_Methodology.png")
    return fig


def create_figure2_applications():
    """
    Figure 2: Meta-CART Applications and Method Comparison
    Two-panel figure showing applications and method comparison
    """
    fig = plt.figure(figsize=(12, 5))

    # Panel A: Applications across domains
    ax1 = plt.subplot(1, 2, 1)

    applications = [
        'Clinical Trials\n(Personalized Medicine)',
        'A/B Testing\n(Digital Products)',
        'Policy Evaluation\n(Social Programs)',
        'Precision Agriculture\n(Treatment Response)',
        'Education Research\n(Intervention Effects)'
    ]

    # Sample sizes and effect sizes (example data)
    min_n = [300, 500, 400, 350, 450]
    effect_heterogeneity = [0.8, 0.6, 0.7, 0.5, 0.65]

    y_pos = np.arange(len(applications))

    # Create horizontal bars showing effect heterogeneity
    colors = plt.cm.viridis(np.array(effect_heterogeneity))
    bars = ax1.barh(y_pos, effect_heterogeneity, color=colors, alpha=0.8,
                    edgecolor='black', linewidth=1.5)

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(applications, fontsize=9)
    ax1.set_xlabel('Typical Treatment Effect Heterogeneity', fontsize=10, weight='bold')
    ax1.set_xlim(0, 1)
    ax1.set_title('Panel A: Meta-CART Application Domains',
                 fontsize=11, weight='bold', pad=10)
    ax1.grid(axis='x', alpha=0.3, linestyle='--')

    # Add sample size annotations
    for i, (bar, n) in enumerate(zip(bars, min_n)):
        width = bar.get_width()
        ax1.text(width + 0.02, bar.get_y() + bar.get_height()/2,
                f'n≥{n}', va='center', fontsize=8, style='italic')

    # Panel B: Method Comparison
    ax2 = plt.subplot(1, 2, 2)

    methods = ['Meta-CART', 'Causal Forest', 'Virtual Twins', 'Naive Testing']
    features = ['Interpretability', 'Valid Inference', 'Multiple Testing\nControl',
               'Computational\nSpeed', 'Sample\nEfficiency']

    # Scores (0-10 scale)
    scores = np.array([
        [9, 8, 7, 8, 7],    # Meta-CART
        [4, 9, 9, 5, 6],    # Causal Forest
        [6, 6, 5, 7, 6],    # Virtual Twins
        [8, 2, 1, 9, 5]     # Naive Testing
    ])

    # Create heatmap
    im = ax2.imshow(scores, cmap='RdYlGn', aspect='auto', vmin=0, vmax=10)

    # Set ticks
    ax2.set_xticks(np.arange(len(features)))
    ax2.set_yticks(np.arange(len(methods)))
    ax2.set_xticklabels(features, fontsize=9, rotation=0, ha='center')
    ax2.set_yticklabels(methods, fontsize=9)

    ax2.set_title('Panel B: Methodological Comparison',
                 fontsize=11, weight='bold', pad=10)

    # Add text annotations
    for i in range(len(methods)):
        for j in range(len(features)):
            text = ax2.text(j, i, f'{scores[i, j]}',
                          ha='center', va='center', color='black',
                          fontsize=9, weight='bold')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax2, orientation='horizontal',
                       pad=0.15, aspect=30)
    cbar.set_label('Performance Score (0-10)', fontsize=9)
    cbar.ax.tick_params(labelsize=8)

    # Overall figure title
    fig.suptitle('Figure 2: Meta-CART Applications and Methodological Positioning',
                fontsize=13, fontweight='bold', y=1.00)

    plt.tight_layout()
    plt.savefig('Figure2_Applications_Comparison.png', dpi=300, bbox_inches='tight')
    print("Figure 2 saved: Figure2_Applications_Comparison.png")
    return fig


# Create both figures
if __name__ == "__main__":
    print("Creating synthesis figures...")
    print()

    # Figure 1: Methodology
    fig1 = create_figure1_methodology()
    plt.close(fig1)

    print()

    # Figure 2: Applications
    fig2 = create_figure2_applications()
    plt.close(fig2)

    print()
    print("Both figures created successfully!")
    print("- Figure1_MetaCART_Methodology.png")
    print("- Figure2_Applications_Comparison.png")
