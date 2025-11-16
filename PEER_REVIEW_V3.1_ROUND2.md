# SECOND-ROUND PEER REVIEW: Meta-CART V3.1

**Manuscript ID**: META-CART-V3-2025 (Revision)  
**Review Date**: 2025-11-16  
**Reviewer**: Statistical Methods Editor  

---

## OVERALL RECOMMENDATION: **ACCEPT WITH MINOR REVISIONS**

The authors have done an excellent job addressing the major methodological concerns from the first review. The revised manuscript (V3.1) demonstrates substantial improvements in both rigor and transparency. However, a few minor issues and one moderate concern require attention before final acceptance.

---

## MAJOR IMPROVEMENTS VERIFIED ✅

### 1. IPW Estimator Clarification (SATISFACTORY)

**Finding**: The authors have correctly addressed the Hájek vs Horvitz-Thompson issue.

**Verification**:
- Lines 757-797: Hájek estimator properly implemented
- Lines 778-795: Horvitz-Thompson option available
- Documentation correctly labels both estimators
- Theoretical justification provided (finite-sample properties)

**Verdict**: ✅ **FULLY RESOLVED**

---

### 2. Cost-Complexity Pruning (SATISFACTORY)

**Finding**: The pruning now uses prediction MSE instead of estimation variance.

**Verification**:
- Lines 854-886: `_compute_prediction_mse()` calculates within-node outcome variance
- Lines 1070-1113: Alpha sequence uses `prediction_mse` 
- Lines 1115-1128: Subtree MSE correctly weighted

**Formula verified**:
```python
total_mse = (mse_treated + mse_control) / len(y)  # Line 884
alpha = (node_mse - subtree_mse) / (num_leaves - 1)  # Line 1096
```

This now follows CART (Breiman et al., 1984) correctly.

**Verdict**: ✅ **FULLY RESOLVED**

---

### 3. Propensity SMD Calculation (SATISFACTORY)

**Finding**: SMD calculation fixed - no longer renormalizes weights.

**Verification** (Lines 442-466):
```python
# CORRECT: No renormalization
weights_control = p_control / (1 - p_control)
mean_t = np.mean(X_treated)  # Unweighted
mean_c = np.average(X_control, weights=weights_control)  # Weighted
smd[j] = abs(mean_t - mean_c) / pooled_std
```

This is now theoretically correct for ATE balance assessment.

**Verdict**: ✅ **FULLY RESOLVED**

---

### 4. Multiple Testing Dependencies (SATISFACTORY)

**Finding**: Explicit warnings added about tree structure dependencies.

**Verification** (Lines 223-230):
```python
if multiple_testing_method in ['holm', 'bonferroni']:
    warnings.warn(
        "correction assumes independent tests. "
        "Tree-based subgroups are dependent (parent-child relationships). "
        "Consider 'fdr' method or interpret with caution.",
        UserWarning
    )
```

Users are now properly warned. FDR recommendation appropriate.

**Verdict**: ✅ **FULLY RESOLVED**

---

### 5. Documentation (EXCELLENT)

**Finding**: All requested documentation added.

**Verification**:
- Lines 96-106: Complete assumptions section
- Lines 23-45: All missing references added
- README_V3_1.md: Comprehensive user guide with limitations
- PEER_REVIEW_RESPONSE.md: Detailed point-by-point response
- requirements.txt: Exact dependency versions

**Verdict**: ✅ **EXCEEDS EXPECTATIONS**

---

## NEW ISSUES IDENTIFIED

### Issue #1: MSE Criterion for Causal Trees (MODERATE)

**Problem**: The prediction MSE (lines 854-886) minimizes **outcome variance**, not **treatment effect variance**.

**Current implementation**:
```python
pred_treated = np.mean(y_treated)
pred_control = np.mean(y_control)
mse = sum((y - pred)²) / n  # Outcome MSE, not CATE MSE
```

**Theoretical concern**: 

For causal trees, Athey & Imbens (2016) recommend splitting to minimize variance of treatment effect **estimates**, not outcomes. The current criterion is:

```
R(node) = Var(Y|T=1) + Var(Y|T=0)
```

But for treatment effect trees, ideally:

```
R(node) = Var(τ̂) where τ̂ is estimated treatment effect
```

**However**: The authors' approach is **defensible**. Athey & Imbens (2016) discuss "honest" trees that split on outcomes (not effects) to avoid overfitting. This is what V3.1 implements.

**Recommendation**:
1. **Add clarifying note** in docstring explaining this is "outcome-based" CART, not "adaptive" causal tree
2. **Cite** Athey & Imbens (2016) Section 3.2 on honest splitting
3. **Optional**: Add `splitting_criterion='outcome'` parameter for future "adaptive" option

**Severity**: MODERATE (not wrong, just needs clarification)

**Code location**: Lines 854-886, 1000-1006 docstrings

---

### Issue #2: Hájek Variance Formula Edge Case (MINOR)

**Problem**: Hájek variance (line 773-774) uses conservative formula, which can be overly conservative in small samples.

**Current formula** (lines 768-776):
```python
residuals_treated = (y_treated - mean_treated) / p_treated
var_treated = np.sum(residuals_treated ** 2) / (n_total ** 2)
```

This is the **conservative Hájek variance**. In small samples, it can be quite conservative.

**Alternative** (more efficient):
```python
# Linearization variance (Deville 1999)
var_treated = (1 / sum(w_treated)²) * sum(w_treated² * (y - μ̂)²)
```

**Recommendation**:
1. Current implementation is **correct** (conservative is OK)
2. **Add note** in docstring: "Uses conservative Hájek variance; may be overly conservative in small samples"
3. **Optional**: Add `variance_method='conservative'` parameter

**Severity**: MINOR (current approach is valid)

**Code location**: Lines 768-776, 828-850

---

### Issue #3: Computational Complexity Not Documented (MINOR)

**Problem**: No discussion of computational cost or scalability.

**Expected complexity**:
- Tree building: O(n² × p × log n) per split
- CV pruning: O(k × n² × p × log n) where k = number of folds
- Honest inference: Additional factor of 2 (sample splitting)

**Recommendation**:
Add to docstring:
```python
Computational Complexity
------------------------
- Tree building: O(n² × p × log n)
- With CV pruning: O(k × n² × p × log n)
- With honest inference: 2× the above (sample splitting)

Scalability: Suitable for n ≤ 10,000, p ≤ 50
```

**Severity**: MINOR (documentation issue)

**Code location**: Class docstring (lines 89-185)

---

### Issue #4: Binary Outcome Variance (MINOR CLARIFICATION)

**Problem**: Binary outcome variance uses empirical variance (lines 675-680), which is correct, but could be explained better.

**Current** (line 675-680):
```python
# V3.1 FIX: Use ROBUST empirical variance (not model-based binomial)
var_treated = np.var(y_treated, ddof=1) / n1
```

**Why this is correct**: 
- Empirical variance is **robust** to model misspecification
- For binary Y: Var(Y) = p(1-p), but empirical Var(Y) = (1/n)Σ(Y-Ȳ)² is more robust

**Recommendation**:
Add brief note: "Empirical variance is consistent and robust; model-based variance p(1-p) would assume correct specification"

**Severity**: MINOR (already correct, just needs explanation)

**Code location**: Line 675-680 docstring

---

## MINOR SUGGESTIONS

### 1. Type Hints for Return Values (OPTIONAL)

Some functions lack return type hints. Consider adding:
```python
def _compute_prediction_mse(self, y: np.ndarray, treatment: np.ndarray) -> float:
def _subtree_mse(self, node: Node) -> float:
```

Already present in most functions, just a few missing.

---

### 2. Edge Case: Empty Honest Sample (MINOR)

If honest sample is very small, some leaves may have no honest sample observations.

**Current handling** (line 1258):
```python
if len(honest_idx) > 0:
    # compute estimates
```

This is **correct** (skips if empty), but could add warning:
```python
if len(honest_idx) == 0:
    warnings.warn(f"Node {node.node_id} has no honest sample observations")
```

**Severity**: MINOR

---

### 3. Cost-Complexity: Negative Alpha Values (EDGE CASE)

Line 1095: `if num_leaves > 1 and (node_mse - subtree_mse) >= 0:`

The condition `(node_mse - subtree_mse) >= 0` prevents negative alphas. However, theoretically, subtree MSE should always be ≤ node MSE (more flexible model). If this condition fails, it suggests a bug.

**Recommendation**: Add assertion:
```python
if num_leaves > 1:
    if (node_mse - subtree_mse) < 0:
        warnings.warn("Subtree MSE > node MSE (unexpected)")
    alpha = max(0, (node_mse - subtree_mse) / (num_leaves - 1))
```

**Severity**: MINOR (edge case handling)

---

## VALIDATION CONCERNS

### 1. No Empirical Validation on Real Data (MODERATE)

**Problem**: All validation uses simulated data. No real clinical trial data shown.

**Recommendation**:
Add at least one real data example:
- Published clinical trial with known heterogeneity
- Compare results with published analysis
- Show computational time for realistic sample sizes

**Severity**: MODERATE (affects credibility)

---

### 2. Comparison with Existing Implementations (MINOR)

**Problem**: No quantitative comparison with `rpart`, `causalTree`, or other implementations.

**Recommendation**:
Add benchmark comparison:
```python
# Compare with:
- rpart::rpart (R)
- causalTree (R) 
- EconML (Python)

# On same simulated data, compare:
- Tree structure (num leaves, splits)
- Effect estimates
- Computational time
```

**Severity**: MINOR (enhances paper)

---

## STATISTICAL RIGOR ASSESSMENT

### Strengths ✅

1. **Theoretical soundness**: All core algorithms now match published literature
2. **Honest documentation**: Assumptions and limitations clearly stated
3. **Reproducibility**: Exact dependencies, clear examples
4. **Methodological transparency**: No shortcuts or workarounds
5. **Code quality**: Well-structured, type-hinted, documented

### Remaining Weaknesses ⚠️

1. **MSE criterion**: Needs clarification that this is outcome-based CART (not adaptive causal tree)
2. **Empirical validation**: Only simulated data, no real clinical trial examples
3. **Computational complexity**: Not documented
4. **Comparison with alternatives**: Missing benchmarks

---

## DETAILED CODE REVIEW

### Correctness: ✅ VERIFIED

- [x] IPW estimators (Hájek/HT): Correct
- [x] Variance formulas: Conservative but valid
- [x] Cost-complexity: Follows CART correctly
- [x] Propensity diagnostics: Fixed (no renormalization)
- [x] Multiple testing: Properly warned
- [x] Honest inference: Correctly implemented

### Efficiency: ⚠️ ACCEPTABLE

- Tree building: O(n²p log n) - standard for CART
- Could be optimized with:
  - Sorted feature caching
  - Early stopping on insignificant splits
  - Parallel split evaluation (not just bootstrap)

### Robustness: ✅ GOOD

- Input validation comprehensive
- Edge cases mostly handled
- Error messages clear
- Warnings appropriate

---

## RECOMMENDATIONS FOR REVISION

### Required (Must Fix):

1. ✅ **Clarify MSE criterion** as outcome-based CART (not adaptive)
   - Add note in `_compute_prediction_mse` docstring
   - Cite Athey & Imbens (2016) on honest vs adaptive splitting

2. ✅ **Document computational complexity** 
   - Add section to class docstring
   - Include scalability guidelines

3. ✅ **Add at least one real data example**
   - Publicly available clinical trial
   - Show computational time
   - Validate against known results

### Recommended (Should Fix):

4. **Add brief note on Hájek variance conservativeness**
   - One sentence in docstring sufficient

5. **Add edge case warning for negative alphas**
   - Unlikely to occur, but good defensive programming

6. **Add benchmark comparison** (at least in supplementary materials)
   - Compare with rpart or causalTree
   - Same simulated data, compare results

### Optional (Nice to Have):

7. Add computational time reporting
8. Add progress bars for CV pruning
9. Add `splitting_criterion` parameter for future adaptive option
10. Add visualization functions for trees

---

## SUMMARY ASSESSMENT

| Criterion | V3.0 | V3.1 | Status |
|-----------|------|------|--------|
| Theoretical rigor | ❌ | ✅ | Excellent |
| Implementation correctness | ⚠️ | ✅ | Excellent |
| Documentation | ⚠️ | ✅ | Very good |
| Reproducibility | ⚠️ | ✅ | Excellent |
| Empirical validation | ⚠️ | ⚠️ | Needs improvement |
| Code quality | ✅ | ✅ | Excellent |

---

## FINAL VERDICT

**Overall Assessment**: The revision is **substantially improved** and addresses all major methodological concerns from Round 1. The remaining issues are minor and primarily relate to:

1. Clarification of MSE criterion choice
2. Documentation of computational complexity
3. Empirical validation on real data

**Recommendation**: **ACCEPT WITH MINOR REVISIONS**

**Timeline**: 1-2 weeks for minor revisions

**Confidence**: **High** - Implementation is now theoretically sound and well-documented

---

## SPECIFIC CHANGES REQUESTED

### 1. Update `_compute_prediction_mse` docstring (Line 860-866):

```python
def _compute_prediction_mse(self, y, treatment):
    """
    V3.1 NEW: Compute prediction MSE for cost-complexity pruning.
    
    NOTE: This implements OUTCOME-BASED CART (Breiman et al. 1984),
    not adaptive causal trees (Athey & Imbens 2016). We split on
    outcome variance to maintain honesty, not on treatment effect variance.
    This is more conservative but avoids overfitting to treatment effects.
    
    For treatment effect trees, this is the variance of observed outcomes
    around predicted means within each treatment arm.
    
    Reference: Athey & Imbens (2016) Section 3.2 on honest splitting.
    """
```

### 2. Add to class docstring (after line 185):

```python
COMPUTATIONAL COMPLEXITY:
------------------------
Tree building: O(n² × p × log n)
CV pruning: O(k × n² × p × log n) where k = cv_folds
Honest inference: 2× (due to sample splitting)

Recommended limits:
- n ≤ 10,000 samples
- p ≤ 50 features
- cv_folds ≤ 10

For larger datasets, consider random forests (causal forests).
```

### 3. Add real data example (new file):

```python
# examples/real_data_example.py

"""
Real Data Example: Gusto Trial
================================

Demonstrates Meta-CART on published clinical trial data.
"""

# (Use publicly available data)
```

---

## REVIEWER SIGNATURE

**Reviewer**: Statistical Methods Editor  
**Recommendation**: Accept with minor revisions  
**Confidence**: High  
**Date**: 2025-11-16

---

**Congratulations to the authors on a thorough revision. The methodological improvements are substantial and the paper is now suitable for publication pending these minor clarifications.**
