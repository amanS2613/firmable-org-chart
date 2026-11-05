# Data Dictionary

## 1. Overview

This document describes the main datasets and tables used by the Firmable Org Chart Inference Platform.

The project uses Databricks Delta tables organized into Bronze, Silver and Gold layers, with a separate evaluation schema.

The tables are designed to support synthetic data generation, employee standardization, manager inference, hierarchy construction, evaluation and application reporting.

## 2. Bronze Layer

**Schema:** `workspace.firmable_v2_bronze`

The Bronze layer stores the original generated data and the isolated ground-truth relationships.

| Table | Description |
|---|---|
| `employees_raw` | Canonical synthetic employee records |
| `employees_ingestion_raw` | Employee records containing simulated ingestion inconsistencies |
| `ground_truth_relationships` | Actual employee-manager relationships, reserved for evaluation |

### Important employee attributes

The employee dataset contains organizational attributes