
from pathlib import Path

import streamlit as st
import pandas as pd
import graphviz


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Firmable | Organization Intelligence",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

FILES = {
    "companies": DATA_DIR / "gold_companies.csv.gz",
    "employees": DATA_DIR / "gold_employee_hierarchy.csv.gz",
    "edges": DATA_DIR / "gold_org_chart_edges.csv.gz",
    "metrics": DATA_DIR / "gold_company_metrics.csv.gz",
}


# ============================================================
# CUSTOM STYLING
# ============================================================

st.markdown("""
<style>
    .stApp {
        background-color: #F6F8FC;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1500px;
    }

    h1, h2, h3 {
        color: #172B4D;
    }

    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #E5EAF2;
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(20, 40, 80, 0.04);
    }

    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E5EAF2;
    }

    div[data-testid="stTabs"] button {
        font-weight: 600;
    }

    .hero {
        background: linear-gradient(110deg, #102A56, #2457A6);
        padding: 28px 32px;
        border-radius: 16px;
        color: white;
        margin-bottom: 24px;
    }

    .hero h1 {
        color: white;
        margin-bottom: 5px;
    }

    .hero p {
        color: #DCE8FF;
        margin-bottom: 0;
    }

    .section-label {
        color: #64748B;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .info-card {
        background: white;
        border: 1px solid #E5EAF2;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data(show_spinner="Loading organization data...")
def load_data():
    data = {}

    for key, path in FILES.items():
        if not path.exists():
            raise FileNotFoundError(
                f"Missing file: {path.name}. "
                f"Expected location: {path}"
            )

        data[key] = pd.read_csv(path, compression="gzip")

    return data


try:
    data = load_data()
    companies = data["companies"]
    employees = data["employees"]
    edges = data["edges"]
    metrics = data["metrics"]

except Exception as exc:
    st.error("The Firmable application could not load its data.")
    st.exception(exc)
    st.info(
        "Check that all four Gold CSV files are committed "
        "inside the repository's data/ directory."
    )
    st.stop()


# ============================================================
# SCHEMA CHECKS
# ============================================================

required_columns = {
    "companies": [
        "company_id", "company_name", "industry",
        "org_structure", "employee_count", "assignment_coverage"
    ],
    "employees": [
        "company_id", "employee_id", "job_title_clean",
        "department", "manager_id", "root_employee_id",
        "hierarchy_depth", "is_root", "root_type"
    ],
    "edges": [
        "company_id", "manager_id", "employee_id",
        "candidate_score", "relationship_type"
    ]
}

for key, columns in required_columns.items():
    missing = [c for c in columns if c not in data[key].columns]

    if missing:
        st.error(f"Missing columns in {key}: {', '.join(missing)}")
        st.stop()


# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div class="hero">
    <h1>Firmable</h1>
    <p>Organization Intelligence &nbsp; | &nbsp;
    Rule-Based Employee Hierarchy Inference</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown("## Organization Explorer")
st.sidebar.caption("Explore inferred company structures")

company_options = (
    companies[["company_id", "company_name"]]
    .drop_duplicates()
    .sort_values("company_name")
)

company_ids = company_options["company_id"].tolist()

selected_company_id = st.sidebar.selectbox(
    "Select a company",
    company_ids,
    format_func=lambda x: company_options.loc[
        company_options["company_id"] == x,
        "company_name"
    ].iloc[0]
)

company = companies[
    companies["company_id"] == selected_company_id
].iloc[0]

company_employees = employees[
    employees["company_id"] == selected_company_id
].copy()

company_edges = edges[
    edges["company_id"] == selected_company_id
].copy()

company_metrics = metrics[
    metrics["company_id"] == selected_company_id
]

if not company_metrics.empty:
    company_metrics = company_metrics.iloc[0]


# ============================================================
# COMPANY OVERVIEW
# ============================================================

st.markdown(
    f"### {company['company_name']}"
)

st.caption(
    f"{company['industry']}  ·  "
    f"{company['org_structure']} structure"
)

total = len(company_employees)
assigned = int(company_employees["manager_id"].notna().sum())
unassigned = total - assigned

coverage = (
    assigned / total * 100
    if total else 0
)

depth = (
    pd.to_numeric(
        company_employees["hierarchy_depth"],
        errors="coerce"
    ).max()
)

depth = int(depth) if pd.notna(depth) else 0

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Total Employees", f"{total:,}")
k2.metric("Assigned Employees", f"{assigned:,}")
k3.metric("Unassigned Employees", f"{unassigned:,}")
k4.metric("Assignment Coverage", f"{coverage:.1f}%")
k5.metric("Hierarchy Depth", depth)

st.divider()


# ============================================================
# TABS
# ============================================================

overview_tab, chart_tab, explorer_tab, gaps_tab = st.tabs([
    "Overview",
    "Organization Chart",
    "Employee Explorer",
    "Hierarchy Gaps"
])


# ============================================================
# OVERVIEW
# ============================================================

with overview_tab:

    st.subheader("Company Overview")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Employees by Department**")

        department_counts = (
            company_employees["department"]
            .fillna("Unknown")
            .value_counts()
            .head(12)
        )

        if not department_counts.empty:
            st.bar_chart(department_counts)
        else:
            st.info("No department information available.")

    with col2:
        st.markdown("**Employees by Seniority**")

        if "inferred_seniority_level" in company_employees.columns:
            seniority = pd.to_numeric(
                company_employees["inferred_seniority_level"],
                errors="coerce"
            )

            seniority_counts = (
                seniority.value_counts()
                .sort_index()
            )

            st.bar_chart(seniority_counts)
        else:
            st.info("Seniority information is unavailable.")

    st.divider()

    st.subheader("Company Information")

    info1, info2, info3 = st.columns(3)

    info1.metric(
        "Industry",
        str(company.get("industry", "N/A"))
    )

    info2.metric(
        "Organization Type",
        str(company.get("org_structure", "N/A"))
    )

    info3.metric(
        "Company Size",
        str(company.get("company_size_category", "N/A"))
    )

    st.markdown("**Inference methodology**")
    st.write(
        "Manager relationships are inferred through deterministic "
        "rules using normalized job titles, seniority, organizational "
        "alignment, management authority, candidate scoring, and "
        "manager capacity constraints."
    )

    st.caption(
        "Candidate scores are rule-based ranking scores, "
        "not calibrated probabilities."
    )


# ============================================================
# ORGANIZATION CHART
# ============================================================

with chart_tab:

    st.subheader("Organization Structure")

    roots = (
        company_employees["root_employee_id"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if not roots:
        st.warning("No organization hierarchy is available.")
    else:

        root_id = st.selectbox(
            "Select hierarchy root",
            sorted(roots)
        )

        depth_limit = st.slider(
            "Maximum hierarchy depth",
            min_value=1,
            max_value=10,
            value=5
        )

        max_nodes = st.select_slider(
            "Maximum nodes to display",
            options=[25, 50, 100, 150, 200],
            value=100
        )

        chart_data = company_employees[
            company_employees["root_employee_id"].astype(str)
            == root_id
        ].copy()

        chart_data["hierarchy_depth"] = pd.to_numeric(
            chart_data["hierarchy_depth"],
            errors="coerce"
        )

        chart_data = chart_data[
            chart_data["hierarchy_depth"] <= depth_limit
        ].sort_values("hierarchy_depth")

        truncated = len(chart_data) > max_nodes
        chart_data = chart_data.head(max_nodes)

        visible_ids = set(
            chart_data["employee_id"].astype(str)
        )

        dot = graphviz.Digraph()
        dot.attr(
            rankdir="TB",
            bgcolor="white",
            nodesep="0.35",
            ranksep="0.65",
            pad="0.3"
        )

        dot.attr(
            "node",
            shape="box",
            style="rounded,filled",
            fillcolor="#EAF2FF",
            color="#B5C9EA",
            fontname="Arial",
            fontsize="10",
            margin="0.15,0.10"
        )

        dot.attr(
            "edge",
            color="#9AAAC0",
            arrowsize="0.7"
        )

        for _, emp in chart_data.iterrows():

            emp_id = str(emp["employee_id"])
            title = str(emp.get("job_title_clean", "Unknown"))
            department = str(emp.get("department", "Unknown"))

            label = (
                f"{title}\\n"
                f"ID: {emp_id}\\n"
                f"{department}"
            )

            dot.node(emp_id, label=label)

        for _, emp in chart_data.iterrows():

            manager_id = emp.get("manager_id")
            employee_id = str(emp["employee_id"])

            if pd.notna(manager_id):
                manager_id = str(manager_id)

                if manager_id in visible_ids:
                    dot.edge(manager_id, employee_id)

        st.graphviz_chart(dot, use_container_width=True)

        if truncated:
            st.warning(
                f"Showing the first {max_nodes} employees. "
                "Increase the node limit to see more."
            )

        st.caption(
            f"Displaying {len(chart_data)} employees "
            f"within the selected hierarchy."
        )


# ============================================================
# EMPLOYEE EXPLORER
# ============================================================

with explorer_tab:

    st.subheader("Employee Explorer")

    search = st.text_input(
        "Search by employee ID, job title, or department"
    )

    filtered = company_employees.copy()

    if search.strip():

        search_lower = search.lower()

        searchable_columns = [
            c for c in [
                "employee_id",
                "job_title_clean",
                "department",
                "business_unit",
                "team_name"
            ]
            if c in filtered.columns
        ]

        mask = pd.Series(False, index=filtered.index)

        for column in searchable_columns:
            mask |= (
                filtered[column]
                .fillna("")
                .astype(str)
                .str.lower()
                .str.contains(search_lower, regex=False)
            )

        filtered = filtered[mask]

    st.caption(f"{len(filtered):,} matching employees")

    display_columns = [
        c for c in [
            "employee_id",
            "job_title_clean",
            "department",
            "business_unit",
            "team_name",
            "inferred_seniority_level",
            "manager_id",
            "candidate_score",
            "relationship_type",
            "assignment_status"
        ]
        if c in filtered.columns
    ]

    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True
    )

    if not filtered.empty:

        selected_employee = st.selectbox(
            "View employee details",
            filtered["employee_id"].astype(str).tolist()
        )

        employee = filtered[
            filtered["employee_id"].astype(str)
            == selected_employee
        ].iloc[0]

        st.markdown("#### Employee Details")

        d1, d2, d3 = st.columns(3)

        d1.metric(
            "Employee ID",
            str(employee["employee_id"])
        )

        d2.metric(
            "Manager ID",
            str(employee.get("manager_id", "N/A"))
            if pd.notna(employee.get("manager_id"))
            else "Unassigned"
        )

        d3.metric(
            "Hierarchy Depth",
            str(employee.get("hierarchy_depth", "N/A"))
        )

        if pd.notna(employee.get("candidate_score")):
            st.metric(
                "Rule-Based Candidate Score",
                f"{float(employee['candidate_score']):.1f}/100"
            )


# ============================================================
# HIERARCHY GAPS
# ============================================================

with gaps_tab:

    st.subheader("Hierarchy Gaps & Unassigned Employees")

    unassigned_df = company_employees[
        company_employees["manager_id"].isna()
    ].copy()

    st.metric(
        "Employees Without an Assigned Manager",
        f"{len(unassigned_df):,}"
    )

    if "root_type" in unassigned_df.columns:

        st.markdown("**Root classification**")

        root_counts = (
            unassigned_df["root_type"]
            .fillna("Unknown")
            .value_counts()
        )

        st.bar_chart(root_counts)

    st.markdown("**Unassigned employee details**")

    gap_columns = [
        c for c in [
            "employee_id",
            "job_title_clean",
            "department",
            "business_unit",
            "team_name",
            "inferred_seniority_level",
            "root_type",
            "assignment_status"
        ]
        if c in unassigned_df.columns
    ]

    st.dataframe(
        unassigned_df[gap_columns],
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown("""
<div style="text-align:center; color:#8492A6; padding:10px;">
    Firmable Organization Intelligence Platform<br>
    <small>Rule-Based Hierarchy Inference · Medallion Architecture</small>
</div>
""", unsafe_allow_html=True)
