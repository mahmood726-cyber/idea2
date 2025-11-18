# Statistical Verification Summary
## Meta-CART Synthesis Document

**Date**: 2025-11-18
**Documents Reviewed**: SYNTHESIS.md, validation_v3.py, meta_cart_v3.py

---

## QUICK VERDICT

**❌ DATA AND STATS DO NOT CHECK OUT**

**2 out of 5 validation claims are FALSE**, contradicted by the authors' own validation code.

---

## CLAIM-BY-CLAIM VERIFICATION

### ✅ CLAIM 1: Power (TRUE)

| Aspect | Synthesis Claims | Validation Shows | Status |
|--------|-----------------|------------------|--------|
| Detection rate | **"exceeding 95 percent"** | **100%** (20/20 simulations) | ✅ **TRUE** |
| Assessment | Conservative, accurate claim | Excellent power in simulations | **VERIFIED** |

---

### ❌ CLAIM 2: Type I Error Control (FALSE)

| Aspect | Synthesis Claims | Validation Shows | Status |
|--------|-----------------|------------------|--------|
| False positive rate | **"maintains nominal false positive rates"** (implies ~5%) | **30%** (6/20 simulations) | ❌ **FALSE** |
| Multiple testing | "when multiple testing corrections are applied" | Holm applied but insufficient | **FAILS** |
| Magnitude of error | Expected: 5% | Observed: 6× higher | **SEVERE** |

**Example False Positive**:
```
Null simulation (no true heterogeneity):
- Adjusted p-value = 0.043 < 0.05 → FALSE POSITIVE
- This happens in 30% of null cases, not 5%
```

**Impact**: Users will find spurious subgroups in 3 out of 10 applications.

---

### ❌ CLAIM 3: Confidence Interval Coverage (FALSE)

| Aspect | Synthesis Claims | Validation Shows | Status |
|--------|-----------------|------------------|--------|
| Coverage rate | **"95 percent confidence intervals achieve their nominal coverage"** | **62%** (31/50 CIs) | ❌ **FALSE** |
| Deviation | Expected: 95% | 33 percentage points too low | **SEVERE** |
| Implication | "Valid statistical inference" | CIs far too narrow | **INVALID** |

**What This Means**:
- CIs should contain true effect 95 times out of 100
- Actually contain true effect only 62 times out of 100
- Uncertainty is severely underestimated

**Impact**: Users will have false confidence in effect estimates.

---

### ✅ CLAIM 4: IPW Bias Reduction (TRUE)

| Aspect | Synthesis Claims | Validation Shows | Status |
|--------|-----------------|------------------|--------|
| Bias reduction | **"60-70 percent"** | **62.2%** | ✅ **TRUE** |
| Naive bias | Not specified | 0.440 | |
| IPW bias | Not specified | 0.166 | |
| Assessment | Within claimed range | Accurate claim | **VERIFIED** |

---

### ⚠️ CLAIM 5: Bootstrap Stability (MISLEADING)

| Aspect | Synthesis Claims | Validation Shows | Status |
|--------|-----------------|------------------|--------|
| Reproducibility | **"stable subgroups showing high co-occurrence frequencies"** | **Mean similarity: 0.0** | ⚠️ **MISLEADING** |
| Stable subgroups | Implies many | 0 found (freq ≥ 50%) | **OPPOSITE** |
| Assessment | Implies high stability typical | Shows low stability typical | **MISLEADING** |

**What This Means**:
- The mechanism works (20/20 bootstraps successful)
- But results show **instability**, not stability
- Claim implies wrong expectation

---

## METHODOLOGY CLAIMS: ALL VERIFIED ✅

| Feature | Claimed | Code Verified | Status |
|---------|---------|---------------|--------|
| Splitting criterion | Weighted variance | Lines 763-766 ✅ | ✅ TRUE |
| Honest inference | 50/50 split | Default = 0.5 ✅ | ✅ TRUE |
| Multiple testing | Holm, Bonferroni, FDR | All implemented ✅ | ✅ TRUE |
| Binary outcomes | Risk differences | Lines 609-643 ✅ | ✅ TRUE |
| Propensity scores | IPW + diagnostics | Lines 327-423 ✅ | ✅ TRUE |

---

## INDEPENDENT SIMULATION RESULTS

Ran fresh simulations to verify all claims:

### Type I Error Test (20 simulations, null hypothesis)
```
Expected false positive rate: 5%
Observed false positive rate: 30%
Status: ❌ FAIL (6-fold inflation)
```

### Power Test (20 simulations, strong heterogeneity)
```
Expected power: ≥95%
Observed power: 100%
Status: ✅ PASS
```

### CI Coverage Test (20 simulations, known effects)
```
Expected coverage: 95%
Observed coverage: 62%
Status: ❌ FAIL (33 points below nominal)
```

### IPW Bias Test (15 simulations, confounding)
```
Naive bias: 0.440
IPW bias: 0.166
Reduction: 62.2%
Expected: 60-70%
Status: ✅ PASS
```

---

## OVERALL ASSESSMENT

### Statistical Accuracy Score: 2/5

| Claim | Status |
|-------|--------|
| Power | ✅ TRUE |
| Type I Error | ❌ FALSE |
| CI Coverage | ❌ FALSE |
| IPW Bias | ✅ TRUE |
| Bootstrap | ⚠️ MISLEADING |

### Other Aspects

| Category | Score | Notes |
|----------|-------|-------|
| Writing Quality | 9/10 | Clear and well-organized |
| Methodology Description | 10/10 | All verified against code |
| References | 10/10 | All 6 properly cited |
| Figures | 7/10 | Good but subjective comparisons |
| Word Count | 1,077/1,000 | 7.7% over target |

---

## CRITICAL ISSUES

### Issue 1: Type I Error Inflation
- **Claimed**: "maintains nominal false positive rates"
- **Reality**: 30% false positive rate (6× too high)
- **Severity**: CRITICAL - fundamental statistical failure

### Issue 2: CI Under-Coverage
- **Claimed**: "95 percent confidence intervals achieve their nominal coverage"
- **Reality**: 62% coverage (33 points below nominal)
- **Severity**: CRITICAL - invalid inference

### Issue 3: Misleading Bootstrap Description
- **Claimed**: "high co-occurrence frequencies"
- **Reality**: 0.0 mean similarity, zero stable subgroups
- **Severity**: MODERATE - sets wrong expectations

---

## WHAT NEEDS TO CHANGE

### Required Corrections

**1. Type I Error Claim** (Line 17):

❌ **REMOVE**: "the method maintains nominal false positive rates when multiple testing corrections are applied"

✅ **REPLACE WITH**: "Type I error control remains challenging, with observed false positive rates of ~30% in simulation studies despite Holm correction. Users should validate findings in independent datasets."

**2. CI Coverage Claim** (Line 17):

❌ **REMOVE**: "95 percent confidence intervals achieve their nominal coverage for honest estimates"

✅ **REPLACE WITH**: "Confidence interval coverage in simulations falls below nominal levels (~62%), suggesting uncertainty may be underestimated. Bootstrap confidence intervals are recommended for more reliable inference."

**3. Bootstrap Stability Claim** (Line 17):

❌ **REMOVE**: "with stable subgroups showing high co-occurrence frequencies across resampled datasets"

✅ **REPLACE WITH**: "Bootstrap stability analysis can reveal low reproducibility in subgroup structures, emphasizing the importance of external validation."

---

## THE BOTTOM LINE

### Question: Do the data and stats check out?

### Answer: **NO**

- ✅ 2 claims are TRUE (Power, IPW)
- ❌ 2 claims are FALSE (Type I error, CI coverage)
- ⚠️ 1 claim is MISLEADING (Bootstrap stability)

### Consequence

**The synthesis makes quantitative statistical claims that are contradicted by validation data.** This is a serious integrity issue that blocks publication.

### Recommendation

**REJECT** until false claims are corrected to accurately reflect the method's actual statistical properties.

---

## FILES CREATED

1. **PEER_REVIEW_SYNTHESIS.md** - Initial comprehensive peer review
2. **EDITORIAL_REVIEW_SYNTHESIS.md** - Detailed editorial review with verification
3. **STATISTICAL_VERIFICATION_SUMMARY.md** - This summary (quick reference)

All committed and pushed to: `claude/write-synthesis-figures-01Uw8PDLyomDEoAJhhBmq1jU`
