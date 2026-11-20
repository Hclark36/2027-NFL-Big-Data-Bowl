# Competition data

Obtain the authorized NFL Big Data Bowl 2027 files from Kaggle. Keep the raw CSVs in a local data folder; they are not distributed in this repository.

The fresh audit will inspect the actual schemas before defining inputs. It will begin with player identities, Combine results, and Combine tracking. NFL tracking and play context will be examined separately if the translation question proceeds.

Record file names, sizes, download/version information when available, and the scope of each audit. Label sample previews separately from full-file checks.

Do not infer physical units from column names. Verify the definitions of coordinates, supplied speed, supplied acceleration, timestamps, drill labels, and attempts. Recording start/finish must not automatically be treated as physical sprint start/finish.

Keep raw data unchanged. Never commit API tokens, Kaggle credentials, or private local configuration. The root .gitignore excludes local files in this folder except this README.
