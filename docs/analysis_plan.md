# Analysis plan

## Scope and hypothesis

Primary population: WR, contingent on data audit. Primary movement hypothesis: early speed acquisition in the Combine predicts speed acquisition in comparable NFL route releases. Secondary football hypothesis: the profile adds information about separation on comparable routes. Association does not establish causality or a training intervention.

## 1. Audit before modeling

Inventory all downloaded files and schemas; establish player/attempt/play/frame keys, measurement units, sampling frequency, drill labels, and repeated attempts. Count unique players by position, class, NFL exposure, and availability. Check whether the launch and full 40 are actually captured. Inspect sensor speed/acceleration definitions; do not assume acceleration is signed or longitudinal. Compare official 10/40 splits to tracking distance and elapsed time. Check joins for row multiplication and selection into NFL participation. The CSV audit is an inventory, not a full data-quality assessment.

## 2. Prepare the 40

Normalize direction and project displacement onto the sprint axis. Define physical launch independently of official timing; flag left-truncated attempts. Inspect timestamps, gaps, duplicate frames, and finish coverage. Use interpolation only within observed coverage. Compare raw and smoothed curves, and multiple reasonable smoothing windows. Differentiate speed only after resolving units and noise. Retain all attempts to measure within-player repeatability before selecting or averaging attempts; do not choose a different best attempt per feature.

## 3. Define a small feature set

Primary candidate: time to a common absolute speed threshold chosen using Combine coverage only. Secondary candidates: time to 90% of a robust within-attempt peak speed; speed at fixed early times; sustained maximum positive acceleration and its timing; late-run speed. Relative thresholds depend on each player's maximum, so retain maximum speed alongside them. Assess feature reliability and collinearity. If launch coverage is poor, drop launch-based claims rather than reconstructing unseen acceleration.

Show matched pairs within position and similar official 40 times (initial exploratory tolerance 0.05 seconds, with sensitivity checks), while preserving the full cohort for modeling. Choose illustrative pairs using Combine profiles alone, before examining NFL outcomes. Do not equate matching on a total time with causal identification.

## 4. Test translation

Confirm available events and route labels before defining the outcome. Primary candidate: speed gained over a fixed post-release interval in comparable, non-motion, unimpeded route releases. Separate starting from rest from already moving. Account for press coverage, route type, alignment, and initial speed when available. Secondary candidate: separation at a specified route landmark or event, with defender assignment and coverage context audited. Do not mix separation at throw across arbitrary route depths as if comparable. Define minimum opportunities before outcome inspection; use rates or equal exposure windows, not cumulative career totals.

## 5. Estimate added information

Baseline: official 40, 10-yard split, size, class, and relevant role/context. Expanded model: same variables plus a small prespecified set of profile features. Draft position is a sensitivity adjustment, not an automatic primary control, since it includes scouting information downstream of athletic evaluation.

Use a simple regularized model initially. All plays and attempts from a player stay in the same fold; fit scaling, imputation, feature selection, and tuning on training folds only. Compare out-of-sample errors on identical held-out players. If sample size supports it, hold out a later draft class. Report player counts, paired model improvement, and player-level bootstrap uncertainty. Thousands of plays do not create thousands of independent Combine observations.

Separate exploratory feature discovery from confirmatory evaluation. Report null findings and sensitivity to alignment, smoothing, threshold, role adjustment, attempt aggregation, and opportunity filters.

## 6. Communicate

Replay: common elapsed-time clock, 0-to-40 lane markers, speed curves, signed acceleration curves, play/pause/scrub, stable colors, attempt labels, and a static export for the writeup. Never align each player's finish to the same clock time; that would hide real differences. Distinguish official timing from tracking elapsed time. No default autoplay. Respect reduced-motion settings in the final dashboard.

Report: keep essential evidence inside the Kaggle writeup and public notebook. Dashboard is a companion until organizer guidance explicitly allows substitution. Recheck rules before submission.
