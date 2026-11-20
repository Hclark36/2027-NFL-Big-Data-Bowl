# Same Forty, Different Gears

*How NFL Prospects Reach Similar 40 Times Through Different Acceleration Profiles*

An NFL Big Data Bowl 2027 project restarting from raw competition data in **R**.

## Research question

Among players in the same Combine position group with similar published 40-yard dash times, how does recorded speed buildup differ?

The analysis will examine observed acceleration timing, time between speed thresholds, and consistency across recorded attempts. Comparisons will primarily stay within position and draft year. A separate NFL movement analysis may follow once the measurements and available samples are understood.

## Current status

This repository has been cleared of the earlier Python analysis and HTML dashboard. It currently contains project documentation only. New R code, results, and report figures have not been uploaded.

The earlier work is available in Git history. Its findings are not treated as established conclusions of the fresh analysis.

## Workflow

1. Audit raw files, schemas, identifiers, timestamps, and player overlap.
2. Verify units, acceleration definitions, and recording boundaries.
3. Define and validate speed-building and acceleration measurements.
4. Assess repeated-attempt agreement and select illustrative player comparisons.
5. Evaluate a clearly defined NFL movement outcome if the data support it.
6. Write the Kaggle report using verified results and selected figures.

Keep peak acceleration distinct from peak speed. Do not assume the first recorded frame is physical launch or that a player-level official 40 time belongs to every recording. Missing coverage must remain explicit.

## Repository structure

```text
README.md
data/       Data access and handling notes; raw files stay local
docs/       Analysis plan and project scope
outputs/    Notes for locally generated analysis results
report/     Plan for the written Kaggle report and figures
```

Git does not track empty folders. The R source folder will be added when the new analysis code is ready.

## Data

Use the [NFL Big Data Bowl 2027 competition data](https://www.kaggle.com/competitions/nfl-big-data-bowl-2027/data), with any required authentication and rule acceptance handled through Kaggle. Do not commit raw competition data, API tokens, or local configuration containing credentials.

See [data notes](data/README.md), the [analysis plan](docs/analysis_plan.md), and [project scope](docs/project_scope.md).

## Report

The main deliverable is a written Kaggle report. Selected-player charts will explain the findings; code will be linked separately. No HTML dashboard is part of the active repository.

See the [report plan](report/README.md).
