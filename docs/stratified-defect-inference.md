# Stratified defect-inference correction — 2026-10-11

## Method and audit

The MH risk ratio was correct: sum(a·n0/t) / sum(b·n1/t), where a/b
are rejected flagged/clean reports and n1/n0 their totals. Strata without both
exposure groups contribute zero to both sums. The former marginal z used a
different comparison and is removed, not renamed as adjusted inference.

For each stratum, E[a]=n1·r/t and Var(a)=n1·n0·r·(t−r)/(t²·(t−1)),
where r=a+b. The signed CMH score is sum(a−E[a])/sqrt(sum Var(a)), without
continuity correction. The primary exact p conditions on each stratum's margins:
convolve Hypergeom(t,r,n1) distributions and double the smaller inclusive tail
of sum(a), capped at 1. This tail convention is explicit; probability-ordering
exact tests can differ. It needs no asymptotic large-cell approximation.

The null is independence within strata; the pooled directional statistic can
miss opposing effects. A pooled RR does not establish a homogeneous effect.
Inspect exported stratum tables. No RR confidence interval is claimed from the
CMH score or exact test. Finite zero RR is allowed; infinite and undefined RR
are distinguished via risk_ratio_status (numeric value null for both).
No informative strata returns null z/p, not evidence for the null.

Reference: [R stats mantelhaen.test documentation](https://stat.ethz.ch/R-manual/R-devel/library/stats/html/mantelhaen.test.html)
for conditional stratified tests; our two-sided convention is doubled inclusive
tails, specified above.

## Recomputed comparisons

All 16 originally reported comparisons retained identical grader identity,
flagged/clean counts, conflicting-report counts, marginal proportions and MH RR.
Source Parquet tables are unchanged. Nasāʾī cross-recension exclusions,
corroborated-grade exclusion, report deduplication and conflict exclusion remain.
The manifest's source revision, SHA-256, licenses and attribution are preserved.
The audit JSON records old/new results, source receipt and input-table hashes.

Holm adjustment below treats all 16 published grader/defect comparisons as one
family. It controls family-wise error without requiring independence between
these tests, provided their individual p-values are valid.

| Grader (source attribution) | Defect | MH RR | z CMH | Exact p | Holm p |
|---|---|---:|---:|---:|---:|
| Ahmad Muhammad Shakir | TADLIS | 1.271 | 1.6287 | 0.1278 | 0.3834 |
| Ahmad Muhammad Shakir | TADLIS_WEAK | 1.412 | 2.0357 | 0.06035 | 0.251 |
| Al-Albani | TADLIS | 1.404 | 4.6001 | 9.174e-06 | 0.0001101 |
| Al-Albani | TADLIS_WEAK | 1.427 | 4.2221 | 5.441e-05 | 0.0005985 |
| Bashar Awad Maarouf | TADLIS | 3.022 | 1.5722 | 0.2737 | 0.5474 |
| Bashar Awad Maarouf | TADLIS_WEAK | 3.962 | 1.7236 | 0.2763 | 0.5474 |
| Muhammad Fouad Abd al-Baqi | TADLIS | 1.406 | 2.3553 | 0.02635 | 0.1844 |
| Muhammad Fouad Abd al-Baqi | TADLIS_WEAK | 1.574 | 2.7978 | 0.009689 | 0.07752 |
| Muhammad Muhyi Al-Din Abdul Hamid | TADLIS | 1.767 | 5.102 | 1.577e-06 | 2.051e-05 |
| Muhammad Muhyi Al-Din Abdul Hamid | TADLIS_WEAK | 1.334 | 2.203 | 0.03826 | 0.2296 |
| Salim al-Hilali | TADLIS | 0.392 | -2.0053 | 0.05021 | 0.251 |
| Salim al-Hilali | CHRONOLOGY | 8.742 | 12.3871 | 1.162e-19 | 1.626e-18 |
| Shuaib Al Arnaut | TADLIS | 1.508 | 3.9132 | 0.000195 | 0.00195 |
| Shuaib Al Arnaut | TADLIS_WEAK | 1.447 | 3.2946 | 0.00175 | 0.01575 |
| Zubair Ali Zai | TADLIS | 2.374 | 17.4945 | 4.785e-63 | 7.656e-62 |
| Zubair Ali Zai | TADLIS_WEAK | 1.884 | 9.5761 | 8.05e-20 | 1.207e-18 |

Zaʾī, al-Albānī and al-Arnaʾūṭ retain positive evidence in both categories even
after Holm adjustment. Shākir does not in either. Across the complete table,
Abdul Hamid's thiqa comparison and al-Hilālī's chronology comparison also survive
Holm at 0.05. Abd al-Baqi's two comparisons and Abdul Hamid's ṣadūq comparison
are nominally below 0.05 but do not survive this adjustment. Bashar's two
comparisons and al-Hilālī's thiqa comparison are not nominally significant.
“Every grader” and “essentially only Zaʾī” claims are withdrawn.

## Interpretation limits

Exact inference still assumes independent report outcomes conditional on margins.
Deduplication removes repeated aligned entries, but reports may share narrators,
texts, collections and grading practices. This dependence is not corrected by
stratification or Holm and may change uncertainty. Corpus selection and alignment
are observational; grades are preserved source attributions, not independent
historical truth. No causal mechanism, doctrinal position, historical authenticity
or jurisprudential ruling follows from these p-values. A cluster-aware design
and external validation would be needed for stronger generalization.

## Reproduce and validate

Run `PYTHONPATH=src python tools/recompute_defect_lift.py` from the repository
root; it updates only comparison results in the manifest and the audit JSON.
Run `python -m pytest -q`, `python -m ruff check src tests tools`, and
`PYTHONPATH=src python -m isnad_graph.cli verify`.
Regressions cover confounding, unequal stratum sizes, sparse exact enumeration,
zero cells, missing exposure groups, genuine effects and exposure reversal.
