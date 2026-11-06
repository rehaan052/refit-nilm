# Recommendation — REFIT Washing-Machine NILM

## Executive recommendation

Use the current model as an **exploratory customer-insight tool**, not as a billing-grade meter, definitive appliance monitor or automated fault detector. LightGBM Tweedie is the preferred candidate from the tested models because it achieved the strongest average F1, cycle precision and overall MAE in both evaluation designs. Keep LightGBM L2 as a comparison model where higher cycle recall or energy-error closeness is more important.

## What the model can support

The system estimates one-minute washing-machine power from household aggregate electricity consumption. A utility could pilot a weekly customer-facing usage summary showing estimated washing-machine activity frequency and typical usage times. This could help customers understand their routines and consider reducing unnecessary cycles or consolidating loads.

The strongest immediate use is **usage awareness**, not precise energy accounting. The model uses aggregate lag and rolling-context features, including positive (future) lags; it is therefore retrospective/offline and should not be described as a real-time predictor.

## Evidence and trade-offs

| Evaluation | Tweedie F1 | Tweedie cycle precision | Tweedie cycle recall | Tweedie energy error |
|---|---:|---:|---:|---:|
| LOHO | 0.414 | 0.513 | 0.592 | -0.595 |
| Timesplit | 0.592 | 0.750 | 0.827 | -0.489 |

Tweedie gave better average F1 and cycle precision than L2 in both evaluations. L2 had higher cycle recall (0.824 LOHO; 0.924 Timesplit), lower ON-state MAE, and energy error closer to zero (+0.012 LOHO; +0.203 Timesplit). The choice depends on whether the priority is fewer false detections or capturing more actual cycles.

Performance was not uniform across households. In LOHO, Tweedie F1 was 0.165 for House 2 and 0.564 for House 7. The cohort includes only four UK homes. Absolute energy estimates are biased low under the reported energy-error convention: -0.595 in LOHO and -0.489 in Timesplit.

## Recommended pilot and success measurement

Run a small, opt-in pilot with a comparison group:

1. Validate model output against an independent WM plug meter or submeter for participating homes before using energy estimates in customer feedback.
2. Provide a weekly summary of estimated WM activation frequency and usage timing. Clearly label estimates and avoid presenting them as exact bills or verified appliance readings.
3. Compare the feedback group with a similar no-feedback group over a defined pre- and post-intervention period.
4. Measure independently metered WM kWh per household-week and WM cycles per household-week, adjusting comparisons for valid observation coverage. Report household-level variation, not only an overall average.

The pilot should be judged successful only if independently measured energy use or unnecessary cycle frequency falls relative to the comparison group. The current analysis does not demonstrate that feedback already saves energy; it proposes a measurable trial.

## Do not use the current model for

- Direct billing, settlement or customer disputes.
- Guaranteed energy-savings claims based on uncalibrated predicted kWh.
- Definitive washing-machine fault diagnosis.
- Strict real-time alerts without removing future-context features and retraining.
- Deployment in Indian homes without local data collection, channel verification and validation.

## Deployment limitations and next steps

Aggregate readings combine multiple appliances, so overlapping signatures can be ambiguous. Missing monitoring intervals and stuck sensor readings affect data availability. The four REFIT households do not establish performance across all UK homes, and transfer to India is untested. At 15- or 30-minute meter resolution, transient power peaks and cycle boundaries would be smoothed; a separate model and evaluation at that resolution would be required.

Before a wider pilot: reconcile the House 7 missing-data discrepancy, integrate stuck-run masking into the reproducible preparation pipeline, validate energy estimates against independent WM meters, test causal features without positive aggregate lags, and evaluate on additional households—including representative Indian homes if that is the intended deployment market.
