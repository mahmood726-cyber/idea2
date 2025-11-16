# Peer Review: Meta-CART V2.0 - "All Issues Fixed"

**Reviewer:** Expert in Causal Inference & Clinical Trial Methodology
**Journal:** Research Synthesis Methods
**Manuscript:** "Meta-CART V2.0: Complete Implementation with All Critical Fixes"

---

## OVERALL RECOMMENDATION

**Decision: MAJOR REVISION STILL REQUIRED**

**Summary:** While the authors claim all critical issues have been addressed, **this is misleading**. V2 makes substantial improvements over V1, particularly in implementing true CV pruning and multiple testing corrections. However, critical gaps remain:

1. **Bootstrap stability is NOT implemented** despite prominent claims
2. **Propensity score implementation has issues**
3. **No empirical validation** (simulation or real data)
4. **File is literally incomplete** (truncated with comment "code continues...")
5. **Survival outcomes claimed but not implemented**

**V2 is better than V1, but still not publication-ready.**

---

## DETAILED ASSESSMENT

### ✅ **What's Actually Fixed and Working Well**

#### 1. Cost-Complexity Cross-Validation Pruning ✅ **IMPLEMENTED**

**Lines 675-752:** TRUE CV pruning is now implemented correctly.

```python
def _cv_prune_tree(self, X, y, treatment, propensity, full_tree):
    # Generate alpha sequence (lines 754-796)
    alpha_sequence = self._generate_alpha_sequence(tree)

    # K-fold cross-validation (lines 700-735)
    for train_idx, val_idx in kf.split(indices, treatment):
        fold_tree = self._build_tree(X_train, y_train, ...)
        for alpha in alpha_sequence:
            pruned_tree = self._prune_with_alpha(fold_tree, alpha)
            score = self._evaluate_tree(pruned_tree, X_val, ...)

    # Select best alpha (lines 740-747)
    best_alpha = alpha_sequence[argmax(cv_scores)]
    return self._prune_with_alpha(full_tree, best_alpha)
```

**Assessment:**
- ✅ Alpha generation uses cost-complexity formula: α = (R_node - R_subtree)/(|T| - 1)
- ✅ K-fold CV properly implemented with StratifiedKFold
- ✅ Evaluation metric uses squared error (appropriate)
- ✅ Stores cv_scores_ and best_alpha_ for inspection

**Minor Issues:**
- ⚠️ No handling of ties in alpha selection
- ⚠️ Evaluation metric (line 878) uses SE² rather than actual prediction error
- ⚠️ No "one SE rule" option (select simpler tree within 1 SE of best)

**Verdict:** This is a **significant improvement**. V1's "fake CV" is replaced with real implementation. Grade: **A-**

---

#### 2. Multiple Testing Corrections ✅ **IMPLEMENTED**

**Lines 997-1055:** Bonferroni, Holm, and FDR methods correctly implemented.

```python
def _apply_multiple_testing_correction(self):
    # Collect leaf p-values
    p_values = [leaf.p_value for all leaves]

    if method == 'bonferroni':
        adjusted_p = min(p * k, 1.0)
        alpha_adj = alpha / k

    elif method == 'holm':
        # Holm-Bonferroni sequential (lines 1022-1028)
        for i, idx in enumerate(sorted_idx):
            adjusted_p[idx] = min(p[idx] * (k - i), 1.0)

    elif method == 'fdr':
        # Benjamini-Hochberg (lines 1030-1041)
        bh_values = sorted_p * k / (rank + 1)

    # Widen CIs (lines 1050-1054)
    z_adj = norm.ppf(1 - alpha_adj/2)
    ci_adj = effect ± z_adj * SE
```

**Assessment:**
- ✅ Bonferroni: Correct implementation
- ✅ Holm: Correct sequential procedure
- ✅ FDR: Correct Benjamini-Hochberg procedure
- ✅ CIs properly widened based on adjusted alpha
- ✅ Stores both raw and adjusted values

**Issues:**
- ⚠️ Holm implementation (line 1026): Should use monotonicity correction
  - Current: `adjusted_p[idx] = min(p[idx] * (k - i), 1.0)`
  - Better: `adjusted_p[idx] = max(adjusted_p[0:idx], p[idx] * (k - i))`
  - Without monotonicity, adjusted p-values may not be properly ordered

**Verdict:** Mostly correct implementation. The Holm procedure should enforce monotonicity. Grade: **B+**

---

#### 3. Stratified Sample Splitting ✅ **IMPLEMENTED**

**Lines 273-333:** Sample splitting now stratifies by treatment AND covariates.

```python
def _stratified_split(self, X, y, treatment, propensity):
    # Create strata (lines 280-288)
    if propensity available:
        propensity_quintiles = pd.qcut(propensity, q=5)
    else:
        # Use PC1 as proxy
        pc1 = X @ first_principal_component
        propensity_quintiles = pd.qcut(pc1, q=5)

    strata = treatment * 10 + propensity_quintiles

    # Stratified split (lines 293-297)
    build_idx, honest_idx = train_test_split(
        indices, stratify=strata, test_size=1-honest_ratio
    )
```

**Assessment:**
- ✅ Stratification by treatment × propensity quintiles
- ✅ Fallback to PC1 when propensity not available
- ✅ Checks treatment balance post-split (lines 318-323)
- ✅ Uses sklearn's train_test_split (well-tested)

**Issues:**
- ⚠️ PC1 calculation (line 286): Uses only first component
  - May not capture full covariate distribution
  - Could use propensity score estimated on X even when use_propensity=False
- ⚠️ Warning threshold (5%) may be too permissive
  - Recommend < 2% imbalance for honest inference validity

**Verdict:** Good implementation, significantly better than V1. Grade: **A-**

---

#### 4. Welch-Satterthwaite Degrees of Freedom ✅ **FIXED**

**Lines 466-484:** Now uses correct df for unequal variances.

```python
# Welch-Satterthwaite degrees of freedom (lines 471-477)
n1, n2 = len(y_treated), len(y_control)
s1_sq, s2_sq = var_treated, var_control

df = ((s1_sq/n1 + s2_sq/n2)**2) / \
     ((s1_sq/n1)**2/(n1-1) + (s2_sq/n2)**2/(n2-1))
df = max(1, int(df))

p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))
```

**Assessment:**
- ✅ Correct Welch-Satterthwaite formula
- ✅ Handles edge case (df >= 1)
- ✅ Uses t-distribution (not normal)

**Verdict:** Correctly implemented. Grade: **A**

---

#### 5. Input Validation ✅ **IMPLEMENTED**

**Lines 185-253:** Comprehensive validation added.

```python
def _validate_inputs(self, X, y, treatment):
    # Type conversion (lines 187-189)
    X = np.asarray(X, dtype=float)  # Explicit dtype
    y = np.asarray(y, dtype=float)
    treatment = np.asarray(treatment, dtype=int)

    # Shape checks (lines 192-194)
    if X.shape[0] != y.shape[0] or X.shape[0] != treatment.shape[0]:
        raise ValueError("Shape mismatch")

    # NaN/Inf checks (lines 197-202)
    if np.any(np.isnan(X)) or np.any(np.isinf(X)):
        raise ValueError("X contains NaN or Inf")

    # Treatment validation (lines 205-209)
    unique_treatment = np.unique(treatment)
    if not set(unique_treatment).issubset({0, 1}):
        raise ValueError(f"Treatment must be 0/1, got {unique_treatment}")

    # Sample size warning (lines 218-223)
    if X.shape[0] < 100:
        warnings.warn("Sample size small. Recommend n >= 200.")
```

**Assessment:**
- ✅ Type checking with error handling
- ✅ Shape validation
- ✅ NaN/Inf detection
- ✅ Treatment binary validation
- ✅ Sample size warnings
- ✅ Outcome type validation (lines 226-229)

**Issues:**
- ⚠️ No check for zero variance features
- ⚠️ No check for perfect collinearity
- ⚠️ No validation of propensity score range [0, 1]

**Verdict:** Much better than V1. Could be even more thorough. Grade: **B+**

---

#### 6. Better Hyperparameter Defaults ✅ **UPDATED**

```python
# V2 defaults (lines 95-99)
min_samples_leaf = 50          # was 30
min_samples_treatment_leaf = 25 # was 10
min_samples_control_leaf = 25   # was 10
```

**Power Analysis:**
- With n=50 (25 per arm), d=0.5: Power ≈ 58%
- With n=100 (50 per arm), d=0.5: Power ≈ 85%

**Assessment:**
- ✅ More conservative than V1
- ✅ Reduces spurious subgroups
- ⚠️ Still somewhat underpowered for medium effects
- ⚠️ No documentation of power calculation

**Verdict:** Improvement, but could be even more conservative. Grade: **B**

---

### ⚠️ **What's Partially Implemented or Problematic**

#### 7. Propensity Score Adjustment ⚠️ **ISSUES**

**Lines 255-271:** Propensity estimation implemented, but with concerns.

```python
def _estimate_propensity(self, X, treatment):
    model = LogisticRegression(random_state=self.random_state, max_iter=1000)
    model.fit(X, treatment)
    propensity_scores = model.predict_proba(X)[:, 1]

    # Trim extreme propensities
    propensity_scores = np.clip(propensity_scores, 0.01, 0.99)

    return propensity_scores
```

**IPW Implementation (lines 436-463):**
```python
if propensity is not None:
    weights_treated = 1.0 / propensity[T==1]
    weights_control = 1.0 / (1 - propensity[T==0])

    # Normalize weights
    weights_treated = weights_treated / sum(weights_treated) * n_treated
    weights_control = weights_control / sum(weights_control) * n_control

    effect = weighted_mean(y_treated, weights_treated) - \
             weighted_mean(y_control, weights_control)
```

**Critical Issues:**

1. **No Balance Checking:**
   - After weighting, should check covariate balance
   - Standard practice: compute standardized mean differences
   - Missing diagnostics for propensity score adequacy

2. **No Overlap Assessment:**
   - Should check positivity assumption: 0 < e(X) < 1
   - Trimming (0.01, 0.99) is arbitrary
   - Better: Trim at percentiles (e.g., 5th and 95th)

3. **Weight Normalization:**
   - Lines 453-454: Normalizes weights to sum to original sample size
   - This changes the estimand! Should normalize to sum to 1
   - Creates bias in effect estimate

4. **No Doubly-Robust Option:**
   - Current: IPW only (inefficient, sensitive to model misspecification)
   - Best practice: AIPW (augmented IPW) combining outcome regression + propensity
   - Missing: Outcome regression component

5. **Model Specification:**
   - Logistic regression with all features linearly
   - No interaction terms, no non-linear terms
   - May underfit, leading to residual confounding

6. **Variance Estimation:**
   - Lines 458-463: Uses weighted variance
   - Should use robust (sandwich) variance estimator
   - Current SE may be too small (anticonservative)

**Verdict:** Implementation has **serious issues**. Works for simple cases but can give biased results. **Not suitable for real observational studies** without major improvements. Grade: **D+**

---

#### 8. Binary Outcomes ⚠️ **CLAIMED BUT NOT VISIBLE**

**Claims (line 14):** "Binary and survival outcome support"

**Reality:**
- Parameter exists: `outcome_type='continuous'` (line 109)
- Type validation exists (lines 226-229)
- But I cannot find the actual implementation!

**Search Results:**
```python
# Lines 226-229
if self.outcome_type == 'binary':
    if not set(np.unique(y)).issubset({0, 1}):
        raise ValueError("Binary outcomes must be 0/1")
```

**Where's the implementation?**
- Treatment effect computation (lines 419-484) only handles continuous
- No risk difference calculation visible
- No binomial variance formula

**Possible locations:**
- May be in _compute_treatment_effect() but I don't see conditional logic on outcome_type
- May be planned but not implemented

**Verdict:** **CLAIMED BUT NOT FOUND** in code. Grade: **F (if not implemented)**

---

### ❌ **What's CLAIMED but NOT Implemented**

#### 9. Bootstrap Stability ❌ **NOT IMPLEMENTED**

**Claims (lines 8, 12):**
- "Complete bootstrap stability metrics"
- "Optimized computational performance" (implying parallelization)

**Reality (lines 1220-1221):**
```python
# Bootstrap stability class would continue here...
# [Code continues but truncated for length - would include complete bootstrap implementation]
```

**CRITICAL ISSUE:** The file is **literally incomplete**!

The bootstrap stability class is **not implemented**. This is mentioned in FIXES_IMPLEMENTED.md as "complete" but the code file is truncated.

**What's missing:**
- Class BootstrapStability (entirely absent)
- Subgroup co-occurrence matrix
- Effect distributions
- Tree similarity metrics
- Split stability scores
- Parallel bootstrap implementation

**Impact:**
- Cannot assess reliability of discovered subgroups
- Cannot compute bootstrap SEs
- Cannot validate variable importance
- Major gap in methodology

**Verdict:** **CRITICAL FAILURE**. Prominently claimed but not delivered. Grade: **F**

---

#### 10. Survival Outcomes ❌ **NOT IMPLEMENTED**

**Claims (line 14):** "Binary and survival outcome support"

**Reality:**
- No survival outcome handling visible in code
- No Cox model integration
- No hazard ratio estimation
- Parameter accepts 'survival' but no implementation follows

**Verdict:** **FALSE CLAIM**. Grade: **F**

---

#### 11. Parallel Processing ⚠️ **IMPORTS BUT DOESN'T USE**

**Claims (line 17):** "Optimized computational performance"

**Code (line 36):**
```python
from joblib import Parallel, delayed
```

**Reality:**
- Import exists but never used in the file!
- No parallelization of bootstrap (because bootstrap class doesn't exist)
- No parallelization of CV folds
- n_jobs parameter exists (line 121) but is never referenced in code

**Search for n_jobs usage:** None found in algorithmic code

**Verdict:** **IMPORTED BUT NOT USED**. Another false claim. Grade: **F**

---

## CRITICAL PROBLEMS WITH SUBMITTED MANUSCRIPT

### 1. **File is Incomplete** 🚨

Lines 1220-1221:
```python
# Bootstrap stability class would continue here...
# [Code continues but truncated for length - would include complete bootstrap implementation]
```

**This is unacceptable for a peer-reviewed publication.**

The authors submitted an **incomplete implementation** with a comment saying the rest "would" be included. This suggests:

a) The code was never finished, OR
b) The authors deliberately truncated it

Either way, this is a major red flag.

---

### 2. **Misleading Claims** 🚨

The documentation makes **multiple false claims**:

| Claim | Reality |
|-------|---------|
| "Complete bootstrap stability metrics" | Not implemented at all |
| "Binary and survival outcome support" | Not found in code |
| "Optimized computational performance" | joblib imported but never used |
| "All critical issues fixed" | Bootstrap stability missing |

**This crosses the line from "incomplete implementation" to "misleading the reviewers."**

---

### 3. **Inconsistency Between Documentation and Code** 🚨

**FIXES_IMPLEMENTED.md** (submitted alongside) claims:

> "8. Complete Bootstrap Stability ✅ COMPLETE"
> - Subgroup co-occurrence matrix
> - Effect distributions across bootstraps
> - Tree similarity metrics
> - Split stability scores

**BUT THE CODE LITERALLY SAYS:**

> "Bootstrap stability class would continue here..."

**This is a major integrity issue.**

---

## ASSESSMENT BY CLAIMED FIX

| Fix | Claimed | Actually Done | Quality | Grade |
|-----|---------|---------------|---------|-------|
| 1. CV Pruning | ✅ Yes | ✅ Yes | Good | **A-** |
| 2. Multiple Testing | ✅ Yes | ✅ Yes | Good | **B+** |
| 3. Stratified Splitting | ✅ Yes | ✅ Yes | Good | **A-** |
| 4. Welch df | ✅ Yes | ✅ Yes | Correct | **A** |
| 5. Input Validation | ✅ Yes | ✅ Yes | Good | **B+** |
| 6. Propensity Scores | ✅ Yes | ⚠️ Partial | Issues | **D+** |
| 7. Binary Outcomes | ✅ Yes | ❓ Unknown | Can't find | **?/F** |
| 8. Bootstrap Stability | ✅ Yes | ❌ NO | Missing | **F** |
| 9. Survival Outcomes | ✅ Yes | ❌ NO | Missing | **F** |
| 10. Parallelization | ✅ Yes | ❌ NO | Not used | **F** |

**Pass Rate:** 5/10 properly implemented
**Fail Rate:** 3/10 not implemented
**Partial:** 1/10 has issues
**Unknown:** 1/10 can't verify

---

## COMPARISON: V1 vs V2

| Category | V1 | V2 | Change |
|----------|----|----|--------|
| **CV Pruning** | ❌ Fake | ✅ Real | **+3** ✅ |
| **Multiple Testing** | ❌ None | ✅ Yes | **+3** ✅ |
| **Stratified Split** | ⚠️ Partial | ✅ Good | **+2** ✅ |
| **Welch df** | ❌ Wrong | ✅ Correct | **+1** ✅ |
| **Input Validation** | ⚠️ Minimal | ✅ Good | **+2** ✅ |
| **Propensity** | ❌ None | ⚠️ Issues | **+1** ⚠️ |
| **Bootstrap** | ⚠️ Partial | ❌ Missing | **-1** ❌ |
| **Binary Outcomes** | ❌ None | ❓ Unknown | **0** ❓ |
| **Documentation** | ⚠️ Gaps | ❌ Misleading | **-2** ❌ |
| **Integrity** | ✅ Honest | ❌ False claims | **-3** ❌ |

**Net Change:** +6 technical, -6 integrity = **0 overall**

---

## REVISED SCORES

### V2 Technical Implementation (If complete):

| Category | V1 | V2 (as submitted) | V2 (if complete) |
|----------|----|--------------------|------------------|
| Methodology | 5/10 | 6/10 | 8/10 |
| Implementation | 5/10 | 5/10 | 8/10 |
| Statistical Rigor | 5/10 | 7/10 | 8/10 |
| Code Quality | 8/10 | 7/10 | 8/10 |
| Validation | 1/10 | 1/10 | 3/10 |
| **Integrity** | **10/10** | **3/10** | **?** |
| **OVERALL** | **5.8/10** | **5.5/10** | **7.5/10** |

**Paradox:** V2 has better algorithms but **worse integrity** due to false claims.

---

## SPECIFIC TECHNICAL ISSUES IN V2 CODE

### Issue 1: Cost-Complexity Alpha Calculation

**Line 774:**
```python
node_error = node.treatment_effect_se ** 2 * node.n_samples
```

**Problem:** Uses SE² × n as "error", but SE already accounts for sample size!
- SE = SD/√n, so SE² = SD²/n
- SE² × n = SD²
- This makes alpha scale with SD², not total variance

**Impact:** Alpha values may not be optimally scaled

**Better:**
```python
node_error = node.treatment_effect_se ** 2  # Already scaled by n
```

---

### Issue 2: Holm Procedure Monotonicity

**Lines 1022-1026:**
```python
for i, idx in enumerate(sorted_idx):
    adjusted_p[idx] = min(p_values[idx] * (len(leaves) - i), 1.0)
```

**Problem:** Doesn't enforce monotonicity

**Standard Holm:** Adjusted p-values must be non-decreasing

**Fix:**
```python
for i, idx in enumerate(sorted_idx):
    p_adj = p_values[idx] * (len(leaves) - i)
    if i > 0:
        p_adj = max(p_adj, adjusted_p[sorted_idx[i-1]])
    adjusted_p[idx] = min(p_adj, 1.0)
```

---

### Issue 3: Propensity Weight Normalization

**Lines 453-454:**
```python
weights_treated = weights_treated / weights_treated.sum() * len(y_treated)
weights_control = weights_control / weights_control.sum() * len(y_control)
```

**Problem:** This changes the estimand!

**Standard IPW:**
```python
# Weights should sum to population size, NOT sample size per group
weights_treated = weights_treated / weights_treated.sum() * N
weights_control = weights_control / weights_control.sum() * N
# where N is total population size
```

**Or better (Horvitz-Thompson):**
```python
# Don't normalize at all
effect = sum(Y*T/e(X)) / N - sum(Y*(1-T)/(1-e(X))) / N
```

---

### Issue 4: Missing Survival Implementation

**Parameter defined (line 109):**
```python
outcome_type: Literal['continuous', 'binary', 'survival'] = 'continuous'
```

**But no handling for 'survival' anywhere in code!**

If someone sets `outcome_type='survival'`, the code will:
1. Pass validation (line 229 only checks binary)
2. Proceed with continuous outcome calculations
3. Give **wrong results** without error

**This is dangerous.**

---

### Issue 5: Evaluation Metric for CV

**Line 878:**
```python
error = se ** 2 * len(y_leaf)
```

**Problem:** Uses SE² as error metric

**Better metrics:**
- Mean squared error of predictions
- Likelihood on validation fold
- Actual treatment effect accuracy if ground truth available

**Current metric conflates:**
- Prediction accuracy (what we want)
- Sample size (what we don't want to penalize)

---

## ADDITIONAL CONCERNS

### 1. No Unit Tests for New Functions

V1 had `test_meta_cart.py` with 8 tests.

**V2 has:**
- No tests for CV pruning
- No tests for multiple testing correction
- No tests for propensity score weighting
- No tests for stratified splitting

**Critical:** New complex code should be tested!

---

### 2. No Simulation Validation

**Claims:** "Type I error ≈ 5% with Holm correction"

**Evidence:** None. No simulation study provided.

**Required:**
```python
# Pseudocode for validation
for sim in 1:1000:
    X, y, T = generate_constant_effect_data()
    model = MetaCART(multiple_testing_method='holm')
    model.fit(X, y, T)
    effects = model.get_subgroup_effects(use_adjusted=True)
    false_positives[sim] = sum(effects['adjusted_p_value'] < 0.05)

print(f"Empirical Type I error: {mean(false_positives)}")
# Should be ≈ 5% if correction works
```

**This is standard practice** for methods papers.

---

### 3. Computational Complexity

**CV Pruning complexity:**
- K folds × |alpha sequence| × tree building
- For K=5, |alpha|=10, this is **50 trees**
- If original tree has depth 4, that's potentially **50 × 2⁴ = 800 nodes**

**No discussion of:**
- Computational cost
- Scalability limits
- Approximations available

---

### 4. Memory Management

**Line 693:**
```python
alpha_sequence = self._generate_alpha_sequence(copy.deepcopy(full_tree))
```

**Line 731:**
```python
pruned_tree = self._prune_with_alpha(copy.deepcopy(fold_tree), alpha)
```

**Concern:** Deep copying entire trees for each alpha

For large trees:
- Memory usage: O(K × |alpha| × tree size)
- For K=5, |alpha|=10, this is 50 copies of the tree
- Could exhaust memory for large datasets

**Better:** In-place pruning with tree restoration

---

## WHAT'S NEEDED FOR PUBLICATION

### Essential (Must Fix):

1. **Complete the implementation**
   - Actually implement BootstrapStability class
   - Implement binary outcome handling
   - Remove survival claims or implement it
   - Actually use joblib for parallelization

2. **Fix propensity score implementation**
   - Add covariate balance checking
   - Fix weight normalization
   - Add overlap assessment
   - Consider doubly-robust estimation

3. **Fix technical issues**
   - Correct Holm monotonicity
   - Fix alpha calculation in cost-complexity
   - Improve CV evaluation metric
   - Add survival support or remove claim

4. **Add validation**
   - Unit tests for all new functions
   - Simulation study (Type I error, power)
   - At least 1 real data application

5. **Fix documentation integrity**
   - Remove false claims
   - Be honest about what's implemented
   - Don't submit incomplete code

### Highly Recommended:

6. Add doubly-robust estimation
7. Optimize memory usage (avoid deep copies)
8. Add computational complexity analysis
9. Parallel CV implementation
10. Better propensity model specification

---

## FINAL VERDICT

### Current State (V2 as submitted):

**Technical Quality:** 6.5/10 (Better algorithms than V1)
**Completeness:** 5/10 (Major features missing)
**Integrity:** 3/10 (False claims, incomplete submission)
**Publication Readiness:** 4/10 (Not ready)

**Overall: 5.5/10 (Still C grade)**

---

### If Properly Completed:

**Technical Quality:** 8.5/10
**Completeness:** 8/10
**Integrity:** 8/10 (if honest about limitations)
**Publication Readiness:** 7.5/10

**Overall: 8/10 (B grade, minor revision)**

---

## RECOMMENDATION

**MAJOR REVISION REQUIRED**

**Specific Actions:**

1. **Complete the implementation** (2-3 months)
   - Finish BootstrapStability class
   - Implement binary outcomes properly
   - Fix propensity score issues
   - Actually use parallelization

2. **Validate empirically** (1 month)
   - Simulation study
   - Real data application
   - Unit tests

3. **Fix integrity issues** (1 week)
   - Remove false claims
   - Update documentation
   - Resubmit complete code

**Timeline:** 3-4 months for resubmission

**Encouragement:** The core improvements (CV pruning, multiple testing) are solid. Finish the work properly and this could be publication-quality.

**Alternative:** Submit as-is to arXiv as "work in progress" but **not** to peer-reviewed journal until complete.

---

## COMPARISON WITH V1 REVIEW

**V1 Verdict:** Major revision (incomplete but honest)
**V2 Verdict:** Major revision (better algorithms but incomplete + false claims)

**Key Difference:**
- V1 was incomplete but **transparent** about limitations
- V2 claims to be complete but **misleads** about what's implemented

**Irony:** V2 technically regresses on integrity despite better algorithms.

---

## QUESTIONS FOR AUTHORS

1. **Why submit incomplete code?** The file literally ends with "would continue here..."

2. **Why claim bootstrap stability is complete** when the class doesn't exist?

3. **Where is the binary outcome implementation?** Parameter accepts 'binary' but where's the code?

4. **Why import joblib if never used?** Is parallelization implemented or not?

5. **Have you tested the propensity score implementation?** It has several issues that would bias results.

6. **Have you validated Type I error control?** Simulation study needed.

7. **What's the actual timeline?** When will you finish this work?

---

## CONCLUSION

**V2 makes important algorithmic improvements** over V1, particularly:
- ✅ True CV pruning
- ✅ Multiple testing corrections
- ✅ Better statistical inference

**BUT V2 has serious problems:**
- ❌ Incomplete submission (file truncated)
- ❌ False claims (bootstrap, binary outcomes, parallelization)
- ❌ Propensity score implementation has bugs
- ❌ No empirical validation

**Bottom Line:** V2 is **not ready for publication** and requires major revision. The authors should:
1. Complete the implementation honestly
2. Validate their claims empirically
3. Fix the technical issues
4. Resubmit when truly ready

**Estimated additional work:** 3-4 months

**Confidence in review:** 95% (very confident - code evidence is clear)

---

**Review Date:** 2025-11-16
**Reviewer:** Expert in Causal Inference & Clinical Trials
**Conflicts:** None

---

*This review was conducted to provide honest feedback. While V2 shows promise, submitting incomplete code with false claims is unacceptable for peer-reviewed publication.*
