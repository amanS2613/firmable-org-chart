# Evaluation Methodology

## 1. Objective

The objective of evaluation is to measure how accurately the rule-based inference pipeline identifies employee-manager relationships.

The system's inferred relationships are compared against the synthetic ground-truth relationships generated alongside the employee dataset.

Evaluation is performed independently of the inference process. Ground truth is used only to measure the quality of the final predictions and is never used to generate candidates, calculate scores or assign managers.

## 2. Evaluation Dataset

The evaluation uses the following dataset:

| Attribute | Value |
|---|---:|
| Companies | 500 |
| Employees | 89,576 |
| Actual manager-report relationships | 89,076 |

The evaluation compares actual manager-report relationships with the relationships produced by the inference pipeline.

**Ground-truth source:** `workspace.firmable_v2_bronze.ground_truth_relationships`

**Evaluation schema:** `workspace.firmable_v2_evaluation`

## 3. Evaluation Approach

The evaluation process follows these steps:

1. Retrieve the actual manager-report relationships from the isolated ground-truth table.
2. Retrieve the final inferred manager-report relationships.
3. Compare actual and predicted relationships using employee and manager identifiers.
4. Identify matching and mismatching relationships.
5. Calculate precision, recall, F1-score and relationship coverage.
6. Store the evaluation results for reporting.

A relationship is considered correct only when both the employee and the assigned manager match the ground truth.

## 4. Evaluation Metrics

### 4.1 True Positives (TP)

The number of inferred manager-report relationships that correctly match the actual relationship.

### 4.2 False Positives (FP)

The number of inferred relationships where the assigned manager does not match the actual manager.

### 4.3 False Negatives (FN)

The number of actual manager-report relationships that the inference system failed to identify.

### 4.4 Precision

Precision measures the proportion of inferred relationships that are correct.

\[
Precision = \frac{TP}{TP + FP}
\]

Higher precision indicates fewer incorrect manager assignments.

### 4.5 Recall

Recall measures the proportion of actual manager-report relationships successfully identified.

\[
Recall = \frac{TP}{TP + FN}
\]

Higher recall indicates that the system identifies a larger share of the actual reporting relationships.

### 4.6 F1-Score

The F1-score is the harmonic mean of precision and recall.

\[
F1 = 2 \times \frac{Precision \times Recall}{Precision + Recall}
\]

It provides a combined measure of precision and recall.

### 4.7 Relationship Coverage

Relationship coverage measures the proportion of employees with an assigned manager among employees who have an actual manager in the ground truth.

\[
Coverage = \frac{\text{Employees with an assigned manager}}{\text{Employees with an actual manager}}
\]

Coverage and recall measure different things: coverage measures assignment completeness, while recall measures whether the assigned manager is correct.

## 5. Evaluation Results

Populate this section using the **latest successful run of Notebook `09_evaluation` after Notebook `07_hierarchy_construction` reconciliation**.

Do not reuse historical baseline results because the hierarchy changed after reconciliation.

| Metric | Latest result |
|---|---:|
| Actual relationships | [Insert latest value] |
| Predicted relationships | [Insert latest value] |
| True positives | [Insert latest value] |
| False positives | [Insert latest value] |
| False negatives | [Insert latest value] |
| Precision | [Insert latest value] |
| Recall | [Insert latest value] |
| F1-score | [Insert latest value] |
| Relationship coverage | [Insert latest value] |

## 6. Hierarchy Construction Results

The final hierarchy validation after reconciliation produced the following results:

| Metric | Result |
|---|---:|
| Total employees | 89,576 |
| Assigned employees | 86,223 |
| Unassigned employees | 3,353 |
| Accepted component reconciliation links | 1,542 |
| CEO roots | 500 |
| Unassigned component roots | 2,853 |
| Maximum hierarchy depth | 5 |
| Duplicate assignments | 0 |
| Invalid manager references | 0 |
| Self-reporting relationships | 0 |
| Seniority violations | 0 |
| Capacity violations | 0 |
| Unreachable employees | 0 |

These results describe hierarchy construction and structural validation. They should not be interpreted as accuracy metrics.

## 7. Ground-Truth Isolation

Ground-truth isolation is a key design principle of the project.

The ground-truth relationships are generated separately and stored in the Bronze layer. They are accessed by the evaluation notebook only.

They are not used by:

- Employee cleaning and standardization.
- Seniority inference.
- Manager candidate generation.
- Candidate scoring.
- Manager assignment.
- Hierarchy construction.
- Component reconciliation.
- Gold-layer publication.

This separation prevents target-label leakage and ensures that the inference pipeline relies on employee attributes and predefined organizational rules rather than actual reporting relationships.

## 8. Interpreting the Results

The evaluation metrics should be considered together.

- **High precision:** The system avoids assigning incorrect managers.
- **High recall:** The system identifies a large proportion of actual reporting relationships.
- **High F1-score:** The system balances correctness and relationship discovery.
- **High coverage:** The system assigns managers to a large proportion of employees who have actual managers.

The system deliberately allows abstention when a suitable manager cannot be identified with sufficient evidence.

Consequently, an unassigned employee is not automatically considered a failed inference. The evaluation distinguishes between missing assignments and incorrect assignments.

## 9. Limitations

- Evaluation results are based on synthetic organizational data.
- Synthetic ground truth may not capture all real-world reporting structures.
- Precision, recall and F1-score depend on the generated dataset and its organizational patterns.
- Rule-based candidate scores are heuristic ranking values, not calibrated probabilities.
- Relationship coverage does not independently establish relationship correctness.
- Structural validation confirms hierarchy consistency but does not guarantee that every inferred relationship is factually correct.

## 10. Reproducibility

The evaluation can be reproduced by executing Notebook `09_evaluation` after the latest inference and hierarchy construction notebooks have completed successfully.

The evaluation should always use the final reconciled hierarchy outputs so that reported metrics correspond to the version published to the Gold layer.