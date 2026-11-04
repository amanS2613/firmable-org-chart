from pathlib import Path

code = r'''from pathlib import Path
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
    """
    Build a complete Graphviz reporting hierarchy for the supplied rows.
    No node cap or default depth truncation is applied.
    """
    if chart_df.empty:
        return None

    chart_df = chart_df.copy()
    chart_df["employee_id"] = chart_df["employee_id"].astype(str)
    chart_df["manager_id"] = chart_df["manager_id"].astype("string")

    visible_ids = set(chart_df["employee_id"])
    dot = graphviz.Digraph("FirmableOrganizationChart", format="svg")

    dot.attr(
        rankdir="TB",
        bgcolor="white",
        splines="polyline",
        nodesep="0.16",
        ranksep="0.32",
        pad="0.25",
        outputorder="edgesfirst",
        ordering="out",
        concentrate="false",
    )

    dot.attr(
        "node",
        shape="box",
        style="rounded,filled",
        fontname="Arial",
        fontsize="8",
        margin="0.08,0.05",
        penwidth="0.9",
        color="#CBD5E1",
        fontcolor="#1E293B",
    )

    dot.attr(
        "edge",
        color="#9AAAC0",
        arrowsize="0.55",
        penwidth="0.8",
    )

    # Seniority is used only for visual grouping/coloring, not inference.
    if "inferred_seniority_level" in chart_df.columns:
        seniority_values = pd.to_numeric(
            chart_df["inferred_seniority_level"], errors="coerce"
        )
    else:
        seniority_values = pd.Series(index=chart_df.index, dtype="float64")

    for index, emp in chart_df.iterrows():
        employee_id = str(emp["employee_id"])
        title = safe_text(emp.get("job_title_clean"), "Unknown title")
        department = safe_text(emp.get("department"), "Unknown")
        root_type = safe_text(emp.get("root_type"), "")
        is_root = str(emp.get("is_root", False)).lower() in ("true", "1", "1.0")

        label_lines = [title, employee_id]
        if show_department:
            label_lines.append(department)

        label = "\\n".join(label_lines)

        if is_root and root_type == "CEO_ROOT":
            fill_color = "#DCEAFE"
            border_color = "#3973C6"
            pen_width = "1.5"
        elif is_root:
            fill_color = "#FFF3D6"
            border_color = "#D69E36"
            pen_width = "1.2"
        else:
            level = seniority_values.loc[index] if index in seniority_values.index else None
            if pd.notna(level) and level <= 7:
                fill_color = "#E8EEFF"
            elif pd.notna(level) and level <= 10:
                fill_color = "#EEF4FF"
            else:
                fill_color = "#F0FDF4"
            border_color = "#CBD5E1"
            pen_width = "0.8"

        dot.node(
            employee_id,
            label=label,
            fillcolor=fill_color,
            color=border_color,
            penwidth=pen_width,
        )

    # Add only edges whose manager and employee are both in this view.
    for _, emp in chart_df.iterrows():
        employee_id = str(emp["employee_id"])
        manager_id = emp.get("manager_id")

        if pd.notna(manager_id):
            manager_id = str(manager_id)
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
    st.subheader("Complete Organization Structure")

    st.write(
        "Explore the full inferred reporting hierarchy, from the company "
        "root(s) through managers and team leads to individual contributors."
    )

    departments = sorted(
        company_employees["department"]
        .fillna("Unknown")
        .astype(str)
        .unique()
        .tolist()
    )

    department_options = ["All Departments"] + departments

    selected_department = st.selectbox(
        "View organization by department",
        department_options,
        index=0,
        help=(
            "A department view includes its employees and the manager "
            "ancestors needed to retain the reporting path to the root."
        ),
        key=f"department_filter_{selected_company_id}",
    )

    chart_data = get_department_view(
        company_employees,
        selected_department,
    )

    if chart_data.empty:
        st.warning("No employees are available for this chart selection.")
    else:
        # All rows in the selected view are rendered. There is no arbitrary
        # node limit or default depth truncation.
        root_count = int(
            chart_data["manager_id"].isna().sum()
        )
        component_count = (
            chart_data["root_employee_id"].nunique(dropna=True)
            if "root_employee_id" in chart_data.columns
            else root_count
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Employees in chart", f"{len(chart_data):,}")
        c2.metric("Root components shown", f"{component_count:,}")
        c3.metric("Employees without manager", f"{root_count:,}")

        st.markdown(
            """
            <div class="chart-note">
                Blue = CEO root &nbsp; · &nbsp;
                Amber = other/disconnected root &nbsp; · &nbsp;
                Light blue = senior leadership &nbsp; · &nbsp;
                Green = team members / individual contributors
            </div>
            """,
            unsafe_allow_html=True,
        )

        chart = build_org_chart(
            chart_data,
            show_department=(selected_department == "All Departments"),
        )

        if chart is not None:
            st.graphviz_chart(chart, use_container_width=True)

        if selected_department == "All Departments":
            st.caption(
                "The complete company view includes all connected and "
                "disconnected components. Disconnected roots are displayed "
                "as separate trees rather than being hidden."
            )
        else:
            st.caption(
                f"Department view: {selected_department}. "
                "Managers outside this department are retained when needed "
                "to show the reporting path to the company's root."
            )

        with st.expander("View employees included in this chart"):
            chart_columns = [
                column
                for column in [
                    "employee_id",
                    "job_title_clean",
                    "department",
                    "manager_id",
                    "inferred_seniority_level",
                    "hierarchy_depth",
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
'''


