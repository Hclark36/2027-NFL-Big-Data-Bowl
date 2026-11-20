# Fresh R analysis plan

The analysis will be rebuilt step by step from raw files. Earlier report findings and selected player examples are not assumed to carry over.

## 1. Audit the data

Inspect file inventory, actual columns, candidate keys, missing values, duplicate frames, timestamp spacing, drill labels, attempt identifiers, and player/results overlap. Distinguish full-file statistics from previews. Account for all candidate recordings.

## 2. Establish measurement definitions

Verify coordinate and speed units, the meaning of supplied acceleration, recording start/finish coverage, and any mapping between official results and individual attempts. Decide what timing references the data support. Document unresolved questions.

## 3. Define profiles and test consistency

Estimate signed changes in speed only after defining the method. Evaluate smoothing and edge sensitivity, retain unsupported intervals as unavailable, and assess agreement between a player's recordings. Separate observed peak acceleration from peak speed.

## 4. Compare players

Use Combine position groups and primarily same-year comparisons. Define a reproducible rule for similar official times and selecting report examples. Show individual attempts so variation is visible. Do not select examples using NFL outcomes or attractive curves alone.

## 5. Consider NFL translation

Define one football movement outcome and its relevant position group before testing it. Audit player overlap, context, exposure, and event coverage. Compare any added tracking feature against a stated baseline using held-out players. Report a lack of improvement when that is the result.

## 6. Write the report

Lead with a selected-player example, explain measurement choices, show broader evidence and consistency, and close with implications and limits. Use only verified numerical results. Keep detailed implementation in the code and documentation.
