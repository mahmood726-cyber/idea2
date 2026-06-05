"""
Comprehensive Example: Meta-CART for Subgroup Discovery
========================================================

This example demonstrates the full Meta-CART workflow for identifying
treatment effect modifiers in a simulated clinical trial.

Scenario:
---------
We simulate a randomized clinical trial where:
- Treatment effect varies by patient characteristics
- Some subgroups benefit more than others
- Some subgroups may not benefit at all

The goal is to identify these subgroups in a statistically rigorous way.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # non-interactive backend: safe for headless import/use
import matplotlib.pyplot as plt
from meta_cart import MetaCART, BootstrapStability
from visualization import (
    plot_tree_structure,
    plot_subgroup_effects,
    plot_comparison_forest,
    plot_variable_importance,
    plot_diagnostic_panel
)


def generate_heterogeneous_trial_data(
    n_samples: int = 1000,
    random_state: int = 42
) -> tuple:
    """
    Generate synthetic trial data with heterogeneous treatment effects.

    The data generating process:
    - Age, biomarker, and disease severity are covariates
    - Treatment effect depends on biomarker and age:
      * High biomarker (>0.5) → large positive effect
      * Low biomarker + young age → moderate positive effect
      * Low biomarker + old age → no effect or negative effect
    - Additional noise from disease severity

    Parameters
    ----------
    n_samples : int
        Number of patients to simulate
    random_state : int
        Random seed

    Returns
    -------
    X : ndarray
        Covariate matrix (n_samples, n_features)
    y : ndarray
        Outcomes (n_samples,)
    treatment : ndarray
        Treatment assignment (n_samples,)
    feature_names : list
        Names of features
    """

    np.random.seed(random_state)

    # Generate covariates
    age = np.random.normal(60, 15, n_samples)
    age = np.clip(age, 18, 90)  # Age between 18-90

    biomarker = np.random.beta(2, 5, n_samples)  # Skewed distribution

    disease_severity = np.random.uniform(0, 10, n_samples)

    gender = np.random.binomial(1, 0.5, n_samples)  # Binary

    bmi = np.random.normal(27, 5, n_samples)
    bmi = np.clip(bmi, 15, 50)

    # Stack features
    X = np.column_stack([age, biomarker, disease_severity, gender, bmi])
    feature_names = ['Age', 'Biomarker', 'DiseaseSeverity', 'Gender', 'BMI']

    # Randomize treatment (1:1 randomization)
    treatment = np.random.binomial(1, 0.5, n_samples)

    # Generate outcomes with heterogeneous treatment effects
    # Baseline outcome (without treatment)
    y_baseline = (
        10 +
        0.1 * age +
        -5 * biomarker +
        0.5 * disease_severity +
        0.05 * bmi +
        np.random.normal(0, 2, n_samples)  # Noise
    )

    # Treatment effect (heterogeneous)
    treatment_effect = np.zeros(n_samples)

    # Subgroup 1: High biomarker → large positive effect
    mask1 = biomarker > 0.5
    treatment_effect[mask1] = 3.0 + np.random.normal(0, 0.5, np.sum(mask1))

    # Subgroup 2: Low biomarker + young age → moderate effect
    mask2 = (biomarker <= 0.5) & (age < 60)
    treatment_effect[mask2] = 1.5 + np.random.normal(0, 0.5, np.sum(mask2))

    # Subgroup 3: Low biomarker + old age → small or negative effect
    mask3 = (biomarker <= 0.5) & (age >= 60)
    treatment_effect[mask3] = -0.5 + np.random.normal(0, 0.5, np.sum(mask3))

    # Final outcome
    y = y_baseline + treatment * treatment_effect

    return X, y, treatment, feature_names


def main():
    """Run comprehensive Meta-CART analysis."""

    print("=" * 80)
    print("Meta-CART for Subgroup Discovery: Comprehensive Example")
    print("=" * 80)
    print()

    # =========================================================================
    # 1. Generate Data
    # =========================================================================
    print("Step 1: Generating synthetic clinical trial data...")
    print("-" * 80)

    X, y, treatment, feature_names = generate_heterogeneous_trial_data(
        n_samples=1000,
        random_state=42
    )

    n_treated = np.sum(treatment == 1)
    n_control = np.sum(treatment == 0)

    print(f"Total patients: {len(X)}")
    print(f"  Treated: {n_treated}")
    print(f"  Control: {n_control}")
    print(f"Features: {', '.join(feature_names)}")
    print()

    # Compute overall treatment effect (ATE)
    y_treated = y[treatment == 1]
    y_control = y[treatment == 0]
    ate = np.mean(y_treated) - np.mean(y_control)
    print(f"Average Treatment Effect (ATE): {ate:.3f}")
    print()

    # =========================================================================
    # 2. Fit Meta-CART
    # =========================================================================
    print("Step 2: Fitting Meta-CART with honest inference...")
    print("-" * 80)

    model = MetaCART(
        min_samples_leaf=40,
        min_samples_treatment_leaf=15,
        min_samples_control_leaf=15,
        max_depth=4,
        alpha=0.05,
        honest_split_ratio=0.5,
        random_state=42
    )

    model.fit(X, y, treatment, feature_names=feature_names, honest=True)

    print("Tree structure:")
    print("-" * 80)
    model.print_tree()
    print()

    # =========================================================================
    # 3. Analyze Subgroups
    # =========================================================================
    print("Step 3: Analyzing discovered subgroups...")
    print("-" * 80)

    # Get subgroup effects
    effects_df = model.get_subgroup_effects()
    print("Subgroup Treatment Effects:")
    print(effects_df.to_string(index=False))
    print()

    # Get splitting rules
    rules = model.get_splitting_rules()
    print("Subgroup Definitions:")
    for rule in rules:
        print(f"  Subgroup {rule['subgroup_id']}: {rule['rule_string']}")
    print()

    # =========================================================================
    # 4. Bootstrap Stability Analysis
    # =========================================================================
    print("Step 4: Running bootstrap stability analysis...")
    print("-" * 80)

    bootstrap = BootstrapStability(
        meta_cart=model,
        n_bootstrap=100,
        random_state=42
    )

    bootstrap.fit(X, y, treatment)

    # Variable importance
    importance_df = bootstrap.get_variable_importance()
    print("Variable Importance (from bootstrap):")
    print(importance_df.to_string(index=False))
    print()

    # =========================================================================
    # 5. Statistical Inference
    # =========================================================================
    print("Step 5: Statistical inference and hypothesis testing...")
    print("-" * 80)

    print("Testing for treatment effect heterogeneity:")
    print()

    # Test if effects differ across subgroups
    honest_effects = effects_df['honest_effect'].values
    honest_ses = effects_df['honest_se'].values

    # Global test: are all effects the same?
    # Using chi-squared test for heterogeneity (like in meta-analysis)
    weights = 1 / (honest_ses ** 2)
    weighted_mean = np.sum(weights * honest_effects) / np.sum(weights)

    Q = np.sum(weights * (honest_effects - weighted_mean) ** 2)
    df = len(honest_effects) - 1

    from scipy.stats import chi2
    p_heterogeneity = 1 - chi2.cdf(Q, df)

    print(f"Test for heterogeneity:")
    print(f"  Q statistic: {Q:.3f}")
    print(f"  Degrees of freedom: {df}")
    print(f"  P-value: {p_heterogeneity:.4f}")

    if p_heterogeneity < 0.05:
        print("  → Significant heterogeneity detected! (p < 0.05)")
    else:
        print("  → No significant heterogeneity (p ≥ 0.05)")
    print()

    # Pairwise comparisons
    print("Pairwise comparisons between subgroups:")
    n_subgroups = len(effects_df)

    for i in range(n_subgroups):
        for j in range(i + 1, n_subgroups):
            effect_i = honest_effects[i]
            effect_j = honest_effects[j]
            se_i = honest_ses[i]
            se_j = honest_ses[j]

            diff = effect_i - effect_j
            se_diff = np.sqrt(se_i**2 + se_j**2)

            if se_diff > 0:
                z_stat = diff / se_diff
                from scipy.stats import norm
                p_val = 2 * (1 - norm.cdf(abs(z_stat)))

                sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"

                print(f"  Subgroup {i} vs {j}: diff = {diff:.3f}, "
                      f"SE = {se_diff:.3f}, p = {p_val:.4f} {sig}")

    print()

    # =========================================================================
    # 6. Visualizations
    # =========================================================================
    print("Step 6: Creating visualizations...")
    print("-" * 80)

    # Create output directory for figures
    import os
    os.makedirs('output', exist_ok=True)

    # Tree structure
    fig1 = plot_tree_structure(model, figsize=(16, 10), show_honest=True)
    fig1.savefig('output/tree_structure.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved tree_structure.png")

    # Subgroup effects
    fig2 = plot_subgroup_effects(model, figsize=(10, 6), use_honest=True)
    fig2.savefig('output/subgroup_effects.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved subgroup_effects.png")

    # Forest plot
    fig3 = plot_comparison_forest(model, figsize=(10, 8), use_honest=True)
    fig3.savefig('output/forest_plot.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved forest_plot.png")

    # Variable importance
    fig4 = plot_variable_importance(bootstrap, figsize=(10, 6))
    fig4.savefig('output/variable_importance.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved variable_importance.png")

    # Diagnostic panel
    fig5 = plot_diagnostic_panel(model, X, y, treatment, figsize=(16, 12))
    fig5.savefig('output/diagnostic_panel.png', dpi=300, bbox_inches='tight')
    print("  ✓ Saved diagnostic_panel.png")

    print()
    print("All figures saved to 'output/' directory")
    print()

    # =========================================================================
    # 7. Clinical Interpretation
    # =========================================================================
    print("Step 7: Clinical interpretation and recommendations...")
    print("-" * 80)

    print("Summary of Findings:")
    print()

    # Identify best and worst subgroups
    best_idx = effects_df['honest_effect'].idxmax()
    worst_idx = effects_df['honest_effect'].idxmin()

    best_subgroup = effects_df.loc[best_idx]
    worst_subgroup = effects_df.loc[worst_idx]

    best_rule = [r for r in rules if r['subgroup_id'] == best_subgroup['subgroup_id']][0]
    worst_rule = [r for r in rules if r['subgroup_id'] == worst_subgroup['subgroup_id']][0]

    print(f"✓ Best responding subgroup: Subgroup {best_subgroup['subgroup_id']}")
    print(f"  Definition: {best_rule['rule_string']}")
    print(f"  Treatment effect: {best_subgroup['honest_effect']:.3f} "
          f"(95% CI: [{best_subgroup['honest_ci_lower']:.3f}, "
          f"{best_subgroup['honest_ci_upper']:.3f}])")
    print(f"  Sample size: {best_subgroup['n_samples']}")
    print()

    print(f"✗ Worst responding subgroup: Subgroup {worst_subgroup['subgroup_id']}")
    print(f"  Definition: {worst_rule['rule_string']}")
    print(f"  Treatment effect: {worst_subgroup['honest_effect']:.3f} "
          f"(95% CI: [{worst_subgroup['honest_ci_lower']:.3f}, "
          f"{worst_subgroup['honest_ci_upper']:.3f}])")
    print(f"  Sample size: {worst_subgroup['n_samples']}")
    print()

    # Clinical recommendations
    print("Clinical Recommendations:")
    for idx, row in effects_df.iterrows():
        rule = [r for r in rules if r['subgroup_id'] == row['subgroup_id']][0]

        effect = row['honest_effect']
        ci_lower = row['honest_ci_lower']
        ci_upper = row['honest_ci_upper']

        if ci_lower > 0:
            recommendation = "TREAT - Clear benefit"
        elif ci_upper < 0:
            recommendation = "DO NOT TREAT - Potential harm"
        elif effect > 0 and ci_upper > 0:
            recommendation = "CONSIDER TREATMENT - Possible benefit"
        else:
            recommendation = "UNCERTAIN - More data needed"

        print(f"  Subgroup {row['subgroup_id']}: {recommendation}")
        print(f"    ({rule['rule_string']})")

    print()

    # =========================================================================
    # 8. Model Validation Metrics
    # =========================================================================
    print("Step 8: Model validation and quality metrics...")
    print("-" * 80)

    # Check sample sizes
    min_samples = effects_df['n_samples'].min()
    print(f"Minimum subgroup size: {min_samples}")

    if min_samples < 30:
        print("  ⚠ Warning: Small subgroup sizes may lead to unstable estimates")
    else:
        print("  ✓ All subgroups have adequate sample sizes")

    # Check treatment balance
    print()
    print("Treatment balance within subgroups:")
    for idx, row in effects_df.iterrows():
        ratio = row['n_treated'] / (row['n_treated'] + row['n_control'])
        print(f"  Subgroup {row['subgroup_id']}: {ratio:.2%} treated")

        if ratio < 0.3 or ratio > 0.7:
            print(f"    ⚠ Imbalanced")

    # Honest vs training estimates
    if 'honest_effect' in effects_df.columns:
        print()
        print("Comparison of training vs. honest estimates:")
        for idx, row in effects_df.iterrows():
            train_est = row['treatment_effect']
            honest_est = row['honest_effect']
            diff = abs(train_est - honest_est)
            print(f"  Subgroup {row['subgroup_id']}: "
                  f"Training={train_est:.3f}, Honest={honest_est:.3f}, "
                  f"Diff={diff:.3f}")

    print()

    # =========================================================================
    # Summary
    # =========================================================================
    print("=" * 80)
    print("Analysis Complete!")
    print("=" * 80)
    print()
    print("Key Takeaways:")
    print(f"  • Identified {len(effects_df)} distinct subgroups")
    print(f"  • Treatment effect heterogeneity: {'Significant' if p_heterogeneity < 0.05 else 'Not significant'}")
    print(f"  • Most important variable: {importance_df.iloc[0]['variable']}")
    print(f"  • Range of effects: [{effects_df['honest_effect'].min():.3f}, "
          f"{effects_df['honest_effect'].max():.3f}]")
    print()
    print("Next Steps:")
    print("  1. Review visualizations in 'output/' directory")
    print("  2. Validate findings in independent dataset")
    print("  3. Consider prospective validation trial")
    print("  4. Develop clinical decision support tool")
    print()


if __name__ == "__main__":
    main()

    # Keep plots open
    plt.show()
