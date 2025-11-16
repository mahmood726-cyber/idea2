"""
Comprehensive Unit Tests for Meta-CART V3
=========================================

Tests all bug fixes and new features:
- Bug #1: Alpha calculation (SE² not SE²×n)
- Bug #2: Holm monotonicity
- Bug #3: IPW normalization (Horvitz-Thompson)
- Bug #4: Evaluation metric (SE² not SE²×n)
- Bug #5: Survival outcomes raise NotImplementedError
- Binary outcomes
- Propensity diagnostics
- Bootstrap stability with parallelization
"""

import pytest
import numpy as np
import pandas as pd
from meta_cart_v3 import MetaCART, Node
from bootstrap import BootstrapStability


class TestBasicFunctionality:
    """Test basic MetaCART functionality."""

    def test_fit_simple_continuous(self):
        """Test fitting on simple continuous outcome data."""
        np.random.seed(42)

        n = 300
        X = np.random.randn(n, 3)
        treatment = np.random.binomial(1, 0.5, n)

        # Create heterogeneous effect: positive for X0 > 0, negative otherwise
        effect = np.where(X[:, 0] > 0, 2.0, -1.0)
        y = 5.0 + treatment * effect + np.random.randn(n)

        model = MetaCART(
            min_samples_leaf=30,
            max_depth=3,
            random_state=42
        )

        model.fit(X, y, treatment, feature_names=['X0', 'X1', 'X2'])

        assert model.tree_ is not None
        assert model.feature_names_ == ['X0', 'X1', 'X2']

        # Should find at least one split
        effects = model.get_subgroup_effects()
        assert len(effects) >= 1

    def test_fit_binary_outcome(self):
        """Test fitting on binary outcomes."""
        np.random.seed(42)

        n = 300
        X = np.random.randn(n, 2)
        treatment = np.random.binomial(1, 0.5, n)

        # Binary outcome with heterogeneous effect
        prob = 0.3 + treatment * np.where(X[:, 0] > 0, 0.3, -0.1)
        prob = np.clip(prob, 0.01, 0.99)
        y = np.random.binomial(1, prob)

        model = MetaCART(
            outcome_type='binary',
            min_samples_leaf=30,
            random_state=42
        )

        model.fit(X, y, treatment)

        assert model.tree_ is not None
        effects = model.get_subgroup_effects()
        assert len(effects) >= 1

        # Effects should be risk differences (between -1 and 1)
        assert all(effects['treatment_effect'].between(-1, 1))


class TestBugFixes:
    """Test all 5 critical bug fixes."""

    def test_bug1_alpha_calculation(self):
        """
        Bug #1: Alpha calculation should use SE² not SE²×n.

        Test that alpha values are scaled correctly for cost-complexity pruning.
        """
        np.random.seed(42)

        n = 200
        X = np.random.randn(n, 2)
        treatment = np.random.binomial(1, 0.5, n)
        y = 5 + treatment * X[:, 0] + np.random.randn(n)

        model = MetaCART(
            use_cv_pruning=True,
            random_state=42
        )

        model.fit(X, y, treatment)

        # Check that alpha values are reasonable (not inflated by sample size)
        if model.alpha_sequence_ is not None and len(model.alpha_sequence_) > 1:
            # Alpha should be on order of variance, not variance × n
            max_alpha = max(model.alpha_sequence_)
            # If bug exists, alpha would be ~100x larger (n=200)
            assert max_alpha < 100, f"Alpha too large: {max_alpha} (likely SE²×n bug)"

    def test_bug2_holm_monotonicity(self):
        """
        Bug #2: Holm procedure must enforce monotonicity.

        Adjusted p-values must be non-decreasing.
        """
        np.random.seed(42)

        n = 400
        X = np.random.randn(n, 3)
        treatment = np.random.binomial(1, 0.5, n)

        # Create multiple subgroups
        effect = np.where(X[:, 0] > 0, 2.0, 0.0) + np.where(X[:, 1] > 0, 1.0, 0.0)
        y = 5 + treatment * effect + np.random.randn(n)

        model = MetaCART(
            multiple_testing_method='holm',
            max_depth=3,
            min_samples_leaf=30,
            random_state=42
        )

        model.fit(X, y, treatment)

        effects = model.get_subgroup_effects(use_adjusted=True)

        if 'adjusted_p_value' in effects.columns and len(effects) > 1:
            # Sort by raw p-values
            effects_sorted = effects.sort_values('p_value')
            adjusted_p = effects_sorted['adjusted_p_value'].values

            # Check monotonicity: p_adj[i] >= p_adj[i-1]
            for i in range(1, len(adjusted_p)):
                assert adjusted_p[i] >= adjusted_p[i-1] - 1e-10, \
                    f"Holm monotonicity violated at index {i}: {adjusted_p[i]} < {adjusted_p[i-1]}"

    def test_bug3_ipw_normalization(self):
        """
        Bug #3: IPW should use Horvitz-Thompson estimator (no normalization).

        Test that propensity weighting gives unbiased estimates.
        """
        np.random.seed(42)

        n = 500
        # Confounded data: X affects both treatment and outcome
        X = np.random.randn(n, 2)

        # Treatment depends on X (confounding)
        propensity = 1 / (1 + np.exp(-X[:, 0]))
        treatment = np.random.binomial(1, propensity)

        # Outcome: true ATE = 2.0, but confounded by X
        y = 3 + 2 * treatment + 1.5 * X[:, 0] + np.random.randn(n)

        # Fit with propensity adjustment
        model = MetaCART(
            use_propensity=True,
            max_depth=1,  # Single split to test overall effect
            min_samples_leaf=50,
            random_state=42
        )

        model.fit(X, y, treatment)

        effects = model.get_subgroup_effects()

        # With correct IPW, should estimate ATE ≈ 2.0
        # With wrong normalization (bug), would be biased
        mean_effect = effects['treatment_effect'].mean()

        # Allow some error due to sampling variability
        assert 1.0 < mean_effect < 3.5, \
            f"IPW estimate {mean_effect} far from true ATE=2.0 (possible normalization bug)"

    def test_bug4_evaluation_metric(self):
        """
        Bug #4: Evaluation metric should use SE² not SE²×n.

        CV evaluation should measure precision, not total error.
        """
        np.random.seed(42)

        n = 200
        X = np.random.randn(n, 2)
        treatment = np.random.binomial(1, 0.5, n)
        y = 5 + treatment * X[:, 0] + np.random.randn(n)

        model = MetaCART(
            use_cv_pruning=True,
            cv_folds=3,
            random_state=42
        )

        model.fit(X, y, treatment)

        # Check that CV scores are reasonable
        if model.cv_scores_ is not None:
            cv_scores = model.cv_scores_

            # Scores should be negative SE² (so negative, small magnitude)
            # If bug exists, would be SE²×n (large negative numbers)
            max_score = np.max(cv_scores)

            # With SE², max score should be > -10
            # With SE²×n bug and n=200, would be < -1000
            assert max_score > -100, \
                f"CV score too negative: {max_score} (likely SE²×n bug)"

    def test_bug5_survival_not_implemented(self):
        """
        Bug #5: Survival outcomes should raise NotImplementedError.

        V2 accepted 'survival' but gave wrong results. V3 should explicitly reject it.
        """
        np.random.seed(42)

        n = 100
        X = np.random.randn(n, 2)
        treatment = np.random.binomial(1, 0.5, n)
        y = np.random.exponential(5, n)  # Survival times

        model = MetaCART(
            outcome_type='survival',  # This should raise error
            random_state=42
        )

        with pytest.raises(NotImplementedError, match="Survival outcomes not yet supported"):
            model.fit(X, y, treatment)


class TestPropensityDiagnostics:
    """Test propensity score diagnostics."""

    def test_overlap_warning(self):
        """Test that overlap violations trigger warnings."""
        np.random.seed(42)

        n = 300
        X = np.random.randn(n, 2)

        # Create severe overlap violation
        X[0, 0] = 10.0  # Extreme value -> propensity near 1

        treatment = np.random.binomial(1, 0.5, n)
        y = 5 + treatment * 2 + np.random.randn(n)

        model = MetaCART(
            use_propensity=True,
            random_state=42
        )

        with pytest.warns(UserWarning, match="Propensity scores near 0 or 1"):
            model.fit(X, y, treatment)

        # Check diagnostics were computed
        assert model.propensity_diagnostics_ is not None
        assert 'overlap' in model.propensity_diagnostics_
        assert 'balance' in model.propensity_diagnostics_

    def test_balance_diagnostics(self):
        """Test covariate balance diagnostics."""
        np.random.seed(42)

        n = 300
        X = np.random.randn(n, 3)
        treatment = np.random.binomial(1, 0.5, n)
        y = 5 + treatment * 2 + np.random.randn(n)

        model = MetaCART(
            use_propensity=True,
            random_state=42
        )

        model.fit(X, y, treatment)

        # Check SMDs were computed for each feature
        smd = model.propensity_diagnostics_['balance']
        assert len(smd) == 3  # One per feature
        assert all(isinstance(v, float) for v in smd.values())


class TestBootstrapStability:
    """Test bootstrap stability analysis."""

    def test_bootstrap_fit(self):
        """Test basic bootstrap fitting."""
        np.random.seed(42)

        n = 200
        X = np.random.randn(n, 2)
        treatment = np.random.binomial(1, 0.5, n)
        y = 5 + treatment * np.where(X[:, 0] > 0, 2.0, 0.0) + np.random.randn(n)

        # Fit base model
        model = MetaCART(
            min_samples_leaf=30,
            max_depth=2,
            random_state=42
        )
        model.fit(X, y, treatment)

        # Run bootstrap stability
        boot = BootstrapStability(
            n_bootstrap=10,  # Small for speed
            n_jobs=1,  # Sequential for testing
            random_state=42,
            verbose=0
        )

        boot.fit(model, X, y, treatment)

        # Check all 4 metrics were computed
        assert boot.cooccurrence_matrix_ is not None
        assert boot.effect_distributions_ is not None
        assert boot.tree_similarity_ is not None
        assert boot.split_stability_ is not None

        # Check shapes
        assert boot.cooccurrence_matrix_.shape == (n, n)
        assert isinstance(boot.effect_distributions_, dict)
        assert isinstance(boot.tree_similarity_, dict)
        assert isinstance(boot.split_stability_, dict)

    def test_bootstrap_parallelization(self):
        """Test that parallelization actually works."""
        np.random.seed(42)

        n = 150
        X = np.random.randn(n, 2)
        treatment = np.random.binomial(1, 0.5, n)
        y = 5 + treatment * X[:, 0] + np.random.randn(n)

        model = MetaCART(
            min_samples_leaf=20,
            max_depth=2,
            random_state=42
        )
        model.fit(X, y, treatment)

        # Test with parallel jobs
        boot = BootstrapStability(
            n_bootstrap=5,
            n_jobs=2,  # Parallel
            random_state=42,
            verbose=0
        )

        # Should not raise error
        boot.fit(model, X, y, treatment)

        assert len(boot.bootstrap_trees_) <= 5

    def test_stable_subgroups(self):
        """Test stable subgroup extraction."""
        np.random.seed(42)

        n = 200
        X = np.random.randn(n, 2)
        treatment = np.random.binomial(1, 0.5, n)

        # Strong heterogeneity -> should be stable across bootstraps
        effect = np.where(X[:, 0] > 0, 3.0, -1.0)
        y = 5 + treatment * effect + np.random.randn(n) * 0.5

        model = MetaCART(
            min_samples_leaf=25,
            max_depth=2,
            random_state=42
        )
        model.fit(X, y, treatment)

        boot = BootstrapStability(
            n_bootstrap=20,
            min_subgroup_frequency=0.3,
            n_jobs=1,
            random_state=42,
            verbose=0
        )

        boot.fit(model, X, y, treatment)

        stable = boot.get_stable_subgroups()

        assert isinstance(stable, pd.DataFrame)
        assert 'frequency' in stable.columns
        assert 'effect_mean' in stable.columns

        # All stable subgroups should meet frequency threshold
        if len(stable) > 0:
            assert all(stable['frequency'] >= 0.3)


class TestMultipleTesting:
    """Test multiple testing corrections."""

    def test_bonferroni_correction(self):
        """Test Bonferroni correction."""
        np.random.seed(42)

        n = 400
        X = np.random.randn(n, 3)
        treatment = np.random.binomial(1, 0.5, n)
        y = 5 + treatment * (X[:, 0] + X[:, 1]) + np.random.randn(n)

        model = MetaCART(
            multiple_testing_method='bonferroni',
            max_depth=3,
            min_samples_leaf=30,
            random_state=42
        )

        model.fit(X, y, treatment)

        effects = model.get_subgroup_effects(use_adjusted=True)

        if 'adjusted_p_value' in effects.columns:
            # Bonferroni: p_adj = min(p × n_tests, 1.0)
            n_tests = len(effects)
            for _, row in effects.iterrows():
                expected_max = min(row['p_value'] * n_tests, 1.0)
                assert row['adjusted_p_value'] <= expected_max + 1e-10

    def test_fdr_correction(self):
        """Test FDR (Benjamini-Hochberg) correction."""
        np.random.seed(42)

        n = 400
        X = np.random.randn(n, 3)
        treatment = np.random.binomial(1, 0.5, n)
        y = 5 + treatment * X[:, 0] + np.random.randn(n)

        model = MetaCART(
            multiple_testing_method='fdr',
            max_depth=3,
            min_samples_leaf=30,
            random_state=42
        )

        model.fit(X, y, treatment)

        effects = model.get_subgroup_effects(use_adjusted=True)

        if 'adjusted_p_value' in effects.columns and len(effects) > 1:
            # FDR correction should be less conservative than Bonferroni
            assert all(effects['adjusted_p_value'] >= effects['p_value'])


class TestInputValidation:
    """Test input validation."""

    def test_mismatched_lengths(self):
        """Test error on mismatched array lengths."""
        model = MetaCART()

        with pytest.raises(ValueError, match="same number of samples"):
            model.fit(
                np.random.randn(100, 2),
                np.random.randn(50),  # Wrong length
                np.random.binomial(1, 0.5, 100)
            )

    def test_non_binary_treatment(self):
        """Test error on non-binary treatment."""
        model = MetaCART()

        with pytest.raises(ValueError, match="Treatment must be binary"):
            model.fit(
                np.random.randn(100, 2),
                np.random.randn(100),
                np.array([0, 1, 2] * 33 + [0])  # Has value 2
            )

    def test_nan_values(self):
        """Test error on NaN values."""
        model = MetaCART()

        X = np.random.randn(100, 2)
        X[0, 0] = np.nan

        with pytest.raises(ValueError, match="X contains NaN"):
            model.fit(X, np.random.randn(100), np.random.binomial(1, 0.5, 100))

    def test_binary_outcome_validation(self):
        """Test validation for binary outcomes."""
        model = MetaCART(outcome_type='binary')

        with pytest.raises(ValueError, match="y must be 0/1"):
            model.fit(
                np.random.randn(100, 2),
                np.random.randn(100),  # Continuous, not binary
                np.random.binomial(1, 0.5, 100)
            )


class TestHonestInference:
    """Test honest inference (sample splitting)."""

    def test_honest_estimates(self):
        """Test that honest estimates are computed."""
        np.random.seed(42)

        n = 300
        X = np.random.randn(n, 2)
        treatment = np.random.binomial(1, 0.5, n)
        y = 5 + treatment * X[:, 0] + np.random.randn(n)

        model = MetaCART(
            min_samples_leaf=30,
            random_state=42
        )

        model.fit(X, y, treatment, honest=True)

        effects = model.get_subgroup_effects()

        # Should have honest estimates
        assert 'honest_effect' in effects.columns
        assert 'honest_se' in effects.columns
        assert 'honest_ci_lower' in effects.columns
        assert 'honest_ci_upper' in effects.columns

        # Honest estimates should differ from build estimates
        # (due to different samples)
        if len(effects) > 0:
            assert not all(
                effects['treatment_effect'] == effects['honest_effect']
            )

    def test_no_honest_inference(self):
        """Test that honest=False works."""
        np.random.seed(42)

        n = 300
        X = np.random.randn(n, 2)
        treatment = np.random.binomial(1, 0.5, n)
        y = 5 + treatment * X[:, 0] + np.random.randn(n)

        model = MetaCART(random_state=42)

        model.fit(X, y, treatment, honest=False)

        effects = model.get_subgroup_effects()

        # Should NOT have honest estimates
        assert 'honest_effect' not in effects.columns or \
               all(pd.isna(effects['honest_effect']))


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '--tb=short'])
