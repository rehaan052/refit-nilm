# DATA.md

Numbers in this file come from the local run of `notebooks/01_raw_house1_cleaning.ipynb` (and `scripts/run_section1.py`, which gives identical numbers). Anything marked "inference" or "our choice" is not a verified fact.

## 1. Dataset facts (from the REFIT documentation)

- 20 UK households (numbered 1-21, no House 14), Loughborough area, Oct 2013 - Jun 2015.
- Per house: 1 aggregate sensor + 9 individual appliance monitors (IAMs). Active power only, in Watts, nominal 8-second interval.
- Raw vs cleaned: cleaned data has duplicate timestamps merged, IAM spikes above 4000 W set to 0, appliance streams re-aligned, NaN gaps under 2 minutes forward-filled and longer gaps zero-filled.
- Known limitations: solar contamination in Houses 3, 11, 21; IAMs not synchronised with the aggregate; sensor error around 6%; long outages (notably February 2014).

## 2. Raw House 1 findings

House 1 raw data comes as two files that overlap in time. Raw `Time` is UK local clock time.

| Check | Part 1 | Part 2 |
|---|---|---|
| Rows | 4,377,877 | 4,140,886 |
| First timestamp (local) | 2013-10-09 14:06:17 | 2014-06-27 21:57:50 |
| Last timestamp (local) | 2014-10-01 01:27:07 | 2015-07-10 11:56:32 |
| Sorted ascending | No (2 out-of-order steps) | Yes |
| Duplicate timestamps | 645,514 (595,935 rows fully identical) | 0 |
| Unparseable timestamps | 0 | 0 |
| Step between unique timestamps (25% / 50% / 75%) | 2 s / 5 s / 13 s | 7 s / 7 s / 7 s (1% quantile 6 s) |
| Longest step | 3,594,413 s | 747,252 s |

The real sampling interval is irregular, not the nominal 8 s. Total raw rows: 8,518,763.

### Missing values and impossible values per channel (raw, both parts)

| Channel | Missing % | Negative | Above limit* | Raw max (W) |
|---|---|---|---|---|
| aggregate | 2.22 | 0 | 66 | 29,159 |
| appliance1 | 5.14 | 0 | 846 | 76,677 |
| appliance2 | 5.39 | 0 | 40 | 98,301 |
| appliance3 | 3.66 | 0 | 118 | 73,725 |
| appliance4 | 6.00 | 0 | 2,085 | 98,301 |
| appliance5 | 5.84 | 0 | 221 | 73,725 |
| appliance6 | 4.02 | 0 | 36 | 37,610 |
| appliance7 | 2.73 | 0 | 374 | 98,299 |
| appliance8 | 4.59 | 0 | 179 | 98,301 |
| appliance9 | 22.44 | 0 | 50 | 65,535 |

\* Limit is 4000 W for appliances (REFIT README) and 23,999 W for the aggregate (our choice, see below). These raw counts include duplicate rows and Part 2 rows that the pipeline later drops. The counts actually set to NaN by the pipeline are in section 3.

The appliance maxima (for example 98,301 W) are clearly not real power values. 65,535 on appliance9 equals 2^16 - 1, which may be a register overflow value (inference).

## 3. Cleaning steps and what each removed

Settings are in `config.yaml`, code in `src/cleaning.py` and `src/stuck.py`.

1. **Combine parts.** Part 1 is primary. Part 2 rows are kept only after the last Part 1 timestamp (2014-10-01 01:27:07). Part 2 rows kept: 3,195,483; dropped as overlap: 945,403. Reason: in the overlap Part 2's clock drifts against Part 1 in our comparison (our choice).
2. **Local time to UTC.** Raw `Time` is treated as Europe/London. This came from row counts around the clock changes (`outputs/section1_checks*.txt`). The `Unix` column is derived from `Time` in these files, so it cannot be used to find the time zone. The repeated hour when clocks go back cannot be placed, so 2,185 rows were dropped (our choice; those hours show as a gap).
3. **Sort and duplicates.** Keep the first row per timestamp. 645,196 duplicate rows removed; 6,925,979 rows left. Large differences between duplicate rows were rare glitch values.
4. **Impossible values to NaN.** Appliance above 4000 W (counts after steps 1-3): appliance1 788, appliance2 36, appliance3 117, appliance4 1,700, appliance5 199, appliance6 35, appliance7 374, appliance8 161, appliance9 46. Aggregate above 23,999 W: 56.
5. **Stuck aggregate windows to NaN** (see section 4).
6. **Resample to 1 minute** (mean). 920,031 minutes on the grid.
7. **Forward-fill gaps up to 3 minutes** (our choice, close to the official 2-minute rule). Aggregate minutes filled: 594. Longer gaps stay NaN.
8. **Flag outages.** Aggregate still missing after filling = `agg_outage`. 122,741 minutes in 459 outages.

## 4. Stuck aggregate windows

Rule (our choice): aggregate identical for at least 30 minutes and at least 20 readings. All channels are set to NaN inside such a window. A real household load does not stay identical to the watt for tens of minutes, so we treat this as a stale logger (inference).

10 windows, 7,546 rows set to NaN, 1,041.6 minutes in total:

| Value (W) | Start (UTC) | End (UTC) | Minutes |
|---|---|---|---|
| 152 | 2014-10-04 14:27:39 | 2014-10-04 16:05:49 | 98.2 |
| 173 | 2014-10-13 08:43:42 | 2014-10-13 09:32:04 | 48.4 |
| 182 | 2014-11-01 14:04:05 | 2014-11-01 15:15:43 | 71.6 |
| 356 | 2014-12-23 18:11:11 | 2014-12-23 19:10:58 | 59.8 |
| 347 | 2015-01-31 21:00:52 | 2015-01-31 21:48:15 | 47.4 |
| 12,505 | 2015-02-08 13:24:00 | 2015-02-08 16:12:32 | 168.5 |
| 283 | 2015-02-14 08:06:29 | 2015-02-14 09:18:33 | 72.1 |
| 265 | 2015-02-14 15:54:23 | 2015-02-14 17:22:59 | 88.6 |
| 167 | 2015-02-18 16:17:38 | 2015-02-18 21:41:00 | 323.4 |
| 377 | 2015-02-25 21:57:13 | 2015-02-25 23:00:55 | 63.7 |

In an earlier check the 12,505 W window and a 460 W window (2014-07-18, not in the table because it falls in the dropped Part 2 overlap) also showed a constant washing-machine channel (appliance5) in the same time span, which supports the stale-logger idea (inference). The official CLEAN House 1 file contains the same 12,505 W artifact, so CLEAN is not ground truth.

## 5. Aggregate readings at 24,000 W and above

66 raw readings are above 23,999 W: 62 are exactly 24,000 W and four are 24,732, 28,855, 28,950 and 29,159 W. They fall on 10 days, in short bursts of one to two minutes (for example 2013-11-09 08:11-08:13). The same value repeating looks like a ceiling value (inference; we did not check whether a real surge happened). We set them to NaN. 56 of the 66 remain after the pipeline's de-duplication and overlap handling. The effect is small, because bursts of up to 3 minutes are forward-filled.

Real spikes of 10-12 kW do exist in the data (for example 2013-11-03 around 14:30) and are kept. We do not clip the aggregate at a low value.

## 6. Outages

459 outages, 122,741 minutes in total. Longest five:

| Start (UTC) | End (UTC) | Minutes |
|---|---|---|
| 2014-01-24 01:57 | 2014-03-06 16:22 | 59,906 |
| 2015-05-10 22:37 | 2015-05-19 14:09 | 12,453 |
| 2015-06-10 12:20 | 2015-06-18 00:38 | 10,819 |
| 2014-08-30 11:01 | 2014-09-04 10:32 | 7,172 |
| 2015-04-03 00:44 | 2015-04-07 09:17 | 6,274 |

The longest outage alone is about 49% of all outage minutes. Outages are flagged, never filled.

## 7. Remaining concerns

- **Appliance NaN.** In Part 2, NaN in an appliance channel often follows 0 W readings and may mean "unchanged reading" (in our check, 92.5% of washing-machine NaN minutes followed 0 W). We keep gaps longer than 3 minutes as NaN. Sections 2 and 3 use the official CLEAN files, which are already forward-filled.
- **Short outages.** The cause of many outages of 11 to 13 minutes (mostly Oct 2013 to Jan 2014) is unknown to us.
- **Dropped repeated hour.** 2,185 rows are lost at the end of daylight saving time. Recovering them is possible but not done.
- **Stuck rule.** The 30 minute / 20 reading thresholds are our choice. A very long constant stretch at a low value (for example 167 W for 323 minutes) is almost certainly stuck, but we cannot confirm this against another source.
- **CLEAN files are not ground truth.** The official CLEAN House 1 clock is inconsistent in our checks and it contains the 12,505 W artifact. Section 2 runs its own stuck-value and flat-line checks on every house used.
- **Where the numbers were produced.** Early exploration was done in a Colab notebook. The numbers above are from the local run in `notebooks/01_raw_house1_cleaning.ipynb`.

## 8. Official CLEAN files used in Sections 2-3

Checked with `scripts/section3_checks_stuck.py` (output in `outputs/section3_checks_stuck.txt`) and `scripts/section3_checks_raw_window.py`.

**CLEAN is not ground truth.** Using the same rule as Section 1 (aggregate identical for at least 30 minutes and at least 20 readings), CLEAN contains stuck stretches in every house we looked at:

| House | Stuck runs | Total minutes in runs | Longest run (min) |
|---|---|---|---|
| 1 | 12 | 3,040 | 1,186 |
| 2 | 16 | 6,914 | 2,672 |
| 5 | 6 | 4,058 | 2,671 |
| 6 | 68 | 7,009 | 1,187 |
| 7 | 21 | 5,628 | 2,671 |

This is roughly 0.3 to 0.8 % of each house's minutes.

**Same windows in several houses.** For example 2014-08-01 17:12 to 2014-08-02 12:58 appears in all five houses (about 1,187 minutes each); 2014-08-30 12:04 to 2014-09-01 08:35 in Houses 2, 5, 7; 2014-09-06 22:52 to 2014-09-07 12:24 in Houses 1, 6, 7. The frozen value differs by house, the window does not. A common cause is likely (inference; the CLEAN readme does not say).

**Two kinds of stuck stretch.** For House 1, the windows 2014-08-01/02 and 2014-09-06/07 have 0 rows in raw Part 1 but 1,149 and 740 rows with one constant aggregate value (227 W, 496 W) in CLEAN: CLEAN holds a value across an outage. In contrast, the 12,505 W stretch (2015-02-08) is in the raw data too (stale logger). We have no raw files for Houses 2, 5, 6, 7, so we cannot tell the two kinds apart there.

**Aggregate frozen while the washing machine runs.** House 6 on 2015-06-09 12:51 to 16:34: aggregate frozen at 795 W while the washing-machine channel reaches 2,137 W. House 6 has 37 runs at exactly 795 W (mostly June 2015). Similar cases: House 7 2015-03-29 (WM up to 412 W), House 6 2015-06-28 (WM up to 1,024 W). In such minutes the aggregate carries no information about the washing machine, so training on them would teach noise.

**Decision (our choice).** The Section 1 stuck rule (30 minutes, 20 readings) is applied to every CLEAN house, setting all channels to NaN in those windows; the minutes are then excluded from training and evaluation. Shorter frozen stretches are not caught.

**Clock.** House 1's stuck run starting 14:27:39 UTC in our Section 1 output starts at 15:27:39 in CLEAN, so CLEAN timestamps are UK local clock time, like raw `Time` (seen in this window; not checked in every house). We therefore keep CLEAN timestamps as they are (`clean_time_zone: null`), which also makes hour-of-day patterns local.


## Section 2 vs Section 3 Data Preparation

The Section 2 and Section 3 pipelines use different
one-minute data preparation procedures.

**Section 2:**
- Time-weighted one-minute aggregation.
- Only complete 60-second observations retained
  for primary analysis.
- Missing intervals remain unavailable.
- Activation and usage analysis performed on
  valid complete-minute observations.

**Section 3:**
- Per-minute mean aggregation.
- Short gaps of up to 3 minutes filled.
- Stuck washing-machine sensor readings above
  the selected threshold masked as NaN.
- Model evaluation uses minutes where both
  aggregate and washing-machine readings are valid.

Consequently, valid-minute counts and missing-data
percentages may differ between the two sections.

For House 7:
- Section 2 coverage: 87.38%.
- Section 2 active-time percentage: 8.38%.
- Section 3 post-mask valid minutes: 766,991
  out of 882,970 (approximately 86.86%).
- Section 3 unavailable percentage: approximately 13.14%.

The approximately 0.52 percentage-point difference
between the two missing-data calculations has not
been reconciled at row level.


# Data Preparation and Model Input

## Source

The project uses cleaned REFIT household electricity data.
The selected households are 1, 2, 6 and 7.

Washing-machine channel assignments:

| House | Channel |
|---|---|
| 1 | Appliance 5 |
| 2 | Appliance 2 |
| 6 | Appliance 2 |
| 7 | Appliance 5 |

These assignments are based on the REFIT dataset README,
not independent physical verification.

## Timestamp Handling

The CLEAN Time field was treated as UK local clock time,
rather than UTC.

The direct decision for modelling was to keep CLEAN timestamps
as stored (`clean_time_zone: null`).

Evidence included the expected missing/repeated local-clock
hours around UK daylight-saving transitions across the
four selected households.

The cause of the missing 00:00 hour on 30 March 2014
was not checked.

## Section 2 vs Section 3 Preparation

The two sections use different one-minute aggregation methods.

### Section 2: Exploratory Analysis

- Time-weighted aggregation.
- Primary analysis retains complete 60-second observations.
- Missing or incomplete minutes remain unavailable.
- Usage and activation analysis uses valid complete minutes.

### Section 3: Model Preparation

- Per-minute mean aggregation.
- Short gaps of up to three minutes are filled.
- Identified stuck washing-machine sensor readings above
  20 W are masked as NaN.
- Point-level evaluation requires both aggregate and
  washing-machine readings to be valid.

Consequently, valid-minute counts and coverage percentages
can differ between the sections.

## Final Section 3 Valid-Minute Counts

| House | Total Minutes | Valid Minutes |
|---|---:|---:|
| 1 | 920091 | 801279 |
| 2 | 889078 | 663642 |
| 6 | 831480 | 699618 |
| 7 | 882970 | 766991 |

## Flat-Run Masking

The following washing-machine readings were masked:

| House | Additional Masked Minutes |
|---|---:|
| 1 | 224 |
| 2 | 44 |
| 6 | 0 |
| 7 | 2 |

The mask was applied to the prepared local Parquet files
using `scripts/mask_wm_flat.py`.

Important: the masking operation is not integrated into
`scripts/prepare_minute_data.py`. Re-running the preparation
script requires the masking step to be applied again.

## Model Target and Missing Values

The model target is washing-machine power in Watts.

Unavailable target readings are represented as NaN.
Point-level metrics use only minutes where both aggregate
input and washing-machine target are valid.

Cycle-level evaluation preserves the full-length series
and does not treat missing target intervals as zero
consumption.