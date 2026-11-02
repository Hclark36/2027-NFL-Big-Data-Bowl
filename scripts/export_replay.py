"""Export a self-contained Plotly replay from audited, normalized 40 attempts.

Example:
python scripts/export_replay.py --input outputs/forties.csv \
    --attempt 123:1 --attempt 456:1 --output outputs/forty_replay.html

Requires full start/finish coverage. No raw-schema or start-detection assumptions.
"""
import argparse
from pathlib import Path


def build_replay(data, selections):
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    required = ["player_id", "player_name", "attempt_id", "time_s", "distance_yd",
                "speed_yd_s", "acceleration_yd_s2"]
    missing = set(required) - set(data.columns)
    if missing:
        raise ValueError(f"Missing normalized columns: {sorted(missing)}")
    if not 2 <= len(selections) <= 4 or len(set(selections)) != len(selections):
        raise ValueError("Select two to four distinct player/attempt pairs")
    attempts = []
    for player, attempt in selections:
        rows = data[(data.player_id.astype(str) == player) &
                    (data.attempt_id.astype(str) == attempt)].sort_values("time_s")
        if len(rows) < 3:
            raise ValueError(f"Too few samples for {player}:{attempt}")
        numbers = rows[required[3:]].to_numpy(dtype=float)
        if not np.isfinite(numbers).all():
            raise ValueError(f"Non-finite trajectory: {player}:{attempt}")
        t, d, s, _ = numbers.T
        if (np.diff(t) <= 0).any() or (np.diff(d) < -1e-6).any():
            raise ValueError("Times must increase and sprint distance must not decrease")
        if abs(t[0]) > 0.01 or abs(d[0]) > 0.05 or abs(d[-1] - 40) > 0.05:
            raise ValueError("Replay needs audited start at (0 s, 0 yd) and finish at 40 yd")
        if (s < 0).any() or (d < 0).any() or (d > 40.05).any():
            raise ValueError("Invalid forward speed or distance")
        attempts.append(rows)

    labels = [f"{r.player_name.iloc[0]} · attempt {r.attempt_id.iloc[0]}" for r in attempts]
    colors = ["#0072B2", "#D55E00", "#009E73", "#CC79A7"]
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.13,
                        subplot_titles=("40-yard replay", "Speed", "Signed acceleration"),
                        row_heights=[0.28, 0.36, 0.36])
    fig.add_trace(go.Scatter(x=[0]*len(attempts), y=list(range(len(attempts))),
                            mode="markers", marker=dict(size=17, color=colors[:len(attempts)]),
                            text=labels, showlegend=False,
                            hovertemplate="%{text}<br>%{x:.2f} yd<extra></extra>"), row=1, col=1)
    for i, rows in enumerate(attempts):
        for panel, column in [(2, "speed_yd_s"), (3, "acceleration_yd_s2")]:
            fig.add_trace(go.Scatter(x=rows.time_s, y=rows[column], name=labels[i],
                                    legendgroup=str(i), showlegend=panel==2,
                                    mode="lines", line=dict(color=colors[i]),
                                    hovertemplate="%{x:.2f} s<br>%{y:.2f}<extra>%{fullData.name}</extra>"),
                          row=panel, col=1)
    max_time = max(float(rows.time_s.iloc[-1]) for rows in attempts)
    times = np.unique(np.append(np.arange(0, max_time, 0.1), max_time))
    def cursors(t):
        return [dict(type="line", xref=f"x{n}", yref=f"y{n} domain", x0=t, x1=t,
                     y0=0, y1=1, line=dict(color="#777777", width=1, dash="dot")) for n in (2, 3)]
    frames = []
    for t in times:
        positions = [float(np.interp(t, rows.time_s, rows.distance_yd)) for rows in attempts]
        frames.append(go.Frame(name=f"{t:.2f}", data=[go.Scatter(x=positions)], traces=[0],
                               layout=go.Layout(shapes=cursors(float(t)))))
    fig.frames = frames
    fig.update_xaxes(range=[0, 40], dtick=10, title_text="Distance (yards)", row=1, col=1)
    fig.update_yaxes(tickvals=list(range(len(labels))), ticktext=labels,
                     range=[-0.6, len(labels)-0.4], row=1, col=1)
    for n in (2, 3):
        fig.update_xaxes(range=[0, max_time], title_text="Elapsed time from audited start (s)", row=n, col=1)
    fig.update_yaxes(title_text="Speed (yd/s)", row=2, col=1)
    fig.update_yaxes(title_text="Acceleration (yd/s²)", zeroline=True, row=3, col=1)
    fig.update_layout(title="Same 40, Different Burst — audited tracking replay", height=900,
        template="plotly_white", margin=dict(l=180, r=35, t=85, b=150), shapes=cursors(0),
        legend=dict(orientation="h", y=-0.18),
        updatemenus=[dict(type="buttons", direction="left", x=0, y=-0.08,
            buttons=[dict(label="Play", method="animate", args=[None, {"frame":{"duration":100,"redraw":False},
                         "transition":{"duration":0}, "fromcurrent":True, "mode":"immediate"}]),
                     dict(label="Pause", method="animate", args=[[None], {"frame":{"duration":0}, "mode":"immediate"}])])],
        sliders=[dict(y=-0.04, currentvalue=dict(prefix="Elapsed seconds: "),
            steps=[dict(label=f"{t:.2f}", method="animate", args=[[f"{t:.2f}"],
                {"mode":"immediate", "frame":{"duration":0,"redraw":False}, "transition":{"duration":0}}]) for t in times])])
    return fig


if __name__ == "__main__":
    import pandas as pd
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--attempt", action="append", required=True, help="player_id:attempt_id")
    parser.add_argument("--output", type=Path, default=Path("outputs/forty_replay.html"))
    args = parser.parse_args()
    selections = []
    for value in args.attempt:
        parts = value.split(":")
        if len(parts) != 2 or not all(parts):
            parser.error("Each --attempt must be player_id:attempt_id")
        selections.append(tuple(parts))
    frame = pd.read_csv(args.input, dtype={"player_id": str, "attempt_id": str})
    figure = build_replay(frame, selections)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(args.output, include_plotlyjs=True, auto_play=False,
                      config={"responsive":True, "displaylogo":False})
    print(f"Wrote {args.output}; tracking elapsed times are distinct from official times.")
