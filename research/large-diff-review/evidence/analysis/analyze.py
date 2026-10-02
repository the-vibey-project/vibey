"""Empirical baseline for the sovereign review on large diffs (gpt-oss:20b, Ollama, Apple M5).

Run (after parse_ollama.py, fetch_diffs.py, parse_reviews.py, join.py):
  uv run --no-project --with pandas --with numpy --with scipy --with statsmodels \
      --with lifelines --with matplotlib python analysis/analyze.py

Writes analysis/results.json and figures/*.png. Every number in results.json carries n and,
where it is an estimate, a 95% interval. Bootstrap: 1000 resamples of requests (seed 20261001)
unless stated. Cutoff: the Ollama snapshot (raw/ollama/SNAPSHOT_AT_UTC) and the GitHub fetch of
2026-10-01 ~21:45Z.

The central object is G*, the number of tokens the model would generate (reasoning + answer)
before stopping on its own. A request that stopped ('stop') observes G* exactly. A request cut
by the token cap, the context end, a client timeout or cancellation observes only G* > g (right
censored at the tokens generated so far). Treating cut requests as failures, or dropping them,
both bias G* downwards; a censored (survival) model is the honest estimator. Its assumption --
censoring independent of G* given the prompt size -- is stated in findings.md.
"""

from __future__ import annotations

import json
import pathlib
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import statsmodels.api as sm  # noqa: E402
from lifelines import (  # noqa: E402
    KaplanMeierFitter,
    LogLogisticAFTFitter,
    LogNormalAFTFitter,
    WeibullAFTFitter,
)
from scipy import stats  # noqa: E402

warnings.filterwarnings("ignore")
HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE.parent
FIG = EVIDENCE / "figures"
FIG.mkdir(exist_ok=True)
RNG = np.random.default_rng(20261001)
B = 1000
CAP = 16384
PR_1316 = pd.Timestamp("2026-10-01T18:16:01Z")
INK, INK2, MUTED, SURF = "#0b0b0b", "#52514e", "#898781", "#fcfcfb"
S1, S2, S3, S4, S5 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
REVIEW_WORKLOADS = [
    "ci_review",
    "study_think_medium",
    "study_source",
]  # known PR-review prompts at default/medium effort
POOLED_WORKLOADS = REVIEW_WORKLOADS + ["other_review_shaped"]

plt.rcParams.update(
    {
        "figure.facecolor": SURF,
        "axes.facecolor": SURF,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK2,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "text.color": INK,
        "axes.grid": True,
        "grid.color": "#e6e5e1",
        "grid.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 9,
        "legend.frameon": False,
        "lines.linewidth": 2,
    }
)


def ci(values, q=(2.5, 97.5)):
    values = np.asarray([v for v in values if v is not None and np.isfinite(v)])
    return (
        [float(np.percentile(values, q[0])), float(np.percentile(values, q[1]))]
        if len(values)
        else [None, None]
    )


def boot(series: np.ndarray, fn):
    n = len(series)
    return ci([fn(series[RNG.integers(0, n, n)]) for _ in range(B)])


def load():
    o = pd.DataFrame(
        [json.loads(ln) for ln in (EVIDENCE / "dataset-ollama.jsonl").read_text().splitlines()]
    )
    r = pd.DataFrame(
        [json.loads(ln) for ln in (EVIDENCE / "dataset-reviews.jsonl").read_text().splitlines()]
    )
    for c in ("gin_start_utc", "gin_end_utc"):
        o[c] = pd.to_datetime(o[c], utc=True, format="ISO8601")
    for c in ("review_step_started_at", "review_step_completed_at", "job_started_at"):
        r[c] = pd.to_datetime(r[c], utc=True, format="ISO8601")
    return o, r


def rates(o, out):
    g = o[(o.model == "gpt-oss:20b") & o.prompt_eval_s.notna()].copy()
    # Prompt reading: requests read from position 0 (no cached prefix) and >= 512 tokens.
    pp = g[(g.cached_tokens == 0) & (g.prompt_eval_tokens >= 512)].copy()
    X = np.column_stack([pp.prompt_eval_tokens, pp.prompt_eval_tokens**2])
    fit = sm.OLS(pp.prompt_eval_s.values, X).fit(cov_type="HC3")
    a, b = fit.params

    def t_pp(n, a=a, b=b):
        return a * n + b * n**2

    boots = []
    idx = np.arange(len(pp))
    for _ in range(B):
        s = RNG.choice(idx, len(idx))
        p = np.linalg.lstsq(X[s], pp.prompt_eval_s.values[s], rcond=None)[0]
        boots.append(p)
    boots = np.array(boots)
    table = {}
    for n in (5000, 10000, 20000, 30000, 40000, 50000):
        tt = [t_pp(n, *p) for p in boots]
        table[str(n)] = {
            "seconds": round(float(t_pp(n)), 1),
            "seconds_ci95": [round(x, 1) for x in ci(tt)],
            "tokens_per_s": round(float(n / t_pp(n)), 1),
            "tokens_per_s_ci95": [round(n / x, 1) for x in ci(tt)[::-1]],
        }
    out["prompt_eval"] = {
        "source": "ollama slot timing 'prompt eval time', gpt-oss:20b, cached prefix 0, >=512 tokens",
        "n": int(len(pp)),
        "model": "seconds = a*N + b*N^2 (OLS, HC3)",
        "a": a,
        "b": b,
        "r2": float(fit.rsquared),
        "observed_tokens_per_s_quantiles": {
            q: round(float(np.percentile(pp.prompt_eval_tps, q)), 1) for q in (5, 25, 50, 75, 95)
        },
        "predicted": table,
    }
    # Generation: per-token time linear in context position.
    # Fitted on review-shaped requests only: across all workloads the rate is dominated by
    # host state (other runners, memory pressure), not context (R^2 ~ 0 on all 408 requests).
    ev = g[
        g.eval_s.notna()
        & (g.generated_tokens >= 100)
        & (g.prompt_tokens >= 1000)
        & g.workload.isin(
            [
                "ci_review",
                "study_think_medium",
                "study_source",
                "study_think_low",
                "other_review_shaped",
            ]
        )
    ].copy()
    ev["ctx_mid"] = ev.prompt_tokens + ev.generated_tokens / 2
    ev["s_per_tok"] = ev.eval_s / ev.generated_tokens
    gf = sm.OLS(ev.s_per_tok.values, sm.add_constant(ev.ctx_mid.values)).fit(cov_type="HC3")
    c0, d0 = gf.params
    gboots = []
    gi = np.arange(len(ev))
    Xg = sm.add_constant(ev.ctx_mid.values)
    for _ in range(B):
        s = RNG.choice(gi, len(gi))
        gboots.append(np.linalg.lstsq(Xg[s], ev.s_per_tok.values[s], rcond=None)[0])
    gboots = np.array(gboots)

    def t_gen(p, gtok, c=c0, d=d0):
        return c * gtok + d * (p * gtok + gtok**2 / 2)

    gt = {}
    for ctx in (1000, 10000, 20000, 30000, 40000, 50000):
        r_ = [1 / (c + d * ctx) for c, d in gboots]
        gt[str(ctx)] = {
            "tokens_per_s": round(float(1 / (c0 + d0 * ctx)), 2),
            "ci95": [round(x, 2) for x in ci(r_)],
        }
    out["generation"] = {
        "source": "ollama slot timing 'eval time', gpt-oss:20b review-shaped requests (prompt >= 1000), >=100 generated tokens",
        "n": int(len(ev)),
        "model": "seconds_per_token = c + d*context_position (OLS, HC3)",
        "c": c0,
        "d": d0,
        "r2": float(gf.rsquared),
        "observed_tokens_per_s_quantiles": {
            q: round(float(np.percentile(ev.eval_tps, q)), 2) for q in (5, 25, 50, 75, 95)
        },
        "tokens_per_s_at_context": gt,
    }
    rvw = ev.copy()
    rvw["day"] = (
        pd.to_datetime(rvw.gin_end_utc, utc=True, format="ISO8601")
        .dt.tz_convert("America/New_York")
        .dt.strftime("%Y-%m-%d")
    )
    out["generation"]["review_shaped_by_local_day"] = {
        d_: {
            "n": int(len(v)),
            "median_tps": round(float(v.eval_tps.median()), 2),
            "min": round(float(v.eval_tps.min()), 2),
            "max": round(float(v.eval_tps.max()), 2),
            "median_prompt": int(v.prompt_tokens.median()),
        }
        for d_, v in rvw.groupby("day")
    }
    rho = stats.spearmanr(rvw.ctx_mid, rvw.eval_tps)
    out["generation"]["review_shaped_spearman_ctx_vs_tps"] = {
        "rho": float(rho[0]),
        "p": float(rho[1]),
        "n": int(len(rvw)),
    }
    out["generation"]["review_shaped_tps_quantiles"] = {
        q: round(float(np.percentile(rvw.eval_tps, q)), 2) for q in (5, 25, 50, 75, 95)
    }
    loads = o[
        (o.model == "gpt-oss:20b") & (o.loaded_runner.eq(True)) & o.load_s.notna() & (o.load_s > 0)
    ].load_s  # noqa: E712
    out["runner_load"] = {
        "source": "ollama 'llama-server started in N seconds' for the request that loaded it",
        "n": int(len(loads)),
        "median_s": float(loads.median()),
        "p90_s": float(loads.quantile(0.9)),
        "max_s": float(loads.max()),
        "share_of_review_requests_that_reloaded": None,
    }
    # figure
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.6))
    ax = axes[0]
    ax.scatter(
        pp.prompt_eval_tokens / 1000, pp.prompt_eval_tps, s=10, color=S1, alpha=0.6, linewidths=0
    )
    xs = np.linspace(500, pp.prompt_eval_tokens.max(), 200)
    ax.plot(xs / 1000, xs / t_pp(xs), color=INK2, lw=1.5)
    ax.set_xlabel("prompt tokens read (thousands)")
    ax.set_ylabel("prompt read rate (tokens/s)")
    ax.set_title(f"Prompt reading slows with length (n={len(pp)})", loc="left", fontsize=9.5)
    ax = axes[1]
    ax.scatter(ev.ctx_mid / 1000, ev.eval_tps, s=10, color=S2, alpha=0.6, linewidths=0)
    xs = np.linspace(0, ev.ctx_mid.max(), 200)
    ax.plot(xs / 1000, 1 / (c0 + d0 * xs), color=INK2, lw=1.5)
    ax.set_xlabel("context position at mid-generation (thousands of tokens)")
    ax.set_ylabel("generation rate (tokens/s)")
    ax.set_title(f"Generation slows with context (n={len(ev)})", loc="left", fontsize=9.5)
    fig.text(
        0.01,
        0.005,
        "Source: Ollama server log, gpt-oss:20b on Apple M5 24 GB, 2026-09-27..10-01 (snapshot 21:45Z). Lines: fitted models.",
        fontsize=7,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "rates.png", dpi=160)
    plt.close(fig)
    return t_pp, t_gen, float(loads.median())


def review_requests(o, workloads=None):
    rv = o[
        o.workload.isin(workloads or REVIEW_WORKLOADS)
        & (o.model == "gpt-oss:20b")
        & (o.prompt_tokens >= 1000)
        & o.end_kind.isin(["stop", "length", "length_ctx", "cancelled", "abandoned"])
    ].copy()
    rv["event"] = (rv.end_kind == "stop").astype(int)
    rv["G"] = rv.generated_tokens.clip(lower=1).astype(float)
    rv["lp"] = np.log(rv.prompt_tokens / 30000.0)
    # Repeated reviews of one PR are not independent: bootstrap resamples PRs (clusters).
    rv["cluster"] = rv.ci_pr.where(rv.ci_pr.notna(), rv.workload + ":" + rv.source).astype(str)
    return rv


def fit_aft(df):
    best = None
    for cls in (WeibullAFTFitter, LogNormalAFTFitter, LogLogisticAFTFitter):
        m = cls()
        try:
            m.fit(df[["G", "event", "lp"]], duration_col="G", event_col="event")
        except Exception:  # noqa: BLE001
            continue
        if best is None or m.AIC_ < best.AIC_:
            best = m
    return best


def p_within(model, prompts, cap=CAP):
    X = pd.DataFrame({"lp": np.log(np.asarray(prompts, dtype=float) / 30000.0)})
    s = model.predict_survival_function(X, times=[cap]).values[0]
    return 1 - s


def quantile_G(model, prompt, q):
    X = pd.DataFrame({"lp": [np.log(prompt / 30000.0)]})
    return float(model.predict_percentile(X, p=1 - q).values[0])


def generation(o, out, t_pp, t_gen, load_s):
    rv = review_requests(o)
    out["review_population"] = {
        "definition": "gpt-oss:20b /api/chat PR-review requests (prompt >= 1000 tokens) at default effort (think '') or "
        "medium: CI (client ::1, inside a Sovereign job's review step) plus the documented local studies "
        "(think=medium pass and source-context pass). Excluded: think=low study, probes, and other host "
        "review-shaped traffic of unknown settings (benchmarks with num_predict 256/2048, an unidentified "
        "host process 2026-10-01 16:38-17:35 local) -- that set is used only as a sensitivity check",
        "n": int(len(rv)),
        "by_workload": rv.workload.value_counts().to_dict(),
        "by_end_kind": rv.end_kind.value_counts().to_dict(),
        "span_utc": [str(rv.gin_start_utc.min()), str(rv.gin_end_utc.max())],
        "prompt_tokens_quantiles": {
            q: int(np.percentile(rv.prompt_tokens, q)) for q in (0, 5, 25, 50, 75, 95, 100)
        },
    }
    done = rv[rv.event == 1]
    gq = {}
    for q in (25, 50, 75, 90, 95, 99):
        gq[str(q)] = {
            "tokens": float(np.percentile(done.G, q)),
            "ci95": boot(done.G.values, lambda x, q=q: np.percentile(x, q)),
        }
    rho, pval = stats.spearmanr(done.prompt_tokens, done.G)
    rb = []
    arr = done[["prompt_tokens", "G"]].values
    for _ in range(B):
        s = arr[RNG.integers(0, len(arr), len(arr))]
        rb.append(stats.spearmanr(s[:, 0], s[:, 1])[0])
    out["generated_completed_only"] = {
        "caveat": "completed requests only: biased low, because the longest generations were cut (see survival)",
        "n": int(len(done)),
        "quantiles": gq,
        "max": float(done.G.max()),
        "spearman_prompt_vs_generated": {"rho": float(rho), "p": float(pval), "ci95": ci(rb)},
    }
    # Kaplan-Meier, overall and by prompt bin
    km = KaplanMeierFitter().fit(rv.G, rv.event)
    s_cap = float(km.survival_function_at_times(CAP).values[0])
    lo, hi = km.confidence_interval_survival_function_.iloc[
        km.confidence_interval_survival_function_.index.get_indexer([CAP], method="ffill")[0]
    ].values
    bins = [(1000, 20000), (20000, 30000), (30000, 40000), (40000, 70000)]
    kmb = {}
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    for (a, b), col in zip(bins, (S1, S2, S3, S4), strict=False):
        sub = rv[(rv.prompt_tokens >= a) & (rv.prompt_tokens < b)]
        if len(sub) < 3:
            continue
        k = KaplanMeierFitter().fit(
            sub.G, sub.event, label=f"{a // 1000}-{b // 1000}k (n={len(sub)})"
        )
        kci = k.confidence_interval_survival_function_
        row = kci.index.get_indexer([CAP], method="ffill")[0]
        med = k.median_survival_time_
        kmb[f"{a}-{b}"] = {
            "n": int(len(sub)),
            "events": int(sub.event.sum()),
            "at_risk_beyond": {str(t): int((t < sub.G).sum()) for t in (4000, 8000, 12000, 16384)},
            "max_censored_G": float(sub[sub.event == 0].G.max())
            if (sub.event == 0).any()
            else None,
            "P_finish_within_16384": round(
                1 - float(k.survival_function_at_times(CAP).values[0]), 3
            ),
            "ci95": [
                round(1 - float(kci.iloc[row].values[1]), 3),
                round(1 - float(kci.iloc[row].values[0]), 3),
            ]
            if row >= 0
            else None,
            "median_G": None if not np.isfinite(med) else float(med),
        }
        k.plot_survival_function(ax=ax, ci_show=False, color=col, lw=2)
    ax.axvline(CAP, color=MUTED, lw=1, ls="--")
    ax.text(CAP, 0.98, " 16,384 cap", color=INK2, fontsize=8, va="top")
    ax.set_xlabel("tokens generated (reasoning + answer)")
    ax.set_ylabel("share still generating")
    ax.set_title(
        "Kaplan-Meier: how long the model keeps reasoning, by prompt size", loc="left", fontsize=9.5
    )
    ax.legend(title="prompt tokens", fontsize=8, title_fontsize=8)
    fig.text(
        0.01,
        0.005,
        "Censored at cap/context end/timeout/cancel. Source: Ollama log, review-shaped gpt-oss:20b requests, 2026-09-27..10-01.",
        fontsize=6.5,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "km_by_prompt.png", dpi=160)
    plt.close(fig)
    out["kaplan_meier"] = {
        "n": int(len(rv)),
        "events": int(rv.event.sum()),
        "censored": int((rv.event == 0).sum()),
        "P_finish_within_16384_all": round(1 - s_cap, 3),
        "ci95": [round(1 - hi, 3), round(1 - lo, 3)],
        "median_G": float(km.median_survival_time_),
        "by_prompt_bin": kmb,
    }
    # AFT
    model = fit_aft(rv)
    grid = np.arange(5000, 65001, 1000)
    pcurve = p_within(model, grid)
    bcurves, bthr, bcoef = [], [], []
    clusters = rv.cluster.unique()
    for _ in range(300):
        pick = RNG.choice(clusters, len(clusters))
        s = pd.concat([rv[rv.cluster == c_] for c_ in pick], ignore_index=True)
        try:
            m = type(model)().fit(s[["G", "event", "lp"]], duration_col="G", event_col="event")
        except Exception:  # noqa: BLE001
            continue
        c = p_within(m, grid)
        bcurves.append(c)
        ok = grid[c >= 0.95]
        bthr.append(float(ok.max()) if len(ok) else 0.0)
        bcoef.append(float([v for k, v in m.params_.items() if k[1] == "lp"][0]))
    bcurves = np.array(bcurves)
    ok = grid[pcurve >= 0.95]
    thr = float(ok.max()) if len(ok) else None
    coef = {f"{k[0]}:{k[1]}": float(v) for k, v in model.params_.items()}
    se = {f"{k[0]}:{k[1]}": float(v) for k, v in model.standard_errors_.items()}
    pts = {}
    for p in (10000, 15000, 20000, 25000, 30000, 35000, 40000, 50000, 60000):
        i = int(np.where(grid == p)[0][0])
        pts[str(p)] = {
            "P": round(float(pcurve[i]), 3),
            "ci95": [
                round(float(np.percentile(bcurves[:, i], 2.5)), 3),
                round(float(np.percentile(bcurves[:, i], 97.5)), 3),
            ],
            "median_G": round(quantile_G(model, p, 0.5)),
            "p90_G": round(quantile_G(model, p, 0.9)),
            "p95_G": round(quantile_G(model, p, 0.95)),
        }
    lp_key = [k for k in coef if k.endswith(":lp")][0]
    out["aft"] = {
        "model": type(model).__name__,
        "AIC": float(model.AIC_),
        "n": int(len(rv)),
        "events": int(rv.event.sum()),
        "covariate": "lp = ln(prompt_tokens / 30000)",
        "params": coef,
        "se": se,
        "lp_coef_bootstrap_ci95": ci(bcoef),
        "lp_coef_wald_p": float(model.summary.loc[tuple(lp_key.split(":")), "p"]),
        "P_finish_within_16384_by_prompt": pts,
        "largest_prompt_with_P_ge_0_95": thr,
        "threshold_bootstrap_ci95": ci(bthr),
        "bootstrap_resamples": int(len(bcurves)),
        "bootstrap_unit": "pull request (cluster); study requests are their own cluster",
        "clusters": int(rv.cluster.nunique()),
    }
    # Sensitivity: CI requests alone.
    ci_only = rv[rv.workload == "ci_review"]
    m_ci = fit_aft(ci_only)
    out["aft_ci_only"] = {
        "model": type(m_ci).__name__,
        "n": int(len(ci_only)),
        "events": int(ci_only.event.sum()),
        "P_finish_within_16384_by_prompt": {
            str(p): round(float(p_within(m_ci, [p])[0]), 3)
            for p in (10000, 20000, 30000, 40000, 50000)
        },
        "lp_coef": float([v for k, v in m_ci.params_.items() if k[1] == "lp"][0]),
    }
    pooled = review_requests(o, POOLED_WORKLOADS)
    m_pool = fit_aft(pooled)
    out["aft_pooled_with_host_runs"] = {
        "model": type(m_pool).__name__,
        "n": int(len(pooled)),
        "events": int(pooled.event.sum()),
        "P_finish_within_16384_by_prompt": {
            str(p): round(float(p_within(m_pool, [p])[0]), 3)
            for p in (10000, 20000, 30000, 40000, 50000)
        },
        "lp_coef": float([v for k, v in m_pool.params_.items() if k[1] == "lp"][0]),
    }
    # Operational completion (finished inside the request at the settings of the time).
    X = sm.add_constant(rv.lp.values)
    lg = sm.Logit(rv.event.values, X).fit(disp=0)
    _pr = (
        lg.get_prediction(sm.add_constant(np.log(grid / 30000.0))).summary_frame(alpha=0.05)
        if hasattr(lg, "get_prediction")
        else None
    )
    lin = sm.add_constant(np.log(grid / 30000.0)) @ lg.params
    cov = lg.cov_params()
    se_lin = np.sqrt(
        np.einsum(
            "ij,jk,ik->i",
            sm.add_constant(np.log(grid / 30000.0)),
            cov,
            sm.add_constant(np.log(grid / 30000.0)),
        )
    )
    plog = 1 / (1 + np.exp(-lin))
    plo, phi = 1 / (1 + np.exp(-(lin - 1.96 * se_lin))), 1 / (1 + np.exp(-(lin + 1.96 * se_lin)))
    out["logistic_operational"] = {
        "definition": "y=1 if the request stopped on its own; 0 if cut (timeout, cancel, cap, context end). "
        "Mixes the model's need with the deadline of the time; an operational, not a model, quantity.",
        "n": int(len(rv)),
        "params": {"const": float(lg.params[0]), "ln(prompt/30000)": float(lg.params[1])},
        "params_ci95": lg.conf_int().tolist(),
        "P_by_prompt": {
            str(p): {
                "P": round(float(plog[i]), 3),
                "ci95": [round(float(plo[i]), 3), round(float(phi[i]), 3)],
            }
            for p in (10000, 20000, 30000, 40000, 50000)
            for i in [int(np.where(grid == p)[0][0])]
        },
        "largest_prompt_with_P_ge_0_95": float(grid[plog >= 0.95].max())
        if (plog >= 0.95).any()
        else None,
    }
    # Figure: scatter + P curve
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.9))
    ax = axes[0]
    d = rv[rv.event == 1]
    c = rv[rv.event == 0]
    ax.scatter(
        d.prompt_tokens / 1000,
        d.G,
        s=14,
        color=S1,
        alpha=0.75,
        linewidths=0,
        label=f"stopped on its own (n={len(d)})",
    )
    ax.scatter(
        c.prompt_tokens / 1000,
        c.G,
        s=18,
        marker="^",
        facecolors="none",
        edgecolors=S2,
        linewidths=1,
        label=f"cut: cap/context/timeout/cancel (n={len(c)}) - true need is higher",
    )
    xs = np.arange(5000, 65001, 2500)
    ax.plot(
        xs / 1000,
        [quantile_G(model, x, 0.5) for x in xs],
        color=INK2,
        lw=1.5,
        label="fitted median need",
    )
    ax.plot(
        xs / 1000,
        [quantile_G(model, x, 0.95) for x in xs],
        color=INK2,
        lw=1.2,
        ls=":",
        label="fitted 95th percentile",
    )
    ax.axhline(CAP, color=MUTED, lw=1, ls="--")
    ax.text(5, CAP, "16,384 cap", color=INK2, fontsize=8, va="bottom")
    ax.set_yscale("log")
    ax.set_xlabel("prompt tokens (thousands)")
    ax.set_ylabel("tokens generated (log scale)")
    ax.set_title("Reasoning length vs prompt size", loc="left", fontsize=9.5)
    ax.legend(fontsize=7, loc="lower right")
    ax = axes[1]
    ax.fill_between(
        grid / 1000,
        np.percentile(bcurves, 2.5, axis=0),
        np.percentile(bcurves, 97.5, axis=0),
        color=S1,
        alpha=0.18,
        lw=0,
    )
    ax.plot(
        grid / 1000,
        pcurve,
        color=S1,
        label=f"censored model ({type(model).__name__[:-11]}), 95% band",
    )
    ax.plot(
        grid / 1000,
        plog,
        color=S2,
        lw=1.5,
        ls="--",
        label="observed: finished inside the request (logistic)",
    )
    for key, v in kmb.items():
        a, b = map(int, key.split("-"))
        mid = rv[(rv.prompt_tokens >= a) & (rv.prompt_tokens < b)].prompt_tokens.median()
        ax.errorbar(
            mid / 1000,
            v["P_finish_within_16384"],
            yerr=None
            if not v["ci95"]
            else [
                [v["P_finish_within_16384"] - v["ci95"][0]],
                [v["ci95"][1] - v["P_finish_within_16384"]],
            ],
            fmt="o",
            color=INK2,
            ms=4,
            lw=1,
            capsize=2,
        )
    ax.axhline(0.95, color=MUTED, lw=1, ls=":")
    ax.text(grid[0] / 1000, 0.95, "0.95", color=INK2, fontsize=8, va="bottom")
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("prompt tokens (thousands)")
    ax.set_ylabel("P(finishes within 16,384 tokens)")
    ax.set_title(
        "Completion probability vs prompt size (dots: Kaplan-Meier by bin)",
        loc="left",
        fontsize=9.5,
    )
    ax.legend(fontsize=7, loc="lower left")
    fig.text(
        0.01,
        0.005,
        f"Source: Ollama log 2026-09-27..10-01 (snapshot 21:45Z); review-shaped gpt-oss:20b requests, n={len(rv)}.",
        fontsize=7,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "completion_vs_prompt.png", dpi=160)
    plt.close(fig)
    # Wall time: validate the time model on completed review requests, then predict.
    d = done.copy()
    d["pred"] = [t_pp(p) + t_gen(p, g_) for p, g_ in zip(d.prompt_tokens, d.G, strict=False)]
    d["actual"] = d.processing_s
    err = (d.pred - d.actual) / d.actual
    wall = {}
    for p in (10000, 20000, 30000, 40000, 50000):
        row = {}
        for q in (0.5, 0.9, 0.95):
            g_ = min(quantile_G(model, p, q), 1e6)
            row[f"G_q{int(q * 100)}"] = round(g_)
            row[f"minutes_q{int(q * 100)}"] = round((load_s + t_pp(p) + t_gen(p, g_)) / 60, 1)
        row["minutes_at_cap_16384"] = round((load_s + t_pp(p) + t_gen(p, CAP)) / 60, 1)
        wall[str(p)] = row
    # Does the #1316 size-scaled deadline (P/200 + reserve/20, floor 600 s) cover a full
    # reserve at the measured rates? Using the true prompt tokens (the lane's estimate is
    # chars/3, which is >= true tokens when real text runs above 3 chars/token).
    adequacy = {}
    for p in (10000, 20000, 30000, 35000, 40000, 45000, 50000):
        need = load_s + t_pp(p) + t_gen(p, CAP)
        slow = (
            load_s + t_pp(p) + CAP / 15.0
        )  # a slow-host day: 15 tok/s (5th-25th pct of review requests)
        deadline = max(600, p / 200 + CAP / 20)
        adequacy[str(p)] = {
            "deadline_s": round(deadline),
            "need_at_fitted_rates_s": round(need),
            "margin_s": round(deadline - need),
            "need_at_15_tok_s": round(slow),
        }
    out["deadline_vs_full_reserve"] = adequacy
    out["wall_time"] = {
        "model": "load (median) + prompt read a*P+b*P^2 + generation c*G + d*(P*G + G^2/2)",
        "validation_on_completed_review_requests": {
            "n": int(len(d)),
            "median_abs_pct_error": round(float(np.median(np.abs(err)) * 100), 1),
            "p90_abs_pct_error": round(float(np.percentile(np.abs(err), 90) * 100), 1),
            "median_signed_pct_error": round(float(np.median(err) * 100), 1),
        },
        "predicted_by_prompt_tokens": wall,
    }
    return rv, model


def ci_reviews(o, r, rv, out):
    ci_req = o[o.workload == "ci_review"].copy()
    cov = r[r.ollama_log_covers == True]  # noqa: E712
    r = r.copy()
    r["after_1316"] = r.review_step_started_at >= PR_1316
    att = r[r.review_step_started_at.notna()]
    out["ci_reviews"] = {
        "source": "GitHub pr-review.yml runs, Sovereign diff review job (logs, job steps, artifacts), fetched 2026-10-01 ~21:45Z",
        "jobs_completed_not_skipped": int(len(r)),
        "with_log": int(r.log_available.sum()),
        "span_utc": [str(r.job_started_at.min()), str(r.job_started_at.max())],
        "codes_all": r.code.value_counts().to_dict(),
        "codes_review_step_ran": att.code.value_counts().to_dict(),
        "in_ollama_log_span": int(len(cov)),
        "in_span_with_joined_requests": int(cov.ollama_sources.map(len).gt(0).sum()),
        "settings_seen": att.settings.map(
            lambda s: json.dumps(
                {
                    k: s.get(k)
                    for k in (
                        "timeout",
                        "context_window",
                        "reasoning_reserve",
                        "think",
                        "max_chunks",
                        "output_tokens_per_second",
                    )
                },
                sort_keys=True,
            )
        )
        .value_counts()
        .to_dict(),
    }
    before = att[~att.after_1316]
    after = att[att.after_1316]

    def tab(x):
        return x.code.value_counts().to_dict()

    def reached(x):
        return x[
            x.code.isin(
                [
                    "reviewed",
                    "model_timeout",
                    "answer_incomplete",
                    "answer_unusable",
                    "prompt_truncated",
                    "model_busy",
                ]
            )
        ]  # noqa: E731

    b_, a_ = reached(before), reached(after)
    table = [
        [int((b_.code == "reviewed").sum()), int((b_.code != "reviewed").sum())],
        [int((a_.code == "reviewed").sum()), int((a_.code != "reviewed").sum())],
    ]
    ft = stats.fisher_exact(table)
    rq_b = ci_req[ci_req.gin_start_utc < PR_1316]
    rq_a = ci_req[ci_req.gin_start_utc >= PR_1316]
    out["pr_1316_before_after"] = {
        "cut": "review step started before/after 2026-10-01T18:16:01Z (7f056017f merged)",
        "jobs_before": tab(before),
        "jobs_after": tab(after),
        "verdict_rate_among_jobs_that_sent_a_request": {
            "before": {
                "reviewed": table[0][0],
                "n": sum(table[0]),
                "rate": round(table[0][0] / max(1, sum(table[0])), 3),
                "wilson95": [
                    round(x, 3)
                    for x in sm.stats.proportion_confint(
                        table[0][0], max(1, sum(table[0])), method="wilson"
                    )
                ],
            },
            "after": {
                "reviewed": table[1][0],
                "n": sum(table[1]),
                "rate": round(table[1][0] / max(1, sum(table[1])), 3),
                "wilson95": [
                    round(x, 3)
                    for x in sm.stats.proportion_confint(
                        table[1][0], max(1, sum(table[1])), method="wilson"
                    )
                ],
            },
            "fisher_exact_p": float(ft[1]),
        },
        "requests_before": rq_b.end_kind.value_counts().to_dict(),
        "requests_after": rq_a.end_kind.value_counts().to_dict(),
        "requests_after_detail": rq_a[
            [
                "gin_end_utc",
                "ci_pr",
                "prompt_tokens",
                "generated_tokens",
                "end_kind",
                "gin_duration_s",
                "n_ctx_slot",
            ]
        ]
        .astype(str)
        .to_dict("records"),
    }
    # Reasoning characters per token, where a length failure gives both.
    pairs = []
    for _, row in r[r.reasoning_chars.notna()].iterrows():
        mine = o[o.source.isin(row.ollama_sources) & o.end_kind.isin(["length", "length_ctx"])]
        for _, q in mine.iterrows():
            pairs.append(
                {
                    "pr": int(row.pr),
                    "reasoning_chars": int(row.reasoning_chars),
                    "tokens": int(q.generated_tokens),
                    "chars_per_token": round(row.reasoning_chars / q.generated_tokens, 2),
                    "source": "ci",
                }
            )
    lane = json.loads(
        (
            pathlib.Path(__file__).resolve().parents[4]
            / "docs/architecture/evidence/review-lane-2026-10-01.json"
        ).read_text()
    )
    study_len = o[(o.workload == "study_think_medium") & (o.end_kind == "length_ctx")].sort_values(
        "gin_end_utc"
    )
    study_rows = [x for x in lane["think_study"]["rows"] if "done_reason=length" in x["last_err"]]
    for x, (_, q) in zip(study_rows, study_len.iterrows(), strict=False):
        chars = int(x["last_err"].split("done_reason=length, ")[1].split(" ")[0])
        pairs.append(
            {
                "pr": x["pr"],
                "reasoning_chars": chars,
                "tokens": int(q.generated_tokens),
                "chars_per_token": round(chars / q.generated_tokens, 2),
                "source": "think_study (matched by order)",
            }
        )
    out["reasoning_chars_per_token"] = {
        "pairs": pairs,
        "n": len(pairs),
        "mean": round(float(np.mean([p["chars_per_token"] for p in pairs])), 2) if pairs else None,
    }
    # Content type: single-request CI reviews whose diff stats are known.
    rows = []
    for _, row in r.iterrows():
        j = row.ollama_join
        if not isinstance(j, dict) or j["requests"] != 1 or not isinstance(row["diff"], dict):
            continue
        rows.append(
            {
                "pr": row.pr,
                "diff_chars": row["diff"]["chars"],
                "files": row["diff"]["files"],
                "dominant": row["diff"]["dominant_class"],
                "prompt": j["prompt_tokens"][0],
                "G": j["generated_tokens"][0],
                "end": j["end_kinds"][0],
                "docs_share": row["diff"]["mix_share"].get("docs", 0),
                "code_share": row["diff"]["mix_share"].get("code", 0)
                + row["diff"]["mix_share"].get("test", 0),
            }
        )
    ct = pd.DataFrame(rows)
    res = {"n": int(len(ct))}
    if len(ct):
        st = ct[ct.end == "stop"]
        res["completed_n"] = int(len(st))
        res["by_dominant_class_completed"] = {
            k: {"n": int(len(v)), "median_G": float(v.G.median())}
            for k, v in st.groupby("dominant")
        }
        res["censored_by_dominant_class"] = ct[ct.end != "stop"].dominant.value_counts().to_dict()
        groups = [v.G.values for _, v in st.groupby("dominant") if len(v) >= 3]
        if len(groups) >= 2:
            res["kruskal_wallis_p"] = float(stats.kruskal(*groups).pvalue)
        rho = stats.spearmanr(st.code_share, st.G)
        res["spearman_code_or_test_share_vs_G_completed"] = {
            "rho": float(rho[0]),
            "p": float(rho[1]),
            "n": int(len(st)),
        }
        rho2 = stats.spearmanr(ct.diff_chars, ct.prompt)
        res["spearman_diff_chars_vs_prompt_tokens"] = {
            "rho": float(rho2[0]),
            "p": float(rho2[1]),
            "n": int(len(ct)),
        }
        ct2 = ct.copy()
        ct2["event"] = (ct2.end == "stop").astype(int)
        ct2["G"] = ct2.G.clip(lower=1).astype(float)
        ct2["lp"] = np.log(ct2.prompt / 30000.0)
        try:
            m2 = LogNormalAFTFitter().fit(
                ct2[["G", "event", "lp", "code_share"]], duration_col="G", event_col="event"
            )
            res["aft_lp_plus_code_or_test_share"] = {
                "n": int(len(ct2)),
                "events": int(ct2.event.sum()),
                "coef": {f"{k[0]}:{k[1]}": round(float(v), 3) for k, v in m2.params_.items()},
                "p": {f"{k[0]}:{k[1]}": float(v) for k, v in m2.summary.p.items()},
            }
        except Exception as e:  # noqa: BLE001
            res["aft_lp_plus_code_or_test_share"] = str(e)
        res["caveat"] = (
            "prompt also carries the declared documents (README.md, docs/index.md; up to 120000 chars) and, from "
            "#1303, the changed files' full text (up to 60000 chars): diff size is a weak proxy for prompt size"
        )
    out["content_type"] = res
    # Contention: did a CI request wait for the slot, and behind whom?
    tasks = o[o.end_kind != "no_task"].dropna(subset=["gin_end_utc"]).copy()
    tasks["proc_start"] = tasks.gin_end_utc - pd.to_timedelta(
        tasks.processing_s.fillna(0) + tasks.load_s.fillna(0), unit="s"
    )
    waits = []
    for _, q in ci_req.iterrows():
        others = tasks[
            (tasks.gin_client != "::1")
            & (tasks.proc_start < q.gin_start_utc + pd.Timedelta(seconds=1))
            & (tasks.gin_end_utc > q.gin_start_utc)
        ]
        same = tasks[
            (tasks.gin_client == "::1")
            & (tasks.source != q.source)
            & (tasks.proc_start < q.gin_start_utc)
            & (tasks.gin_end_utc > q.gin_start_utc)
        ]
        waits.append(
            {"wait_s": q.wait_s, "behind_other_client": len(others) > 0, "behind_ci": len(same) > 0}
        )
    w = pd.DataFrame(waits)
    out["contention"] = {
        "source": "Ollama access-line duration minus llama-server load and slot processing time (wait_s); in-flight overlap by timestamps",
        "ci_requests": int(len(w)),
        "wait_s_quantiles": {
            q: round(float(np.nanpercentile(w.wait_s, q)), 1) for q in (50, 75, 90, 95, 99)
        },
        "share_wait_gt_10s": round(float((w.wait_s > 10).mean()), 3),
        "share_wait_gt_60s": round(float((w.wait_s > 60).mean()), 3),
        "wilson95_wait_gt_60s": [
            round(x, 3)
            for x in sm.stats.proportion_confint(
                int((w.wait_s > 60).sum()), len(w), method="wilson"
            )
        ],
        "arrived_while_other_client_in_flight": int(w.behind_other_client.sum()),
        "arrived_while_other_ci_request_in_flight": int(w.behind_ci.sum()),
        "ci_probes_wait_s": o[o.workload == "ci_probe"].wait_s.round(1).tolist(),
        "load_failures_no_task": int(
            ((o.end_kind == "no_task") & (o.gin_path == "/api/chat") & (o.gin_status >= 500)).sum()
        ),
        "all_requests_wait_gt_60s_by_workload": o[(o.wait_s > 60)]
        .workload.value_counts()
        .to_dict(),
    }
    # Think low vs medium (paired by order within the study).
    low = o[o.workload == "study_think_low"].sort_values("gin_end_utc")
    med = o[o.workload == "study_think_medium"].sort_values("gin_end_utc")
    out["think_study_generated"] = {
        "low": {
            "n": int(len(low)),
            "G": low.generated_tokens.tolist(),
            "end": low.end_kind.tolist(),
            "prompt": low.prompt_tokens.tolist(),
        },
        "medium": {
            "n": int(len(med)),
            "G": med.generated_tokens.tolist(),
            "end": med.end_kind.tolist(),
            "prompt": med.prompt_tokens.tolist(),
        },
        "note": "study_think_low/medium are the host (127.0.0.1) requests in the documented windows; the study's own table says "
        "think=low passed all 8 PRs incl. the 4 whose default-effort gate was blocking (rubber stamp)",
    }
    # Timeline figure of CI job outcomes
    fig, ax = plt.subplots(figsize=(9.5, 2.9))
    order = [
        "reviewed",
        "model_timeout",
        "answer_incomplete",
        "answer_unusable",
        "diff_exceeds_window",
        "chunk_budget_exceeded",
        "cancelled",
    ]
    cols = {
        "reviewed": S3,
        "model_timeout": S2,
        "answer_incomplete": "#e34948",
        "answer_unusable": S4,
        "diff_exceeds_window": S5,
        "chunk_budget_exceeded": "#4a3aa7",
        "cancelled": MUTED,
    }
    att2 = att.copy()
    att2["cat"] = att2.code.where(att2.code.isin(order), "cancelled")
    for i, k in enumerate(order):
        sub = att2[att2.cat == k]
        ax.scatter(sub.review_step_started_at, [i] * len(sub), s=16, color=cols[k], linewidths=0)
    ax.set_yticks(
        range(len(order)), [f"{k} ({int((att2.cat == k).sum())})" for k in order], fontsize=8
    )
    ax.axvline(PR_1316, color=INK2, lw=1, ls="--")
    ax.text(PR_1316, len(order) - 0.6, " #1316 merged", fontsize=8, color=INK2)
    ax.set_title(
        "Sovereign diff review outcomes over time (review step started)", loc="left", fontsize=9.5
    )
    ax.grid(axis="y", visible=False)
    fig.text(
        0.01,
        0.005,
        "Source: GitHub pr-review.yml job logs/artifacts, 2026-09-21..10-01 (fetched 21:45Z). 'cancelled' includes other early ends.",
        fontsize=7,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "ci_outcomes_timeline.png", dpi=160)
    plt.close(fig)
    # Wait figure
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ww = np.sort(w.wait_s.fillna(0).values)
    ax.step(ww, np.arange(1, len(ww) + 1) / len(ww), where="post", color=S1)
    ax.set_xscale("symlog", linthresh=1)
    ax.set_xlabel("seconds queued before the slot took the request")
    ax.set_ylabel("share of CI requests")
    ax.set_title(
        f"CI review requests: time waiting for the model (n={len(ww)})", loc="left", fontsize=9.5
    )
    fig.text(
        0.01,
        0.005,
        "Source: Ollama log access-line duration minus load and processing, 2026-09-27..10-01.",
        fontsize=7,
        color=MUTED,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "ci_wait_cdf.png", dpi=160)
    plt.close(fig)


def main():
    o, r = load()
    out = {
        "cutoff": {
            "ollama_snapshot_utc": (EVIDENCE / "raw" / "ollama" / "SNAPSHOT_AT_UTC")
            .read_text()
            .strip(),
            "github_fetch_utc": "2026-10-01T21:40Z..21:50Z",
        }
    }
    t_pp, t_gen, load_s = rates(o, out)
    rv, model = generation(o, out, t_pp, t_gen, load_s)
    reloaded = o[o.workload == "ci_review"].loaded_runner.mean()
    out["runner_load"]["share_of_review_requests_that_reloaded"] = round(float(reloaded), 3)
    ci_reviews(o, r, rv, out)
    (HERE / "results.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
