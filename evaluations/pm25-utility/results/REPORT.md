# First utility test — no demonstrated useful advantage

**Decision: stop Discovery Workbench expansion on this evidence.** The preregistered acceptance gate failed. This was a completed retrospective test on real measurements, not a scientific discovery, prospective validation, operational deployment or evidence of adoption.

## Question and frozen design

Does the unchanged 0.1.0 engine materially improve next-hour PM2.5 forecasts compared with established alternatives? The application release under test was `191245df224bdbdb585848997eee0ba7a50ae121`. No application runtime code was modified.

The protocol was committed at `c2238efdfe1f7964307ea219e1206df2bb373cd4`, before successful data retrieval or examination of test outcomes. The executed harness was `5f972fbd586a0cd2f24f7a8f7d1f1df8c7241356`. Run 35039862223, job 104617093431, attempt 1 completed successfully. Passing the execution checks does not mean passing the scientific utility gate.

Source: [UCI Beijing Multi-Site Air Quality](https://archive.ics.uci.edu/dataset/501/beijing), Song Chen (2017), DOI 10.24432/C5RK5G, CC BY 4.0. Air-quality observations come from the Beijing Municipal Environmental Monitoring Center; matched weather comes from the China Meteorological Administration. This test used measured station data, not simulations.

Development used Aotizhongxin forecast origins in March 2013–December 2014. Final test cohorts were Dongsi and Dingling forecast origins in calendar 2016, neither used for training or model selection. These are different measured site/time observations, not resampled development rows. They are NOT statistically independent sites or hourly observations: shared regional weather, the same monitoring network and residual serial dependence remain.

The target was PM2.5 one hour after the forecast origin, using exactly four predictors: current PM2.5, previous-hour PM2.5, current PM10 and current wind speed. Forecasts originated at local hours 0, 6, 12 and 18. Exact timestamp joins preceded missing-data filtering; there was no interpolation, missing-hour bridging or test-error-based exclusion. Distinct selected origins have nonoverlapping t-1/t/t+1 measurement windows.

A deterministic hash-based sample selected 2,000 distinct-input development observations, sorted chronologically: 1,200 engine fitting rows, 400 validation rows and 400 internal audit rows. The internal audit was not the external test. Equal-data ridge and histogram-gradient-boosting baselines used the same 1,200 training rows. Full-training alternatives used all 1,552 eligible earlier six-hour origins before the training cutoff. All baseline selection used the same 400 development-validation rows, not external test outcomes.

Acceptance required ALL of the following: at least 5% lower RMSE than BOTH the frozen primary comparator and persistence at EACH site; a paired-block-bootstrap upper 95% RMSE-ratio bound below one; no greater than 5% MAE degradation versus either comparator at either site; and no provenance, invalid-prediction, leakage or coverage failure. This is an operator-selected screening threshold, not a universal scientific standard.

## Fitted model and comparator frozen before test extraction

The selected Workbench model was:

`next_PM25 = 3.889112033232905 + 0.9706808460121485 * pm25_now`

The engine evaluated 499 candidates. This expression is essentially a small linear adjustment of the current reading. Its internal `supported_on_this_split` result compared it against a training-mean constant, not against persistence or tuned forecasting models. The internal audit RMSE was 18.28667648644205; this did not determine the final utility decision.

The frozen primary comparator was equal-data histogram gradient boosting: absolute-error training loss, 31 leaves, L2 regularization 0, 200 iterations, learning rate 0.05, minimum 20 samples per leaf, no early stopping, seed 42. It had the lowest baseline validation RMSE, 15.665719546957831. Workbench's validation RMSE was 15.958118499734773. Both ridge variants selected alpha 1. The full-training boosted-tree model selected the same configuration as the equal-data variant.

The model-freeze timestamp recorded in the original run was `2026-09-16T00:24:56.469251+00:00`. The first external-station extraction was Dongsi at `2026-09-16T00:24:56.486177+00:00`, followed by Dingling at `2026-09-16T00:24:56.610446+00:00`. The frozen code emits the model record before opening either test station. No settings or models were revised after test outcomes were examined.

## Results

RMSE is in micrograms per cubic metre; lower is better. Site-balanced RMSE is the square root of the mean of the two site mean-squared errors, so the larger cohort does not dominate.

| Model | Dongsi RMSE | Dingling RMSE | Site-balanced RMSE | Site-balanced MAE |
|---|---:|---:|---:|---:|
| Discovery Workbench | 21.6488 | 28.4290 | 25.2674 | 9.8556 |
| Persistence: next hour = current reading | 21.5852 | 28.4776 | 25.2675 | 9.5753 |
| Training median | 86.6930 | 69.8610 | 78.7281 | 53.8009 |
| Ridge, equal training data | 20.4580 | 28.1751 | 24.6208 | 9.4995 |
| Gradient boosting, frozen primary comparator | 24.5959 | 29.1142 | 26.9499 | 10.5211 |
| Ridge, full eligible pre-cutoff training data | 20.5267 | 28.1697 | 24.6462 | 9.5452 |
| Gradient boosting, full eligible pre-cutoff training data | 22.9783 | 28.6687 | 25.9798 | 10.1495 |

**The negative result:** Workbench reduced pooled RMSE versus persistence by only 0.000519%, while pooled MAE was 2.927% higher. Its RMSE was 0.294% worse than persistence at Dongsi and 0.170% better at Dingling: neither site cleared the 5% improvement requirement. These are observed comparisons, not a formal proof of statistical equivalence.

**The positive sub-result is preserved:** Workbench reduced pooled RMSE versus the frozen boosted-tree comparator by 6.243%. The 4,000-replicate paired bootstrap, jointly resampling aligned seven-day blocks across both sites, produced a Workbench/comparator RMSE ratio of 0.9375678365956018, with percentile 95% interval [0.855168919738908, 0.9734782148255136]. However, improvement against that comparator was 11.982% at Dongsi and only 2.353% at Dingling. The latter did not clear the per-site requirement. The bootstrap passing one part of the gate does not override the failed parts.

Ridge alternatives also achieved lower test error than Workbench. They are not retroactively relabeled as the preregistered primary comparator, and their superiority in this test is not an independently confirmed deployment recommendation.

## Coverage and verification

Dongsi: 1,381 eligible of 1,464 scheduled origins, 94.33% coverage; 83 excluded for missing/nonfinite required readings. Dingling: 1,382 of 1,464, 94.40% coverage; 82 excluded for missing/nonfinite required readings. Total: **2,763 measured test observations**. Both sites populated all 53 calendar-week blocks. No finite out-of-range input was excluded, and no nonfinite forecast was dropped.

All five live application runtime assets matched the published release hashes, and the unchanged engine's 35 tests passed. The evaluation harness's 14 checks passed. Predictions from the JavaScript engine agreed with a separate Python evaluator of the frozen expression. Metrics independently recalculated from the temporary prediction CSV agreed with the recorded results. These checks support numerical/execution integrity, not scientific novelty or real-world operational benefit.

## Retained evidence and limits

- [Frozen protocol](../PROTOCOL.md)
- [Complete recorded test-result object](result.json), including every model's site metrics, tail metrics, missingness, bootstrap interval, source hashes and negative decision
- [Original one-shot run and logs](https://github.com/jarrettdustinqq/discovery-workbench/actions/runs/35039862223), including the full FREEZE_JSON, all development-validation grid scores and a compressed receipt containing the exact development split indices and timestamps
- [Executed harness source](https://github.com/jarrettdustinqq/discovery-workbench/tree/5f972fbd586a0cd2f24f7a8f7d1f1df8c7241356/evaluations/pm25-utility)

Original full freeze SHA-256: `c1b07e58796b8262e073984b7972feb42b72874df8aa45008631b900af524966`. The adjacent result.json is a formatted copy of the run's RESULT_JSON, not a second evaluation. The protocol, executed code and recorded test outcomes are preserved in Git history. The original full model-freeze and split receipt also remain in the provider's run logs, subject to its log retention; they are not represented as an indefinitely retained repository archive.

**Retention limitation:** the row-level predictions, fitted baseline pickle files and monthly output files were created and checked on the temporary runner but were not uploaded or included in its compact receipt. Recorded hashes and reproducible source are not substitutes for possessing those files. The attempt to retrieve and archive the full compact receipt through the overloaded laptop timed out before any repository write. The report/result were therefore retained through the GitHub connector instead. No second evaluation was run to recreate output files or seek a better score.

This was retrospective validation within one monitoring network, not newly collected prospective evidence. Publication latency, missing-data deployment behavior, alert consequences, operational costs and actual user benefit are unmeasured. It tested the forecasting component, not the proposed-experiment feature. One dataset cannot establish universal failure or broad usefulness.

No new spending, paid API, new account, recurring schedule, private-data publication, application modification, main-branch update or external outreach was introduced. Execution used a standard public-repository runner with read-only contents access. Results were preserved only on the dedicated evaluation branch. An empty local staging directory may remain from the timed-out evidence-retrieval attempt; no existing projects or data were removed.

## Reopening criterion

Keep the negative decision fixed. Do not enlarge the grammar, fit these test outcomes, weaken the baselines or search repeatedly for a flattering benchmark. Further expansion requires a concrete, externally evidenced use where the existing capabilities could improve a specified decision, with a new untouched evaluation cohort and a baseline fixed in advance. Otherwise keep the shipped preview unchanged.
