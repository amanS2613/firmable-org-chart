# Reproducibility and Setup Guide

## 1. Overview

This guide explains how to set up, execute and reproduce the Firmable Org Chart Inference Platform.

The project uses Databricks for data generation and processing, Delta tables for structured storage, and Streamlit for application deployment.

The inference pipeline uses SQL- and Python-based organizational rules and does not require machine learning model training.

## 2. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Synthetic data generation and data processing |
| SQL / Spark SQL | Data transformation and inference logic |
| PySpark | Distributed data processing |
| Databricks | Notebook execution and pipeline development |
| Delta Lake | Structured storage for pipeline layers |
| Streamlit | Interactive application |
| GitHub | Source code and project documentation |

## 3. Repository Structure

```text
firmable-org-chart/
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
├── app/
│   └── Streamlit application files
│
├── data/
│   └── Published application datasets
│
├── docs/
│   ├── methodology.md
│   ├── architecture.md
│   ├── evaluation.md
│   ├── design_decisions.md
│   ├── data_dictionary.md
│   └── reproducibility.md
│
├── README.md
└── requirements.txt
```

*The tree is a logical project layout. Keep the actual repository paths and filenames if they differ.*

## 4. Databricks Setup

1. Create or access a Databricks workspace.
2. Import the project notebooks into the workspace.
3. Confirm that the required compute environment is available.
4. Ensure that the workspace catalog is accessible.
5. Execute the notebooks in the documented order.

The project uses the following catalog and schemas:

**Catalog:** `workspace`

- `workspace.firmable_v2_bronze`
- `workspace.firmable_v2_silver`
- `workspace.firmable_v2_gold`
- `workspace.firmable_v2_evaluation`

The setup notebook initializes the project configuration and schemas.

## 5. Pipeline Execution Order

Execute the notebooks sequentially:

| Step | Notebook | Expected output |
|---:|---|---|
| 1 | `00_project_setup` | Project schemas and configuration |
| 2 | `01_synthetic_data_generation` | Synthetic companies, employees and ground truth |
| 3 | `02_bronze_data_validation` | Validated Bronze datasets |
| 4 | `03_silver_transformation` | Cleaned employee datasets |
| 5 | `04_manager_candidate_generation` | Manager candidate relationships |
| 6 | `05_manager_candidate_scoring` | Scored candidate relationships |
| 7 | `06_manager_assignment` | Initial manager assignments |
| 8 | `07_hierarchy_construction` | Reconciled hierarchy |
| 9 | `08_hierarchy_validation` | Structural validation results |
| 10 | `09_evaluation` | Evaluation metrics |
| 11 | `10_gold_layer_publication` | Application-ready Gold datasets |

**Important:** Run downstream notebooks after their upstream dependencies have completed successfully. If an upstream transformation or inference stage changes, rerun the affected downstream stages before publishing final outputs.

## 6. Synthetic Data Generation

Notebook `01_synthetic_data_generation` generates the synthetic organization dataset.

The configured dataset contains:

- 500 companies.
- 89,576 employees.
- 100–250 employees per company.
- Multiple organizational structures.
- Multiple departments, teams and business units.
- Job-title and employee-data inconsistencies.
- Separate ground-truth reporting relationships.

The generated data is stored in the Bronze layer.

Ground truth must remain isolated from the inference notebooks.

## 7. Inference Pipeline

The inference process consists of:

1. Employee data cleaning and title normalization.
2. Manager candidate generation.
3. Candidate scoring.
4. Manager assignment.
5. Hierarchy construction and reconciliation.
6. Structural hierarchy validation.

Important configuration values include:

| Parameter | Value |
|---|---:|
| Minimum assignment score | 55 |
| Ambiguity margin | 8 |
| Initial assignment rounds | Up to 3 |
| Reconciliation capacity extension | 1 additional direct report per manager |

These values represent the implemented project configuration and should be updated if the inference rules change.

## 8. Evaluation

Notebook `09_evaluation` compares