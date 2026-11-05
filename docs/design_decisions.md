# Design Decisions and Trade-offs

## 1. Rule-Based Inference Instead of Machine Learning

**Decision:** Use SQL- and Python-based organizational rules rather than machine learning models.

**Rationale:**
- Manager-reporting relationships depend heavily on organizational structure, job titles, seniority and reporting conventions.
- Explicit rules make the inference process easier to understand and explain.
- Candidate scores can be decomposed into individual evidence components.
- The approach avoids requiring a separately trained model or labeled training dataset.

**Trade-off:** Rule-based systems require domain knowledge and may need updates when organizational structures or title conventions change.

## 2. Candidate Generation Before Manager Assignment

**Decision:** Separate potential manager discovery from final manager assignment.

**Rationale:**
- An employee may have multiple plausible manager candidates.
- Candidate generation creates a shortlist without immediately committing to a relationship.
- Candidate scoring ranks potential relationships using organizational evidence.
- Assignment applies additional constraints such as ambiguity, seniority and manager capacity.

**Trade-off:** The quality of the final hierarchy depends partly on whether the candidate-generation stage includes the actual manager in its shortlist.

## 3. Explainable Candidate Scoring

**Decision:** Use a weighted scoring system based on organizational evidence.

The scoring process considers:

- Structural relationship fit.
- Team alignment.
- Department alignment.
- Business-unit alignment.
- Management authority.
- Seniority gap.

**Rationale:**
- Each candidate's ranking can be explained using identifiable attributes.
- Structural compatibility receives greater importance than weaker supporting signals.
- The scoring system can be adjusted without retraining a model.

**Trade-off:** The scores are heuristic ranking values, not calibrated probabilities. A higher score indicates a stronger rule-based ranking, not a guaranteed probability of being the correct manager.

## 4. Seniority-Based Reporting Constraints

**Decision:** Require the proposed manager to be more senior than the employee.

**Rationale:**
- Reporting relationships should respect organizational seniority.
- The constraint prevents junior employees from being assigned as managers of senior employees.
- It helps maintain a coherent hierarchy.

**Trade-off:** Real organizations may contain exceptions, such as project-based reporting or specialist roles where title seniority does not reflect actual reporting authority.

## 5. Management Authority as Supporting Evidence

**Decision:** Use management authority as one of the candidate-scoring signals rather than treating it as the sole eligibility criterion.

**Rationale:**
- Job titles and organizational roles can provide evidence of people-management responsibility.
- Management authority helps distinguish likely managers from individual contributors.
- Combining it with structural fit and seniority reduces dependence on any single attribute.

**Trade-off:** Job titles do not always accurately represent actual managerial responsibilities.

## 6. Ambiguity-Based Abstention

**Decision:** Abstain when the leading manager candidates are too close in score.

The configured ambiguity margin is 8.

**Rationale:**
- A small score difference may not provide sufficient evidence to distinguish between candidates.
- Automatically selecting the highest-ranked candidate could introduce incorrect reporting relationships.
- Abstention preserves uncertainty instead of hiding it.

**Trade-off:** Abstention can reduce relationship coverage, but it helps avoid unsupported assignments.

## 7. Minimum Assignment Score

**Decision:** Require a minimum candidate score of 55 before accepting a manager assignment.

**Rationale:**
- Weak candidates should not be assigned simply because they are the best available option.
- The threshold provides a consistent minimum suitability requirement.
- It supports conservative inference.

**Trade-off:** Some genuine manager relationships may remain unassigned when their available evidence does not meet the threshold.

## 8. Manager Reporting Capacity

**Decision:** Apply reporting capacity limits to managers.

Initial assignment capacity:

| Manager category | Maximum direct reports |
|---|---:|
| CEO | 8 |
| Senior executives / Department Heads | 7 |
| Team Managers / Team Leads | 9 |
| Other eligible managers | 6 |

**Rationale:**
- Prevents unrealistic reporting structures.
- Avoids assigning an excessive number of employees to a single manager.
- Encourages the construction of multiple organizational levels.

**Trade-off:** Actual organizations can have managers with larger or smaller teams. Capacity limits are assumptions used to produce plausible synthetic hierarchies.

## 9. Multi-Round Assignment

**Decision:** Run manager assignment for up to three rounds.

**Rationale:**
- Some manager candidates may become usable as the hierarchy develops.
- Multiple rounds allow additional relationships to be considered without immediately forcing all employees into the hierarchy.
- The process provides a controlled way to expand the assigned structure.

**Trade-off:** Additional rounds increase processing complexity and do not guarantee that every employee will receive a manager.

## 10. Component Reconciliation

**Decision:** Run an additional reconciliation pass to connect eligible disconnected hierarchy components.

The reconciliation process:
- Uses existing candidate scores.
- Enforces the minimum score threshold.
- Excludes ambiguous candidates.
- Requires a valid seniority relationship.
- Considers only relationships connecting separate components.
- Allows one additional direct-report slot per manager during reconciliation.

**Rationale:**
- Initial assignments can leave otherwise plausible organizational components disconnected.
- Reconciliation provides another opportunity to connect these components without discarding the original assignment decisions.
- Restricting the additional capacity helps control reporting structure size.

**Outcome:** The final reconciliation accepted 1,542 additional links.

**Trade-off:** Reconciliation reduces disconnected components but does not guarantee that all employees can be connected to the CEO. Remaining disconnected components are retained and exposed in the application.

## 11. Preserve Disconnected Components

**Decision:** Do not force every employee into one company-wide tree.

**Rationale:**
- A disconnected component may represent insufficient evidence or an unresolved reporting relationship.
- Artificially connecting it to a CEO or another senior employee would make the hierarchy appear more complete than the evidence supports.
- Showing disconnected components makes inference limitations transparent.

**Trade-off:** Some company charts contain multiple roots rather than a single root.

## 12. Ground-Truth Isolation

**Decision:** Keep ground-truth reporting relationships separate from the inference pipeline.

**Rationale:**
- Prevents target-label leakage.
- Ensures candidate generation and scoring rely on employee attributes and organizational rules.
- Makes evaluation independent of the inference decisions.

Ground truth is accessed only by the evaluation process.

**Trade-off:** The inference pipeline cannot use actual manager relationships to correct its own predictions during execution.

## 13. Medallion Architecture

**Decision:** Organize the processing pipeline into Bronze, Silver and Gold layers, with a separate evaluation schema.

**Rationale:**
- Bronze preserves source data.
- Silver handles cleaning, candidate generation, scoring and assignment.
- Gold provides application-ready outputs.
- Evaluation remains logically separate from inference.

**Trade-off:** The architecture introduces additional tables and processing stages, but improves separation of responsibilities and traceability.

## 14. Delta Tables for Intermediate and Final Data

**Decision:** Use Delta tables to store structured pipeline outputs in Databricks.

**Rationale:**
- Provides consistent storage for intermediate processing results.
- Supports SQL and PySpark workflows.
- Makes it easier to inspect and validate outputs across notebook stages.

## 15. Summary of Key Trade-offs

| Design choice | Main benefit | Main trade-off |
|---|---|---|
| Rule-based inference | Explainability | Requires rule maintenance |
| Candidate scoring | Ranked manager options | Scores are heuristic |
| Seniority constraints | Hierarchy consistency | May exclude real-world exceptions |
| Ambiguity abstention | Avoids weak assignments | Reduces coverage |
| Minimum score threshold | Conservative assignment | Some valid links may be missed |
| Capacity constraints | Plausible team sizes | Simplifies real organizations |
| Multi-round assignment | More assignment opportunities | Additional processing |
| Component reconciliation | Connects eligible components | Cannot resolve every gap |
| Ground-truth isolation | Prevents leakage | No label-based correction |
| Medallion architecture | Clear data separation | More processing stages |

## 16. Overall Design Philosophy

The platform prioritizes explainability, structural consistency and transparent uncertainty handling.

Rather than forcing a manager assignment for every employee, it generates plausible candidates, ranks them using organizational evidence, applies structural constraints and abstains when the evidence is insufficient.

This produces an inferred hierarchy that is easier to inspect, validate and improve.