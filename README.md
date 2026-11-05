# Firmable — Organization Intelligence & Employee Hierarchy Inference

**A rule-based employee organization hierarchy inference platform built using Databricks, PySpark, Spark SQL, Delta Lake, and Streamlit.**

[Live Application](https://firmable-org-chart-aman2613.streamlit.app/) | [GitHub Repository](https://github.com/amanS2613/firmable-org-chart)

---

## 1. Project Overview

### Problem Statement

Organizations often maintain employee datasets containing job titles, departments, business units, teams, and other attributes, but explicit reporting relationships may be missing or incomplete.

Firmable addresses this problem by inferring employee-manager relationships from organizational attributes using deterministic, explainable rules.

The platform identifies potential managers, evaluates candidate relationships, assigns managers subject to organizational constraints, and constructs employee reporting hierarchies.

### Objectives

- Infer employee-manager relationships from employee attributes.
- Support different organizational structures.
- Generate explainable manager candidate scores.
- Handle ambiguous or incomplete employee information.
- Enforce manager reporting capacity constraints.
- Abstain when a reliable manager cannot be identified.
- Visualize inferred organization structures through an interactive application.
- Evaluate inferred relationships against isolated ground-truth data.

### Project Scale

| Attribute | Details |
|---|---|
| Companies | 500 |
| Employees | 89,576 |
| Employees per company | 100–250 |
| Organization structures | Functional, Flat, Divisional, Hybrid |
| Processing platform | Databricks |
| Data processing | PySpark, Spark SQL |
| Storage format | Delta tables |
| Application | Streamlit |
| Inference approach | Deterministic rule-based system |
| Machine learning | Not used |

---

## 2. Technology Stack

| Technology | Purpose |
|---|---|
| Databricks | Data engineering and pipeline execution |
| PySpark | Distributed data processing |
| Spark SQL | Data transformation and validation |
| Delta Lake | Structured data storage |
| Python | Rule-based inference and automation |
| Pandas | Application-side data handling |
| Graphviz | Organization chart visualization |
| Streamlit | Interactive application |
| GitHub | Version control and source management |
| Streamlit Community Cloud | Application deployment |

---

## 3. System Architecture

Firmable follows the Medallion Architecture, separating raw ingestion, standardized data processing, and application-ready outputs.

### End-to-End Data Flow

Synthetic Employee Data → Bronze → Silver → Gold → Streamlit Application

Ground truth follows a separate evaluation-only path and is never used to generate or score manager relationships.

### Medallion Architecture

#### Bronze Layer — Raw Data

The Bronze layer stores the generated employee data in its original ingestion-oriented form.

**Responsibilities:**

- Store raw employee records.
- Preserve original employee attributes.
- Retain ingestion variations and data-quality issues.
- Maintain isolated ground-truth relationships for evaluation.

**Example data characteristics:**

- Missing job titles and departments.
- Inconsistent capitalization and whitespace.
- Job-title aliases and variations.
- Inconsistent organizational attributes.

Ground-truth manager relationships are stored separately from inference inputs and are excluded from all inference and scoring operations.

#### Silver Layer — Cleansed and Inferred Data

The Silver layer performs data standardization, feature derivation, candidate generation, scoring, manager assignment, and hierarchy construction.

**Main transformations:**

1. Clean employee attributes and normalize job titles.
2. Standardize departments, business units, and teams.
3. Derive employee seniority levels.
4. Identify management authority from normalized job-title attributes.
5. Generate potential manager candidates.
6. Score candidate reporting relationships.
7. Assign managers subject to score, ambiguity, seniority, and capacity constraints.
8. Reconcile disconnected hierarchy components where additional defensible relationships exist.
9. Validate the final hierarchy.

**Important derived attributes:**

- `inferred_seniority_level`
- `management_authority`
- `title_function`
- Department and team alignment attributes
- Candidate relationship type
- Candidate score
- Assignment status

Lower seniority values represent more senior positions.

Unknown job titles remain unclassified rather than being assigned an unsupported seniority level.

#### Gold Layer — Analytics and Application Outputs

The Gold layer contains curated tables designed for reporting, evaluation summaries, and application consumption.

| Gold Table | Purpose |
|---|---|
| `gold_companies` | Company-level information |
| `gold_employee_hierarchy` | Employee attributes and inferred reporting hierarchy |
| `gold_org_chart_edges` | Manager-employee relationships |
| `gold_company_metrics` | Company-level hierarchy metrics |

The Streamlit application consumes exported Gold CSV files.

---

## 4. Rule-Based Manager Inference Methodology

Firmable uses deterministic rules rather than machine learning.

The inference process is designed around organizational structure, employee seniority, title function, management authority, and organizational alignment.

### Step 1 — Employee Standardization

Raw employee attributes are cleaned and normalized.

Examples include:

- Removing unnecessary whitespace.
- Normalizing capitalization.
- Standardizing job-title variations.
- Cleaning department and business-unit values.
- Handling missing or unknown titles.

The objective is to create consistent employee attributes before generating reporting candidates.

### Step 2 — Seniority and Management Attributes

Each employee is assigned an inferred seniority level based on normalized job-title information.

Lower values indicate higher seniority.

Management authority is derived from title-related attributes and is used as supporting evidence during candidate scoring.

It is not treated as an independent guarantee that an employee manages people.

### Step 3 — Manager Candidate Generation

Potential manager relationships are generated using organizational hierarchy patterns.

Examples include:

| Employee Role | Potential Manager Role |
|---|---|
| Individual Contributor | Team Lead |
| Individual Contributor | Team Manager |
| Individual Contributor | Department Head |
| Team Lead | Team Manager |
| Team Lead | Department Head |
| Team Manager | Department Head |
| Department Head | Functional Executive |
| Department Head | Division President |
| Department Head | CEO |
| C-suite Executive | CEO |
| Division President | CEO |

Candidate generation supports primary and fallback relationships.

For example, a Team Lead may be considered under a Team Manager as a primary candidate, with a Department Head as a fallback where the organizational structure permits it.

Candidate generation does not automatically assign the next most senior employee as manager.

### Step 4 — Candidate Scoring

Each employee-manager candidate pair receives a deterministic ranking score.

The score considers:

1. Structural relationship fit.
2. Team alignment.
3. Department alignment.
4. Business-unit alignment.
5. Management authority.
6. Seniority gap.

The candidate with the strongest eligible evidence is preferred, subject to ambiguity and capacity constraints.

### Step 5 — Manager Assignment

Candidate assignments are processed using multiple rounds.

A relationship is accepted only when it satisfies the configured assignment rules.

The system checks:

- Minimum candidate score.
- Candidate ambiguity.
- Valid employee-manager references.
- Seniority ordering.
- Manager reporting capacity.
- Duplicate and self-reporting constraints.

If no defensible candidate is available, the employee remains unassigned.

### Step 6 — Hierarchy Reconciliation

After the initial assignment process, disconnected components are evaluated for possible additional reporting relationships.

Reconciliation considers:

- Candidate score.
- Ambiguity.
- Seniority ordering.
- Existing manager capacity.
- Whether the candidate would connect two different components.

The reconciliation process allows one additional direct-report slot per manager beyond the original assignment capacity, exclusively for reconciliation.

Only existing eligible candidates are considered. Reconciliation does not create arbitrary reporting relationships.

### Step 7 — Hierarchy Construction and Validation

The final manager assignments are converted into hierarchy edges and employee hierarchy records.

Validation checks include:

- Duplicate hierarchy records.
- Duplicate manager assignments.
- Invalid manager references.
- Self-reporting relationships.
- Invalid seniority relationships.
- Manager capacity violations.
- Unreachable employees.

Disconnected components are preserved rather than artificially connected.

---

## 5. Candidate Scoring, Thresholds and Capacity Constraints

### Candidate Score Components

The implemented scoring system uses additive rule-based weights.

| Scoring Component | Implemented Score |
|---|---:|
| Direct structural relationship | 45 |
| Functional Executive → Department Head | 49 |
| Team Manager → Individual Contributor | 24 |
| Department Head → Team Lead fallback | 22 |
| CEO → Department Head fallback | 18 |
| Department Head → Individual Contributor | 10 |
| Team alignment | 15 |
| Department alignment | 12 |
| Business-unit alignment | 8 |
| People Manager authority | 8 |
| Potential People Manager authority | 5 |
| Executive authority | 4 |
| CEO seniority-level override | 10 |
| Seniority gap of 1–2 levels | 5 |
| Seniority gap of 3–4 levels | 3 |
| Seniority gap of 5–6 levels | 2 |
| Seniority gap greater than 6 | 1 |

The structural relationship score varies according to the candidate relationship type.

The CEO override applies specifically to employees classified at seniority level 0.

The final candidate score is a heuristic ranking score, not a calibrated probability.

### Assignment Thresholds

| Parameter | Configured Value |
|---|---:|
| Minimum assignment score | 55 |
| Ambiguity margin | 8 |
| Initial assignment rounds | 3 |
| Reconciliation passes | Iterative until no eligible links remain |

A candidate below the minimum score is not assigned.

An employee is also excluded from automatic assignment when the difference between competing candidate scores is below the configured ambiguity margin.

### Manager Capacity

The initial manager capacity rules are:

| Manager Category | Maximum Direct Reports |
|---|---:|
| CEO | 8 |
| Senior executives and department heads, seniority level ≤ 7 | 10 |
| Team managers and team leads, seniority level ≤ 9 | 8 |
| Other eligible managers | 6 |

**Reconciliation exception:** One additional direct-report slot is allowed per manager during the reconciliation process. This exception does not change the original assignment capacity configuration.

### Abstention Strategy

Firmable deliberately supports abstention.

An employee may remain unassigned when:

- No eligible candidate exists.
- All candidates fall below the minimum score.
- Candidate scores are too close to distinguish reliably.
- Manager capacity is exhausted.
- Available employee attributes do not provide sufficient evidence.

This prevents unsupported reporting relationships from being introduced merely to create a fully connected chart.

---

## 6. Ground-Truth Isolation and Evaluation

A central design principle is preventing data leakage.

Ground-truth manager relationships are available exclusively for evaluation.

### Separation of Responsibilities

| Process | Ground Truth Access |
|---|---|
| Data cleaning | No |
| Seniority derivation | No |
| Candidate generation | No |
| Candidate scoring | No |
| Manager assignment | No |
| Hierarchy reconciliation | No |
| Hierarchy construction | No |
| Final evaluation | Yes |

Ground truth is retained in the Bronze dataset but is excluded from the inference pipeline.

The evaluation process compares predicted employee-manager relationships with actual relationships only after the inference process has completed.

### Evaluation Metrics

| Metric | Description |
|---|---|
| True Positives | Predicted manager matches the actual manager |
| False Positives | An incorrect manager relationship is predicted |
| False Negatives | An actual reporting relationship is not correctly predicted |
| Precision | Correct predictions divided by all predicted relationships |
| Recall | Correct predictions divided by all actual relationships |
| F1 Score | Harmonic mean of precision and recall |
| Assignment Coverage | Proportion of actual reporting relationships for which a manager was predicted |

Evaluation also examines correct roots, abstentions, error categories, and performance across organization structures.

**Final evaluation results:** Populate this section using the latest successful execution of Notebook 09 after Notebook 07 reconciliation. Do not substitute pre-reconciliation baseline metrics for final results.

---

## 7. Final Hierarchy Results

Latest successful hierarchy construction:

| Metric | Result |
|---|---:|
| Total employees | 89,576 |
| Assigned employees | 86,223 |
| Unassigned employees | 3,353 |
| CEO roots | 500 |
| Unassigned roots | 2,853 |
| Accepted reconciliation links | 1,542 |
| Maximum hierarchy depth | 5 |
| Unreachable employees | 0 |

### Hierarchy Validation

The latest Notebook 07 execution reported:

- Duplicate hierarchy rows: 0
- Duplicate manager assignments: 0
- Invalid manager references: 0
- Invalid seniority relationships: 0
- Capacity violations: 0
- Self relationships: 0
- Unreachable employees: 0

These are structural validation results, not accuracy metrics.

Every employee is reachable within their own reporting component. Not every employee is necessarily connected to the company's CEO.

---

## 8. Repository Structure

```text
firmable-org-chart/
│
├── app/
│   └── app.py
│
├── data/
│   ├── gold_companies.csv.gz
│   ├── gold_employee_hierarchy.csv.gz
│   ├── gold_org_chart_edges.csv.gz
│   └── gold_company_metrics.csv.gz
│
├── notebooks/
│   ├── 00_project_setup
│   ├── 01_synthetic_data_generation
│   ├── 02_bronze_data_validation
│   ├── 03_silver_transformation
│   ├── 04_manager_candidate_generation
│   ├── 05_manager_candidate_scoring
│   ├── 06_manager_assignment
│   ├── 07_hierarchy_construction
│   ├── 08_hierarchy_validation
│   ├── 09_evaluation
│   └── 10_gold_layer_publication
│
├── requirements.txt
└── README.md
```

---

## 9. Running the Application

### Prerequisites

- Python 3.x
- Git
- Required Python packages
- Gold CSV exports in the `data/` directory

### Installation

Clone the repository:

```bash
git clone https://github.com/amanS2613/firmable-org-chart.git

cd firmable-org-chart
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run app/app.py
```

The application provides:

- Company selection.
- Company overview.
- Organization chart visualization.
- Reporting component exploration.
- Department filtering.
- Employee search and details.
- Hierarchy gaps and unassigned employee analysis.

### Live Deployment

The application is deployed using Streamlit Community Cloud.

https://firmable-org-chart-aman2613.streamlit.app/

---

## 10. Design Decisions

### Why deterministic rules instead of machine learning?

The project prioritizes explainability and traceability.

A reviewer can inspect why a manager candidate received a particular score and which organizational attributes influenced the relationship.

The rule-based approach also avoids requiring labeled training data for inference.

### Why generate multiple manager candidates?

The most senior employee is not necessarily the correct manager.

Generating primary and fallback candidates provides alternatives when the preferred relationship is unavailable or ineligible.

### Why use seniority as a constraint?

Reporting relationships should generally point from a more senior employee to a less senior employee.

The implementation uses lower numerical seniority values to represent more senior roles.

### Why enforce manager capacity?

Without capacity constraints, the system could assign an unrealistic number of direct reports to a single manager.

Capacity constraints help produce more plausible reporting structures.

### Why allow disconnected components?

Forcing every employee into a CEO-rooted hierarchy would introduce unsupported relationships.

Firmable preserves disconnected components when the evidence is insufficient.

### Why use reconciliation?

Initial assignment may leave disconnected components because eligible managers are unavailable under the original capacity limits.

Reconciliation makes a controlled additional attempt to connect components while retaining score, ambiguity, seniority, and capacity checks.

---

## 11. Limitations

1. **Title-based inference:** Job titles may not accurately represent actual reporting authority or responsibilities.

2. **Incomplete employee attributes:** Missing departments, teams, business units, or titles can reduce candidate quality.

3. **Heuristic scoring:** Candidate scores are manually configured ranking scores and are not statistically calibrated probabilities.

4. **Capacity assumptions:** Reporting capacity limits are fixed rules and may not represent every organization's management structure.

5. **Matrix organizations:** Employees may report to multiple managers, whereas the current hierarchy primarily models one direct manager per employee.

6. **Disconnected components:** Some employees remain unassigned when no sufficiently defensible manager relationship is identified.

7. **Synthetic data:** The generated dataset may not capture every complexity found in real enterprise employee data.

8. **Static hierarchy:** The current implementation does not provide full temporal tracking of promotions, transfers, and historical reporting changes.

9. **Rule maintenance:** New job titles, organizational patterns, and industries may require additional normalization and rule configuration.

---

## 12. Future Improvements

- Introduce configurable scoring weights by organization type.
- Support matrix and multiple-manager relationships.
- Incorporate historical employee movement and reporting changes.
- Add explainability at individual employee-manager relationship level.
- Improve handling of unknown and ambiguous job titles.
- Introduce configurable manager capacity policies.
- Support incremental processing when employee data changes.
- Add hierarchy versioning and historical comparisons.
- Evaluate the system on real, appropriately governed organizational datasets.

---

## 13. Conclusion

Firmable demonstrates an end-to-end data engineering and rule-based inference solution for reconstructing employee reporting hierarchies.

The platform combines synthetic data generation, Medallion Architecture, distributed data processing, deterministic candidate scoring, constrained manager assignment, hierarchy reconciliation, evaluation, and interactive visualization.

Its central design principle is to prioritize explainability and defensible reporting relationships over forcing a completely connected hierarchy.

**Built with Databricks, PySpark, Spark SQL, Delta Lake, Python, Graphviz, and Streamlit.**