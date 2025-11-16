"""
Real Data Example: Meta-CART on IHDP Dataset
==============================================

Demonstrates Meta-CART V3.2 on the Infant Health and Development Program (IHDP)
dataset, a well-known benchmark for causal inference methods.

Dataset:
- IHDP: Randomized trial of educational intervention for low birth weight infants
- n ≈ 747 observations
- Treatment: Intensive early intervention
- Outcome: Cognitive test scores at age 3
- Covariates: Demographics, birth characteristics

This example uses a simulated version of IHDP with known treatment effect
heterogeneity, commonly used for benchmarking causal inference methods.

References:
- Hill (2011): Bayesian Nonparametric Modeling for Causal Inference, JCGS
- Used in: Wager & Athey (2018), Künzel et al. (2019)
"""

import numpy as np
import pandas as pd
import time

# Note: This is a simulated IHDP-like dataset for demonstration
# Real IHDP data available from: https://github.com/AMLab-Amsterdam/CEVAE


def generate_ihdp_simulation(n=747, seed=42):
    """
    Generate IHDP-like simulated data with known heterogeneity.
    
    Based on the IHDP simulation framework from Hill (2011).
    """
    np.random.seed(seed)
    
    # Covariates (simplified version)
    # X1: Mother's age (years)
    mother_age = np.random.normal(25, 5, n)
    mother_age = np.clip(mother_age, 15, 45)
    
    # X2: Birth weight (grams)
    birth_weight = np.random.normal(2500, 500, n)
    birth_weight = np.clip(birth_weight, 500, 4000)
    
    # X3: Gestational age (weeks)
    gestational_age = np.random.normal(37, 3, n)
    gestational_age = np.clip(gestational_age, 24, 42)
    
    # X4: Mother's education (years)
    mother_edu = np.random.poisson(12, n)
    mother_edu = np.clip(mother_edu, 8, 18)
    
    # X5: Number of previous children
    num_children = np.random.poisson(1, n)
    num_children = np.clip(num_children, 0, 5)
    
    X = np.column_stack([
        mother_age,
        birth_weight / 1000,  # Scale to kg
        gestational_age,
        mother_edu,
        num_children
    ])
    
    feature_names = [
        'mother_age',
        'birth_weight_kg',
        'gestational_age_weeks',
        'mother_education_years',
        'num_previous_children'
    ]
    
    # Treatment assignment (randomized in IHDP)
    treatment = np.random.binomial(1, 0.5, n)
    
    # Outcome: Cognitive test score
    # True heterogeneity: Effect larger for lower birth weight and lower maternal education
    
    # Baseline (no treatment)
    baseline = (
        80 +  # Baseline score
        0.5 * mother_age +
        5.0 * (birth_weight / 1000) +  # Higher birth weight -> higher score
        1.0 * gestational_age +
        2.0 * mother_edu +
        -1.0 * num_children
    )
    
    # Treatment effect (heterogeneous)
    # Larger effect for:
    # - Lower birth weight (< 2.5 kg)
    # - Lower maternal education (< 12 years)
    
    low_birth_weight = (birth_weight < 2500).astype(float)
    low_education = (mother_edu < 12).astype(float)
    
    treatment_effect = (
        3.0 +  # Average treatment effect
        8.0 * low_birth_weight +  # Extra benefit for low birth weight
        5.0 * low_education  # Extra benefit for low education
    )
    
    # Observed outcome
    y = baseline + treatment * treatment_effect + np.random.normal(0, 5, n)
    
    return X, y, treatment, feature_names


def run_metacart_ihdp_example():
    """
    Run Meta-CART on IHDP-like data and report results.
    """
    print("="*70)
    print("Meta-CART V3.2: Real Data Example (IHDP Simulation)")
    print("="*70)
    print()
    
    # Generate data
    print("1. Generating IHDP-like data...")
    X, y, treatment, feature_names = generate_ihdp_simulation(n=747, seed=42)
    
    print(f"   Sample size: n = {len(X)}")
    print(f"   Features: p = {X.shape[1]}")
    print(f"   Treatment: {treatment.sum()} treated, {len(treatment) - treatment.sum()} control")
    print(f"   Outcome: mean = {y.mean():.2f}, std = {y.std():.2f}")
    print()
    
    # Known truth (for this simulation)
    print("2. Known treatment effect heterogeneity (simulation truth):")
    print("   - High-risk subgroup (low birth weight < 2.5kg): TE ≈ 11.0 points")
    print("   - Low education subgroup (< 12 years): TE ≈ 8.0 points")
    print("   - Standard subgroup: TE ≈ 3.0 points")
    print()
    
    # Fit Meta-CART
    print("3. Fitting Meta-CART with honest inference...")
    
    try:
        # Try to import - will fail if not in same directory
        from meta_cart_v3_1 import MetaCART
        
        start_time = time.time()
        
        model = MetaCART(
            min_samples_leaf=75,  # Conservative for n=747
            max_depth=3,
            use_cv_pruning=True,
            cv_folds=5,
            multiple_testing_method='fdr',  # Recommended for tree dependencies
            honest_split_ratio=0.5,
            random_state=42
        )
        
        model.fit(X, y, treatment, feature_names=feature_names, honest=True)
        
        elapsed = time.time() - start_time
        print(f"   Completed in {elapsed:.2f} seconds")
        print()
        
        # Display tree
        print("4. Discovered subgroup tree structure:")
        print("-" * 70)
        model.print_tree()
        print("-" * 70)
        print()
        
        # Get subgroup effects
        effects = model.get_subgroup_effects(use_adjusted=True)
        
        print("5. Subgroup treatment effects (with FDR correction):")
        print()
        print(effects[['subgroup_id', 'n_samples', 'n_treated', 'n_control',
                       'honest_effect', 'honest_se', 'honest_ci_lower', 
                       'honest_ci_upper', 'adjusted_p_value']].to_string(index=False))
        print()
        
        # Get splitting rules
        rules = model.get_splitting_rules()
        
        print("6. Subgroup definitions:")
        for rule in rules:
            print(f"   Subgroup {rule['subgroup_id']}: {rule['rule_string']}")
        print()
        
        # Summary
        print("7. Summary:")
        print(f"   - Found {len(effects)} subgroup(s)")
        print(f"   - Range of treatment effects: {effects['honest_effect'].min():.2f} to "
              f"{effects['honest_effect'].max():.2f}")
        
        # Check if found expected heterogeneity
        has_birth_weight_split = any('birth_weight' in r['rule_string'].lower() for r in rules)
        has_education_split = any('education' in r['rule_string'].lower() for r in rules)
        
        print()
        print("8. Validation against known truth:")
        print(f"   - Detected birth weight heterogeneity: {'YES ✓' if has_birth_weight_split else 'NO ✗'}")
        print(f"   - Detected education heterogeneity: {'YES ✓' if has_education_split else 'NO ✗'}")
        
        # Compare effect sizes
        if len(effects) > 1:
            print(f"   - Effect heterogeneity magnitude: {effects['honest_effect'].max() - effects['honest_effect'].min():.2f}")
            print(f"     (Expected: ~8-11 points)")
        
        print()
        print("="*70)
        print("Example completed successfully!")
        print("="*70)
        
        return model, effects
        
    except ImportError:
        print("   ERROR: Could not import MetaCART.")
        print("   Make sure meta_cart_v3_1.py is in the same directory.")
        print()
        return None, None


if __name__ == '__main__':
    # Run example
    model, effects = run_metacart_ihdp_example()
    
    # Additional notes
    print()
    print("NOTES:")
    print("------")
    print("1. This uses a SIMULATED IHDP-like dataset for demonstration.")
    print("2. Real IHDP data available from: https://github.com/AMLab-Amsterdam/CEVAE")
    print("3. For production use, consider:")
    print("   - Larger sample sizes (n >= 1000) for stable subgroup discovery")
    print("   - Cross-validation of discovered subgroups on held-out data")
    print("   - Bootstrap stability analysis (see bootstrap.py)")
    print("4. Computational time: ~2-5 seconds for n=747, p=5")
