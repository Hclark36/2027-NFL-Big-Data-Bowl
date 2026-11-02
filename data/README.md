# Data and replay contract

Do not commit competition files or credentials. The snippet supplied in chat downloads data; it does not expose file contents to this project.

After the audit, implement a documented raw-to-normalized adapter. The replay exporter expects a CSV with:

| Column | Meaning |
|---|---|
| player_id | Stable identifier, read as string |
| player_name | Display name |
| attempt_id | Distinguishes repeated attempts |
| time_s | Seconds from the audited physical start, not simply the first recorded frame |
| distance_yd | Forward distance from that start, 0 through 40 yards |
| speed_yd_s | Validated forward speed in yards/second |
| acceleration_yd_s2 | Signed change in forward speed, yards/second squared |

One row per player/attempt/time; no duplicated times. Speed and acceleration must be finite, with nonnegative speed. Describe start detection, smoothing, units, missing frames, finish interpolation, and exclusions in the preparation notebook. Do not silently fill a missing launch or finish. Preserve attempt-level rows until reliability is assessed. Run replay with up to four player_id:attempt_id selections; all curves share elapsed seconds. The exporter rejects incomplete 0-to-40 attempts. Use official 40 times separately; sensor elapsed times need not match official timing.
