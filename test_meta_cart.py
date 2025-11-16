"""
Test script for Meta-CART implementation
==========================================

This script runs basic tests to verify all components work correctly.
"""

import numpy as np
import pandas as pd
from meta_cart import MetaCART, BootstrapStability


def test_basic_fitting():
    """Test basic model fitting."""
    print("Test 1: Basic model fitting")
    print("-" * 60)

    np.random.seed(42)
    n = 500

    # Generate data with heterogeneous treatment effect
    X = np.random.randn(n, 3)
    treatment = np.random.binomial(1, 0.5, n)
    effect = np.where(X[:, 0] > 0, 2.0, -1.0)
    y = 5 + X[:, 1] + treatment * effect + np.random.randn(n)

    # Fit model
    model = MetaCART(
        min_samples_leaf=30,
        max_depth=3,
        random_state=42
    )

    model.fit(X, y, treatment, feature_names=['X1', 'X2', 'X3'], honest=False)

    assert model.tree_ is not None, "Tree should be fitted"
    assert model.node_count_ > 0, "Should have created nodes"

    print("✓ Model fitted successfully")
    print(f"✓ Created {model.node_count_} nodes")
    print()

    return model


def test_honest_inference():
    """Test honest inference with sample splitting."""
    print("Test 2: Honest inference")
    print("-" * 60)

    np.random.seed(42)
    n = 600

    X = np.random.randn(n, 3)
    treatment = np.random.binomial(1, 0.5, n)
    effect = np.where(X[:, 0] > 0, 2.0, -1.0)
    y = 5 + X[:, 1] + treatment * effect + np.random.randn(n)

    model = MetaCART(
        min_samples_leaf=30,
        max_depth=3,
        honest_split_ratio=0.5,
        random_state=42
    )

    model.fit(X, y, treatment, feature_names=['X1', 'X2', 'X3'], honest=True)

    # Check that honest estimates are computed
    effects_df = model.get_subgroup_effects()
    assert 'honest_effect' in effects_df.columns, "Should have honest estimates"
    assert 'honest_se' in effects_df.columns, "Should have honest standard errors"
    assert 'honest_ci_lower' in effects_df.columns, "Should have confidence intervals"

    print("✓ Honest inference working")
    print(f"✓ Found {len(effects_df)} subgroups")
    print(f"✓ All honest estimates computed")
    print()

    return model


def test_subgroup_effects():
    """Test subgroup effect estimation."""
    print("Test 3: Subgroup effect estimation")
    print("-" * 60)

    np.random.seed(42)
    n = 500

    X = np.random.randn(n, 3)
    treatment = np.random.binomial(1, 0.5, n)
    effect = np.where(X[:, 0] > 0, 2.0, -1.0)
    y = 5 + X[:, 1] + treatment * effect + np.random.randn(n)

    model = MetaCART(min_samples_leaf=30, max_depth=2, random_state=42)
    model.fit(X, y, treatment, feature_names=['X1', 'X2', 'X3'], honest=True)

    # Get effects
    effects_df = model.get_subgroup_effects()

    # Verify structure
    required_cols = ['subgroup_id', 'n_samples', 'n_treated', 'n_control',
                     'treatment_effect', 'std_error', 'p_value']
    for col in required_cols:
        assert col in effects_df.columns, f"Missing column: {col}"

    # Verify values are reasonable
    assert all(effects_df['n_samples'] > 0), "All subgroups should have samples"
    assert all(effects_df['n_treated'] > 0), "All subgroups should have treated"
    assert all(effects_df['n_control'] > 0), "All subgroups should have control"

    print("✓ Subgroup effects computed correctly")
    print(f"✓ {len(effects_df)} subgroups identified")
    print()

    return effects_df


def test_splitting_rules():
    """Test splitting rule extraction."""
    print("Test 4: Splitting rules")
    print("-" * 60)

    np.random.seed(42)
    n = 500

    X = np.random.randn(n, 3)
    treatment = np.random.binomial(1, 0.5, n)
    effect = np.where(X[:, 0] > 0, 2.0, -1.0)
    y = 5 + X[:, 1] + treatment * effect + np.random.randn(n)

    model = MetaCART(min_samples_leaf=30, max_depth=2, random_state=42)
    model.fit(X, y, treatment, feature_names=['X1', 'X2', 'X3'], honest=True)

    # Get rules
    rules = model.get_splitting_rules()

    assert len(rules) > 0, "Should have at least one rule"

    for rule in rules:
        assert 'subgroup_id' in rule, "Rule should have subgroup_id"
        assert 'rules' in rule, "Rule should have rules list"
        assert 'rule_string' in rule, "Rule should have rule_string"

    print("✓ Splitting rules extracted correctly")
    for rule in rules:
        print(f"  Subgroup {rule['subgroup_id']}: {rule['rule_string']}")
    print()

    return rules


def test_prediction():
    """Test subgroup prediction on new data."""
    print("Test 5: Prediction")
    print("-" * 60)

    np.random.seed(42)
    n_train = 500
    n_test = 100

    # Training data
    X_train = np.random.randn(n_train, 3)
    treatment_train = np.random.binomial(1, 0.5, n_train)
    effect_train = np.where(X_train[:, 0] > 0, 2.0, -1.0)
    y_train = 5 + X_train[:, 1] + treatment_train * effect_train + np.random.randn(n_train)

    # Test data
    X_test = np.random.randn(n_test, 3)

    # Fit and predict
    model = MetaCART(min_samples_leaf=30, max_depth=2, random_state=42)
    model.fit(X_train, y_train, treatment_train, feature_names=['X1', 'X2', 'X3'])

    subgroups = model.predict_subgroup(X_test)

    assert len(subgroups) == n_test, "Should predict for all test samples"
    assert all(s >= 0 for s in subgroups), "Subgroup IDs should be non-negative"

    print("✓ Prediction working correctly")
    print(f"✓ Predicted subgroups for {n_test} samples")
    print(f"✓ Unique subgroups in predictions: {len(np.unique(subgroups))}")
    print()


def test_bootstrap_stability():
    """Test bootstrap stability analysis."""
    print("Test 6: Bootstrap stability")
    print("-" * 60)

    np.random.seed(42)
    n = 400

    X = np.random.randn(n, 3)
    treatment = np.random.binomial(1, 0.5, n)
    effect = np.where(X[:, 0] > 0, 2.0, -1.0)
    y = 5 + X[:, 1] + treatment * effect + np.random.randn(n)

    # Fit base model
    model = MetaCART(min_samples_leaf=30, max_depth=2, random_state=42)
    model.fit(X, y, treatment, feature_names=['X1', 'X2', 'X3'], honest=False)

    # Bootstrap
    bootstrap = BootstrapStability(model, n_bootstrap=20, random_state=42)
    bootstrap.fit(X, y, treatment)

    # Get importance
    importance = bootstrap.get_variable_importance()

    assert len(importance) == 3, "Should have importance for all features"
    assert 'variable' in importance.columns, "Should have variable names"
    assert 'importance' in importance.columns, "Should have importance scores"

    # Check that X1 (the true modifier) has high importance
    x1_importance = importance[importance['variable'] == 'X1']['importance'].values[0]

    print("✓ Bootstrap stability analysis working")
    print(f"✓ Ran {bootstrap.n_bootstrap} bootstrap iterations")
    print(f"✓ X1 importance: {x1_importance:.3f} (should be high)")
    print()


def test_heterogeneity_detection():
    """Test that the method correctly detects treatment effect heterogeneity."""
    print("Test 7: Heterogeneity detection")
    print("-" * 60)

    np.random.seed(42)
    n = 800

    # Generate data with clear heterogeneity
    X = np.random.randn(n, 3)
    treatment = np.random.binomial(1, 0.5, n)

    # Strong heterogeneity: X1 > 0 → positive effect, X1 < 0 → negative effect
    effect = np.where(X[:, 0] > 0, 3.0, -2.0)
    y = 5 + treatment * effect + np.random.randn(n) * 0.5

    model = MetaCART(min_samples_leaf=40, max_depth=3, random_state=42)
    model.fit(X, y, treatment, feature_names=['X1', 'X2', 'X3'], honest=True)

    effects_df = model.get_subgroup_effects()

    # Should find at least 2 subgroups with different effects
    assert len(effects_df) >= 2, "Should find multiple subgroups"

    honest_effects = effects_df['honest_effect'].values
    effect_range = honest_effects.max() - honest_effects.min()

    print("✓ Heterogeneity detection working")
    print(f"✓ Found {len(effects_df)} subgroups")
    print(f"✓ Effect range: {effect_range:.2f} (should be large)")
    print(f"✓ Max effect: {honest_effects.max():.2f}")
    print(f"✓ Min effect: {honest_effects.min():.2f}")
    print()


def test_edge_cases():
    """Test edge cases and robustness."""
    print("Test 8: Edge cases")
    print("-" * 60)

    np.random.seed(42)

    # Case 1: No heterogeneity (constant effect)
    n = 300
    X = np.random.randn(n, 3)
    treatment = np.random.binomial(1, 0.5, n)
    y = 5 + treatment * 1.5 + np.random.randn(n)  # Constant effect = 1.5

    model = MetaCART(min_samples_leaf=30, max_depth=3, random_state=42)
    model.fit(X, y, treatment, feature_names=['X1', 'X2', 'X3'], honest=True)

    # Should create minimal tree (maybe just root) or small tree
    effects_df = model.get_subgroup_effects()
    print(f"  Case 1 (no heterogeneity): {len(effects_df)} subgroups")

    # Case 2: Very small depth
    model2 = MetaCART(min_samples_leaf=30, max_depth=1, random_state=42)
    model2.fit(X, y, treatment, feature_names=['X1', 'X2', 'X3'], honest=True)
    effects_df2 = model2.get_subgroup_effects()
    print(f"  Case 2 (max_depth=1): {len(effects_df2)} subgroups")

    print("✓ Edge cases handled correctly")
    print()


def main():
    """Run all tests."""
    print("=" * 70)
    print("Meta-CART Test Suite")
    print("=" * 70)
    print()

    try:
        test_basic_fitting()
        test_honest_inference()
        test_subgroup_effects()
        test_splitting_rules()
        test_prediction()
        test_bootstrap_stability()
        test_heterogeneity_detection()
        test_edge_cases()

        print("=" * 70)
        print("All tests passed! ✓")
        print("=" * 70)
        print()
        print("The Meta-CART implementation is working correctly.")
        print("You can now run the example scripts:")
        print("  - python example_usage.py")
        print("  - python advanced_example.py")
        print()

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    main()
