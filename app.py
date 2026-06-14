import os
import re
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import cohort_analytics as ca

# Custom stylesheet for glassmorphic cards and hover elevations
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .login-container {
        max-width: 500px;
        margin: 5rem auto;
        background: #1e1b4b; 
        padding: 2.5rem;
        border-radius: 12px;
        border: 1px solid #312e81;
        box-shadow: 0 4px 30px rgba(0,0,0,0.2);
        text-align: center;
    }
    
    .login-title {
        font-size: 2rem;
        font-weight: 700;
        color: #f8fafc;
        margin-bottom: 0.25rem;
        letter-spacing: 0.05em;
    }
    
    .login-subtitle {
        font-size: 0.875rem;
        color: #c084fc;
        margin-bottom: 2rem;
    }
    
    .metric-container {
        display: flex;
        gap: 1rem;
        margin-bottom: 2rem;
        flex-wrap: wrap;
    }
    
    .metric-card {
        flex: 1;
        min-width: 180px;
        background: #1e1b4b;
        color: #f8fafc;
        border-radius: 8px;
        padding: 1.25rem;
        border: 1px solid #312e81;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #db2777;
        box-shadow: 0 8px 20px rgba(219, 39, 119, 0.2);
    }
    
    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #c084fc;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f1f5f9;
    }
    
    .metric-desc {
        font-size: 0.7rem;
        color: #94a3b8;
        margin-top: 0.25rem;
        font-style: italic;
    }
    
    .guide-card {
        background: rgba(30, 27, 75, 0.3);
        border-left: 3px solid #db2777;
        border-radius: 4px;
        padding: 1rem;
        margin-bottom: 1.5rem;
        font-size: 0.875rem;
        color: #cbd5e1;
    }
    
    .guide-title {
        font-weight: 700;
        color: #f472b6;
        margin-bottom: 0.3rem;
    }
    
    .section-divider {
        margin: 2.5rem 0;
        border-bottom: 1px solid #1e293b;
    }
</style>
""", unsafe_allow_html=True)

def parse_reference_queries(filepath):
    """
    Parses cohort_analysis.sql and extracts query blocks tagged with [QUERY_START] and [QUERY_END]
    """
    queries = {}
    if not os.path.exists(filepath):
        return queries
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        pattern = r'--\s*\[QUERY_START:\s*(\w+)\](.*?)--\s*\[QUERY_END:\s*\1\]'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for qname, sql in matches:
            queries[qname] = sql.strip()
    except Exception as err:
        print(f"Error parsing SQL file: {err}")
        
    return queries

# Initialize local session states
if "connected" not in st.session_state:
    st.session_state.connected = False
if "mysql_details" not in st.session_state:
    st.session_state.mysql_details = {
        "host": "localhost",
        "port": "3306",
        "user": "root",
        "password": "",
        "database": "ecommerce_analytics"
    }
if "conn_error" not in st.session_state:
    st.session_state.conn_error = None

# Load reference SQL queries dynamically
sql_queries = parse_reference_queries("cohort_analysis.sql")

# ==========================================
# LOGIN SCREEN
# ==========================================
if not st.session_state.connected:
    st.markdown("""
    <div class="login-container">
        <div class="login-title">✨ THREAD & TREND</div>
        <div class="login-subtitle">Fashion Cohort & Retail Analytics Studio</div>
    </div>
    """, unsafe_allow_html=True)
    
    _, form_col, _ = st.columns([1, 1.2, 1])
    with form_col:
        with st.form("connection_form"):
            st.markdown("### 🔑 Database Setup")
            host = st.text_input("Host", value=st.session_state.mysql_details["host"])
            port = st.text_input("Port", value=st.session_state.mysql_details["port"])
            user = st.text_input("User", value=st.session_state.mysql_details["user"])
            pwd = st.text_input("Password", type="password", value=st.session_state.mysql_details["password"])
            db = st.text_input("Database Name", value=st.session_state.mysql_details["database"])
            
            submit = st.form_submit_button("⚡ Unlock Studio Console", use_container_width=True)
            
            if submit:
                creds = {
                    "host": host,
                    "port": port,
                    "user": user,
                    "password": pwd,
                    "database": db
                }
                st.session_state.mysql_details = creds
                
                try:
                    conn = ca.get_connection(creds)
                    conn.close()
                    st.session_state.connected = True
                    st.session_state.conn_error = None
                    st.rerun()
                except Exception as err:
                    st.session_state.conn_error = str(err)
                    
        if st.session_state.conn_error:
            st.error("⚠️ Database connection failed.")
            st.caption(f"Details: {st.session_state.conn_error}")
            
        with st.expander("❓ Database Seeding Guide"):
            st.markdown("""
            **How to configure local MySQL Workbench:**
            1. Connect to your local server in **MySQL Workbench**.
            2. Open the file **`setup_mysql.sql`** in a query tab.
            3. Run the entire script (click the **Lightning Bolt ⚡** icon).
            4. Re-enter your credentials above to connect.
            """)

# ==========================================
# STORYBOARD EXECUTIVE VIEW
# ==========================================
else:
    try:
        df_customers, df_products, df_orders = ca.fetch_data_from_db(st.session_state.mysql_details)
    except Exception as err:
        st.session_state.connected = False
        st.session_state.conn_error = str(err)
        st.rerun()
        
    with st.sidebar:
        st.markdown("### ✨ Thread & Trend")
        st.caption("Retail Analytics Engine")
        st.success("🟢 Connected")
        st.markdown("---")
        
        segment_filter = st.selectbox(
            "Target Segment",
            options=["All", "Retail", "Corporate", "Direct"]
        )
        
        st.markdown("---")
        if st.button("🔒 Terminate Session", use_container_width=True):
            st.session_state.connected = False
            st.session_state.conn_error = None
            st.rerun()
            
    # Apply global segment filters
    if segment_filter != "All":
        df_customers = df_customers[df_customers["segment"] == segment_filter]
        df_orders = df_orders[df_orders["customer_id"].isin(df_customers["customer_id"])]
        
    # Main content header
    st.title("💼 Customer Lifecycle Analytics Storyboard")
    st.markdown("Guided diagnostics dashboard detailing shopper acquisition value and cohort retention.")
    
    # ------------------------------------------
    # STORY 1: SALES & METRICS
    # ------------------------------------------
    tot_sales = df_orders["order_value"].sum()
    tot_cust = df_customers["customer_id"].nunique()
    tot_ord = df_orders["order_id"].nunique()
    aov = tot_sales / tot_ord if tot_ord > 0 else 0
    basket_depth = df_orders["quantity"].mean()
    
    st.markdown(f"""
    <div class="metric-container">
        <div class="metric-card">
            <div class="metric-label">💰 Sales Revenue</div>
            <div class="metric-value">₹{tot_sales:,.2f}</div>
            <div class="metric-desc">Gross clothing sales in INR</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">👥 Acquired Shoppers</div>
            <div class="metric-value">{tot_cust:,}</div>
            <div class="metric-desc">Total signed up customers</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">📦 Total Orders</div>
            <div class="metric-value">{tot_ord:,}</div>
            <div class="metric-desc">Total transaction count</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">🛒 Average Order Value</div>
            <div class="metric-value">₹{aov:.2f}</div>
            <div class="metric-desc">Average cart value at checkout</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">🧥 Items Per Order</div>
            <div class="metric-value">{basket_depth:.2f}</div>
            <div class="metric-desc">Average basket size per checkout</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # ------------------------------------------
    # STORY 2: SEASONAL PATTERNS
    # ------------------------------------------
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.header("📅 Section 1: Sales Trends & Category Distribution")
    
    col1, col2 = st.columns(2)
    with col1:
        df_orders["order_month"] = df_orders["order_date"].dt.to_period("M").astype(str)
        monthly_sales = df_orders.groupby("order_month")["order_value"].sum().reset_index()
        
        fig_sales = px.bar(
            monthly_sales, 
            x="order_month", 
            y="order_value",
            labels={"order_month": "Month", "order_value": "Revenue (₹)"},
            template="plotly_dark",
            color_discrete_sequence=["#db2777"]
        )
        fig_sales.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False),
            yaxis=dict(gridcolor="#312e81")
        )
        st.plotly_chart(fig_sales, use_container_width=True)
        
    with col2:
        df_merged = pd.merge(df_orders, df_products, on="product_id", how="inner")
        cat_data = df_merged.groupby("category")["order_value"].sum().reset_index()
        
        fig_cat = px.pie(
            cat_data,
            names="category",
            values="order_value",
            template="plotly_dark",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        fig_cat.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_cat, use_container_width=True)
        
    # ------------------------------------------
    # STORY 3: RETENTION MATRIX
    # ------------------------------------------
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.header("📈 Section 2: Cohort Loyalty Heatmap")
    
    st.markdown("""
    <div class="guide-card">
        <div class="guide-title">💡 Reading the Heatmap:</div>
        <ul>
            <li>Every row traces a cohort (shoppers acquired in a specific month).</li>
            <li>Month 0 represents their sign-up purchase, while Month 1+ tracks return shopping percentages.</li>
            <li><b>Business Insight</b>: High retention rates (darker teal) reflect sustainable customer fit. Immediate drop-offs signify collection fit issues or post-purchase friction.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    counts, percentages = ca.calculate_cohort_retention(df_orders, df_customers)
    disp_mode = st.radio("Display Metric", options=["Percentage (%)", "User Count"], horizontal=True)
    
    if disp_mode == "Percentage (%)":
        z_data = percentages * 100
        hov_text = "Cohort: %{y}<br>Tenure Month: %{x}<br>Retention: %{z:.1f}%<extra></extra>"
        scale = "Tealgrn"
    else:
        z_data = counts
        hov_text = "Cohort: %{y}<br>Tenure Month: %{x}<br>Shoppers: %{z}<extra></extra>"
        scale = "Viridis"
        
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=z_data.values,
        x=z_data.columns,
        y=z_data.index,
        colorscale=scale,
        hovertemplate=hov_text,
        xgap=1,
        ygap=1
    ))
    fig_heatmap.update_layout(
        template="plotly_dark",
        xaxis=dict(title="Tenure Month Index", tickmode="linear"),
        yaxis=dict(title="Cohort Month", autorange="reversed"),
        height=450,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    # ------------------------------------------
    # STORY 4: LTV & INTERVAlS
    # ------------------------------------------
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.header("🔄 Section 3: Customer Value Accumulation vs Acquisition Cost")
    
    st.markdown("""
    <div class="guide-card">
        <div class="guide-title">💡 Reading the LTV Curves:</div>
        <ul>
            <li>Tracks average cumulative shopper spend per cohort across active months.</li>
            <li>The dashed red line represents **Target CAC (₹1,000)**.</li>
            <li><b>Profitability</b> is unlocked when the curve crosses the red line.</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    cohort_ltv = ca.calculate_cohort_ltv(df_orders, df_customers)
    
    fig_ltv = go.Figure()
    top_cohorts = cohort_ltv.index[-8:]
    for ch in top_cohorts:
        vals = cohort_ltv.loc[ch].dropna()
        fig_ltv.add_trace(go.Scatter(
            x=vals.index, y=vals.values,
            name=f"Cohort {ch}", mode="lines+markers"
        ))
        
    fig_ltv.add_trace(go.Scatter(
        x=cohort_ltv.columns, y=[1000.0] * len(cohort_ltv.columns),
        name="Target CAC (₹1,000)", mode="lines",
        line=dict(color="red", width=2, dash="dash")
    ))
    fig_ltv.update_layout(
        template="plotly_dark",
        xaxis=dict(title="Tenure Month Index", tickmode="linear"),
        yaxis=dict(title="Shopper Cumulative Value (₹)"),
        height=450,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )
    st.plotly_chart(fig_ltv, use_container_width=True)
    
    st.markdown("---")
    st.subheader("⏱️ Purchase Latency Intervals")
    
    df_ints = ca.calculate_purchase_intervals(df_orders)
    if len(df_ints) > 0:
        fig_hist = px.histogram(
            df_ints, x="days_between", nbins=50,
            labels={"days_between": "Days between Orders"},
            template="plotly_dark", color_discrete_sequence=["#10b981"]
        )
        fig_hist.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="Order Frequency")
        )
        st.plotly_chart(fig_hist, use_container_width=True)
        
        st.info(f"💡 On average, repeat shoppers checkout every **{df_ints['days_between'].mean():.1f} days**.")
        
    # ------------------------------------------
    # STORY 5: DEVELOPER CONSOLE
    # ------------------------------------------
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    
    with st.expander("🛠️ Advanced Developer Console (SQL Playground & Power BI Blueprint)"):
        st.subheader("💻 SQL Sandbox Console")
        st.markdown("Queries are loaded dynamically from `cohort_analysis.sql` using structural annotation markers.")
        
        # Map presets to parsed dictionary names
        preset_mapping = {
            "1. Cohort Retention Matrix (Active Shoppers)": "retention_matrix",
            "2. Cumulative LTV Curve by Cohort": "cohort_ltv",
            "3. Purchase Latency Interval (LAG function)": "repeat_intervals",
            "4. Customer Purchase Sequence Rank (DENSE_RANK)": "dense_rank_orders"
        }
        
        selected_preset = st.selectbox("Preset Query Templates", options=list(preset_mapping.keys()))
        db_key = preset_mapping[selected_preset]
        
        # Load parsed query text
        query_text = sql_queries.get(db_key, "-- Query template not found in file")
        
        editor_sql = st.text_area("SQL Terminal", value=query_text, height=200, key="db_sql_terminal")
        
        if st.button("▶ Execute SQL Script", type="primary", key="db_run_query"):
            with st.spinner("Executing query against local MySQL server..."):
                try:
                    conn = ca.get_connection(st.session_state.mysql_details)
                    res = pd.read_sql(editor_sql, conn)
                    conn.close()
                    st.success(f"Execution complete. Returned {len(res)} rows.")
                    st.dataframe(res, use_container_width=True)
                except Exception as err:
                    st.error(f"SQL Error: {err}")
                    
        st.markdown("---")
        st.subheader("🖥️ Power BI Star Schema Blueprint")
        st.markdown("""
        To establish the Power BI report data model, connect the files in the Model view:
        - `dim_customers.csv (customer_id)` ➡️ `1-to-many (*)` ➡️ `fact_orders.csv (customer_id)`
        - `dim_products.csv (product_id)` ➡️ `1-to-many (*)` ➡️ `fact_orders.csv (product_id)`
        """)
        
        col_c, col_p, col_o = st.columns(3)
        c_csv = df_customers.to_csv(index=False).encode('utf-8')
        p_csv = df_products.to_csv(index=False).encode('utf-8')
        o_csv = df_orders.to_csv(index=False).encode('utf-8')
        
        with col_c:
            st.download_button("📥 Download dim_customers.csv", data=c_csv, file_name="dim_customers.csv", mime="text/csv")
        with col_p:
            st.download_button("📥 Download dim_products.csv", data=p_csv, file_name="dim_products.csv", mime="text/csv")
        with col_o:
            st.download_button("📥 Download fact_orders.csv", data=o_csv, file_name="fact_orders.csv", mime="text/csv")
