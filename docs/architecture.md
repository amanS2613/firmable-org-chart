# System Architecture

## 1. Overview

The Firmable Org Chart Inference Platform follows a Medallion architecture implemented using Databricks, Apache Spark, PySpark, Spark SQL and Delta Lake.

The pipeline transforms synthetic employee and company records into inferred organizational hierarchies. It separates raw data ingestion, data standardization, manager inference, hierarchy construction, evaluation and final application-ready outputs.

The architecture consists of four logical layers:

1. **Bronze:** Raw synthetic data and isolated ground truth.
2. **Silver:** Cleaned employee data, manager candidates, scoring and assignment results.
3. **Gold:** Final inferred hierarchy and company-level outputs.
4. **Evaluation:** Independent comparison of inferred relationships against ground truth.

Ground truth is isolated from the inference pipeline and is accessed only by the evaluation process.

## 2. High-Level Data Flow

```text
Synthetic Data Generation
          |
          v
   BRONZE LAYER
   -------------------------
   employees_raw
   employees_ingestion_raw
   ground_truth_relationships
          |
          v
   SILVER LAYER
   -------------------------
   employees_clean
   employees_title_normalized
          |
          v
   Manager Candidate Generation
          |
          v
   Manager Candidate Scoring
          |
          v
   Manager Assignment
          |
          v
   Hierarchy Construction
          |
          v
   GOLD LAYER
   -------------------------
   gold_companies
   gold_employee_hierarchy
   gold_org_chart_edges
   gold_company_metrics
          |
          v
   Streamlit Application

   EVALUATION LAYER
   -------------------------
   Compares inferred relationships
   against isolated ground truth
```

## 3. Bronze Layer — Raw Data Ingestion

**Schema:** `workspace.firmable_v2_bronze`

The Bronze layer stores the generated source data before downstream standardization and inference.

| Table | Purpose |
|---|---|
| `employees_raw` | Canonical synthetic employee records |
| `employees_ingestion_raw` | Employee records with simulated ingestion noise |
| `ground_truth_relationships` | Actual manager-reporting relationships used exclusively for evaluation |

The synthetic dataset contains:

- 500 companies.
- 89,576 employees.
- 100–250 employees per company.
- Functional, Flat, Divisional and Hybrid organizational structures.
- Multiple industries, departments, job titles and seniority levels.
- Simulated missing values, inconsistent formatting, aliases and title variations.

**Important design decision:** Ground truth is stored separately and is never used for candidate generation, scoring, assignment or hierarchy construction.

## 4. Silver Layer — Data Transformation and Inference

**Schema:** `workspace.firmable_v2_silver`

The Silver layer contains cleaned employee records and the intermediate outputs required to infer reporting relationships.

### 4.1 Employee standardization

Notebook: `03_silver_transformation`

The raw employee records are standardized to create:

- `employees_clean`
- `employees_title_normalized`

Key transformations include:

- Normalizing job titles and department names.
- Standardizing business units and team identifiers.
- Handling missing and inconsistent values.
- Deriving `inferred_seniority_level`.
- Deriving `management_authority`.
- Deriving `title_function`.
- Preserving unknown or unrecognized titles rather than assigning unsupported seniority values.

### 4.2 Manager candidate generation

Notebook: `04_manager_candidate_generation`

Potential manager-report relationships are generated using organizational attributes such as:

- Company membership.
- Department and business-unit alignment.
- Team membership.
- Seniority hierarchy.
- Title function and management authority.
- Recognized organizational reporting patterns.

The output is stored in:

`workspace.firmable_v2_silver.manager_candidates`

Candidate generation produces a shortlist of plausible managers for each employee. It does not make the final assignment.

### 4.3 Candidate scoring

Notebook: `05_manager_candidate_scoring`

Each candidate relationship receives a rule-based score based on structural fit and supporting organizational evidence.

The scoring process considers:

- Relationship-type compatibility.
- Team alignment.
- Department alignment.
- Business-unit alignment.
- Management authority.
- Seniority gap.

The scores are heuristic ranking values, not calibrated probabilities.

### 4.4 Manager assignment

Notebook: `06_manager_assignment`

The assignment process selects suitable manager-report relationships while enforcing:

- Minimum candidate score of 55.
- Ambiguity margin of 8.
- Seniority constraints.
- Manager reporting capacity.
- Duplicate and self-assignment prevention.

The initial assignment process runs for up to three rounds, allowing additional relationships to be assigned as the hierarchy develops.

Employees without sufficiently reliable candidates remain unassigned rather than receiving arbitrary managers.

### 4.5 Hierarchy construction and reconciliation

Notebook: `07_hierarchy_construction`

The hierarchy construction process builds organizational components from accepted manager-report relationships.

A reconciliation pass attempts to connect eligible disconnected components using the existing candidate scores and structural constraints.

During reconciliation:

- Candidate score must meet the assignment threshold.
- Ambiguous candidates are excluded.
- Manager seniority must be higher than employee seniority.
- Only relationships connecting separate components are considered.
- Each manager receives at most one additional reporting slot during reconciliation.

The process stops when no eligible candidate links remain.

Notebook: `08_hierarchy_validation`

The resulting hierarchy is checked for:

- Duplicate employee records.
- Duplicate manager assignments.
- Invalid manager references.
- Self-reporting relationships.
- Invalid seniority relationships.
- Manager capacity violations.
- Employees unreachable within their assigned hierarchy component.

## 5. Gold Layer — Application-Ready Outputs

**Schema:** `workspace.firmable_v2_gold`

The Gold layer contains the final outputs consumed by the Streamlit application.

| Table | Purpose |
|---|---|
| `gold_companies` | Company-level information for company selection |
| `gold_employee_hierarchy` | Employee records with inferred hierarchy information |
| `gold_org_chart_edges` | Manager-reporting edges used to render organizational charts |
| `gold_company_metrics` | Company-level hierarchy and inference metrics |

The Gold layer provides a structured interface between the Databricks processing pipeline and the application.

Notebook: `10_gold_layer_publication`

This notebook publishes the validated hierarchy and supporting metrics into the Gold schema and exports the application datasets.

## 6. Evaluation Layer — Independent Quality Measurement

**Schema:** `workspace.firmable_v2_evaluation`

Notebook: `09_evaluation`

The evaluation layer measures the quality of inferred manager-reporting relationships against the synthetic ground truth.

Evaluation is performed separately from inference.

The evaluation process measures:

- True positives.
- False positives.
- False negatives.
- Precision.
- Recall.
- F1-score.
- Relationship coverage.

The evaluation layer reads the ground-truth relationships, compares them with inferred relationships and stores evaluation results.

Ground-truth records are not passed back into the Silver inference pipeline or used to modify manager assignments.

## 7. Notebook Execution Order

The notebooks are designed to run in the following sequence:

| Order | Notebook | Responsibility |
|---:|---|---|
| 1 | `00_project_setup` | Initialize project configuration and schemas |
| 2 | `01_synthetic_data_generation` | Generate companies, employees and ground truth |
| 3 | `02_bronze_data_validation` | Validate generated Bronze data |
| 4 | `03_silver_transformation` | Clean and standardize employee records |
| 5 | `04_manager_candidate_generation` | Generate potential manager candidates |
| 6 | `05_manager_candidate_scoring` | Score candidate relationships |
| 7 | `06_manager_assignment` | Assign managers subject to constraints |
| 8 | `07_hierarchy_construction` | Construct and reconcile hierarchy components |
| 9 | `08_hierarchy_validation` | Validate the final hierarchy |
| 10 | `09_evaluation` | Evaluate inferred relationships against ground truth |
| 11 | `10_gold_layer_publication` | Publish application-ready Gold outputs |

## 8. Application Architecture

The Streamlit application consumes the published Gold datasets rather than executing the inference pipeline at runtime.

The application provides:

- Company selection.
- Organizational chart visualization.
- Employee exploration.
- Hierarchy gap and disconnected-component visibility.
- Company-level hierarchy metrics.

The application preserves disconnected components instead of artificially connecting every employee to a CEO. This makes unresolved hierarchy gaps visible to users.

**Application:** https://firmable-org-chart-aman2613.streamlit.app/

**GitHub repository:** https://github.com/amanS2613/firmable-org-chart

## 9. Key Architectural Decisions

| Decision | Rationale |
|---|---|
| Medallion architecture | Separates raw data, standardized data and application-ready outputs |
| Delta tables | Provides reliable structured storage for intermediate and final datasets |
| Rule-based inference | Keeps manager assignment explainable and avoids dependence on ML models |
| Ground-truth isolation | Prevents evaluation labels from leaking into inference |
| Candidate scoring before assignment | Separates candidate suitability from final hierarchy decisions |
| Capacity constraints | Prevents unrealistic reporting structures |
| Ambiguity-based abstention | Avoids forcing uncertain manager assignments |
| Component reconciliation | Attempts to reduce disconnected hierarchy components without violating structural constraints |
| Disconnected-component visibility | Preserves the distinction between inferred relationships and unresolved reporting gaps |

## 10. Limitations

- The hierarchy is inferred from available employee attributes and predefined organizational rules.
- Candidate scores are heuristic ranking values and are not calibrated probabilities.
- Some employees remain unassigned when no suitable manager candidate is available or when assignment constraints prevent a reliable relationship.
- The reconciliation process reduces disconnected components but does not guarantee that every employee will connect to the company's CEO.
- Synthetic data may not represent every organizational structure or exception found in real-world enterprise datasets.

The architecture is designed to prioritize explainability, structural consistency and transparent handling of uncertainty over forced assignment coverage.