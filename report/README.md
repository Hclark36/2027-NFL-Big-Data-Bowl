# Same 40, Different Burst — local research report

Open `index.html` in a browser. It is self-contained: styles, charts, player records, and static figures are embedded. It needs no server, API token, login, or internet connection for the report and comparison controls. Source links require internet when opened. Nothing has been published or submitted.

Use **Player comparison** to select Combine position, exact official time, draft year, players, and recorded attempts. Cross-position mode is optional. Peak markers and speed-band tables retain observation limits; the cursor replays the selected recorded-time reference and does not reconstruct a physical launch or finish-line race.

`writeup.md` is the written draft. `templates/writeup.md` is its editable source. The current draft is 1,426 whitespace-counted words, five figures, and one table. Edit the source template, then run Notebook 06 or the builder; editing generated `writeup.md` alone will be replaced on rebuild.

From the project root:

```sh
python scripts/build_report.py
```

Notebook 06 rebuilds and previews the same files. Its builder verifies source hashes and checks the fixed numerical claims in the draft, failing if those facts change rather than silently reporting stale findings. The report does not scan NFL tracking or refit models.

The analysis is a research draft. Physical-unit and sprint-boundary checks, the intended all-position NFL linkage, and public Kaggle notebook packaging are not complete. The 43-WR movement model is preserved and reported as an earlier limited pilot with no established incremental predictive improvement. The HTML companion is supplementary to the required Kaggle writeup and public notebook, not a replacement for either.
