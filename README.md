# Meta-CART for Subgroup Discovery

**A Python implementation of Interaction Trees (Meta-CART) for identifying treatment effect modifiers in randomized clinical trials and observational studies.**

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

Meta-CART (Model-based Adaptive Recursive Tree) is a principled statistical method for discovering subgroups with differential treatment effects. Unlike traditional subgroup analysis that suffers from multiple testing issues and p-hacking, Meta-CART provides:

- **Structured search**: Tree-based partitioning avoids exhaustive testing
- **Cross-validation pruning**: Prevents overfitting
- **Honest inference**: Sample splitting for valid confidence intervals
- **Bootstrap stability**: Assesses reliability of findings
- **Variable importance**: Identifies key effect modifiers

## Key Features

### ✅ Recursive Partitioning for Effect Modifiers
- Splits based on treatment effect heterogeneity (not just outcomes)
- Identifies clinically meaningful subgroups automatically

### ✅ Honest Inference (Split-Sample Approach)
- Separates tree building from effect estimation
- Provides valid p-values and confidence intervals
- Avoids selection bias

### ✅ Cross-Validation Pruning
- Prevents overfitting through principled model selection
- Prunes statistically insignificant splits

### ✅ Bootstrap Stability Analysis
- Assesses reliability of discovered subgroups
- Variable importance through bootstrap aggregation
- Quantifies uncertainty in subgroup membership

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/meta-cart
cd meta-cart

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```python
import numpy as np
from meta_cart import MetaCART

# Your data: X (covariates), y (outcomes), treatment (0/1)
X, y, treatment = load_your_data()

# Fit Meta-CART with honest inference
model = MetaCART(
    min_samples_leaf=40,
    max_depth=4,
    honest_split_ratio=0.5,
    random_state=42
)

model.fit(X, y, treatment, feature_names=['Age', 'Biomarker', 'Severity'])

# Print tree structure
model.print_tree()

# Get subgroup effects with confidence intervals
effects = model.get_subgroup_effects()
print(effects)

# Get splitting rules
rules = model.get_splitting_rules()
for rule in rules:
    print(f"Subgroup {rule['subgroup_id']}: {rule['rule_string']}")
```

## Comprehensive Example

See `example_usage.py` for a complete workflow:

```bash
python example_usage.py
```

This example demonstrates:
1. Synthetic data generation with known heterogeneous effects
2. Meta-CART fitting with honest inference
3. Subgroup identification and characterization
4. Bootstrap stability analysis
5. Statistical hypothesis testing
6. Clinical interpretation
7. Publication-ready visualizations

**Output**: Creates visualizations in `output/` directory including:
- Tree structure diagram
- Forest plots of treatment effects
- Variable importance plots
- Diagnostic panels

## Advanced Example

See `advanced_example.py` for method comparisons and validation:

```bash
python advanced_example.py
```

This demonstrates:
1. Comparison with naive subgroup analysis
2. False discovery rate control
3. Sensitivity analysis
4. Feature selection validation
5. Robustness checks

## Method Details

### Splitting Criterion

Meta-CART uses a specialized splitting criterion that maximizes treatment effect heterogeneity:

```
Score = (n_L/n) * (TE_L - TE)² + (n_R/n) * (TE_R - TE)²
```

where:
- `n_L`, `n_R` = sample sizes in left and right children
- `TE_L`, `TE_R` = treatment effects in children
- `TE` = overall treatment effect

This differs from standard CART which splits on outcomes directly.

### Honest Inference

To obtain valid statistical inference, the algorithm:

1. **Splits data**: 50% for building tree, 50% for estimation
2. **Builds tree**: Uses first half to determine splits
3. **Estimates effects**: Uses second half to compute treatment effects
4. **Computes CI**: Valid confidence intervals from independent sample

This avoids selection bias and provides honest p-values.

### Pruning Strategy

The implementation includes:
- **Statistical pruning**: Remove splits where child effects don't differ significantly
- **Cross-validation**: Can be extended with cost-complexity pruning
- **Minimum sample size**: Enforces minimum samples per leaf

## API Reference

### MetaCART Class

```python
MetaCART(
    min_samples_leaf=30,           # Minimum samples in leaf
    min_samples_treatment_leaf=10, # Minimum treated samples in leaf
    min_samples_control_leaf=10,   # Minimum control samples in leaf
    max_depth=5,                   # Maximum tree depth
    min_effect_size=0.0,           # Minimum effect size to consider
    alpha=0.05,                    # Significance level
    cv_folds=5,                    # CV folds for pruning
    honest_split_ratio=0.5,        # Proportion for building vs estimation
    random_state=None              # Random seed
)
```

**Methods**:
- `fit(X, y, treatment, feature_names, honest=True)`: Fit the model
- `predict_subgroup(X)`: Predict subgroup membership
- `get_subgroup_effects()`: Get treatment effects with CIs
- `get_splitting_rules()`: Get interpretable rules
- `print_tree()`: Display tree structure

### BootstrapStability Class

```python
BootstrapStability(
    meta_cart,        # Fitted MetaCART model
    n_bootstrap=100,  # Number of bootstrap samples
    random_state=None # Random seed
)
```

**Methods**:
- `fit(X, y, treatment)`: Run bootstrap analysis
- `get_variable_importance()`: Variable importance scores

## Visualization Functions

```python
from visualization import (
    plot_tree_structure,      # Tree diagram
    plot_subgroup_effects,    # Treatment effects with CIs
    plot_comparison_forest,   # Forest plot
    plot_variable_importance, # Bootstrap importance
    plot_diagnostic_panel     # Comprehensive diagnostics
)

# Example
fig = plot_tree_structure(model, show_honest=True)
fig.savefig('tree.png', dpi=300)
```

## Use Cases

### 1. Clinical Trials
Identify patient subgroups that benefit most from treatment:
```python
# Example: Cancer trial
# Who benefits from new chemotherapy?
model.fit(X_patients, survival_time, treatment_arm)
```

### 2. A/B Testing
Find user segments with differential responses:
```python
# Example: Product feature test
# Which users prefer the new feature?
model.fit(X_users, engagement_score, feature_enabled)
```

### 3. Policy Evaluation
Discover which populations benefit from interventions:
```python
# Example: Job training program
# Who benefits most from training?
model.fit(X_participants, income_change, received_training)
```

## Best Practices

### 1. Sample Size Requirements
- **Minimum**: 200-300 total samples
- **Recommended**: 500+ for stable results
- Each leaf should have 30+ samples (15+ per treatment arm)

### 2. Feature Selection
- Include **potential effect modifiers** (baseline characteristics)
- Exclude **post-treatment variables** (intermediate outcomes)
- Pre-specify features when possible

### 3. Hyperparameter Tuning
- Start conservative: `min_samples_leaf=50`, `max_depth=3`
- Use cross-validation for final selection
- Perform sensitivity analysis

### 4. Reporting Results
- **Always** report honest estimates (not training estimates)
- Include confidence intervals
- Show bootstrap stability
- Pre-specify primary analysis when possible
- Validate in independent dataset

### 5. Multiple Testing
- Meta-CART provides some protection through structured search
- Consider additional corrections for exploratory analyses
- Validate findings in confirmatory study

## Limitations and Considerations

### When to Use
✅ Randomized trials with heterogeneous effects
✅ Large observational studies (with confounding adjustment)
✅ Exploratory subgroup discovery
✅ Hypothesis generation for future trials

### When NOT to Use
❌ Small samples (n < 200)
❌ Highly imbalanced treatment groups
❌ As sole basis for clinical decisions (validate first!)
❌ When you need exact p-values (these are approximate)

### Key Assumptions
1. **Randomization**: Treatment is randomized (or exchangeability holds)
2. **SUTVA**: No interference between units
3. **Sample size**: Sufficient samples for stable estimates
4. **Continuity**: Tree can approximate true effect heterogeneity

## Comparison with Other Methods

| Method | Multiple Testing | Honest Inference | Interpretability | Stability |
|--------|-----------------|------------------|------------------|-----------|
| Naive subgroup testing | ❌ | ❌ | ✅ | ❌ |
| Meta-CART | ⚠️ Partial | ✅ | ✅ | ✅ |
| Causal Forest | ✅ | ✅ | ❌ | ✅ |
| Virtual Twins | ⚠️ Partial | ⚠️ Optional | ⚠️ Moderate | ⚠️ |

**Note**: For pure prediction of individual treatment effects, consider Causal Forests. For interpretable subgroup discovery, Meta-CART is preferred.

## Mathematical Background

### Treatment Effect Estimation

For subgroup $S$:

```
TE(S) = E[Y(1) - Y(0) | X ∈ S]
     ≈ (1/n_T) Σ Y_i - (1/n_C) Σ Y_j
```

where the sums are over treated (T) and control (C) units in S.

### Standard Error

Under randomization:

```
SE(TE) = √(Var(Y|T=1)/n_T + Var(Y|T=0)/n_C)
```

### Confidence Interval

95% CI: `TE ± 1.96 * SE`

## References

### Primary References

1. **Lipkovich, I., Dmitrienko, A., & D'Agostino, R. B. (2017)**
   *Tutorial in biostatistics: data-driven subgroup identification and analysis in clinical trials*
   Statistics in Medicine, 36(1), 136-196.
   [DOI: 10.1002/sim.7064](https://doi.org/10.1002/sim.7064)

2. **Lipkovich, I., Dmitrienko, A., Denne, J., & Enas, G. (2011)**
   *Subgroup identification based on differential effect search (SIDES)*
   Statistics in Medicine, 30(21), 2781-2803.
   [DOI: 10.1002/sim.4289](https://doi.org/10.1002/sim.4289)

3. **Su, X., Tsai, C. L., Wang, H., Nickerson, D. M., & Li, B. (2009)**
   *Subgroup analysis via recursive partitioning*
   Journal of Machine Learning Research, 10(2).

### Related Methods

4. **Athey, S., & Imbens, G. (2016)**
   *Recursive partitioning for heterogeneous causal effects*
   Proceedings of the National Academy of Sciences, 113(27), 7353-7360.

5. **Wager, S., & Athey, S. (2018)**
   *Estimation and inference of heterogeneous treatment effects using random forests*
   Journal of the American Statistical Association, 113(523), 1228-1242.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Citation

If you use this code in your research, please cite:

```bibtex
@software{metacart2024,
  title={Meta-CART for Subgroup Discovery: Python Implementation},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/meta-cart}
}
```

And cite the original papers:

```bibtex
@article{lipkovich2017tutorial,
  title={Tutorial in biostatistics: data-driven subgroup identification and analysis in clinical trials},
  author={Lipkovich, Ilya and Dmitrienko, Alex and D'Agostino, Ralph B},
  journal={Statistics in medicine},
  volume={36},
  number={1},
  pages={136--196},
  year={2017}
}
```

## License

MIT License - see LICENSE file for details

## Support

For questions or issues:
- Open an issue on GitHub
- Email: your.email@example.com

## Roadmap

Future enhancements:
- [ ] Multi-arm trials (>2 treatment groups)
- [ ] Survival outcomes (time-to-event)
- [ ] Binary outcomes (risk differences, odds ratios)
- [ ] Doubly robust estimation
- [ ] Integration with causal inference packages
- [ ] Interactive visualization dashboard
- [ ] Automatic report generation

## Acknowledgments

This implementation is based on the seminal work of Lipkovich et al. (2011, 2017) on subgroup identification in clinical trials. We thank the authors for their foundational contributions to this methodology.

---

**Disclaimer**: This software is provided for research and educational purposes. Always validate findings in independent datasets before making clinical decisions. Consult with statisticians and domain experts when analyzing real trial data.
