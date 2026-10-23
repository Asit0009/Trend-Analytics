import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from src.segmentation.features import RFM_COLUMNS

warnings.filterwarnings("ignore", message="Could not find the number of physical cores")

SEED = 42
K_RANGE = range(2, 9)
SMALLEST_USEFUL_K = 3


def scale_features(rfm):
    logged = np.log1p(rfm[RFM_COLUMNS].astype(float))
    return StandardScaler().fit_transform(logged)


def fit_kmeans(scaled, k, seed=SEED):
    return KMeans(n_clusters=k, n_init=10, random_state=seed).fit(scaled)


def find_elbow(k_values, inertias):
    x = np.array(k_values, dtype=float)
    y = np.array(inertias, dtype=float)
    x_scaled = (x - x.min()) / (x.max() - x.min())
    y_scaled = (y - y.min()) / (y.max() - y.min())
    distance_to_line = np.abs(x_scaled + y_scaled - 1) / np.sqrt(2)
    return int(x[np.argmax(distance_to_line)])


def evaluate_k(scaled, k_range=K_RANGE, seed=SEED):
    rows = []
    for k in k_range:
        model = fit_kmeans(scaled, k, seed)
        rows.append({
            "k": k,
            "inertia": float(model.inertia_),
            "silhouette": float(silhouette_score(scaled, model.labels_)),
        })
    scores = pd.DataFrame(rows)
    useful = scores[scores["k"] >= SMALLEST_USEFUL_K]
    best_k = int(useful.loc[useful["silhouette"].idxmax(), "k"])
    elbow_k = find_elbow(scores["k"], scores["inertia"])
    return scores, best_k, elbow_k


def label_cluster(row, overall):
    recent = row["recency_days"] <= overall["recency_days"]
    frequent = row["frequency"] > overall["frequency"]
    big_spender = row["monetary"] > overall["monetary"]
    if frequent and recent:
        return "Loyal"
    if big_spender and not frequent:
        return "Big spenders"
    if not frequent and recent and row["frequency"] < 1.5:
        return "New"
    if not recent and (frequent or big_spender):
        return "At risk"
    if not recent:
        return "Lapsed"
    return "Occasional"


def name_segments(profile, overall):
    names = {}
    used = {}
    for cluster_id, row in profile.sort_values("monetary", ascending=False).iterrows():
        base = label_cluster(row, overall)
        used[base] = used.get(base, 0) + 1
        names[cluster_id] = base if used[base] == 1 else f"{base} {used[base]}"
    return names


def segment_customers(rfm, k, seed=SEED):
    scaled = scale_features(rfm)
    model = fit_kmeans(scaled, k, seed)
    result = rfm.copy()
    result["cluster"] = model.labels_
    overall = result[RFM_COLUMNS].mean()
    profile = result.groupby("cluster")[RFM_COLUMNS].mean()
    names = name_segments(profile, overall)
    result["segment"] = result["cluster"].map(names)

    pca = PCA(n_components=2, random_state=seed)
    coordinates = pca.fit_transform(scaled)
    result["pc1"] = coordinates[:, 0]
    result["pc2"] = coordinates[:, 1]
    return result, pca.explained_variance_ratio_


def summarise_segments(segmented):
    summary = segmented.groupby("segment").agg(
        customers=("customer_id", "count"),
        avg_spend=("monetary", "mean"),
        avg_orders=("frequency", "mean"),
        avg_recency_days=("recency_days", "mean"),
        total_spend=("monetary", "sum"),
    )
    summary["share_of_customers"] = summary["customers"] / summary["customers"].sum()
    summary["share_of_revenue"] = summary["total_spend"] / summary["total_spend"].sum()
    return summary.sort_values("avg_spend", ascending=False).reset_index()


def stability_check(rfm, k, seeds=range(10), reference_seed=SEED):
    scaled = scale_features(rfm)
    reference = fit_kmeans(scaled, k, reference_seed).labels_
    scores = []
    for seed in seeds:
        labels = fit_kmeans(scaled, k, seed).labels_
        scores.append(adjusted_rand_score(reference, labels))
    return {
        "seeds": len(list(seeds)),
        "mean_ari": float(np.mean(scores)),
        "min_ari": float(np.min(scores)),
    }
