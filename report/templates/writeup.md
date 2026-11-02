# Same 40, Different Burst

*Observed acceleration profiles across Combine position groups — research draft*

Two players can share a published 40-yard dash time without sharing the same recorded speed curve. This project examines where their observed acceleration peaks occur, how they move between speed levels, and whether those measurements repeat across attempts. An interactive companion lets an evaluator select a Combine position, exact official time, players, and individual recordings.

The main result is descriptive: a shared stopwatch result can coexist with different recorded profiles. Measurement consistency varies by position and feature. An earlier, narrower NFL test did not establish added predictive value. The broader position-specific NFL linkage remains unfinished.

## The question and cohort

The question is: **among players in the same Combine position group with the same published 40 time, how do observed acceleration timing and speed buildup differ?**

The dataset contains 418 players with 793 recorded player attempts from the 2023–2025 Combines. All have an official 40 result. There are 375 players with two recordings and 43 with one. Single-recording players remain available for comparison, but cannot contribute a repeated-attempt pair.

| Combine group | Players | Recordings | Players with two recordings |
|---|---:|---:|---:|
| DB | 102 | 195 | 93 |
| DL | 93 | 177 | 84 |
| OL | 95 | 179 | 84 |
| TE | 34 | 66 | 32 |
| WR | 94 | 176 | 82 |

Combine position defines the comparison group; NFL position remains separate. For example, Elijah Higgins belongs to the Combine WR group although his NFL position is TE. Comparisons default to one position. Cross-position exploration is optional and should not substitute for role-specific interpretation.

Published times are grouped at their reported hundredth-second precision. A player-level official time is not a verified time for every displayed recorded attempt. The comparison does not require equal 10-yard splits, two recordings, or NFL playing opportunities.

## Building observed profiles

The audit found 41,500 40-yard player frames, with no missing attempt keys or timestamps, no duplicate timestamps within attempts, and consistent approximately 0.1-second spacing. These checks establish recording continuity, not physical start or finish coverage.

The supplied acceleration field remained nonnegative during 230 inspected frames where recorded speed decreased beyond an exploratory diagnostic threshold. We therefore estimate **signed change in speed** from the supplied speed series rather than interpreting that field as signed tangential acceleration.

A quadratic local polynomial produces the direct first derivative, with 5-, 7-, and 9-frame windows retained as sensitivity settings. Estimates use complete centered windows; unsupported edges are not extrapolated. A peak at the supported-region boundary is flagged. Even an interior peak is only an observed maximum: a higher peak could have occurred outside the recording.

Two timing references are retained: seconds from the first recorded frame and seconds relative to an observed, sustained 3-unit speed crossing. Neither certifies physical launch. The latter can yield negative peak times when a peak precedes the reference. Sampling remains at 0.1 seconds; interpolated reference values do not establish finer physical accuracy. Physical speed units remain unverified, so speed and acceleration axes use raw-unit labels.

![Figure 1. Four 2023 Combine WRs share a published 4.54-second 40. Their eight recordings retain individual speed curves and observed acceleration peaks; triangles flag supported-region boundary peaks. Time zero is recording start, not confirmed launch.](figures/01_same_time_profiles.png)

The illustration includes Cedric Tillman, Elijah Higgins, Ronnie Bell, and Joseph Ngata. The group was chosen for having the most same-year WRs sharing an exact official time, with ties resolved by year and time—not by NFL outcomes. Seven-frame observed peak times span 0.3–0.6 seconds from recording start. Some peaks touch the valid-region boundary, so this is not evidence of an equally precise difference in true launch-relative peak timing.

## Speed intervals complement peaks

A peak describes one moment. Elapsed time through an observed speed band describes a stretch of speed buildup. The shared working bands are 2–4, 4–6, 6–8, and 8–10 raw speed units, with 3–7 retained from the pilot analysis.

An interval requires bracketed lower and upper crossings and at least 0.3 seconds of observed coverage at or above the upper threshold. Crossings are interpolated only between observed samples. Missing coverage stays unavailable, not zero. Bands represent speed levels; they are not distance splits, guaranteed early/middle/late sprint phases, or a reconstruction of the official 40.

![Figure 2. Availability of raw-speed intervals by position, under the stated crossing and sustained-coverage rule. Every recording stays in the denominator.](figures/02_speed_band_coverage.png)

The 8–10 band is supported in all WR and DB recordings, but only 92 of 177 DL recordings and 6 of 179 OL recordings. An unavailable interval does not establish that a player cannot reach a speed: the threshold, recording coverage, or sustained-coverage requirement may be responsible. Position groups should not inherit a feature merely because it is measurable for receivers.

## How consistently do attempts agree?

Repeatability is evaluated within position, using two measured attempts per feature. Correlations describe ranking; absolute differences describe agreement. These capture execution and measurement variation together, not pure sensor noise. Year-specific and interior-peak-only summaries remain available as sensitivity checks.

![Figure 3. Paired observed peak magnitudes within each position using seven-frame derivatives. One point represents one player; the dashed line indicates equal measurements. This is not a comparison of position-group athletic rankings.](figures/03_peak_repeatability.png)

Seven-frame peak-magnitude Spearman correlations range from 0.256 for WRs to 0.693 for DLs. These results do not support assuming that a single observed maximum is equally dependable for every position. Group differences, recording processing, and the available athlete range can influence correlations.

![Figure 4. Median absolute peak-timing differences between two attempts, under two observed references. Intervals resample paired players within draft year and condition on the measured recordings.](figures/04_timing_agreement.png)

For recording-start timing, median absolute differences are 0.1 seconds in DB, DL, OL, and WR groups and 0.2 seconds for TE. Relative to the observed speed reference, medians range from approximately 0.058 to 0.103 seconds. One recording lacks that reference, reducing the TE pair count from 32 to 31. A smaller difference after changing reference does not prove that physical launch was recovered; the reference is derived from the same speed series.

Conditional bootstrap intervals are descriptive, not independent-test guarantees. Discrete sampling can collapse an interval for a median onto one grid value. Timing differences should be interpreted at the recording's resolution rather than as exact physiological distinctions.

## NFL linkage: a limited pilot

The earlier pilot tested a mean 3–7 speed interval in 43 NFL WRs with two Combine recordings and at least 10 measured rookie-season, regular-season GO routes without pre-snap motion. Its outcome was mean speed gained during the first second after the snap, with suitable event coverage and the pass at or after that horizon.

![Figure 5. The archived WR pilot's held-out errors. Lower RMSE is better; the added interval did not improve the primary model and both primary models trailed the training-fold draft-year mean reference.](figures/05_wr_pilot_result.png)

Repeated player-level validation gave RMSE 0.31205 for the context-adjusted baseline and 0.31249 after adding the interval. The conditional paired-error interval for RMSE improvement was −0.01303 to 0.01318; the year-mean reference achieved 0.30023. Sensitivities did not show a consistent benefit.

This is retrospective movement linkage, not a draft-time forecast or an overall NFL-success test. It does not test all positions or establish that peak timing has no football relevance. The expanded Notebook 04 outcomes and subsequent position-specific NFL models are not complete. The current all-position profiles therefore remain exploratory.

## Use and limits

The companion is a review tool: compare players sharing a reported time, inspect every available attempt, distinguish peak magnitude from timing, and check whether speed bands are actually observed. It should prompt further review, not produce an unsupported prospect ranking.

Key limits are unverified physical units and sprint boundaries, official times not mapped to each attempt, possible year-dependent processing, only one or two recordings per player, and incomplete all-position NFL linkage. Position-derived and supplied speed agree closely in inspected discrepancies, but may share upstream processing and are not independent validation.

The defensible conclusion is: **the official 40 compresses observed movement differences, but useful scouting interpretation requires explicit coverage, timing references, repeatability, and a separately validated NFL link.**

## Sources and reproduction

Data: [NFL Big Data Bowl 2027](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/data). Methods and provenance: Notebooks 02, 03, and 05; the earlier NFL model is retained in `notebooks/archive/05_wr_nfl_validation_pilot.ipynb`. Notebook 06 rebuilds this report from saved, hash-checked outputs.

This local HTML companion does not replace the [required Kaggle writeup and public notebook](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/overview/submission-requirements). This draft contains five figures and one table; broader NFL linkage, physical-unit verification, and public-notebook packaging remain before a final submission.
