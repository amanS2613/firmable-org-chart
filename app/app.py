from pathlib import Path
from collections import defaultdict

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
    initial_sidebar_state="expanded",
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

st.markdown(
    """
    <style>
        .stApp {
            background-color: #F6F8FC;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1700px;
        }

        h1, h2, h3 {
            color: #172B4D;
        }

        [data-testid="stMetric"] {
            background: white;
            border: 1px solid #E5EAF2;
            padding: 16px;
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

        .chart-note {
            color: #64748B;
            font-size: 0.85rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# DATA LOADING
# ============================================================

@st.cache_data(show_spinner="Loading organization data...")
def load_data():
    loaded = {}

    for key, path in FILES.items():
        if not path.exists():
            raise FileNotFoundError(
                f"Missing file: {path.name}. "
                f"Expected location: {path}"
            )

        loaded[key] = pd.read_csv(path, compression="gzip")

    return loaded


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
        "company_id",
        "company_name",
        "industry",
        "org_structure",
        "employee_count",
        "assignment_coverage",
    ],
    "employees": [
        "company_id",
        "employee_id",
        "job_title_clean",
        "department",
        "manager_id",
        "root_employee_id",
        "hierarchy_depth",
        "is_root",
        "root_type",
    ],
    "edges": [
        "company_id",
        "manager_id",
        "employee_id",
        "candidate_score",
        "relationship_type",
    ],
    "metrics": ["company_id"],
}

for key, columns in required_columns.items():
    missing = [column for column in columns if column not in data[key].columns]

    if missing:
        st.error(f"Missing columns in {key}: {', '.join(missing)}")
        st.stop()


# Normalize identifiers and nullable text columns once after loading.
employees = employees.copy()
for column in ["company_id", "employee_id", "manager_id", "root_employee_id"]:
    employees[column] = employees[column].astype("string").str.strip()

employees["department"] = employees["department"].fillna("Unknown").astype(str)
employees["job_title_clean"] = (
    employees["job_title_clean"].fillna("Unknown title").astype(str)
)


# ============================================================
# HELPERS
# ============================================================

def safe_text(value, fallback="Unknown"):
    """Return a display-safe string for null/blank values."""
    if pd.isna(value):
        return fallback
    value = str(value).strip()
    return value if value else fallback


def get_department_view(company_df, selected_department):
    """
    For a department view, include:
      1. Every employee in the selected department.
      2. Every manager ancestor required to connect those employees
         back to their root(s).

    The source hierarchy remains unchanged; this is only a display filter.
    """
    company_df = company_df.copy()

    if selected_department == "All Departments":
        return company_df

    employee_ids = set(company_df["employee_id"].dropna().astype(str))
    manager_by_employee = (
        company_df.set_index("employee_id")["manager_id"].to_dict()
    )

    department_rows = company_df[
        company_df["department"].fillna("Unknown").astype(str)
        == selected_department
    ]

    visible_ids = set(department_rows["employee_id"].dropna().astype(str))

    # Retain every ancestor so the selected department remains connected
    # to the CEO/root wherever that chain exists in the inferred hierarchy.
    for employee_id in list(visible_ids):
        current_id = employee_id
        visited = set()

        while current_id in manager_by_employee:
            if current_id in visited:
                break
            visited.add(current_id)

            manager_id = manager_by_employee.get(current_id)
            if pd.isna(manager_id):
                break

            manager_id = str(manager_id)
            if manager_id not in employee_ids:
                break

            visible_ids.add(manager_id)
            current_id = manager_id

    return company_df[
        company_df["employee_id"].astype(str).isin(visible_ids)
    ].copy()


def build_org_chart(chart_df, show_department=True):
    """Build one top-to-bottom chart containing every employee in the view."""
    if chart_df.empty:
        return None

    chart_df = chart_df.copy()
    chart_df["employee_id"] = chart_df["employee_id"].astype(str).str.strip()
    chart_df["manager_id"] = chart_df["manager_id"].astype("string").str.strip()

    visible_ids = set(chart_df["employee_id"])
    dot = graphviz.Digraph("FirmableFullCompanyChart", format="svg")
    dot.attr(
        rankdir="TB",
        bgcolor="white",
        splines="ortho",
        nodesep="0.10",
        ranksep="0.28",
        pad="0.18",
        margin="0",
        outputorder="edgesfirst",
        ordering="out",
        newrank="true",
    )
    dot.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="Arial",
        fontsize="9",
        margin="0.10,0.07",
        penwidth="1.1",
        fontcolor="#172B4D",
    )
    dot.attr("edge", color="#94A3B8", arrowsize="0.55", penwidth="0.9")

    seniority = pd.to_numeric(
        chart_df.get("inferred_seniority_level", pd.Series(index=chart_df.index)),
        errors="coerce",
    )

    for index, emp in chart_df.iterrows():
        employee_id = str(emp["employee_id"])
        title = safe_text(emp.get("job_title_clean"), "Unknown title")
        department = safe_text(emp.get("department"), "Unknown")
        root_type = safe_text(emp.get("root_type"), "")
        is_root = str(emp.get("is_root", False)).lower() in ("true", "1", "1.0")
        level = seniority.loc[index] if index in seniority.index else None

        # Visual categories only; these do not change inference or reporting lines.
        if root_type == "CEO_ROOT" or "chief executive" in title.lower() or title.lower() == "ceo":
            icon, rank_label = "👑", "CEO"
            fill, border = "#DCEAFE", "#2563EB"
        elif pd.notna(level) and level <= 4:
            icon, rank_label = "🏛️", "EXECUTIVE"
            fill, border = "#EDE9FE", "#7C3AED"
        elif pd.notna(level) and level <= 7:
            icon, rank_label = "💼", "SENIOR LEADER"
            fill, border = "#DBEAFE", "#3B82F6"
        elif pd.notna(level) and level <= 9:
            icon, rank_label = "🧑‍💼", "MANAGER"
            fill, border = "#CCFBF1", "#0F766E"
        elif pd.notna(level) and level <= 10:
            icon, rank_label = "👥", "TEAM LEAD"
            fill, border = "#FEF3C7", "#D97706"
        else:
            icon, rank_label = "👤", "INDIVIDUAL CONTRIBUTOR"
            fill, border = "#F0FDF4", "#16A34A"

        if is_root and root_type != "CEO_ROOT":
            icon, rank_label = "⚪", "UNASSIGNED ROOT"
            fill, border = "#FFF7ED", "#EA580C"

        label_lines = [f"{icon}  {rank_label}", title, employee_id]
        if show_department:
            label_lines.append(department)
        label = "\\n".join(label_lines)

        dot.node(
            employee_id,
            label=label,
            fillcolor=fill,
            color=border,
            penwidth="1.6" if is_root else "1.0",
        )

    for _, emp in chart_df.iterrows():
        employee_id = str(emp["employee_id"])
        manager_id = emp.get("manager_id")
        if pd.notna(manager_id):
            manager_id = str(manager_id).strip()
            if manager_id in visible_ids and manager_id != employee_id:
                dot.edge(manager_id, employee_id)

    return dot


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="hero">
        <h1>Firmable</h1>
        <p>Organization Intelligence &nbsp; | &nbsp;
        Rule-Based Employee Hierarchy Inference</p>
    </div>
    """,
    unsafe_allow_html=True,
)


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

company_ids = company_options["company_id"].astype(str).tolist()

selected_company_id = st.sidebar.selectbox(
    "Select a company",
    company_ids,
    format_func=lambda company_id: company_options.loc[
        company_options["company_id"].astype(str) == company_id,
        "company_name",
    ].iloc[0],
)

company = companies[
    companies["company_id"].astype(str) == selected_company_id
].iloc[0]

company_employees = employees[
    employees["company_id"].astype(str) == selected_company_id
].copy()

company_edges = edges[
    edges["company_id"].astype(str) == selected_company_id
].copy()

company_metrics = metrics[
    metrics["company_id"].astype(str) == selected_company_id
]

if not company_metrics.empty:
    company_metrics = company_metrics.iloc[0]


# ============================================================
# COMPANY OVERVIEW
# ============================================================

st.markdown(f"### {company['company_name']}")

st.caption(
    f"{company['industry']}  ·  "
    f"{company['org_structure']} structure"
)

total = len(company_employees)
assigned = int(company_employees["manager_id"].notna().sum())
unassigned = total - assigned

coverage = assigned / total * 100 if total else 0

depth = pd.to_numeric(
    company_employees["hierarchy_depth"], errors="coerce"
).max()
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

overview_tab, chart_tab, explorer_tab, gaps_tab = st.tabs(
    [
        "Overview",
        "Organization Chart",
        "Employee Explorer",
        "Hierarchy Gaps",
    ]
)


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
                errors="coerce",
            )
            seniority_counts = seniority.value_counts().sort_index()

            if not seniority_counts.empty:
                st.bar_chart(seniority_counts)
            else:
                st.info("Seniority information is unavailable.")
        else:
            st.info("Seniority information is unavailable.")

    st.divider()
    st.subheader("Company Information")

    info1, info2, info3 = st.columns(3)
    info1.metric("Industry", str(company.get("industry", "N/A")))
    info2.metric("Organization Type", str(company.get("org_structure", "N/A")))
    info3.metric(
        "Company Size",
        str(company.get("company_size_category", "N/A")),
    )

    st.markdown("**Inference methodology**")
    st.write(
        "Manager relationships are inferred through deterministic rules "
        "using normalized job titles, seniority, organizational alignment, "
        "management authority, candidate scoring, and manager capacity "
        "constraints."
    )
    st.caption(
        "Candidate scores are rule-based ranking scores, "
        "not calibrated probabilities."
    )


# ============================================================
# ORGANIZATION CHART
# ============================================================

with chart_tab:
    st.subheader("Full Company Organization Chart")
    st.write(
        "The complete company is displayed in one top-to-bottom view, "
        "from the CEO and senior leadership through managers, team leads "
        "and individual contributors. Disconnected roots remain separate "
        "branches because no unsupported reporting links are invented."
    )

    departments = sorted(
        company_employees["department"].fillna("Unknown").astype(str).unique().tolist()
    )
    selected_department = st.selectbox(
        "Department filter",
        ["All Departments"] + departments,
        index=0,
        help=(
            "All Departments shows every employee in one company-wide chart. "
            "A department selection retains that department's manager ancestors."
        ),
        key=f"department_filter_{selected_company_id}",
    )

    chart_data = get_department_view(company_employees, selected_department).copy()
    chart_data["employee_id"] = chart_data["employee_id"].astype("string").str.strip()
    chart_data["manager_id"] = chart_data["manager_id"].astype("string").str.strip()

    total_without_manager = int(chart_data["manager_id"].isna().sum())
    component_count = (
        chart_data["root_employee_id"].nunique(dropna=True)
        if "root_employee_id" in chart_data.columns
        else total_without_manager
    )
    max_depth = pd.to_numeric(chart_data["hierarchy_depth"], errors="coerce").max()
    max_depth = int(max_depth) if pd.notna(max_depth) else 0

    m1, m2, m3 = st.columns(3)
    m1.metric("Employees in chart", f"{len(chart_data):,}")
    m2.metric("Reporting components", f"{component_count:,}")
    m3.metric("Maximum hierarchy level", max_depth)

    st.markdown(
        """
        <div class="chart-note">
            👑 CEO &nbsp; · &nbsp; 🏛️ Executive &nbsp; · &nbsp;
            💼 Senior leader &nbsp; · &nbsp; 🧑‍💼 Manager &nbsp; · &nbsp;
            👥 Team lead &nbsp; · &nbsp; 👤 Individual contributor
            &nbsp; · &nbsp; ⚪ Unassigned root
        </div>
        """,
        unsafe_allow_html=True,
    )

    if chart_data.empty:
        st.warning("No employees are available for this chart selection.")
    else:
        st.caption(
            "All employees in this view are included in the same chart. "
            "Use the chart's zoom controls (if available) or browser zoom to "
            "inspect dense areas. Scroll vertically to inspect lower levels."
        )
        chart = build_org_chart(
            chart_data,
            show_department=(selected_department == "All Departments"),
        )
        if chart is not None:
            # A fixed-height viewport allows tall charts to be inspected without
            # shrinking the complete hierarchy to fit a single screen.
            st.graphviz_chart(
                chart,
                width="content",
                height=1000,
                alt="Complete company organization chart from senior leaders to individual contributors",
            )

        with st.expander("View all employees included in this chart"):
            chart_columns = [
                column
                for column in [
                    "employee_id",
                    "job_title_clean",
                    "department",
                    "manager_id",
                    "inferred_seniority_level",
                    "hierarchy_depth",
                    "root_employee_id",
                    "root_type",
                    "assignment_status",
                ]
                if column in chart_data.columns
            ]
            st.dataframe(
                chart_data[chart_columns].sort_values(
                    ["hierarchy_depth", "department", "job_title_clean"],
                    na_position="last",
                ),
                use_container_width=True,
                hide_index=True,
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
            column
            for column in [
                "employee_id",
                "job_title_clean",
                "department",
                "business_unit",
                "team_name",
            ]
            if column in filtered.columns
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
        column
        for column in [
            "employee_id",
            "job_title_clean",
            "department",
            "business_unit",
            "team_name",
            "inferred_seniority_level",
            "manager_id",
            "candidate_score",
            "relationship_type",
            "assignment_status",
        ]
        if column in filtered.columns
    ]

    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True,
    )

    if not filtered.empty:
        selected_employee = st.selectbox(
            "View employee details",
            filtered["employee_id"].astype(str).tolist(),
        )

        employee = filtered[
            filtered["employee_id"].astype(str) == selected_employee
        ].iloc[0]

        st.markdown("#### Employee Details")

        d1, d2, d3 = st.columns(3)
        d1.metric("Employee ID", str(employee["employee_id"]))

        manager_value = employee.get("manager_id")
        d2.metric(
            "Manager ID",
            str(manager_value) if pd.notna(manager_value) else "Unassigned",
        )

        d3.metric(
            "Hierarchy Depth",
            str(employee.get("hierarchy_depth", "N/A")),
        )

        if pd.notna(employee.get("candidate_score")):
            st.metric(
                "Rule-Based Candidate Score",
                f"{float(employee['candidate_score']):.1f}/100",
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
        f"{len(unassigned_df):,}",
    )

    if "root_type" in unassigned_df.columns:
        st.markdown("**Root classification**")
        root_counts = (
            unassigned_df["root_type"]
            .fillna("Unknown")
            .value_counts()
        )

        if not root_counts.empty:
            st.bar_chart(root_counts)

    st.markdown("**Unassigned employee details**")

    gap_columns = [
        column
        for column in [
            "employee_id",
            "job_title_clean",
            "department",
            "business_unit",
            "team_name",
            "inferred_seniority_level",
            "root_type",
            "assignment_status",
        ]
        if column in unassigned_df.columns
    ]

    st.dataframe(
        unassigned_df[gap_columns],
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center; color:#8492A6; padding:10px;">
        Firmable Organization Intelligence Platform<br>
        <small>Rule-Based Hierarchy Inference · Medallion Architecture</small>
    </div>
    """,
    unsafe_allow_html=True,
)
