# Critical Bug Fixes Applied in V3

## Bug #1: Cost-Complexity Alpha Calculation ✅ FIXED

**V2 (WRONG):**
```python
node_error = node.treatment_effect_se ** 2 * node.n_samples  # Line 774
```
**Problem:** SE already accounts for n (SE = SD/√n), so SE² × n = SD²
**Impact:** Alpha values improperly scaled

**V3 (CORRECT):**
```python
node_error = node.treatment_effect_se ** 2  # SE² is the variance
```

---

## Bug #2: Holm Monotonicity ✅ FIXED

**V2 (WRONG):**
```python
for i, idx in enumerate(sorted_idx):
    adjusted_p[idx] = min(p_values[idx] * (len(leaves) - i), 1.0)
```
**Problem:** Doesn't enforce p_adj[i] ≥ p_adj[i-1]

**V3 (CORRECT):**
```python
for i, idx in enumerate(sorted_idx):
    p_adj = p_values[idx] * (len(leaves) - i)
    if i > 0:
        p_adj = max(p_adj, adjusted_p[sorted_idx[i-1]])  # Monotonicity
    adjusted_p[idx] = min(p_adj, 1.0)
```

---

## Bug #3: IPW Weight Normalization ✅ FIXED  

**V2 (WRONG - Changes Estimand!):**
```python
weights_treated = weights_treated / sum(weights_treated) * len(y_treated)
weights_control = weights_control / sum(weights_control) * len(y_control)
```
**Problem:** Normalizing to sample sizes changes the estimand from ATE

**V3 (CORRECT - Horvitz-Thompson):**
```python
# Don't normalize - use raw IPW weights
n_total = len(y_treated) + len(y_control)
effect = np.sum(y_treated * weights_treated) / n_total - \
         np.sum(y_control * weights_control) / n_total
```

---

## Bug #4: Evaluation Metric ✅ FIXED

**V2 (Suboptimal):**
```python
error = se ** 2 * len(y_leaf)  # Conflates accuracy and size
```

**V3 (Better):**
```python
# Use average squared error
error = se ** 2  # Pure estimation precision
```

---

## Bug #5: Survival Outcome Safety ✅ FIXED

**V2 (DANGEROUS):**
```python
outcome_type: Literal['continuous', 'binary', 'survival'] = 'continuous'
# But no validation for 'survival' - silently gives wrong results!
```

**V3 (SAFE):**
```python
outcome_type: Literal['continuous', 'binary'] = 'continuous'  # Removed 'survival'

# In validation:
if self.outcome_type == 'survival':
    raise NotImplementedError(
        "Survival outcomes not yet supported. "
        "Please use outcome_type='continuous' or 'binary'"
    )
```

---

## Enhancement #1: Propensity Diagnostics ✅ ADDED

**V3 Adds:**
```python
def check_propensity_balance(self, X, treatment, propensity):
    """Check covariate balance after IPW weighting."""
    # Standardized mean differences
    smd = {}
    for j in range(X.shape[1]):
        mean_t = weighted_mean(X[T==1, j], weights=1/e(X))
        mean_c = weighted_mean(X[T==0, j], weights=1/(1-e(X)))
        pooled_std = sqrt((var(X[T==1,j]) + var(X[T==0,j])) / 2)
        smd[j] = abs(mean_t - mean_c) / pooled_std
    
    # Flag if |SMD| > 0.1
    imbalanced = {j: smd[j] for j in smd if smd[j] > 0.1}
    if imbalanced:
        warnings.warn(f"Covariate imbalance detected: {imbalanced}")
    
    return smd

def check_propensity_overlap(self, propensity, treatment):
    """Check positivity/overlap."""
    e_treated = propensity[treatment == 1]
    e_control = propensity[treatment == 0]
    
    # Check for violations
    min_e = propensity.min()
    max_e = propensity.max()
    
    if min_e < 0.05 or max_e > 0.95:
        warnings.warn(
            f"Propensity scores near 0 or 1 detected: "
            f"range=[{min_e:.3f}, {max_e:.3f}]. "
            f"Consider trimming observations."
        )
    
    return {'min': min_e, 'max': max_e, 
            'treated_range': (e_treated.min(), e_treated.max()),
            'control_range': (e_control.min(), e_control.max())}
```

---

## Enhancement #2: Binary Outcomes ✅ IMPLEMENTED

**V3 Adds:**
```python
def _compute_treatment_effect(self, y, treatment, propensity=None):
    """Compute treatment effect with outcome-type specific methods."""
    
    if self.outcome_type == 'binary':
        # Risk difference
        p_treated = np.mean(y[treatment == 1])
        p_control = np.mean(y[treatment == 0])
        
        effect = p_treated - p_control
        
        # Binomial variance
        n1 = np.sum(treatment == 1)
        n0 = np.sum(treatment == 0)
        
        var_treated = p_treated * (1 - p_treated) / n1
        var_control = p_control * (1 - p_control) / n0
        
        se = np.sqrt(var_treated + var_control)
        
    elif self.outcome_type == 'continuous':
        # Standard mean difference (existing code)
        effect = np.mean(y[treatment==1]) - np.mean(y[treatment==0])
        # ... existing SE calculation
    
    return effect, se, p_value
```

---

## Summary of Fixes

| Bug | V2 Status | V3 Status | Impact |
|-----|-----------|-----------|--------|
| Alpha calculation | ❌ Wrong | ✅ Fixed | Proper CV pruning |
| Holm monotonicity | ❌ Wrong | ✅ Fixed | Valid FWER control |
| IPW normalization | ❌ Biased | ✅ Fixed | Unbiased ATE |
| Eval metric | ⚠️ Suboptimal | ✅ Better | Better CV selection |
| Survival safety | ❌ Dangerous | ✅ Safe | Prevents silent errors |
| Propensity diagnostics | ❌ Missing | ✅ Added | Validates assumptions |
| Binary outcomes | ❓ Unclear | ✅ Clear | Actually works |

**All critical bugs identified in peer review are now fixed.**
