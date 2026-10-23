import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

PALETTE = ["#1f6f8b", "#e07a5f", "#3d8361", "#8e6c9c", "#c9a227", "#5c6b73", "#b5495b", "#4c9be8"]
TEMPLATE = "plotly_white"


def style(figure, height=380, legend_on_top=True):
    figure.update_layout(
        template=TEMPLATE,
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        colorway=PALETTE,
    )
    if legend_on_top:
        figure.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return figure


def monthly_revenue_chart(monthly):
    figure = go.Figure()
    figure.add_bar(
        x=monthly["month"], y=monthly["revenue"], name="Revenue", marker_color=PALETTE[0],
        hovertemplate="%{x|%b %Y}<br>Revenue: ₹%{y:,.0f}<extra></extra>",
    )
    figure.add_scatter(
        x=monthly["month"], y=monthly["orders"], name="Orders", yaxis="y2", mode="lines+markers",
        line=dict(color=PALETTE[1]), hovertemplate="%{x|%b %Y}<br>Orders: %{y:,}<extra></extra>",
    )
    figure.update_layout(
        yaxis=dict(title="Revenue (INR)"),
        yaxis2=dict(title="Orders", overlaying="y", side="right", showgrid=False),
    )
    return style(figure)


def category_share_chart(category_revenue):
    figure = px.pie(category_revenue, names="category", values="order_value", hole=0.5)
    figure.update_traces(textinfo="percent+label", hovertemplate="%{label}<br>₹%{value:,.0f}<extra></extra>")
    figure.update_layout(showlegend=False)
    return style(figure, legend_on_top=False)


def top_products_chart(top_products):
    figure = px.bar(
        top_products, x="revenue", y="product_name", orientation="h", color="category",
        labels={"revenue": "Revenue (INR)", "product_name": ""},
    )
    figure.update_layout(yaxis=dict(autorange="reversed"))
    return style(figure)


def basket_chart(basket_counts):
    figure = px.bar(
        basket_counts, x="items_in_order", y="total_orders", text="total_orders",
        labels={"items_in_order": "Items in one order", "total_orders": "Orders"},
    )
    figure.update_xaxes(tickmode="linear")
    figure.update_traces(textposition="outside", marker_color=PALETTE[0])
    return style(figure, legend_on_top=False)


def retention_heatmap(matrix, as_percent, colorscale="Blues"):
    values = matrix * 100 if as_percent else matrix
    suffix = "%" if as_percent else ""
    digits = 1 if as_percent else 0
    text = values.apply(lambda column: column.map(lambda v: "" if np.isnan(v) else f"{v:.{digits}f}{suffix}"))
    figure = go.Figure(go.Heatmap(
        z=values.values,
        x=[f"+{column}" for column in values.columns],
        y=list(values.index),
        text=text.values,
        texttemplate="%{text}",
        colorscale=colorscale,
        xgap=1,
        ygap=1,
        colorbar=dict(title="%" if as_percent else "Customers"),
        hovertemplate="Cohort %{y}<br>Month %{x}<br>%{z:.1f}<extra></extra>",
    ))
    figure.update_layout(
        xaxis=dict(title="Months since signup"),
        yaxis=dict(title="Signup month", autorange="reversed"),
    )
    return style(figure, height=560, legend_on_top=False)


def ltv_chart(ltv, cac_target, max_cohorts=10):
    figure = go.Figure()
    for cohort in ltv.index[-max_cohorts:]:
        row = ltv.loc[cohort].dropna()
        figure.add_scatter(
            x=[f"+{month}" for month in row.index], y=row.values, name=cohort, mode="lines+markers",
            hovertemplate=f"Cohort {cohort}<br>Month %{{x}}<br>LTV: ₹%{{y:,.0f}}<extra></extra>",
        )
    figure.add_hline(
        y=cac_target, line_dash="dash", line_color="#b5495b",
        annotation_text=f"Target CAC ₹{cac_target:,}", annotation_position="top left",
    )
    figure.update_layout(
        xaxis=dict(title="Months since signup"),
        yaxis=dict(title="Cumulative spend per customer (INR)"),
    )
    return style(figure, height=440)


def interval_histogram(intervals):
    figure = px.histogram(
        intervals, x="days_between", nbins=45, labels={"days_between": "Days between orders"},
    )
    figure.update_traces(marker_color=PALETTE[2])
    figure.update_layout(yaxis=dict(title="Orders"))
    return style(figure, legend_on_top=False)


def order_sequence_chart(sequence_stats):
    figure = px.bar(
        sequence_stats, x="order_sequence", y="avg_value",
        labels={"order_sequence": "Order number", "avg_value": "Average order value (INR)"},
    )
    figure.update_traces(marker_color=PALETTE[3], texttemplate="%{y:,.0f}", textposition="outside")
    return style(figure, legend_on_top=False)


def forecast_chart(history, forecast, title, other_models=None):
    figure = go.Figure()
    figure.add_scatter(
        x=history.index, y=history.values, name="History", mode="lines+markers",
        line=dict(color=PALETTE[0]), marker=dict(size=5),
    )
    figure.add_scatter(
        x=forecast["month"], y=forecast["upper"], mode="lines", line=dict(width=0),
        showlegend=False, hoverinfo="skip",
    )
    figure.add_scatter(
        x=forecast["month"], y=forecast["lower"], mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor="rgba(224,122,95,0.25)", name="Prediction range", hoverinfo="skip",
    )
    for name, other in (other_models or {}).items():
        figure.add_scatter(
            x=other["month"], y=other["forecast"], name=name, mode="lines",
            line=dict(dash="dot", width=1.5),
        )
    figure.add_scatter(
        x=forecast["month"], y=forecast["forecast"], name="Forecast", mode="lines+markers",
        line=dict(color=PALETTE[1]), marker=dict(size=6),
        hovertemplate="%{x|%b %Y}<br>Forecast: ₹%{y:,.0f}<extra></extra>",
    )
    figure.update_layout(title=title, yaxis=dict(title="Monthly revenue (INR)"))
    figure = style(figure, height=460)
    figure.update_layout(margin=dict(l=10, r=10, t=90, b=10))
    return figure


def backtest_chart(backtest_results, title):
    one_step = backtest_results[backtest_results["step"] == 1].sort_values("target_month")
    figure = go.Figure()
    figure.add_scatter(x=one_step["target_month"], y=one_step["actual"], name="Actual", mode="lines+markers")
    figure.add_scatter(
        x=one_step["target_month"], y=one_step["predicted"], name="One month ahead forecast",
        mode="lines+markers", line=dict(dash="dot"),
    )
    figure.update_layout(title=title, yaxis=dict(title="Monthly revenue (INR)"))
    figure = style(figure, height=340)
    figure.update_layout(margin=dict(l=10, r=10, t=90, b=10))
    return figure


def k_selection_chart(scores, best_k, elbow_k):
    figure = make_subplots(rows=1, cols=2, subplot_titles=("Elbow plot (inertia)", "Silhouette score"))
    figure.add_scatter(x=scores["k"], y=scores["inertia"], mode="lines+markers", row=1, col=1, showlegend=False)
    figure.add_scatter(x=scores["k"], y=scores["silhouette"], mode="lines+markers", row=1, col=2, showlegend=False)
    figure.add_vline(x=elbow_k, line_dash="dash", line_color=PALETTE[1], row=1, col=1)
    figure.add_vline(x=best_k, line_dash="dash", line_color=PALETTE[1], row=1, col=2)
    figure.update_xaxes(title_text="Number of segments (k)", dtick=1)
    return style(figure, height=320, legend_on_top=False)


def pca_chart(segmented, explained_variance):
    figure = px.scatter(
        segmented, x="pc1", y="pc2", color="segment", opacity=0.6,
        hover_data={"customer_id": True, "frequency": True, "monetary": ":,.0f", "recency_days": True,
                    "pc1": False, "pc2": False},
        labels={
            "pc1": f"Component 1 ({explained_variance[0] * 100:.0f}% of variance)",
            "pc2": f"Component 2 ({explained_variance[1] * 100:.0f}% of variance)",
        },
    )
    figure.update_traces(marker=dict(size=5))
    return style(figure, height=480)


def segment_size_chart(summary):
    figure = px.bar(
        summary, x="segment", y="customers", text="customers", labels={"segment": "", "customers": "Customers"},
    )
    figure.update_traces(marker_color=PALETTE[0], textposition="outside")
    return style(figure, height=300, legend_on_top=False)
