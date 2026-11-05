# Firmable — Manager Inference Methodology

## 1. Introduction

Firmable reconstructs employee reporting hierarchies using deterministic, rule-based inference.

The objective is to identify plausible employee-manager relationships using available organizational attributes without relying on machine learning or ground-truth reporting relationships.

The inference engine considers:

- Normalized job titles.
- Inferred seniority.
- Management authority.
- Department alignment.
- Team alignment.
- Business-unit alignment.
- Organizational structure.
- Manager reporting capacity.

The system generates multiple potential managers, scores candidate relationships, applies assignment constraints, and abstains when the available evidence is insufficient.

---

## 2. Input Attributes

The inference process uses standardized employee attributes from the Silver layer.

| Attribute | Purpose |
|---|---|
| `company_id` | Restricts candidate relationships to the same company |
| `employee_id` | Identifies the employee |
| `job_title_clean` | Provides normalized job-title information |
| `inferred_seniority_level` | Establishes relative organizational seniority |
| `management_authority` | Provides supporting evidence of management authority |
| `title_function` | Helps identify organizational role categories |
| `department` | Supports department-level alignment |
| `team_id` / `team_name` | Supports team-level alignment |
| `business_unit` | Supports business-unit alignment |

Seniority is represented numerically, with lower values indicating more senior positions.

Unknown job titles are not automatically assigned an unsupported seniority level.

---

## 3. Candidate Generation

Candidate generation identifies potential managers for each employee.

The process uses predefined organizational relationship patterns rather than selecting the next most senior employee.

### Supported relationship patterns

| Employee Category | Candidate Manager Category |
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

These relationships support primary and fallback candidate paths.

The applicable relationship depends on organizational structure and the employee's available attributes.

### Candidate generation principles

1. Candidates belong to the same company.
2. Employees cannot be their own managers.
3. Candidate seniority must be compatible with the reporting direction.
4. Team, department, and business-unit relationships are considered.
5. Multiple candidates are retained to allow alternative assignment paths.
6. Ground-truth manager IDs are never used to generate candidates.

Candidate generation and candidate scoring are separate operations.

---

## 4. Candidate Scoring

Each candidate employee-manager pair receives a deterministic ranking score.

The score combines structural fit and organizational evidence.

### 4.1 Structural relationship fit

The relationship type receives a base score according to the predefined organizational rules.

Examples of implemented structural weights include:

| Relationship Type | Score |
|---|---:|
| Direct structural relationship | 45 |
| Functional Executive → Department Head | 49 |
| Team Manager → Individual Contributor | 24 |
| Department Head → Team Lead fallback | 22 |
| CEO → Department Head fallback | 18 |
| Department Head → Individual Contributor | 10 |

The structural score depends on the candidate relationship type.

### 4.2 Organizational alignment

Additional points are awarded for organizational alignment.

| Evidence | Score |
|---|---:|
| Team alignment | 15 |
| Department alignment | 12 |
| Business-unit alignment | 8 |

These attributes help distinguish candidates who occupy compatible organizational areas.

### 4.3 Management authority

Management authority provides supporting evidence.

| Authority | Score |
|---|---:|
| People Manager | 8 |
| Potential People Manager | 5 |
| Executive | 4 |
| CEO seniority-level override | 10 |

The CEO override applies to seniority level 0.

Management authority is not treated as an independent guarantee that an employee manages people.

### 4.4 Seniority gap

The score also considers the difference in seniority between the employee and candidate manager.

| Seniority Gap | Score |
|---|---:|
| 1–2 levels | 5 |
| 3–4 levels | 3 |
| 5–6 levels | 2 |
| Greater than 6 levels | 1 |

Lower numerical seniority values represent more senior roles.

### 4.5 Final candidate score

The candidate score is the sum of the applicable structural and supporting evidence scores.

Conceptually:

```text
Candidate Score =
    Structural Relationship Fit
  + Team Alignment
  + Department Alignment
  + Business Unit Alignment
  + Management Authority
  + Seniority Gap Score
```

Only applicable evidence contributes to the score.

**Important:** Candidate scores are heuristic ranking scores. They are not probabilities, calibrated confidence values, or statistically estimated likelihoods.

---

## 5. Ambiguity Detection

A high-scoring candidate does not automatically imply that the relationship is unambiguous.

The system compares the leading candidate with competing candidates.

The configured ambiguity margin is 8 points.

Conceptually:

```text
Score Margin = Best Candidate Score - Second Best Candidate Score
```

When competing candidates are too close under the configured margin, the employee is treated as ambiguous and is not automatically assigned.

This prevents the system from making unsupported decisions when multiple managers have similar evidence.

The exact handling of missing or absent alternatives follows the implementation in the scoring notebook.

---

## 6. Manager Assignment

Manager assignment selects eligible candidates subject to scoring and organizational constraints.

### Assignment configuration

| Parameter | Value |
|---|---:|
| Minimum candidate score | 55 |
| Ambiguity margin | 8 |
| Initial assignment rounds | 3 |

A candidate must satisfy the minimum score and ambiguity conditions before assignment.

The system also validates:

- Employee and manager references.
- Same-company relationship.
- Seniority ordering.
- Self-reporting prevention.
- Duplicate assignment prevention.
- Manager capacity.

### Assignment rounds

The initial assignment process uses multiple rounds.

- Primary candidates are considered first.
- Eligible fallback candidates can be considered in subsequent rounds.
- Remaining employees are retained as unassigned when no eligible candidate can be accepted.

The process does not force an assignment simply to increase hierarchy coverage.

---

## 7. Manager Capacity Constraints

Manager capacity prevents unrealistic reporting structures.

The configured initial direct-report limits are:

| Manager Category | Maximum Direct Reports |
|---|---:|
| CEO | 8 |
| Senior executives and department heads, seniority level ≤ 7 | 10 |
| Team managers and team leads, seniority level ≤ 9 | 8 |
| Other eligible managers | 6 |

Capacity is evaluated using the manager's existing direct-report count.

Once a manager reaches the applicable limit, additional candidates cannot be assigned to that manager through the initial assignment process.

### Reconciliation capacity exception

The hierarchy reconciliation process permits one additional direct report per manager beyond the original capacity.

This exception is restricted to reconciliation.

It does not modify the original assignment capacity configuration.

---

## 8. Hierarchy Reconciliation

Initial manager assignment can produce disconnected reporting components.

Some components remain disconnected because potential managers are unavailable under the initial capacity constraints.

The reconciliation process makes an additional controlled attempt to connect these components.

### Reconciliation conditions

A proposed reconciliation relationship must:

1. Have a candidate score of at least 55.
2. Be unambiguous under the configured margin.
3. Follow valid seniority ordering.
4. Connect different reporting components.
5. Satisfy the reconciliation-specific capacity allowance.
6. Avoid self-reporting and duplicate relationships.

### Reconciliation execution

The process operates iteratively:

1. Identify currently unassigned component roots.
2. Generate eligible candidate-manager options.
3. Recalculate manager availability and remaining capacity.
4. Select acceptable relationships.
5. Update existing manager assignments.
6. Recalculate components for the next pass.
7. Stop when no eligible links remain.

The implementation updates existing employee assignment records rather than inserting duplicate employee records.

### Latest reconciliation outcome

| Metric | Result |
|---|---:|
| Accepted reconciliation links | 1,542 |
| Pass 1 accepted links | 1,542 |
| Pass 2 accepted links | 0 |
| Unassigned employees after reconciliation | 3,353 |
| CEO roots | 500 |
| Unassigned roots | 2,853 |

Reconciliation is not intended to guarantee that every employee becomes connected to the CEO.

It only adds relationships supported by the configured rules.

---

## 9. Hierarchy Construction

After assignment and reconciliation, the system constructs:

- Manager-employee hierarchy edges.
- Employee hierarchy records.
- Reporting component roots.
- Hierarchy depth.
- Root classification.

Each employee belongs to one reporting component.

A company can contain multiple disconnected components.

These components are retained separately for visualization rather than connected through artificial manager relationships.

---

## 10. Abstention Strategy

Abstention is an intentional feature of Firmable.

An employee may remain unassigned because:

- No candidate manager was generated.
- No candidate meets the minimum score.
- Competing candidates are ambiguous.
- All eligible managers have reached capacity.
- Seniority or other structural constraints are not satisfied.
- Available employee attributes are insufficient.

The system prefers an explicit unresolved relationship over an unsupported reporting assignment.

This improves the interpretability of the resulting hierarchy.

---

## 11. Ground-Truth Isolation

Ground-truth manager relationships are used exclusively for evaluation.

They are not used in:

- Employee cleaning.
- Seniority derivation.
- Management authority derivation.
- Candidate generation.
- Candidate scoring.
- Manager assignment.
- Hierarchy reconciliation.
- Hierarchy construction.

The inference pipeline uses employee attributes and deterministic organizational rules.

Only after predictions are generated does the evaluation notebook compare the predicted manager IDs with actual manager IDs.

This separation prevents target leakage and provides a more meaningful evaluation of inference performance.

---

## 12. Evaluation Methodology

The evaluation process compares predicted manager relationships against ground truth.

### Metrics

**True Positive (TP):** Predicted manager matches the actual manager.

**False Positive (FP):** A manager is predicted incorrectly.

**False Negative (FN):** An actual reporting relationship is not correctly identified.

**Precision:**

```text
TP / (TP + FP)
```

**Recall:**

```text
TP / (TP + FN)
```

**F1 Score:**

```text
2 × Precision × Recall / (Precision + Recall)
```

**Assignment Coverage:**

```text
Predicted Reporting Relationships / Actual Reporting Relationships
```

The evaluation also examines correct roots, abstentions, error categories, and performance across organizational structures.

Structural validation metrics and prediction accuracy metrics are reported separately.

---

## 13. Design Trade-offs

| Design Decision | Rationale |
|---|---|
| Deterministic rules | Explainable and reproducible inference |
| Multiple candidate managers | Supports primary and fallback relationships |
| Seniority constraints | Prevents implausible reporting direction |
| Organizational alignment | Uses team, department, and business-unit context |
| Capacity constraints | Avoids unrealistic reporting loads |
| Ambiguity detection | Prevents arbitrary selection between similar candidates |
| Abstention | Preserves unresolved relationships |
| Reconciliation | Provides a controlled opportunity to connect components |
| Ground-truth isolation | Prevents evaluation leakage |
| Separate reporting components | Preserves the actual inferred graph structure |

---

## 14. Known Limitations

- Job titles may not accurately represent reporting authority.
- Missing organizational attributes can reduce inference quality.
- Manually configured weights may require tuning for different industries.
- Capacity constraints are assumptions rather than observed management limits.
- Matrix reporting structures are not fully represented by a single-manager hierarchy.
- Synthetic data cannot represent every real-world organizational pattern.
- The system does not currently provide full historical hierarchy versioning.
- Candidate scores are not calibrated probabilities.

---

## 15. Future Enhancements

Potential future improvements include:

- Configurable scoring policies by organization type.
- Support for matrix reporting relationships.
- Historical hierarchy versioning.
- Incremental processing for employee changes.
- More detailed candidate-level explanation records.
- Improved title normalization.
- Additional evaluation across real-world organizational datasets.

---

## 16. Conclusion

Firmable uses a structured, explainable inference process to reconstruct employee reporting hierarchies.

By combining candidate generation, deterministic scoring, seniority constraints, manager capacity, ambiguity detection, reconciliation, and abstention, the platform prioritizes defensible organizational relationships.

The methodology is designed to preserve uncertainty rather than hide it through artificial hierarchy completion.