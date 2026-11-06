# Section 3 — Model Results, Decision and Future Recommendations

**Project:** REFIT NILM — estimate washing-machine (WM) power from household aggregate power at 1-minute resolution  
**Status:** Masked-parquet rerun completed; results below are the current results to report. Further tuning is deferred to future work because of the submission deadline.

## 1. Current data used

The updated minute Parquets were loaded in Colab after the WM flat-run masks had been applied to Houses 1, 2 and 7. House 6 was unchanged.

| House | Total minute bins | Valid minutes after mask |
|---:|---:|---:|
| 1 | 920,091 | 801,279 |
| 2 | 889,078 | 663,642 |
| 6 | 831,480 | 699,618 |
| 7 | 882,970 | 766,991 |

The local masking counts were verified as House 1: +224 minutes, House 2: +44 minutes, House 6: +0 minutes, House 7: +2 minutes. The updated files were loaded successfully in Colab Cell 5 before the full run.

## 2. Current model results

### 2.1 Leave-one-house-out (LOHO): mean across the four test households

| Model | MAE (W) | ON-state MAE (W) | Energy error | F1 | Cycle recall | Cycle precision |
|---|---:|---:|---:|---:|---:|---:|
| always_off | 18.447 | 443.348 | -1.000 | 0.000 | 0.000 | N/A |
| hourly_profile | 34.518 | 418.269 | +0.582 | 0.105 | 0.711 | 0.200 |
| lgbm_l2 | 23.989 | 322.968 | +0.012 | 0.332 | 0.824 | 0.307 |
| lgbm_tweedie | 17.973 | 362.787 | -0.595 | 0.414 | 0.592 | 0.513 |
| train_mean | 35.049 | 425.333 | +0.584 | 0.018 | 0.500 | 0.366 |

### 2.2 Within-house time split: mean across the four test households

| Model | MAE (W) | ON-state MAE (W) | Energy error | F1 | Cycle recall | Cycle precision |
|---|---:|---:|---:|---:|---:|---:|
| always_off | 20.668 | 475.230 | -1.000 | 0.000 | 0.000 | N/A |
| hourly_profile | 33.720 | 446.929 | -0.143 | 0.152 | 0.713 | 0.236 |
| lgbm_l2 | 23.059 | 264.428 | +0.203 | 0.371 | 0.924 | 0.348 |
| lgbm_tweedie | 16.576 | 333.814 | -0.489 | 0.592 | 0.827 | 0.750 |
| train_mean | 35.373 | 458.334 | -0.146 | 0.042 | 0.250 | 0.857 |

*Interpretation of energy-error sign: negative values indicate underestimation and positive values indicate overestimation, consistent with the interpretation used in the experiment notes.*

### 2.3 Per-house LOHO results for the two LightGBM models

| Test house | Model | True cycles | Predicted cycles | F1 | Cycle recall | Cycle precision | Energy error |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | lgbm_tweedie | 391 | 366 | 0.432 | 0.476 | 0.525 | -0.717 |
| 1 | lgbm_l2 | 391 | 1,078 | 0.268 | 0.877 | 0.312 | -0.160 |
| 2 | lgbm_tweedie | 339 | 147 | 0.165 | 0.145 | 0.333 | -0.821 |
| 2 | lgbm_l2 | 339 | 635 | 0.243 | 0.463 | 0.287 | -0.196 |
| 6 | lgbm_tweedie | 121 | 248 | 0.495 | 0.926 | 0.548 | -0.322 |
| 6 | lgbm_l2 | 121 | 778 | 0.291 | 0.967 | 0.188 | +0.424 |
| 7 | lgbm_tweedie | 876 | 1,177 | 0.564 | 0.821 | 0.646 | -0.521 |
| 7 | lgbm_l2 | 876 | 2,157 | 0.527 | 0.990 | 0.442 | -0.022 |

### 2.4 Per-house time-split results for the two LightGBM models

| Test house | Model | True cycles | Predicted cycles | F1 | Cycle recall | Cycle precision | Energy error |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | lgbm_tweedie | 116 | 81 | 0.650 | 0.672 | 0.963 | -0.609 |
| 1 | lgbm_l2 | 116 | 387 | 0.279 | 0.940 | 0.282 | +0.182 |
| 2 | lgbm_tweedie | 123 | 226 | 0.411 | 0.772 | 0.478 | -0.518 |
| 2 | lgbm_l2 | 123 | 430 | 0.250 | 0.756 | 0.277 | +0.529 |
| 6 | lgbm_tweedie | 35 | 52 | 0.542 | 0.914 | 0.731 | -0.398 |
| 6 | lgbm_l2 | 35 | 121 | 0.352 | 1.000 | 0.347 | +0.181 |
| 7 | lgbm_tweedie | 283 | 358 | 0.764 | 0.951 | 0.830 | -0.431 |
| 7 | lgbm_l2 | 283 | 599 | 0.604 | 1.000 | 0.486 | -0.081 |

## 3. Model decision for this submission

**Recommended primary model: `lgbm_tweedie` [our choice based on the reported results].**

- It has the best mean F1 in both evaluations: 0.414 in LOHO and 0.592 in the within-house time split.
- It has higher mean cycle precision than L2 in both evaluations: 0.513 vs 0.307 in LOHO, and 0.750 vs 0.348 in the time split.
- It also has the lowest mean overall MAE among the tested learned models in both evaluations: 17.973 W in LOHO and 16.576 W in the time split.
- Its important limitation is energy underestimation: mean energy error is -0.595 in LOHO and -0.489 in the time split. House 2 is particularly weak in LOHO (F1 0.165; cycle recall 0.145; energy error -0.821).

**Keep `lgbm_l2` as the energy-balance / high-recall comparison model, not as the primary cycle-detection model.**

- It has near-zero mean energy error in LOHO (+0.012), but overestimates in the time split (+0.203).
- It has higher cycle recall than Tweedie in both mean evaluations, but much lower cycle precision and F1.
- It predicts many more cycles than are present, especially in LOHO: House 7 has 2,157 predicted vs 876 true cycles.

Do not select a model using overall MAE alone. The OFF minutes dominate the minute-level target distribution, and `always_off` is a deceptively strong baseline on overall MAE. Report ON-state MAE, cycle metrics and energy error alongside overall MAE.

The `train_mean` cycle metrics should not be treated as meaningful evidence of model quality; constant or near-constant predictions can interact with the 20 W cycle threshold in misleading ways. This is an [inference] based on the observed baseline behaviour.

## 4. Effect of masking the suspicious WM flat runs

The masked-parquet run changed aggregate metrics only slightly compared with the previous unmasked run. This is consistent with the small number of masked minutes relative to the available minute data. The test labels/cycle counts also changed slightly for some houses, so this is a before/after pipeline comparison rather than a perfectly identical test-set comparison.

| Experiment | Model | Metric | Before mask | After mask |
|---|---|---|---:|---:|
| LOHO | lgbm_tweedie | MAE (W) | 18.067 | 17.973 |
| LOHO | lgbm_tweedie | ON-state MAE (W) | 362.251 | 362.787 |
| LOHO | lgbm_tweedie | Energy error | -0.592 | -0.595 |
| LOHO | lgbm_tweedie | F1 | 0.413 | 0.414 |
| LOHO | lgbm_tweedie | Cycle recall | 0.594 | 0.592 |
| LOHO | lgbm_tweedie | Cycle precision | 0.505 | 0.513 |
| LOHO | lgbm_l2 | MAE (W) | 24.112 | 23.989 |
| LOHO | lgbm_l2 | ON-state MAE (W) | 320.226 | 322.968 |
| LOHO | lgbm_l2 | Energy error | +0.029 | +0.012 |
| LOHO | lgbm_l2 | F1 | 0.330 | 0.332 |
| LOHO | lgbm_l2 | Cycle recall | 0.813 | 0.824 |
| LOHO | lgbm_l2 | Cycle precision | 0.305 | 0.307 |
| Time split | lgbm_tweedie | MAE (W) | 16.586 | 16.576 |
| Time split | lgbm_tweedie | ON-state MAE (W) | 331.190 | 333.814 |
| Time split | lgbm_tweedie | Energy error | -0.487 | -0.489 |
| Time split | lgbm_tweedie | F1 | 0.588 | 0.592 |
| Time split | lgbm_tweedie | Cycle recall | 0.830 | 0.827 |
| Time split | lgbm_tweedie | Cycle precision | 0.752 | 0.750 |
| Time split | lgbm_l2 | MAE (W) | 23.344 | 23.059 |
| Time split | lgbm_l2 | ON-state MAE (W) | 266.004 | 264.428 |
| Time split | lgbm_l2 | Energy error | +0.211 | +0.203 |
| Time split | lgbm_l2 | F1 | 0.369 | 0.371 |
| Time split | lgbm_l2 | Cycle recall | 0.922 | 0.924 |
| Time split | lgbm_l2 | Cycle precision | 0.341 | 0.348 |

## 5. Feature-importance findings (completed inspection)

Feature importance was extracted in `scripts/run_section3.py` using:

```python
imp[name] = pd.Series(m.feature_importances_, index=Xtr.columns)
```

The model constructor in `src/models.py` does not explicitly pass `importance_type`, and neither `DEFAULT_LGBM` nor `config.yaml` overrides it. Therefore, the saved `feature_importances_` values are interpreted as LightGBM's default **split importance** (feature split counts), not gain importance. This was checked in the source code; gain-based importance was not calculated.

The saved files are `outputs/section3/importance_loho.csv` and `outputs/section3/importance_timesplit.csv`. Each contains 144 rows and the columns `Unnamed: 0` (feature name), `lgbm_tweedie`, `lgbm_l2`, and `test_house`; importance is recorded separately for each test-house fold.

### Observed patterns

- **Tweedie:** `roll61_max` was the highest split-importance feature for each of the four test houses in both LOHO and Timesplit. Other 61-minute rolling statistics (`roll61_min`, `roll61_std`, and `roll61_mean`) also repeatedly appeared among the top features.
- **L2:** Aggregate lag features were prominent in LOHO, including `agg_t-30`, `agg_t+30`, `agg_t-20`, and `agg_t+20`. In Timesplit, rolling statistics and aggregate lag features both appeared among the top features; the leading feature varied by house.
- **Both objectives:** The models repeatedly used surrounding aggregate context, not only the current aggregate reading. The ranking varied by objective, test house, and evaluation strategy.

### Interpretation limits

- Split importance measures how often a feature is used in tree splits. It does not measure the magnitude of its predictive contribution or establish causality.
- **Gain-based importance was not evaluated.**
- Positive aggregate lags such as `agg_t+15`, `agg_t+20`, and `agg_t+30` use future-context readings. Their presence means the current feature set is retrospective/offline; strict real-time use would require a causal feature set and a new evaluation.

## 6. Deferred fine-tuning recommendations

These are future-work recommendations, not experiments completed for the current submission.

| Priority | Recommendation | Reason / question to test | Status |
|---|---|---|---|
| 1 | Increase the Tweedie tree budget above 2,000, or test a lower learning rate with a larger tree budget. | In LOHO, Tweedie reached the 2,000-tree cap for House 1 (2,000), House 6 (1,998) and House 7 (1,998). The current model may not have fully converged. | NOT RUN |
| 2 | Test `tweedie_variance_power` values 1.2 and 1.8 against the current 1.5. | Check whether the energy underestimation can be reduced without losing cycle F1/precision. | NOT RUN |
| 3 | Run a `use_time_features: true` ablation against the current `false` setting. | Determine whether local hour/day information improves generalisation, especially in the within-house time split. | NOT RUN |
| 4 | Calculate and compare gain-based feature importance. | The saved files were inspected and the current values are split counts. Gain-based importance would provide a different importance measure. | NOT RUN |
| 5 | Extend prediction-vs-truth plots to additional periods and/or houses. | LOHO plots were generated for House 7 (stronger result) and House 2 (weaker generalisation); broader coverage could show more variation. | PARTIALLY DONE |
| 6 | Extend cross-house metric visualization if needed. | Cross-house summary CSVs and comparison figures were generated for F1, cycle metrics and energy error. | DONE for current requested figures |
| 7 | Reconcile the House 7 missing-minute percentage and document the Section 2 vs Section 3 preprocessing difference. | Important clarification: the Section 2 value **8.38% is the above-20 W (active-time) share**, not the missing-data share; 91.62% is the OFF-time share. The Section 2 period table separately reports about 87.38% coverage (so its complement is about 12.62% missing/invalid by arithmetic). The Section 3 pipeline was reported as about 13.1% missing/invalid. Recheck the exact denominators from code before comparing these percentages. | OPEN |
| 8 | Investigate why CLEAN has zero rows in local hour 00 on 2014-03-30 (House 6 has one row). | The cause of this date-specific anomaly was not determined. | NOT CHECKED |
| 9 | Keep a reproducible record of the masked-parquet preparation. | `mask_wm_flat.py` is not part of `prepare_minute_data.py`; rerunning the preparation script regenerates Parquets without the additional WM mask unless the mask script is run again. | IMPORTANT |
| 10 | Run a `use_time_features: true` ablation against the current `false` setting. | Test whether local hour/day information improves within-house and cross-house performance. | NOT RUN |
| 11 | Evaluate a causal feature set without positive aggregate lags. | Check whether performance remains useful when future-context features are removed, as required for prospective/real-time use. | NOT RUN |

## 7. Evaluation and interpretation cautions

- LOHO evaluates transfer to a household not used for training; the within-house time split evaluates later observations from a household whose earlier observations were used for training. These test sets differ, so their mean scores are not directly comparable as if they were the same test population.
- Point metrics use minutes where both aggregate and WM target are valid. Cycle metrics are evaluated on the full-length series with NaN gaps.
- Overall MAE is strongly influenced by OFF minutes. Always report ON-state MAE and cycle/energy metrics as complementary measures.
- The Section 2 EDA pipeline and Section 3 modelling pipeline are not identical. Section 2 required a fully observed 60-second minute; Section 3 uses per-minute means, fills short gaps (up to 3 minutes, as stated in the project status), and removes the selected stuck WM runs. Document this explicitly in `DATA.md` or `README.md`.
- The channel mapping is taken from the REFIT README and was not physically verified at the appliance level.
- The frozen-run interpretation is an [inference]; the masking rule treats the selected non-zero flat runs above 20 W as suspect sensor values.

## 8. Reproducibility notes

- The user reports that `python -m pytest -q` passed: **46 passed**.
- The user reports that masked Parquets were uploaded/replaced in Drive and Cell 5 confirmed the expected valid-minute counts before the masked full run.
- Preserve the exact masked Parquets used for the current metrics. Do not rerun `scripts/prepare_minute_data.py` without subsequently rerunning `scripts/mask_wm_flat.py` and verifying the mask counts.
- Current full-run outputs are in Drive under `refit-nilm/outputs/section3/`, including `metrics_loho.csv`, `metrics_timesplit.csv`, predictions Parquets and feature-importance CSVs (individual output-file presence after the latest run: NOT CHECKED here).
- Prediction-vs-ground-truth figures were generated for LOHO Houses 7 and 2: `outputs/section3/figures/prediction_vs_actual_loho_house7.png` and `outputs/section3/figures/prediction_vs_actual_loho_house2.png`.
- Cross-house comparison figures were generated: `outputs/section3/figures/cross_house_f1_comparison.png`, `cross_house_cycle_metrics.png`, and `cross_house_energy_error.png`.
- Cross-house metric tables were generated: `outputs/section3/cross_house_metrics_summary.csv` and `outputs/section3/cross_house_metrics_by_house.csv`. The latest local/Drive sync of these newly generated files should be verified before submission.

## 9. Submission recommendation

For the current deadline, report **LightGBM Tweedie as the primary model**, with LightGBM L2 as a comparison model that gives higher cycle recall / more balanced aggregate energy in LOHO but generates substantially more predicted cycles. Be transparent that Tweedie underestimates total energy and that performance varies by household, particularly for House 2 in LOHO.

Do not claim the deferred tuning items were completed. List them as future work / recommendations. Keep the present masked-run results as the final reported experiment unless a later verified run supersedes them.

---

# Cross-Section Recommendations and Practical Implications

This section adds recommendations for Sections 1, 2 and 4, and includes the utility-facing recommendation required by the assignment. The Section 3 model results and deferred experiments above are retained.

## 10. Section 1 — Data ingestion, cleaning and quality recommendations

The following are recommendations for making the data-preparation stage more robust and reproducible. They should not be read as claims that every item was already implemented.

1. **Keep source data immutable.** Retain the supplied REFIT files unchanged and write cleaned or transformed data to separate, versioned output locations.
2. **Make cleaning decisions auditable.** For every cleaning operation, record the affected house, channel, timestamp range, number of changed rows and reason. Avoid silently replacing unusual readings or dropping intervals.
3. **Validate each selected house independently.** Run schema, timestamp ordering, duplicate timestamp, missing-value, sampling-interval, negative-value and aggregate-versus-appliance consistency checks on Houses 1, 2, 6 and 7. Do not assume that a check run on House 1 generalizes to the other houses.
4. **Preserve timestamp provenance.** Keep the original `Time` field and any available Unix timestamp. The Section 3 investigation treats CLEAN `Time` as UK local clock time; daylight-saving transitions can create missing or repeated local hours. Do not convert naive local timestamps to UTC without an explicit, tested timezone-localization rule.
5. **Make anomaly handling reproducible.** Keep spike handling and stuck/flat-line masking as explicit, testable steps. The current Section 3 WM mask is applied by `scripts/mask_wm_flat.py` and is not integrated into `scripts/prepare_minute_data.py`; future preparation runs must either invoke the mask step automatically or verify that it has been applied.
6. **Add before/after audit summaries.** Save row counts, valid-minute counts, missing intervals, and affected-channel counts before and after each cleaning operation. This makes data loss and label changes visible.
7. **Extend automated tests.** In addition to the existing 46 passing tests, add regression tests that confirm the intended timestamp, gap-filling and flat-run masking behaviour on representative examples from more than one household.

## 11. Section 2 — Washing-machine EDA recommendations

1. **Keep the cohort rationale explicit.** The primary EDA/model cohort is Houses 1, 2, 6 and 7 [our choice]. House 5 was retained as a secondary quality-review case but excluded from the primary cohort because of suspicious constant WM readings. Channel assignments came from the REFIT README and were not physically verified.
2. **Call detected events “estimated activation episodes.”** The rule (>20 W, merge up to 5 consecutive observed OFF minutes, minimum merged span 27 minutes, no energy filter) is a threshold-based analytical choice, not proof of a complete physical washing cycle. Preserve that wording in figures, tables and conclusions.
3. **Keep unavailable data separate from zero power.** Missing or incomplete minutes must remain unavailable. Do not fill long outages with zero or bridge activation episodes across NaN/unavailable minutes.
4. **Report denominators with every percentage.** State whether percentages use native time-weighted observations, complete one-minute bins, or another valid-minute definition. Report valid coverage and missingness separately from zero-power, OFF-time and ON-time shares.
5. **Clarify the House 7 percentage.** The Section 2 value 8.38% is the share of valid complete minutes with WM power above 20 W (active-time share), not the missing-data percentage. The Section 2 period table reports 87.38% coverage, whose arithmetic complement is 12.62%. The Section 3 pipeline reports 766,991 valid minutes out of 882,970 (about 86.86% valid, or 13.14% unavailable). The row-level difference between Section 2 and Section 3 has not been reconciled; do not present these as directly comparable measures.
6. **Retain exposure-normalized usage rates.** Raw episode counts are affected by different monitoring durations. Continue reporting rates normalized by observed hour/day exposure, alongside raw counts and denominators.
7. **Treat quality flags as context, not automatic truth labels.** The REFIT `Issues` flag and suspicious plateaus should be disclosed. Do not silently remove all flagged observations without a documented rule and sensitivity analysis.
8. **Improve channel verification when possible.** Before operational use, validate the appliance-channel mapping against appliance-level metering or other trustworthy household records. The current mappings are from the dataset README, not physical verification.
9. **Extend the cohort before broad claims.** Four households are enough for the stated comparative EDA and take-home model experiments, but are not enough to characterize all REFIT homes or other populations.

## 12. Section 4 — Utility-facing recommendation

### Executive recommendation

Use the current model as an **exploratory customer-insight tool**, not as a billing-grade meter, definitive appliance monitor or automated fault detector. LightGBM Tweedie is the preferred candidate from the tested models because it achieved the strongest average F1, cycle precision and overall MAE in both evaluation designs. Keep LightGBM L2 as a comparison model where higher cycle recall or energy-error closeness is more important.

### What the model can support

The system estimates one-minute washing-machine power from household aggregate electricity consumption. A utility could pilot a weekly customer-facing usage summary showing estimated washing-machine activity frequency and typical usage times. This could help customers understand their routines and consider reducing unnecessary cycles or consolidating loads.

The strongest immediate use is **usage awareness**, not precise energy accounting. The model uses aggregate lag and rolling-context features, including positive (future) lags; it is therefore retrospective/offline and should not be described as a real-time predictor.

### Evidence and trade-offs

| Evaluation | Tweedie F1 | Tweedie cycle precision | Tweedie cycle recall | Tweedie energy error |
|---|---:|---:|---:|---:|
| LOHO | 0.414 | 0.513 | 0.592 | -0.595 |
| Timesplit | 0.592 | 0.750 | 0.827 | -0.489 |

Tweedie gave better average F1 and cycle precision than L2 in both evaluations. L2 had higher cycle recall (0.824 LOHO; 0.924 Timesplit), lower ON-state MAE, and energy error closer to zero (+0.012 LOHO; +0.203 Timesplit). The choice depends on whether the priority is fewer false detections or capturing more actual cycles.

Performance was not uniform across households. In LOHO, Tweedie F1 was 0.165 for House 2 and 0.564 for House 7. The cohort includes only four UK homes. Absolute energy estimates are biased low under the reported energy-error convention: -0.595 in LOHO and -0.489 in Timesplit.

### Recommended pilot and success measurement

Run a small, opt-in pilot with a comparison group:

1. Validate model output against an independent WM plug meter or submeter for participating homes before using energy estimates in customer feedback.
2. Provide a weekly summary of estimated WM activation frequency and usage timing. Clearly label estimates and avoid presenting them as exact bills or verified appliance readings.
3. Compare the feedback group with a similar no-feedback group over a defined pre- and post-intervention period.
4. Measure independently metered WM kWh per household-week and WM cycles per household-week, adjusting comparisons for valid observation coverage. Report household-level variation, not only an overall average.

The pilot should be judged successful only if independently measured energy use or unnecessary cycle frequency falls relative to the comparison group. The current analysis does not demonstrate that feedback already saves energy; it proposes a measurable trial.

### Do not use the current model for

- Direct billing, settlement or customer disputes.
- Guaranteed energy-savings claims based on uncalibrated predicted kWh.
- Definitive washing-machine fault diagnosis.
- Strict real-time alerts without removing future-context features and retraining.
- Deployment in Indian homes without local data collection, channel verification and validation.

### Deployment limitations and next steps

Aggregate readings combine multiple appliances, so overlapping signatures can be ambiguous. Missing monitoring intervals and stuck sensor readings affect data availability. The four REFIT households do not establish performance across all UK homes, and transfer to India is untested. At 15- or 30-minute meter resolution, transient power peaks and cycle boundaries would be smoothed; a separate model and evaluation at that resolution would be required.

Before a wider pilot: reconcile the House 7 missing-data discrepancy, integrate stuck-run masking into the reproducible preparation pipeline, validate energy estimates against independent WM meters, test causal features without positive aggregate lags, and evaluate on additional households—including representative Indian homes if that is the intended deployment market.

## 13. Section 4 — Practical answer summary for the assignment

- **Energy-saving/customer-insight opportunity:** An opt-in weekly washing-machine usage summary. Measure impact through independently metered WM kWh per household-week and cycles per household-week, comparing a feedback group with a similar control group before and after the pilot.
- **Limitations:** Appliance signatures overlap in aggregate readings; the dataset has missing intervals and sensor anomalies; household behaviour and model performance differ; and transfer from four UK homes to Indian homes is unvalidated.
- **15-minute/30-minute meter data:** Coarser intervals smooth transient power peaks and blur cycle boundaries. Short activations may be diluted or lost, and overlapping appliances become harder to distinguish. A new model must be trained and evaluated at the intended 15- or 30-minute resolution; the current one-minute metrics cannot be assumed to transfer.

## 14. Remaining open checks before deployment or a stronger claim

- Reconcile the House 7 Section 2 versus Section 3 valid-minute/missing-percentage difference at row level.
- Integrate or formally orchestrate the WM flat-run mask with the preparation pipeline.
- Investigate the missing local hour around 00:00 on 30 March 2014; the cause remains NOT CHECKED.
- Confirm that the current local/Drive copy contains all final Section 3 prediction, metrics, importance and figure outputs.
- Verify channel mappings with appliance-level evidence before any operational deployment.
- Validate against independent WM meters and collect representative data for any intended non-UK deployment, including India.
