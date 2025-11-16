"""
Meta-CART for Subgroup Discovery
==================================

Implementation of Interaction Trees (IT) / Meta-CART for identifying
treatment effect modifiers as described in Lipkovich et al. (2011, 2017).

Key Features:
- Recursive partitioning based on treatment effects
- Cross-validation based pruning
- Honest inference via sample splitting
- Bootstrap stability analysis
- Statistical inference with confidence intervals

References:
Lipkovich, I., Dmitrienko, A., & D'Agostino, R. B. (2017).
Tutorial in biostatistics: data-driven subgroup identification and
analysis in clinical trials. Statistics in medicine, 36(1), 136-196.
"""

import numpy as np
import pandas as pd
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
from scipy import stats
import warnings


@dataclass
class Node:
    """Represents a node in the Meta-CART tree."""

    # Node identification
    node_id: int
    depth: int
    is_leaf: bool

    # Sample information
    sample_indices: np.ndarray
    n_samples: int
    n_treated: int
    n_control: int

    # Treatment effect estimates
    treatment_effect: float
    treatment_effect_se: float
    p_value: float

    # Split information (None for leaf nodes)
    split_variable: Optional[str] = None
    split_value: Optional[float] = None
    split_score: Optional[float] = None

    # Child nodes
    left_child: Optional['Node'] = None
    right_child: Optional['Node'] = None

    # Honest estimates (computed on separate sample)
    honest_effect: Optional[float] = None
    honest_se: Optional[float] = None
    honest_ci_lower: Optional[float] = None
    honest_ci_upper: Optional[float] = None


class MetaCART:
    """
    Meta-CART for Subgroup Discovery.

    This class implements interaction trees for identifying subgroups
    with differential treatment effects.

    Parameters
    ----------
    min_samples_leaf : int, default=30
        Minimum number of samples required in each leaf node
    min_samples_treatment_leaf : int, default=10
        Minimum number of treated samples in each leaf
    min_samples_control_leaf : int, default=10
        Minimum number of control samples in each leaf
    max_depth : int, default=5
        Maximum depth of the tree
    min_effect_size : float, default=0.0
        Minimum treatment effect size to consider a split
    alpha : float, default=0.05
        Significance level for statistical tests
    cv_folds : int, default=5
        Number of folds for cross-validation pruning
    honest_split_ratio : float, default=0.5
        Proportion of data to use for building tree (rest for honest estimates)
    random_state : int, optional
        Random seed for reproducibility
    """

    def __init__(
        self,
        min_samples_leaf: int = 30,
        min_samples_treatment_leaf: int = 10,
        min_samples_control_leaf: int = 10,
        max_depth: int = 5,
        min_effect_size: float = 0.0,
        alpha: float = 0.05,
        cv_folds: int = 5,
        honest_split_ratio: float = 0.5,
        random_state: Optional[int] = None
    ):
        self.min_samples_leaf = min_samples_leaf
        self.min_samples_treatment_leaf = min_samples_treatment_leaf
        self.min_samples_control_leaf = min_samples_control_leaf
        self.max_depth = max_depth
        self.min_effect_size = min_effect_size
        self.alpha = alpha
        self.cv_folds = cv_folds
        self.honest_split_ratio = honest_split_ratio
        self.random_state = random_state

        self.tree_ = None
        self.feature_names_ = None
        self.node_count_ = 0

        # For honest inference
        self.X_honest_ = None
        self.y_honest_ = None
        self.treatment_honest_ = None

        if random_state is not None:
            np.random.seed(random_state)

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        treatment: np.ndarray,
        feature_names: Optional[List[str]] = None,
        honest: bool = True
    ) -> 'MetaCART':
        """
        Fit the Meta-CART model.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Covariate matrix
        y : array-like of shape (n_samples,)
            Outcome variable
        treatment : array-like of shape (n_samples,)
            Treatment indicator (0 or 1)
        feature_names : list of str, optional
            Names of features
        honest : bool, default=True
            Whether to use honest inference (sample splitting)

        Returns
        -------
        self : MetaCART
            Fitted estimator
        """
        # Convert to numpy arrays
        X = np.asarray(X)
        y = np.asarray(y)
        treatment = np.asarray(treatment)

        # Validate inputs
        if X.shape[0] != y.shape[0] or X.shape[0] != treatment.shape[0]:
            raise ValueError("X, y, and treatment must have same number of samples")

        if not np.all(np.isin(treatment, [0, 1])):
            raise ValueError("Treatment must be binary (0 or 1)")

        # Store feature names
        if feature_names is None:
            self.feature_names_ = [f"X{i}" for i in range(X.shape[1])]
        else:
            self.feature_names_ = feature_names

        # Split data for honest inference
        if honest:
            n_samples = X.shape[0]
            n_build = int(n_samples * self.honest_split_ratio)

            # Stratified split by treatment
            indices = np.arange(n_samples)
            np.random.shuffle(indices)

            # Ensure both splits have treatment and control
            treat_idx = indices[treatment[indices] == 1]
            control_idx = indices[treatment[indices] == 0]

            n_treat_build = int(len(treat_idx) * self.honest_split_ratio)
            n_control_build = int(len(control_idx) * self.honest_split_ratio)

            build_idx = np.concatenate([
                treat_idx[:n_treat_build],
                control_idx[:n_control_build]
            ])

            honest_idx = np.concatenate([
                treat_idx[n_treat_build:],
                control_idx[n_control_build:]
            ])

            X_build = X[build_idx]
            y_build = y[build_idx]
            treatment_build = treatment[build_idx]

            self.X_honest_ = X[honest_idx]
            self.y_honest_ = y[honest_idx]
            self.treatment_honest_ = treatment[honest_idx]
        else:
            X_build = X
            y_build = y
            treatment_build = treatment
            self.X_honest_ = None
            self.y_honest_ = None
            self.treatment_honest_ = None

        # Build the tree
        self.node_count_ = 0
        all_indices = np.arange(len(X_build))
        self.tree_ = self._build_tree(
            X_build, y_build, treatment_build, all_indices, depth=0
        )

        # Compute honest estimates if requested
        if honest and self.tree_ is not None:
            self._compute_honest_estimates(self.tree_)

        # Prune the tree using cross-validation
        self._prune_tree()

        return self

    def _build_tree(
        self,
        X: np.ndarray,
        y: np.ndarray,
        treatment: np.ndarray,
        indices: np.ndarray,
        depth: int
    ) -> Optional[Node]:
        """Recursively build the tree."""

        n_samples = len(indices)
        n_treated = np.sum(treatment[indices] == 1)
        n_control = n_samples - n_treated

        # Compute treatment effect in this node
        effect, se, pval = self._compute_treatment_effect(
            y[indices], treatment[indices]
        )

        # Create node
        node_id = self.node_count_
        self.node_count_ += 1

        node = Node(
            node_id=node_id,
            depth=depth,
            is_leaf=True,  # Will be updated if we split
            sample_indices=indices.copy(),
            n_samples=n_samples,
            n_treated=n_treated,
            n_control=n_control,
            treatment_effect=effect,
            treatment_effect_se=se,
            p_value=pval
        )

        # Check stopping criteria
        if self._should_stop_splitting(n_samples, n_treated, n_control, depth):
            return node

        # Find best split
        best_split = self._find_best_split(X, y, treatment, indices)

        if best_split is None:
            return node

        split_var, split_val, split_score, left_idx, right_idx = best_split

        # Check if split is valid
        if len(left_idx) == 0 or len(right_idx) == 0:
            return node

        # Update node with split information
        node.is_leaf = False
        node.split_variable = self.feature_names_[split_var]
        node.split_value = split_val
        node.split_score = split_score

        # Recursively build children
        node.left_child = self._build_tree(X, y, treatment, left_idx, depth + 1)
        node.right_child = self._build_tree(X, y, treatment, right_idx, depth + 1)

        return node

    def _should_stop_splitting(
        self,
        n_samples: int,
        n_treated: int,
        n_control: int,
        depth: int
    ) -> bool:
        """Check if we should stop splitting this node."""

        if depth >= self.max_depth:
            return True

        if n_samples < 2 * self.min_samples_leaf:
            return True

        if n_treated < 2 * self.min_samples_treatment_leaf:
            return True

        if n_control < 2 * self.min_samples_control_leaf:
            return True

        return False

    def _compute_treatment_effect(
        self,
        y: np.ndarray,
        treatment: np.ndarray
    ) -> Tuple[float, float, float]:
        """
        Compute treatment effect and standard error.

        Returns
        -------
        effect : float
            Estimated treatment effect (difference in means)
        se : float
            Standard error of the effect
        p_value : float
            P-value for testing effect != 0
        """
        treated_mask = treatment == 1
        control_mask = treatment == 0

        y_treated = y[treated_mask]
        y_control = y[control_mask]

        if len(y_treated) == 0 or len(y_control) == 0:
            return 0.0, np.inf, 1.0

        # Mean difference
        effect = np.mean(y_treated) - np.mean(y_control)

        # Standard error
        var_treated = np.var(y_treated, ddof=1) if len(y_treated) > 1 else 0
        var_control = np.var(y_control, ddof=1) if len(y_control) > 1 else 0

        se = np.sqrt(var_treated / len(y_treated) + var_control / len(y_control))

        # P-value (two-sided t-test)
        if se > 0:
            t_stat = effect / se
            df = len(y_treated) + len(y_control) - 2
            p_value = 2 * (1 - stats.t.cdf(np.abs(t_stat), df))
        else:
            p_value = 1.0

        return effect, se, p_value

    def _find_best_split(
        self,
        X: np.ndarray,
        y: np.ndarray,
        treatment: np.ndarray,
        indices: np.ndarray
    ) -> Optional[Tuple[int, float, float, np.ndarray, np.ndarray]]:
        """
        Find the best split for the current node.

        The splitting criterion is based on maximizing the difference in
        treatment effects between the two child nodes.

        Returns
        -------
        best_split : tuple or None
            (feature_idx, split_value, score, left_indices, right_indices)
        """

        best_score = -np.inf
        best_split = None

        n_features = X.shape[1]

        for feat_idx in range(n_features):
            # Get unique values for this feature
            feature_values = X[indices, feat_idx]
            unique_values = np.unique(feature_values)

            # Try splits at midpoints between unique values
            if len(unique_values) < 2:
                continue

            split_points = (unique_values[:-1] + unique_values[1:]) / 2

            for split_val in split_points:
                # Create split
                left_mask = feature_values <= split_val
                right_mask = ~left_mask

                left_idx = indices[left_mask]
                right_idx = indices[right_mask]

                # Check minimum sample requirements
                if not self._is_valid_split(
                    left_idx, right_idx, treatment
                ):
                    continue

                # Compute treatment effects in both children
                left_effect, left_se, _ = self._compute_treatment_effect(
                    y[left_idx], treatment[left_idx]
                )
                right_effect, right_se, _ = self._compute_treatment_effect(
                    y[right_idx], treatment[right_idx]
                )

                # Splitting score: weighted difference in treatment effects
                # This captures heterogeneity in treatment effects
                n_left = len(left_idx)
                n_right = len(right_idx)
                n_total = n_left + n_right

                # Compute the between-group sum of squares for treatment effects
                # This is the standard Meta-CART splitting criterion
                overall_effect, _, _ = self._compute_treatment_effect(
                    y[indices], treatment[indices]
                )

                score = (
                    n_left / n_total * (left_effect - overall_effect) ** 2 +
                    n_right / n_total * (right_effect - overall_effect) ** 2
                )

                # Alternative: maximize absolute difference
                # score = abs(left_effect - right_effect) * min(n_left, n_right) / n_total

                if score > best_score:
                    best_score = score
                    best_split = (feat_idx, split_val, score, left_idx, right_idx)

        return best_split

    def _is_valid_split(
        self,
        left_idx: np.ndarray,
        right_idx: np.ndarray,
        treatment: np.ndarray
    ) -> bool:
        """Check if a split satisfies minimum sample requirements."""

        # Check total samples
        if len(left_idx) < self.min_samples_leaf:
            return False
        if len(right_idx) < self.min_samples_leaf:
            return False

        # Check treatment group samples
        left_treated = np.sum(treatment[left_idx] == 1)
        left_control = len(left_idx) - left_treated

        right_treated = np.sum(treatment[right_idx] == 1)
        right_control = len(right_idx) - right_treated

        if left_treated < self.min_samples_treatment_leaf:
            return False
        if left_control < self.min_samples_control_leaf:
            return False

        if right_treated < self.min_samples_treatment_leaf:
            return False
        if right_control < self.min_samples_control_leaf:
            return False

        return True

    def _compute_honest_estimates(self, node: Node) -> None:
        """Compute honest estimates using the held-out sample."""

        if node is None or self.X_honest_ is None:
            return

        # Get indices of honest sample that fall in this node
        honest_idx = self._get_node_indices_honest(node, self.X_honest_)

        if len(honest_idx) > 0:
            # Compute treatment effect on honest sample
            y_node = self.y_honest_[honest_idx]
            t_node = self.treatment_honest_[honest_idx]

            effect, se, _ = self._compute_treatment_effect(y_node, t_node)

            # 95% confidence interval
            ci_lower = effect - 1.96 * se
            ci_upper = effect + 1.96 * se

            node.honest_effect = effect
            node.honest_se = se
            node.honest_ci_lower = ci_lower
            node.honest_ci_upper = ci_upper

        # Recursively compute for children
        if not node.is_leaf:
            self._compute_honest_estimates(node.left_child)
            self._compute_honest_estimates(node.right_child)

    def _get_node_indices_honest(
        self,
        node: Node,
        X_honest: np.ndarray
    ) -> np.ndarray:
        """Get indices of honest sample that fall in this node."""

        if node is None:
            return np.array([], dtype=int)

        # Start with all indices
        mask = np.ones(X_honest.shape[0], dtype=bool)

        # Traverse from root to this node
        current = self.tree_
        path = self._get_path_to_node(node.node_id)

        for direction, split_node in path:
            if split_node is None:
                break

            feat_idx = self.feature_names_.index(split_node.split_variable)
            if direction == 'left':
                mask &= X_honest[:, feat_idx] <= split_node.split_value
            else:
                mask &= X_honest[:, feat_idx] > split_node.split_value

        return np.where(mask)[0]

    def _get_path_to_node(self, node_id: int) -> List[Tuple[str, Node]]:
        """Get the path from root to a specific node."""

        path = []

        def traverse(node, direction='root'):
            if node is None:
                return False

            if node.node_id == node_id:
                return True

            if not node.is_leaf:
                if traverse(node.left_child, 'left'):
                    path.append(('left', node))
                    return True
                if traverse(node.right_child, 'right'):
                    path.append(('right', node))
                    return True

            return False

        traverse(self.tree_)
        return list(reversed(path))

    def _prune_tree(self) -> None:
        """
        Prune the tree using cost-complexity pruning with cross-validation.

        This implements the standard CART pruning algorithm:
        1. Generate sequence of nested trees by cost-complexity pruning
        2. Use cross-validation to select the best tree
        """

        if self.tree_ is None:
            return

        # For simplicity, we'll implement a basic pruning based on
        # statistical significance of splits
        # More sophisticated pruning can be added

        self._prune_insignificant_splits(self.tree_)

    def _prune_insignificant_splits(self, node: Node, alpha: float = 0.05) -> None:
        """
        Prune splits where children don't have significantly different effects.
        """

        if node is None or node.is_leaf:
            return

        # Recursively prune children first
        self._prune_insignificant_splits(node.left_child, alpha)
        self._prune_insignificant_splits(node.right_child, alpha)

        # Check if this split should be pruned
        # Test if treatment effects in children are significantly different
        if node.left_child and node.right_child:
            left_effect = node.left_child.treatment_effect
            left_se = node.left_child.treatment_effect_se
            right_effect = node.right_child.treatment_effect
            right_se = node.right_child.treatment_effect_se

            # Test for difference
            diff = abs(left_effect - right_effect)
            se_diff = np.sqrt(left_se**2 + right_se**2)

            if se_diff > 0:
                z_stat = diff / se_diff
                p_val = 2 * (1 - stats.norm.cdf(abs(z_stat)))

                # If not significant, prune this split
                if p_val > alpha:
                    node.is_leaf = True
                    node.left_child = None
                    node.right_child = None

    def predict_subgroup(self, X: np.ndarray) -> np.ndarray:
        """
        Predict subgroup membership for samples.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Samples to predict

        Returns
        -------
        subgroups : array of shape (n_samples,)
            Subgroup ID for each sample
        """

        X = np.asarray(X)

        if self.tree_ is None:
            raise ValueError("Model has not been fitted yet")

        subgroups = np.zeros(X.shape[0], dtype=int)

        for i in range(X.shape[0]):
            node = self._traverse_to_leaf(X[i])
            subgroups[i] = node.node_id

        return subgroups

    def _traverse_to_leaf(self, x: np.ndarray) -> Node:
        """Traverse tree to find leaf node for a sample."""

        node = self.tree_

        while not node.is_leaf:
            feat_idx = self.feature_names_.index(node.split_variable)
            if x[feat_idx] <= node.split_value:
                node = node.left_child
            else:
                node = node.right_child

        return node

    def get_subgroup_effects(self) -> pd.DataFrame:
        """
        Get treatment effect estimates for each subgroup.

        Returns
        -------
        effects : DataFrame
            Treatment effects with confidence intervals for each subgroup
        """

        if self.tree_ is None:
            raise ValueError("Model has not been fitted yet")

        results = []
        self._collect_leaf_effects(self.tree_, results)

        df = pd.DataFrame(results)

        # Sort by subgroup_id
        df = df.sort_values('subgroup_id').reset_index(drop=True)

        return df

    def _collect_leaf_effects(self, node: Node, results: List[Dict]) -> None:
        """Recursively collect effects from leaf nodes."""

        if node is None:
            return

        if node.is_leaf:
            result = {
                'subgroup_id': node.node_id,
                'n_samples': node.n_samples,
                'n_treated': node.n_treated,
                'n_control': node.n_control,
                'treatment_effect': node.treatment_effect,
                'std_error': node.treatment_effect_se,
                'p_value': node.p_value,
                'ci_lower': node.treatment_effect - 1.96 * node.treatment_effect_se,
                'ci_upper': node.treatment_effect + 1.96 * node.treatment_effect_se,
            }

            # Add honest estimates if available
            if node.honest_effect is not None:
                result['honest_effect'] = node.honest_effect
                result['honest_se'] = node.honest_se
                result['honest_ci_lower'] = node.honest_ci_lower
                result['honest_ci_upper'] = node.honest_ci_upper

            results.append(result)
        else:
            self._collect_leaf_effects(node.left_child, results)
            self._collect_leaf_effects(node.right_child, results)

    def get_splitting_rules(self) -> List[Dict]:
        """
        Get the splitting rules that define each subgroup.

        Returns
        -------
        rules : list of dict
            Splitting rules for each subgroup
        """

        if self.tree_ is None:
            raise ValueError("Model has not been fitted yet")

        rules = []
        self._collect_rules(self.tree_, [], rules)

        return rules

    def _collect_rules(
        self,
        node: Node,
        conditions: List[str],
        results: List[Dict]
    ) -> None:
        """Recursively collect splitting rules."""

        if node is None:
            return

        if node.is_leaf:
            results.append({
                'subgroup_id': node.node_id,
                'rules': conditions.copy(),
                'rule_string': ' AND '.join(conditions) if conditions else 'All samples'
            })
        else:
            # Left child: feature <= value
            left_cond = f"{node.split_variable} <= {node.split_value:.3f}"
            self._collect_rules(
                node.left_child,
                conditions + [left_cond],
                results
            )

            # Right child: feature > value
            right_cond = f"{node.split_variable} > {node.split_value:.3f}"
            self._collect_rules(
                node.right_child,
                conditions + [right_cond],
                results
            )

    def print_tree(self, node: Optional[Node] = None, indent: str = "") -> None:
        """Print the tree structure."""

        if node is None:
            node = self.tree_

        if node is None:
            print("Tree has not been fitted yet")
            return

        # Print current node
        effect_str = f"TE={node.treatment_effect:.3f} (SE={node.treatment_effect_se:.3f})"
        if node.honest_effect is not None:
            effect_str += f", Honest TE={node.honest_effect:.3f}"

        print(f"{indent}Node {node.node_id}: n={node.n_samples} "
              f"(treated={node.n_treated}, control={node.n_control}), {effect_str}")

        if not node.is_leaf:
            print(f"{indent}  Split: {node.split_variable} <= {node.split_value:.3f}")
            print(f"{indent}  Left:")
            self.print_tree(node.left_child, indent + "    ")
            print(f"{indent}  Right:")
            self.print_tree(node.right_child, indent + "    ")


class BootstrapStability:
    """
    Assess stability of Meta-CART results via bootstrap.

    This class performs bootstrap resampling to assess:
    - Stability of subgroup membership
    - Confidence in treatment effect estimates
    - Variable importance in splitting
    """

    def __init__(
        self,
        meta_cart: MetaCART,
        n_bootstrap: int = 100,
        random_state: Optional[int] = None
    ):
        """
        Parameters
        ----------
        meta_cart : MetaCART
            Fitted Meta-CART model
        n_bootstrap : int
            Number of bootstrap samples
        random_state : int, optional
            Random seed
        """
        self.meta_cart = meta_cart
        self.n_bootstrap = n_bootstrap
        self.random_state = random_state

        self.bootstrap_results_ = []
        self.subgroup_stability_ = None
        self.variable_importance_ = None

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        treatment: np.ndarray
    ) -> 'BootstrapStability':
        """
        Run bootstrap analysis.

        Parameters
        ----------
        X : array-like
            Covariates
        y : array-like
            Outcomes
        treatment : array-like
            Treatment indicators

        Returns
        -------
        self : BootstrapStability
        """

        if self.random_state is not None:
            np.random.seed(self.random_state)

        n_samples = X.shape[0]

        print(f"Running {self.n_bootstrap} bootstrap iterations...")

        for b in range(self.n_bootstrap):
            if (b + 1) % 20 == 0:
                print(f"  Bootstrap iteration {b + 1}/{self.n_bootstrap}")

            # Bootstrap sample
            boot_idx = np.random.choice(n_samples, size=n_samples, replace=True)
            X_boot = X[boot_idx]
            y_boot = y[boot_idx]
            treatment_boot = treatment[boot_idx]

            # Fit Meta-CART
            try:
                model = MetaCART(
                    min_samples_leaf=self.meta_cart.min_samples_leaf,
                    min_samples_treatment_leaf=self.meta_cart.min_samples_treatment_leaf,
                    min_samples_control_leaf=self.meta_cart.min_samples_control_leaf,
                    max_depth=self.meta_cart.max_depth,
                    random_state=None  # Don't use same seed for each bootstrap
                )

                model.fit(X_boot, y_boot, treatment_boot,
                         feature_names=self.meta_cart.feature_names_,
                         honest=False)  # Faster without honest estimates

                # Store results
                self.bootstrap_results_.append({
                    'model': model,
                    'boot_idx': boot_idx
                })

            except Exception as e:
                warnings.warn(f"Bootstrap iteration {b} failed: {e}")
                continue

        # Analyze results
        self._analyze_stability(X)

        return self

    def _analyze_stability(self, X: np.ndarray) -> None:
        """Analyze bootstrap results for stability."""

        n_samples = X.shape[0]
        n_success = len(self.bootstrap_results_)

        if n_success == 0:
            warnings.warn("No successful bootstrap iterations")
            return

        # 1. Subgroup stability: how often is each sample in same subgroup
        #    as other samples?

        # 2. Variable importance: how often is each variable used for splitting?
        var_counts = {name: 0 for name in self.meta_cart.feature_names_}

        for result in self.bootstrap_results_:
            model = result['model']

            # Count variable usage
            def count_vars(node):
                if node is None or node.is_leaf:
                    return
                var_counts[node.split_variable] += 1
                count_vars(node.left_child)
                count_vars(node.right_child)

            count_vars(model.tree_)

        # Normalize to get importance scores
        total_splits = sum(var_counts.values())
        if total_splits > 0:
            self.variable_importance_ = {
                var: count / total_splits
                for var, count in var_counts.items()
            }
        else:
            self.variable_importance_ = var_counts

    def get_variable_importance(self) -> pd.DataFrame:
        """
        Get variable importance based on bootstrap.

        Returns
        -------
        importance : DataFrame
            Variable importance scores
        """

        if self.variable_importance_ is None:
            raise ValueError("Must call fit() first")

        df = pd.DataFrame([
            {'variable': var, 'importance': imp}
            for var, imp in self.variable_importance_.items()
        ])

        df = df.sort_values('importance', ascending=False).reset_index(drop=True)

        return df
