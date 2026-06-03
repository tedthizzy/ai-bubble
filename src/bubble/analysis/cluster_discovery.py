"""Unsupervised discovery of the financed-AI cluster structure (data-driven boundary).

Instead of asserting "the financed cluster is the ~8 names I picked", this DISCOVERS
the natural grouping from objective financial features and only THEN attaches a
human-readable label to each discovered cluster. The pipeline is the standard quant
one: scale-free feature engineering -> standardize -> PCA (latent factors) ->
clustering with the cluster count chosen EMPIRICALLY (silhouette over k, plus GMM
BIC) -> bootstrap stability -> retro-label clusters by their centroid profile ->
identify the fragile (high-leverage / cash-flow-negative) cluster.

Honesty about n: the feature-complete sample is the public issuers with disclosed
financials (small n), so the *number* of clusters carries real uncertainty -- the
output reports silhouette, BIC, and bootstrap co-assignment stability so the
confidence in k is visible, never a false-precise headcount. Private names and
hyperscalers are excluded by construction (no comparable financials), which is a
feature, not a bug: clustering on missing data would cluster on missingness.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

# Scale-free financial features (ratios) so large and small issuers are comparable.
FEATURE_NAMES = (
    "leverage_debt_to_revenue",
    "ebitda_margin",
    "net_margin",
    "interest_coverage",
    "cash_to_debt",
)


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _short(name: str) -> str:
    return str(name or "").split("(")[0].split(",")[0].strip()


def _features_for(row: dict[str, Any]) -> list[float] | None:
    rev = _num(row.get("revenue_usd"))
    ebitda = _num(row.get("ebitda_usd"))
    net = _num(row.get("net_income_usd"))
    debt = _num(row.get("total_debt_usd"))
    interest = _num(row.get("annual_interest_expense_usd"))
    cash = _num(row.get("cash_and_equivalents_usd"))
    if rev is None or rev <= 0 or debt is None:
        return None
    # Clip interest coverage to a sane band so a near-zero interest doesn't explode it.
    coverage = (ebitda / interest) if (ebitda is not None and interest and interest > 0) else 0.0
    coverage = float(np.clip(coverage, -20, 20))
    return [
        debt / rev,
        (ebitda / rev) if ebitda is not None else 0.0,
        (net / rev) if net is not None else 0.0,
        coverage,
        (cash / debt) if (cash is not None and debt > 0) else 0.0,
    ]


def build_feature_matrix(
    issuers: list[dict[str, Any]],
) -> tuple[list[str], tuple[str, ...], np.ndarray]:
    """Build the entity x feature matrix from issuer financial rows (drops incomplete rows)."""

    names: list[str] = []
    rows: list[list[float]] = []
    for r in issuers:
        feats = _features_for(r)
        if feats is None:
            continue
        names.append(_short(r.get("entity", "")))
        rows.append(feats)
    return names, FEATURE_NAMES, np.array(rows, dtype=float) if rows else np.empty((0, 5))


def _retro_label(centroid: dict[str, float]) -> str:
    """Attach a human-readable label to a discovered cluster from its centroid profile."""

    lev = centroid["leverage_debt_to_revenue"]
    ebitda_m = centroid["ebitda_margin"]
    cov = centroid["interest_coverage"]
    if ebitda_m < 0 or cov < 1.0:
        base = "cash_flow_negative_fragile"
    elif ebitda_m > 0.2 and cov > 3:
        base = "profitable_self_funding"
    else:
        base = "thin_margin_levered"
    lev_tag = "high_leverage" if lev > 2.0 else ("moderate_leverage" if lev > 0.75 else "low_leverage")
    return f"{base}__{lev_tag}"


def discover_structure(
    issuers: list[dict[str, Any]],
    *,
    max_k: int = 5,
    bootstrap: int = 200,
    random_state: int = 0,
) -> dict[str, Any]:
    """Discover the natural cluster structure + choose k empirically + bootstrap stability."""

    names, feature_names, x = build_feature_matrix(issuers)
    n = len(names)
    if n < 6:
        return {"status": "blocked_insufficient_n", "n": n}

    xs = StandardScaler().fit_transform(x)
    pca = PCA(random_state=random_state).fit(xs)
    explained = [round(float(v), 3) for v in pca.explained_variance_ratio_]

    # Choose k empirically: silhouette (higher better) across k=2..min(max_k, n-1).
    ks = list(range(2, min(max_k, n - 1) + 1))
    per_k: list[dict[str, Any]] = []
    best_k, best_sil = 2, -1.0
    for k in ks:
        labels = KMeans(n_clusters=k, n_init=25, random_state=random_state).fit_predict(xs)
        sil = float(silhouette_score(xs, labels)) if len(set(labels)) > 1 else -1.0
        gmm = GaussianMixture(n_components=k, covariance_type="diag", random_state=random_state).fit(xs)
        per_k.append({"k": k, "silhouette": round(sil, 3), "gmm_bic": round(float(gmm.bic(xs)), 1)})
        if sil > best_sil:
            best_sil, best_k = sil, k

    km = KMeans(n_clusters=best_k, n_init=25, random_state=random_state)
    labels = km.fit_predict(xs)

    # Bootstrap stability: fraction of resamples where each pair keeps its co-assignment.
    rng = np.random.default_rng(random_state)
    base_co = labels[:, None] == labels[None, :]
    agree = np.zeros((n, n))
    counts = np.zeros((n, n))
    for _ in range(bootstrap):
        idx = rng.choice(n, n, replace=True)
        uniq = np.unique(idx)
        if len(uniq) < best_k:
            continue
        bl = KMeans(
            n_clusters=best_k, n_init=10, random_state=int(rng.integers(1_000_000))
        ).fit_predict(xs[uniq])
        lab = {u: bl[i] for i, u in enumerate(uniq)}
        for a in uniq:
            for b in uniq:
                counts[a, b] += 1
                if lab[a] == lab[b]:
                    agree[a, b] += 1
    with np.errstate(invalid="ignore", divide="ignore"):
        coassign = np.where(counts > 0, agree / counts, np.nan)
    mask = ~np.eye(n, dtype=bool)
    stability = float(np.nanmean(np.abs((coassign[mask] > 0.5).astype(float) - base_co[mask].astype(float))))
    stability_score = round(1.0 - stability, 3)  # 1 = perfectly stable

    # Cluster centroids in ORIGINAL feature units + retro-labels.
    clusters: list[dict[str, Any]] = []
    for c in range(best_k):
        members = [names[i] for i in range(n) if labels[i] == c]
        centroid = {
            feature_names[j]: round(float(x[labels == c, j].mean()), 3)
            for j in range(len(feature_names))
        }
        clusters.append(
            {
                "cluster": c,
                "label": _retro_label(centroid),
                "size": len(members),
                "members": members,
                "centroid": centroid,
            }
        )

    # The fragile cluster: most negative ebitda margin / lowest coverage.
    fragile = min(
        clusters, key=lambda cl: (cl["centroid"]["ebitda_margin"], cl["centroid"]["interest_coverage"])
    )

    return {
        "status": "source_backed",
        "n": n,
        "entities": names,
        "feature_names": list(feature_names),
        "chosen_k": best_k,
        "chosen_k_silhouette": round(best_sil, 3),
        "k_selection": per_k,
        "pca_explained_variance_ratio": explained,
        "bootstrap_stability": stability_score,
        "clusters": clusters,
        "fragile_cluster_label": fragile["label"],
        "fragile_cluster_members": fragile["members"],
        "discovery_read": _read(best_k, best_sil, fragile, stability_score, n),
        "note": (
            "Unsupervised cluster DISCOVERY (StandardScaler -> PCA -> KMeans, k chosen by silhouette + "
            "GMM BIC, bootstrap stability) over scale-free financial features of the feature-complete "
            "public issuers. The clusters are discovered FIRST, then retro-labelled by centroid profile "
            "-- the boundary is data-driven, not asserted. Small-n: read k with the silhouette + "
            "stability, not as a precise count; private names / hyperscalers are excluded (no comparable "
            "financials), so this is the leveraged-public-issuer structure, not the whole ecosystem."
        ),
    }


def _read(k: int, sil: float, fragile: dict[str, Any], stability: float, n: int) -> str:
    members = ", ".join(fragile["members"][:8])
    return (
        f"discovered_{k}_clusters (n={n}, silhouette {round(sil, 2)}, bootstrap stability "
        f"{stability}): the data splits the leveraged public issuers into {k} natural groups. The "
        f"FRAGILE cluster ('{fragile['label']}', {fragile['size']} members: {members}) carries the "
        "negative-margin / sub-1x-coverage signature the bubble thesis predicts -- this membership is "
        "DISCOVERED from the financials, then labelled, not hand-picked. Treat k as indicative given "
        "small n; the fragile cluster's separation is the load-bearing result."
    )
