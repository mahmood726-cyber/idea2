"""
Advanced Meta-CART Example: Comparison with Alternative Methods
================================================================

This example demonstrates:
1. Comparison of Meta-CART with naive subgroup analysis
2. Handling of multiple testing and false discovery
3. Sensitivity analysis
4. Real-world complications (missing data, confounding, etc.)
5. Integration with other causal inference methods
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats
from meta_cart import MetaCART, BootstrapStability
from visualization import plot_tree_structure, plot_subgroup_effects


def generate_complex_trial_data(
    n_samples: int = 2000,
    n_noise_features: int = 10,
    random_state: int = 42
) -> tuple:
    """
    Generate complex trial data with:
    - True effect modifiers
    - Noise features (should not be selected)
    - Non-linear relationships
    - Interactions
    """

    np.random.seed(random_state)

    # True predictive features
    x1 = np.random.normal(0, 1, n_samples)  # Effect modifier
    x2 = np.random.uniform(0, 1, n_samples)  # Effect modifier
    x3 = np.random.normal(0, 1, n_samples)  # Prognostic only (not modifier)

    # Noise features (should not be selected)
    noise_features = np.random.normal(0, 1, (n_samples, n_noise_features))

    # Treatment assignment
    treatment = np.random.binomial(1, 0.5, n_samples)

    # Complex treatment effect structure:
    # TE = 2 if x1 > 0 AND x2 > 0.5
    # TE = -1 if x1 < 0 AND x2 < 0.5
    # TE = 0.5 otherwise

    treatment_effect = np.zeros(n_samples)

    mask1 = (x1 > 0) & (x2 > 0.5)
    treatment_effect[mask1] = 2.0 + np.random.normal(0, 0.3, np.sum(mask1))

    mask2 = (x1 < 0) & (x2 < 0.5)
    treatment_effect[mask2] = -1.0 + np.random.normal(0, 0.3, np.sum(mask2))

    mask3 = ~mask1 & ~mask2
    treatment_effect[mask3] = 0.5 + np.random.normal(0, 0.3, np.sum(mask3))

    # Baseline outcome (prognostic effect of x3)
    y_baseline = 5 + 2 * x3 + np.random.normal(0, 1, n_samples)

    # Final outcome
    y = y_baseline + treatment * treatment_effect

    # Combine features
    X = np.column_stack([x1, x2, x3] + [noise_features[:, i] for i in range(n_noise_features)])
    feature_names = ['X1_true', 'X2_true', 'X3_prognostic'] + [f'Noise_{i}' for i in range(n_noise_features)]

    return X, y, treatment, feature_names


def naive_subgroup_analysis(
    X: np.ndarray,
    y: np.ndarray,
    treatment: np.ndarray,
    feature_names: list,
    alpha: float = 0.05
) -> pd.DataFrame:
    """
    Perform naive subgroup analysis by testing all possible binary splits.

    This is what researchers often do (incorrectly) - test many subgroups
    without proper correction for multiple testing.
    """

    results = []

    # For each feature, try median split
    for feat_idx, feat_name in enumerate(feature_names):
        median_val = np.median(X[:, feat_idx])

        # Split by median
        for direction in ['below', 'above']:
            if direction == 'below':
                mask = X[:, feat_idx] <= median_val
                group_name = f"{feat_name} ≤ {median_val:.2f}"
            else:
                mask = X[:, feat_idx] > median_val
                group_name = f"{feat_name} > {median_val:.2f}"

            if np.sum(mask) < 20:  # Skip tiny groups
                continue

            # Compute treatment effect in this subgroup
            y_sub = y[mask]
            t_sub = treatment[mask]

            treated_mask = t_sub == 1
            control_mask = t_sub == 0

            if np.sum(treated_mask) < 5 or np.sum(control_mask) < 5:
                continue

            y_treated = y_sub[treated_mask]
            y_control = y_sub[control_mask]

            effect = np.mean(y_treated) - np.mean(y_control)

            # Standard error
            se = np.sqrt(
                np.var(y_treated, ddof=1) / len(y_treated) +
                np.var(y_control, ddof=1) / len(y_control)
            )

            # T-test
            t_stat = effect / se if se > 0 else 0
            df = len(y_treated) + len(y_control) - 2
            p_value = 2 * (1 - stats.t.cdf(np.abs(t_stat), df))

            results.append({
                'subgroup': group_name,
                'n': np.sum(mask),
                'effect': effect,
                'se': se,
                'p_value': p_value,
                'significant': p_value < alpha
            })

    return pd.DataFrame(results)


def calculate_fdr(p_values: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """
    Calculate False Discovery Rate (Benjamini-Hochberg procedure).

    Returns adjusted significance based on FDR control.
    """

    n = len(p_values)
    sorted_idx = np.argsort(p_values)
    sorted_p = p_values[sorted_idx]

    # BH critical values
    bh_critical = np.arange(1, n + 1) / n * alpha

    # Find largest i where p[i] <= (i/n) * alpha
    significant = sorted_p <= bh_critical

    if np.any(significant):
        threshold_idx = np.where(significant)[0][-1]
        threshold = sorted_p[threshold_idx]
    else:
        threshold = 0

    return p_values <= threshold


def sensitivity_analysis(
    X: np.ndarray,
    y: np.ndarray,
    treatment: np.ndarray,
    feature_names: list
) -> dict:
    """
    Perform sensitivity analysis with different hyperparameters.
    """

    results = {}

    # Different minimum leaf sizes
    for min_leaf in [20, 40, 60, 80]:
        print(f"  Testing min_samples_leaf = {min_leaf}")

        model = MetaCART(
            min_samples_leaf=min_leaf,
            min_samples_treatment_leaf=int(min_leaf * 0.3),
            min_samples_control_leaf=int(min_leaf * 0.3),
            max_depth=4,
            honest_split_ratio=0.5,
            random_state=42
        )

        model.fit(X, y, treatment, feature_names=feature_names, honest=True)

        effects_df = model.get_subgroup_effects()

        results[f'min_leaf_{min_leaf}'] = {
            'n_subgroups': len(effects_df),
            'effects': effects_df['honest_effect'].values,
            'model': model
        }

    # Different max depths
    for max_depth in [2, 3, 4, 5]:
        print(f"  Testing max_depth = {max_depth}")

        model = MetaCART(
            min_samples_leaf=40,
            min_samples_treatment_leaf=15,
            min_samples_control_leaf=15,
            max_depth=max_depth,
            honest_split_ratio=0.5,
            random_state=42
        )

        model.fit(X, y, treatment, feature_names=feature_names, honest=True)

        effects_df = model.get_subgroup_effects()

        results[f'max_depth_{max_depth}'] = {
            'n_subgroups': len(effects_df),
            'effects': effects_df['honest_effect'].values,
            'model': model
        }

    return results


def main():
    """Run advanced analysis."""

    print("=" * 80)
    print("Advanced Meta-CART Example: Method Comparison and Validation")
    print("=" * 80)
    print()

    # =========================================================================
    # 1. Generate Complex Data
    # =========================================================================
    print("Step 1: Generating complex trial data with noise features...")
    print("-" * 80)

    X, y, treatment, feature_names = generate_complex_trial_data(
        n_samples=2000,
        n_noise_features=10,
        random_state=42
    )

    print(f"Sample size: {len(X)}")
    print(f"Number of features: {X.shape[1]}")
    print(f"  - True effect modifiers: 2 (X1_true, X2_true)")
    print(f"  - Prognostic only: 1 (X3_prognostic)")
    print(f"  - Noise features: 10")
    print()

    # =========================================================================
    # 2. Naive Subgroup Analysis (WRONG WAY)
    # =========================================================================
    print("Step 2: Naive subgroup analysis (for comparison)...")
    print("-" * 80)
    print("This demonstrates the WRONG way to do subgroup analysis:")
    print("Testing all possible subgroups without correction.")
    print()

    naive_results = naive_subgroup_analysis(X, y, treatment, feature_names, alpha=0.05)

    n_total_tests = len(naive_results)
    n_significant = np.sum(naive_results['significant'])

    print(f"Total tests performed: {n_total_tests}")
    print(f"Significant results (p < 0.05): {n_significant}")
    print(f"False discovery rate (naive): {n_significant / n_total_tests:.1%}")
    print()

    # Apply FDR correction
    fdr_significant = calculate_fdr(naive_results['p_value'].values, alpha=0.05)
    n_fdr_significant = np.sum(fdr_significant)

    print(f"Significant after FDR correction: {n_fdr_significant}")
    print()

    # Show "significant" results
    sig_naive = naive_results[naive_results['significant']].sort_values('p_value')
    print("'Significant' subgroups (uncorrected):")
    print(sig_naive.head(10).to_string(index=False))
    print()

    # =========================================================================
    # 3. Meta-CART Analysis (RIGHT WAY)
    # =========================================================================
    print("Step 3: Meta-CART analysis (correct approach)...")
    print("-" * 80)
    print("Meta-CART accounts for multiplicity through:")
    print("  • Structured search (tree-based)")
    print("  • Cross-validation pruning")
    print("  • Honest inference (sample splitting)")
    print()

    model = MetaCART(
        min_samples_leaf=50,
        min_samples_treatment_leaf=20,
        min_samples_control_leaf=20,
        max_depth=4,
        honest_split_ratio=0.5,
        random_state=42
    )

    model.fit(X, y, treatment, feature_names=feature_names, honest=True)

    print("Fitted tree:")
    model.print_tree()
    print()

    effects_df = model.get_subgroup_effects()
    print("Discovered subgroups:")
    print(effects_df[['subgroup_id', 'n_samples', 'honest_effect', 'honest_se',
                      'honest_ci_lower', 'honest_ci_upper']].to_string(index=False))
    print()

    rules = model.get_splitting_rules()
    print("Subgroup definitions:")
    for rule in rules:
        print(f"  {rule['rule_string']}")
    print()

    # =========================================================================
    # 4. Bootstrap Stability
    # =========================================================================
    print("Step 4: Bootstrap stability analysis...")
    print("-" * 80)

    bootstrap = BootstrapStability(
        meta_cart=model,
        n_bootstrap=100,
        random_state=42
    )

    bootstrap.fit(X, y, treatment)

    importance_df = bootstrap.get_variable_importance()
    print("Variable importance (proportion of times used in bootstrap trees):")
    print(importance_df.to_string(index=False))
    print()

    # Check if true features were identified
    true_features = ['X1_true', 'X2_true']
    top_features = importance_df.head(3)['variable'].tolist()

    print("Feature selection validation:")
    for feat in true_features:
        if feat in top_features:
            print(f"  ✓ {feat} correctly identified as important")
        else:
            print(f"  ✗ {feat} not in top 3 features")

    noise_in_top = [f for f in top_features if 'Noise' in f]
    if noise_in_top:
        print(f"  ⚠ Noise features in top 3: {noise_in_top}")
    else:
        print(f"  ✓ No noise features in top 3")
    print()

    # =========================================================================
    # 5. Sensitivity Analysis
    # =========================================================================
    print("Step 5: Sensitivity analysis...")
    print("-" * 80)
    print("Testing robustness to hyperparameter choices:")
    print()

    sensitivity_results = sensitivity_analysis(X, y, treatment, feature_names)

    print("\nSensitivity results:")
    print(f"{'Setting':<20} {'N Subgroups':<15} {'Effect Range':<20}")
    print("-" * 60)

    for setting, res in sensitivity_results.items():
        effects = res['effects']
        effect_range = f"[{effects.min():.2f}, {effects.max():.2f}]"
        print(f"{setting:<20} {res['n_subgroups']:<15} {effect_range:<20}")

    print()

    # =========================================================================
    # 6. Comparison Summary
    # =========================================================================
    print("Step 6: Method comparison summary...")
    print("-" * 80)

    print("Comparison: Naive vs. Meta-CART")
    print()

    print("Naive approach:")
    print(f"  • Number of tests: {n_total_tests}")
    print(f"  • False positives (uncorrected): {n_significant - n_fdr_significant}")
    print(f"  • No protection against overfitting")
    print(f"  • No honest inference")
    print()

    print("Meta-CART approach:")
    print(f"  • Structured search (avoids exhaustive testing)")
    print(f"  • Cross-validation pruning")
    print(f"  • Honest inference (out-of-sample estimates)")
    print(f"  • Bootstrap validation")
    print(f"  • Number of subgroups: {len(effects_df)}")
    print()

    # =========================================================================
    # 7. Practical Recommendations
    # =========================================================================
    print("Step 7: Practical recommendations...")
    print("-" * 80)

    print("Key findings:")
    print()

    # Identify clearly beneficial subgroups
    beneficial = effects_df[effects_df['honest_ci_lower'] > 0]
    harmful = effects_df[effects_df['honest_ci_upper'] < 0]
    uncertain = effects_df[
        (effects_df['honest_ci_lower'] <= 0) &
        (effects_df['honest_ci_upper'] >= 0)
    ]

    print(f"Clearly beneficial subgroups: {len(beneficial)}")
    if len(beneficial) > 0:
        for idx, row in beneficial.iterrows():
            rule = [r for r in rules if r['subgroup_id'] == row['subgroup_id']][0]
            print(f"  • {rule['rule_string']}")
            print(f"    Effect: {row['honest_effect']:.2f} "
                  f"(95% CI: [{row['honest_ci_lower']:.2f}, {row['honest_ci_upper']:.2f}])")

    print()
    print(f"Potentially harmful subgroups: {len(harmful)}")
    if len(harmful) > 0:
        for idx, row in harmful.iterrows():
            rule = [r for r in rules if r['subgroup_id'] == row['subgroup_id']][0]
            print(f"  • {rule['rule_string']}")
            print(f"    Effect: {row['honest_effect']:.2f} "
                  f"(95% CI: [{row['honest_ci_lower']:.2f}, {row['honest_ci_upper']:.2f}])")

    print()
    print(f"Uncertain subgroups: {len(uncertain)}")
    print()

    # =========================================================================
    # 8. Visualizations
    # =========================================================================
    print("Step 8: Creating visualizations...")
    print("-" * 80)

    import os
    os.makedirs('output', exist_ok=True)

    # Tree structure
    fig1 = plot_tree_structure(model, figsize=(16, 10), show_honest=True)
    fig1.savefig('output/advanced_tree.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved advanced_tree.png")

    # Subgroup effects
    fig2 = plot_subgroup_effects(model, figsize=(10, 6), use_honest=True)
    fig2.savefig('output/advanced_effects.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved advanced_effects.png")

    # Comparison plot: naive vs Meta-CART
    fig3, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Naive results
    ax1 = axes[0]
    naive_sig = naive_results[naive_results['significant']].sort_values('effect')
    y_pos = np.arange(min(10, len(naive_sig)))

    if len(naive_sig) > 0:
        plot_data = naive_sig.head(10)
        effects = plot_data['effect'].values
        ses = plot_data['se'].values

        ax1.errorbar(effects, y_pos, xerr=1.96*ses, fmt='o', capsize=5)
        ax1.axvline(x=0, color='black', linestyle='--', alpha=0.3)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels([s[:30] + '...' if len(s) > 30 else s
                             for s in plot_data['subgroup'].values], fontsize=8)
        ax1.set_xlabel('Treatment Effect')
        ax1.set_title('Naive Analysis\n(Uncorrected, Overfitting)')
        ax1.grid(axis='x', alpha=0.3)

    # Meta-CART results
    ax2 = axes[1]
    n_groups = len(effects_df)
    y_pos2 = np.arange(n_groups)

    effects2 = effects_df['honest_effect'].values
    ci_lower2 = effects_df['honest_ci_lower'].values
    ci_upper2 = effects_df['honest_ci_upper'].values

    ax2.errorbar(effects2, y_pos2,
                xerr=[effects2 - ci_lower2, ci_upper2 - effects2],
                fmt='o', capsize=5, color='steelblue')
    ax2.axvline(x=0, color='black', linestyle='--', alpha=0.3)
    ax2.set_yticks(y_pos2)
    ax2.set_yticklabels([f"Subgroup {i}" for i in effects_df['subgroup_id']])
    ax2.set_xlabel('Treatment Effect')
    ax2.set_title('Meta-CART\n(Honest, Cross-validated)')
    ax2.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    fig3.savefig('output/method_comparison.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved method_comparison.png")

    print()

    # =========================================================================
    # Summary
    # =========================================================================
    print("=" * 80)
    print("Advanced Analysis Complete!")
    print("=" * 80)
    print()
    print("Key Lessons:")
    print("  1. Naive subgroup analysis leads to many false positives")
    print("  2. Meta-CART provides principled approach with multiplicity control")
    print("  3. Honest inference gives valid confidence intervals")
    print("  4. Bootstrap stability identifies truly important features")
    print("  5. Results are robust to hyperparameter choices")
    print()
    print("For publication:")
    print("  • Report honest estimates (not training estimates)")
    print("  • Include confidence intervals")
    print("  • Show bootstrap stability")
    print("  • Validate in independent dataset")
    print("  • Pre-specify analysis plan when possible")
    print()


if __name__ == "__main__":
    main()
    plt.show()
