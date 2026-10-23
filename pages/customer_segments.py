import streamlit as st

from src import ui
from src.plots import charts
from src.segmentation.clustering import (
    SMALLEST_USEFUL_K,
    evaluate_k,
    scale_features,
    segment_customers,
    stability_check,
    summarise_segments,
)
from src.segmentation.features import build_rfm


@st.cache_data(show_spinner="Trying different numbers of segments...")
def score_k_values(rfm):
    return evaluate_k(scale_features(rfm))


@st.cache_data(show_spinner="Grouping customers...")
def run_segmentation(rfm, k):
    return segment_customers(rfm, k)


@st.cache_data(show_spinner="Checking stability across random seeds...")
def run_stability(rfm, k):
    return stability_check(rfm, k)


ui.require_router()

st.title("Customer Segments")
st.caption(
    "Customers are grouped by how recently they bought, how often they buy and how much they spend. "
    "The sales channel filter in the sidebar applies here."
)

tables = ui.page_tables()
rfm = build_rfm(tables.orders)
if len(rfm) < 50:
    st.warning("Fewer than 50 customers have orders in this selection. Widen the channel filter.")
    st.stop()

scores, best_k, elbow_k = score_k_values(rfm)
k = st.slider("Number of segments", 2, 8, best_k)

segmented, explained = run_segmentation(rfm, k)
summary = summarise_segments(segmented)

with st.expander("How the number of segments was chosen", expanded=False):
    st.plotly_chart(charts.k_selection_chart(scores, best_k, elbow_k), width="stretch")
    top = scores.loc[scores["silhouette"].idxmax()]
    chosen = scores[scores["k"] == best_k].iloc[0]
    st.write(
        f"The silhouette score is highest at k={int(top['k'])} ({top['silhouette']:.2f}), but two groups only "
        f"split active customers from lapsed ones, which is too coarse to act on. Starting from "
        f"k={SMALLEST_USEFUL_K}, the best silhouette is at k={best_k} ({chosen['silhouette']:.2f}). "
        f"The elbow plot bends at k={elbow_k}, "
        + ("which agrees." if elbow_k == best_k else "so the two checks are close but not identical. You can move the slider to compare.")
    )
    st.write(
        "Features are put on a log scale and then standardised, because a few customers spend far more than "
        "the rest and would otherwise decide the clusters."
    )

st.subheader("Segment summary")
st.dataframe(
    summary,
    hide_index=True,
    width="stretch",
    column_config={
        "segment": "Segment",
        "customers": "Customers",
        "avg_spend": st.column_config.NumberColumn("Average spend", format="₹%.0f"),
        "avg_orders": st.column_config.NumberColumn("Average orders", format="%.2f"),
        "avg_recency_days": st.column_config.NumberColumn("Days since last order", format="%.0f"),
        "total_spend": st.column_config.NumberColumn("Total spend", format="₹%.0f"),
        "share_of_customers": st.column_config.NumberColumn("Share of customers", format="percent"),
        "share_of_revenue": st.column_config.NumberColumn("Share of revenue", format="percent"),
    },
)
st.caption("Segment names are given from each group's average recency, frequency and spend.")

left, right = st.columns([1.6, 1])
with left:
    st.subheader("Customers in two dimensions")
    st.plotly_chart(charts.pca_chart(segmented, explained), width="stretch")
    st.caption(
        f"PCA squeezes the three scaled features into two axes. Together they keep "
        f"{explained.sum() * 100:.0f}% of the variation."
    )
with right:
    st.subheader("Segment sizes")
    st.plotly_chart(charts.segment_size_chart(summary), width="stretch")
    stability = run_stability(rfm, k)
    st.write(
        f"Stability: K-Means was rerun with {stability['seeds']} different random seeds. "
        f"The groups matched the first run with an adjusted Rand index of {stability['mean_ari']:.3f} on "
        f"average and {stability['min_ari']:.3f} at worst (1.0 means identical)."
    )

export = segmented.merge(
    tables.customers[["customer_id", "customer_name", "segment"]].rename(columns={"segment": "channel"}),
    on="customer_id",
    how="left",
).rename(columns={"segment": "customer_segment"})
export = export[[
    "customer_id", "customer_name", "channel", "recency_days", "frequency", "monetary", "customer_segment",
]]
st.download_button(
    "Download customers with segment labels",
    export.to_csv(index=False).encode("utf-8"),
    "customer_segments.csv",
    "text/csv",
)
