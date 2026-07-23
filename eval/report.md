# Eval Report (V1 Baseline)
_Generated 2026-07-23T02:58:59+00:00_
_Scenarios scored: 10_

## Master Table

| Pillar | Metric | V1 Baseline |
|--------|--------|-------------|
| Structural | Format pass rate | 100% (40/40) (retries used: 2) |
| Functional | Defect-detection recall (suite mean) | 0.93 |
| Functional | Defect-detection strict precision (suite mean) | 0.11 |

Recall is the mean across scenarios carrying seeded defects, since recall is undefined where zero defects are seeded. Strict precision is the mean across scenarios that raised at least one flag.

## Per-Scenario L2

| Scenario | Seeded | Caught | Recall | Flags | Matched | Strict Precision |
|----------|--------|--------|--------|-------|---------|------------------|
| scn_001_pii_logging | 2 | 2 | 1.00 | 36 | 3 | 0.08 |
| scn_002_vague_acceptance_criteria | 2 | 2 | 1.00 | 24 | 6 | 0.25 |
| scn_003_synchronous_vendor_call_in_checkout | 3 | 3 | 1.00 | 32 | 7 | 0.22 |
| scn_004_unbounded_compute_for_reconciliation | 2 | 2 | 1.00 | 33 | 5 | 0.15 |
| scn_005_cross_border_data_residency | 2 | 2 | 1.00 | 34 | 7 | 0.21 |
| scn_006_mid_sprint_scope_addition | 3 | 3 | 1.00 | 38 | 8 | 0.21 |
| scn_007_ledger_service_circular_dependency | 2 | 1 | 0.50 | 34 | 1 | 0.03 |
| scn_008_clean_idempotency_key_rollout | 0 | 0 | n/a | 21 | 0 | 0.00 |
| scn_009_clean_observability_dashboard | 0 | 0 | n/a | 29 | 0 | 0.00 |
| scn_010_clean_db_index_addition | 0 | 0 | n/a | 20 | 0 | 0.00 |

Recall reads n/a for clean scenarios, which seed no defects. Those rows are excluded from the suite recall mean and included in the strict precision mean.

## Unmatched Flags (264 total)

These concerns did not match any seeded defect ID. Each falls into one of three categories:

- **Real but unseeded**: the agent caught a legitimate issue not present in the seeded set. 
  Adding it to the scenario's `seeded_defects` improves both recall and precision.
- **Noise**: the agent over-flagged. Counts as a true false positive.
- **Catalog typo**: the agent malformed a defect ID (e.g. `def_def_pii_in_logs`). 
  This is a V1 schema-discipline failure; tool-use enforcement in V2 prevents it.

- **scn_001_pii_logging** / pm_agent / `def_unmeasurable_acceptance_criteria` / high
  > The two acceptance criteria (200ms p-latency and 5000 RPS) lack percentile definitions and test conditions. 'Under 200ms' — at what percentile (p50, p99, p999)? Under what load profile? Without these ...

- **scn_001_pii_logging** / pm_agent / `def_missing_success_metric` / high
  > There are no business-level success metrics defined — e.g., fraud detection rate, false positive rate, dollar value of fraud prevented. Technical SLOs alone do not tell us whether the product is worki...

- **scn_001_pii_logging** / pm_agent / `def_no_rollback_plan` / high
  > No rollback procedure is documented in the artifacts. For a real-time fraud scoring service integrated into payment flows, the absence of a defined rollback plan is a material risk. This must be addre...

- **scn_001_pii_logging** / pm_agent / `def_sla_math_broken` / medium
  > The 200ms latency SLO assumes upstream and downstream dependency SLAs have been reviewed, but no dependency SLA documentation appears in the artifact list. If any critical-path dependency has a p99 la...

- **scn_001_pii_logging** / pm_agent / `def_no_circuit_breaker` / medium
  > The data flow diagram is listed as an artifact but no design decision around circuit breakers or fallback behavior on critical-path dependencies is referenced. At 5000 RPS, a dependency outage without...

- **scn_001_pii_logging** / pm_agent / `def_missing_cost_estimate` / medium
  > No cost estimate is referenced in the artifact list. A service designed for 5000 sustained RPS with real-time scoring will carry significant compute and data costs. A cost estimate or ceiling must be ...

- **scn_001_pii_logging** / pm_agent / `def_no_cost_ceiling` / medium
  > If the service uses autoscaling to meet the 5000 RPS target, there is no documented maximum cost cap or compute ceiling. Uncapped autoscaling at this throughput poses budget risk.

- **scn_001_pii_logging** / engineering_lead_agent / `def_no_timeout` / blocking
  > No timeout configurations are documented for synchronous calls in the data flow diagram. At 5000 RPS, a slow upstream dependency without timeouts will cascade and violate the 200ms SLA acceptance crit...

- **scn_001_pii_logging** / engineering_lead_agent / `def_no_circuit_breaker` / blocking
  > No circuit breaker or fallback strategy is defined for critical-path dependencies (e.g., feature store, rules engine). A dependency failure at 5000 RPS will cause full service outage with no degraded-...

- **scn_001_pii_logging** / engineering_lead_agent / `def_sla_math_broken` / high
  > The design doc does not enumerate dependency SLAs (p99 latencies) or provide a latency budget breakdown. Without this, the 200ms end-to-end target cannot be validated as achievable given all hops in t...

- **scn_001_pii_logging** / engineering_lead_agent / `def_single_point_of_failure` / high
  > The data flow diagram shows no redundancy plan for the scoring engine or feature store. At 5000 RPS sustained, a single-instance critical path component is an unacceptable reliability risk.

- **scn_001_pii_logging** / engineering_lead_agent / `def_no_backpressure` / high
  > No backpressure mechanism or queue depth limits are described for the high-throughput ingestion path. Under spike load beyond 5000 RPS, the system may cascade rather than shed load gracefully.

- **scn_001_pii_logging** / engineering_lead_agent / `def_no_rollback_plan` / high
  > No rollback procedure is documented. Given that fraud scoring is on the critical payment path, a bad model or config deployment without a rollback plan poses significant operational risk.

- **scn_001_pii_logging** / engineering_lead_agent / `def_missing_vendor_sla` / medium
  > If any third-party data enrichment or model inference vendors are used (not clearly excluded in the design doc), their SLA terms must be documented and factored into the latency and availability budge...

- **scn_001_pii_logging** / engineering_lead_agent / `def_no_audit_logging` / medium
  > Fraud scoring decisions are security-sensitive actions. The design doc does not describe audit logging for score decisions, model version used, or override events, which is required for forensics and ...

- **scn_001_pii_logging** / engineering_lead_agent / `def_no_cost_ceiling` / medium
  > No autoscaling cap or compute cost ceiling is defined. At 5000 RPS with potential burst traffic, unbounded autoscaling could produce runaway infrastructure costs.

- **scn_001_pii_logging** / engineering_lead_agent / `def_no_idempotency` / medium
  > The design does not specify idempotency guarantees for score request endpoints. Retry storms at high RPS without idempotency could result in duplicate fraud actions or state corruption.

- **scn_001_pii_logging** / security_privacy_agent / `def_missing_pci_scope_review` / blocking
  > Fraud scoring services frequently touch or proxy card data (PANs, BINs, transaction amounts). No PCI-DSS scope assessment is present in the design artifacts. This must be resolved before proceeding to...

- **scn_001_pii_logging** / security_privacy_agent / `def_no_audit_logging` / high
  > The design artifacts do not describe audit logging for security-sensitive actions such as model updates, score overrides, administrative access, or configuration changes. These must be captured with t...

- **scn_001_pii_logging** / security_privacy_agent / `def_gdpr_residency` / high
  > If EU subjects' transaction or identity data is processed, the design must document data residency controls. There is no mention of region pinning, replication restrictions, or residency guarantees in...

- **scn_001_pii_logging** / security_privacy_agent / `def_no_transfer_mechanism` / high
  > No legal mechanism (SCCs, adequacy decision, BCRs) is documented for any cross-border transfer of personal or financial data. If the service operates across jurisdictions, this is a blocking GDPR comp...

- **scn_001_pii_logging** / security_privacy_agent / `def_no_encryption_at_rest` / high
  > The design does not specify encryption-at-rest requirements for feature stores, model inputs/outputs caches, or any persistent data stores used by the fraud scoring service. Sensitive financial and id...

- **scn_001_pii_logging** / security_privacy_agent / `def_overbroad_iam` / medium
  > No IAM design is documented. Fraud scoring services require least-privilege access to data stores, model registries, and downstream systems. Without a defined IAM model, over-broad permissions are lik...

- **scn_001_pii_logging** / security_privacy_agent / `def_secrets_in_code` / medium
  > The design does not specify a secrets management solution (e.g., Vault, AWS Secrets Manager) for API keys, model endpoint credentials, or database passwords. Without this, there is risk of secrets bei...

- **scn_001_pii_logging** / finops_legal_agent / `def_no_cost_ceiling` / blocking
  > No maximum autoscaling cap is documented. At 5000 RPS sustained with burst potential, unbounded compute scaling creates uncontrolled cost exposure. A hard ceiling must be defined before approval.

- **scn_001_pii_logging** / finops_legal_agent / `def_missing_cost_estimate` / blocking
  > No cost estimate is present in the design artifacts for compute, storage, or data transfer at the stated 5000 RPS load target. A gated estimate is required at design stage.

- **scn_001_pii_logging** / finops_legal_agent / `def_missing_vendor_sla` / high
  > Design references third-party dependencies (implied by a real-time scoring pipeline) but no vendor SLA terms are documented. Any external model provider, enrichment service, or data vendor must have S...

- **scn_001_pii_logging** / finops_legal_agent / `def_missing_pci_scope_review` / blocking
  > Fraud scoring services frequently operate on or adjacent to payment card data. No PCI DSS scope assessment is present in the design artifacts. This must be resolved before design approval.

- **scn_001_pii_logging** / finops_legal_agent / `def_gdpr_residency` / high
  > The data flow diagram does not specify residency controls for EU transaction or cardholder data. If EU subjects are in scope, storage and processing regions must be declared and compliant.

- **scn_001_pii_logging** / finops_legal_agent / `def_no_transfer_mechanism` / high
  > No documented legal mechanism (SCCs, adequacy decision, BCRs) exists for any cross-border data transfer in the fraud scoring pipeline. Required before any EU or similarly regulated data is processed c...

- **scn_001_pii_logging** / finops_legal_agent / `def_no_egress_cost_model` / medium
  > The data flow diagram does not model cross-region egress costs. At 5000 RPS, even modest per-request data payloads can generate significant egress charges that are not accounted for in any visible cos...

- **scn_001_pii_logging** / finops_legal_agent / `def_def_pii_in_logs` / high
  > No log redaction policy is documented for a service that will process fraud-related transaction data likely containing PII. GDPR and equivalent regulations require this to be addressed at design time.

- **scn_001_pii_logging** / finops_legal_agent / `def_license_incompatible` / medium
  > No license inventory is present in the design artifacts. Fraud scoring models and ML libraries may carry AGPL, CC, or proprietary licenses that restrict commercial use. A license review is required be...

- **scn_002_vague_acceptance_criteria** / pm_agent / `def_missing_success_metric` / high
  > No quantitative success metric exists for this project. Without a baseline and a target, it is impossible to evaluate whether this initiative succeeded after launch. Add at minimum: current conversion...

- **scn_002_vague_acceptance_criteria** / engineering_lead_agent / `def_missing_success_metric` / blocking
  > No measurable success metrics are defined anywhere in the project state. There are no targets for conversion rate delta, p95 page load time, error rate, or any other quantifiable KPI. The project cann...

- **scn_002_vague_acceptance_criteria** / engineering_lead_agent / `def_missing_pci_scope_review` / high
  > This is a checkout flow and likely handles payment card data. No PCI DSS scope assessment is referenced in the artifacts. Before design is approved, the team must determine whether this service is in-...

- **scn_002_vague_acceptance_criteria** / engineering_lead_agent / `def_no_rollback_plan` / high
  > Only a PRD artifact is present at the design gate. There is no rollback plan documented. Checkout is a revenue-critical path; a rollback strategy must be defined before engineering begins.

- **scn_002_vague_acceptance_criteria** / security_privacy_agent / `def_missing_pci_scope_review` / blocking
  > This is a checkout improvement project that almost certainly touches payment card data flows, yet there is no PCI-DSS scope assessment documented in the artifacts. Before design can proceed, the team ...

- **scn_002_vague_acceptance_criteria** / security_privacy_agent / `def_no_audit_logging` / high
  > No mention of audit logging for security-sensitive checkout actions (payment attempts, address changes, coupon/discount applications, order confirmation). These events must be audit-logged with actor,...

- **scn_002_vague_acceptance_criteria** / security_privacy_agent / `def_pii_in_logs` / high
  > Checkout flows collect highly sensitive PII (name, address, email, phone, partial card data). The design does not address log redaction strategy. Without explicit controls, PAN, CVV fragments, or full...

- **scn_002_vague_acceptance_criteria** / security_privacy_agent / `def_no_log_retention` / medium
  > No log retention policy is defined. PCI-DSS requires audit logs to be retained for at least 12 months with 3 months immediately available. GDPR also constrains how long personal-data-bearing logs may ...

- **scn_002_vague_acceptance_criteria** / security_privacy_agent / `def_gdpr_residency` / high
  > If the checkout serves EU customers, customer PII and order data must remain within the EU or have explicit residency controls. The PRD does not document data residency requirements or any region-pinn...

- **scn_002_vague_acceptance_criteria** / security_privacy_agent / `def_no_transfer_mechanism` / high
  > No cross-border data transfer mechanism (SCCs, adequacy decision, BCRs) is documented. If payment processors, analytics providers, or CDN vendors process EU customer data outside the EU, a legal trans...

- **scn_002_vague_acceptance_criteria** / security_privacy_agent / `def_no_encryption_at_rest` / high
  > The design does not specify encryption-at-rest requirements for any data stores that will hold order data, customer PII, or payment tokens. Encryption-at-rest with managed key policies must be explici...

- **scn_002_vague_acceptance_criteria** / security_privacy_agent / `def_overbroad_iam` / medium
  > No IAM / access-control design is present. Checkout services should operate under least-privilege roles. Without a defined IAM boundary, there is risk of over-permissioned service accounts able to rea...

- **scn_002_vague_acceptance_criteria** / security_privacy_agent / `def_secrets_in_code` / medium
  > Integration with payment processors and third-party services will require API keys. The design must mandate secrets management (e.g., Vault, AWS Secrets Manager) and explicitly prohibit secrets in sou...

- **scn_002_vague_acceptance_criteria** / finops_legal_agent / `def_missing_success_metric` / blocking
  > No measurable success metric is defined. There is no conversion rate target, p-value threshold, revenue impact estimate, or latency target (e.g., LCP < Xms). Without these, cost justification and ROI ...

- **scn_002_vague_acceptance_criteria** / finops_legal_agent / `def_missing_cost_estimate` / high
  > No cost estimate is present in the artifact set for compute, third-party services, or infrastructure changes associated with checkout improvements. A design gate requires at least a rough order-of-mag...

- **scn_002_vague_acceptance_criteria** / finops_legal_agent / `def_no_cost_ceiling` / high
  > Checkout improvements may introduce autoscaling or increased compute demand during peak traffic. No cost ceiling or spend cap is documented, creating unbounded resource exposure during high-traffic ev...

- **scn_002_vague_acceptance_criteria** / finops_legal_agent / `def_missing_pci_scope_review` / blocking
  > This project modifies the checkout flow, which is likely in or adjacent to card data scope. No PCI DSS scope assessment or carve-out documentation is present in the artifact set. This is a mandatory c...

- **scn_002_vague_acceptance_criteria** / finops_legal_agent / `def_missing_vendor_sla` / medium
  > Checkout flows typically depend on payment processors and potentially A/B testing or analytics vendors. No vendor SLA terms are referenced in the available artifacts, creating unquantified third-party...

- **scn_003_synchronous_vendor_call_in_checkout** / pm_agent / `def_unmeasurable_acceptance_criteria` / blocking
  > Acceptance criterion 'AML screening completes before order confirmation' has no numeric threshold. What is the maximum acceptable AML screening latency? Without a number, this criterion cannot be test...

- **scn_003_synchronous_vendor_call_in_checkout** / pm_agent / `def_missing_vendor_sla` / high
  > No AML vendor SLA is referenced in the artifacts. If the external AML provider does not have a documented SLA, the p99 checkout latency target of 1.5s cannot be validated as achievable, and the compos...

- **scn_003_synchronous_vendor_call_in_checkout** / pm_agent / `def_no_rollback_plan` / medium
  > No rollback procedure is documented. Given that AML screening is gating order confirmation, a failed deployment must have a defined rollback path to avoid blocking all purchases.

- **scn_003_synchronous_vendor_call_in_checkout** / pm_agent / `def_missing_success_metric` / medium
  > There is no measurable business success metric (e.g., AML hit rate, false positive rate, orders screened per day). Acceptance criteria cover only latency; there is no way to evaluate whether the integ...

- **scn_003_synchronous_vendor_call_in_checkout** / engineering_lead_agent / `def_missing_vendor_sla` / high
  > The AML screening provider is referenced in the architecture but no SLA terms (p99 latency, availability) are documented. Without these, the latency acceptance criterion cannot be validated and operat...

- **scn_003_synchronous_vendor_call_in_checkout** / engineering_lead_agent / `def_no_idempotency` / high
  > There is no documented idempotency mechanism for AML screening requests. Network retries on timeout could trigger duplicate screenings, causing false positives or double-flagging customer orders.

- **scn_003_synchronous_vendor_call_in_checkout** / engineering_lead_agent / `def_single_point_of_failure` / high
  > The AML screening service appears as a single integration endpoint on the critical checkout path with no redundancy, failover region, or secondary provider documented in the architecture.

- **scn_003_synchronous_vendor_call_in_checkout** / engineering_lead_agent / `def_no_rollback_plan` / medium
  > No rollback procedure is documented for this release. If the AML integration introduces regressions in checkout, there is no defined path to revert without blocking orders or disabling screening entir...

- **scn_003_synchronous_vendor_call_in_checkout** / engineering_lead_agent / `def_no_audit_logging` / medium
  > AML screening decisions are security-sensitive and likely regulatory-sensitive actions. The architecture does not document audit logging of screening results, decisions, or overrides, which is typical...

- **scn_003_synchronous_vendor_call_in_checkout** / security_privacy_agent / `def_pii_in_logs` / blocking
  > AML screening workflows process highly sensitive PII (names, dates of birth, national IDs, addresses). No evidence of log redaction or masking controls in the architecture artifacts. PII written to lo...

- **scn_003_synchronous_vendor_call_in_checkout** / security_privacy_agent / `def_no_audit_logging` / blocking
  > AML screening decisions are security-sensitive and legally significant actions. The architecture artifacts provide no documentation of immutable audit logging for screening outcomes, manual overrides,...

- **scn_003_synchronous_vendor_call_in_checkout** / security_privacy_agent / `def_no_encryption_at_rest` / blocking
  > Architecture does not document encryption-at-rest for data stores holding AML screening results, customer PII, or watchlist match data. Given the sensitivity of financial crime data, encryption at res...

- **scn_003_synchronous_vendor_call_in_checkout** / security_privacy_agent / `def_gdpr_residency` / high
  > No data residency controls are documented. If EU customer data is processed through AML screening, the architecture must specify that data remains within the EU or identify approved transfer mechanism...

- **scn_003_synchronous_vendor_call_in_checkout** / security_privacy_agent / `def_no_transfer_mechanism` / high
  > The architecture does not document the legal mechanism for any cross-border transfer of PII to AML screening third-party services. Standard Contractual Clauses or Binding Corporate Rules must be in pl...

- **scn_003_synchronous_vendor_call_in_checkout** / security_privacy_agent / `def_missing_pci_scope_review` / high
  > AML screening occurs before order confirmation in the checkout flow, which likely processes payment card data. No PCI DSS scope assessment is documented. It must be confirmed whether AML service compo...

- **scn_003_synchronous_vendor_call_in_checkout** / security_privacy_agent / `def_overbroad_iam` / high
  > No IAM policy documentation is present in the architecture artifacts. Services interacting with AML screening data must operate under least-privilege roles. Overly broad IAM grants on watchlist data o...

- **scn_003_synchronous_vendor_call_in_checkout** / security_privacy_agent / `def_secrets_in_code` / high
  > No secrets management approach is documented for API keys used to call the AML screening provider. Architecture must explicitly specify a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault) a...

- **scn_003_synchronous_vendor_call_in_checkout** / security_privacy_agent / `def_no_log_retention` / medium
  > AML regulations typically require record retention of 5 years or more. No log or record retention policy is defined in the architecture. This must be explicitly specified to ensure compliance with AML...

- **scn_003_synchronous_vendor_call_in_checkout** / finops_legal_agent / `def_missing_vendor_sla` / blocking
  > The AML screening integration relies on a third-party vendor (implied by 'integration' scope), but no vendor SLA terms are documented in the artifacts. For a blocking synchronous checkout dependency, ...

- **scn_003_synchronous_vendor_call_in_checkout** / finops_legal_agent / `def_no_cost_ceiling` / high
  > No cost ceiling or per-transaction cost cap is defined for AML screening API calls. At checkout volume, unbounded per-call vendor pricing without a cap creates material unit economics risk. A maximum ...

- **scn_003_synchronous_vendor_call_in_checkout** / finops_legal_agent / `def_missing_cost_estimate` / high
  > No cost estimate is present in the architecture artifacts for the AML vendor API consumption, infrastructure hosting, or data transfer costs. A gate-level cost estimate is required before architecture...

- **scn_003_synchronous_vendor_call_in_checkout** / finops_legal_agent / `def_no_transfer_mechanism` / blocking
  > AML screening involves processing customer financial and identity data. If the AML vendor processes data cross-border (e.g., EU customer data sent to a US-based vendor), a documented legal transfer me...

- **scn_003_synchronous_vendor_call_in_checkout** / finops_legal_agent / `def_gdpr_residency` / high
  > No data residency controls are documented for the AML screening flow. EU customer PII and financial data transmitted to an external AML vendor must have residency constraints explicitly addressed, par...

- **scn_003_synchronous_vendor_call_in_checkout** / finops_legal_agent / `def_no_egress_cost_model` / medium
  > If AML screening involves sending customer transaction data to an external vendor endpoint in a different region, there is no egress cost model documented. At scale, per-GB egress fees for outbound AP...

- **scn_003_synchronous_vendor_call_in_checkout** / finops_legal_agent / `def_missing_pci_scope_review` / blocking
  > AML screening at checkout may occur in proximity to card data flows. No PCI DSS scope assessment is documented to confirm whether the AML integration component is in-scope for cardholder data environm...

- **scn_004_unbounded_compute_for_reconciliation** / pm_agent / `def_unmeasurable_acceptance_criteria` / high
  > The acceptance criterion '100% record coverage' lacks a testable definition. What constitutes a record? How is coverage measured and by whom? What is the tolerance for late-arriving records? This need...

- **scn_004_unbounded_compute_for_reconciliation** / pm_agent / `def_unmeasurable_acceptance_criteria` / medium
  > 'Reconciliation completes by 6am ET' is directionally measurable but needs clarification: does this apply every business day, calendar day, or only on trading days? What is the acceptable failure rate...

- **scn_004_unbounded_compute_for_reconciliation** / pm_agent / `def_missing_success_metric` / medium
  > There are no post-launch success metrics defined beyond the two operational acceptance criteria. The project should define how business value will be measured after go-live (e.g., reduction in manual ...

- **scn_004_unbounded_compute_for_reconciliation** / engineering_lead_agent / `def_unmeasurable_acceptance_criteria` / high
  > Acceptance criterion '100% record coverage' lacks a testable definition. What constitutes a record? How is coverage measured and verified? What is the tolerance for late-arriving records? This needs a...

- **scn_004_unbounded_compute_for_reconciliation** / engineering_lead_agent / `def_no_timeout` / high
  > Design doc v3 does not document timeout configurations for synchronous upstream calls (e.g., to source-of-record payment systems). With a hard 6am ET deadline, an unbounded synchronous call can cause ...

- **scn_004_unbounded_compute_for_reconciliation** / engineering_lead_agent / `def_no_circuit_breaker` / high
  > No circuit breaker or fallback pattern documented for critical-path dependencies such as ledger systems or external clearing house APIs. A degraded upstream during the reconciliation window with no fa...

- **scn_004_unbounded_compute_for_reconciliation** / engineering_lead_agent / `def_no_rollback_plan` / high
  > No rollback procedure is documented. For a financial settlement system, a failed or partially completed reconciliation run requires a clearly defined rollback or compensating transaction strategy to a...

- **scn_004_unbounded_compute_for_reconciliation** / engineering_lead_agent / `def_no_idempotency` / high
  > Reconciliation mutation operations (e.g., marking records as reconciled, posting adjustments) are not documented as idempotent. Retries on failure without idempotency guarantees risk duplicate settlem...

- **scn_004_unbounded_compute_for_reconciliation** / engineering_lead_agent / `def_sla_math_broken` / medium
  > The 6am ET completion SLA has not been validated against documented upstream dependency SLAs. If clearing house or core banking system SLAs allow delivery windows that overlap with the reconciliation ...

- **scn_004_unbounded_compute_for_reconciliation** / engineering_lead_agent / `def_missing_vendor_sla` / medium
  > Design references external clearing or payment network integrations but no vendor SLA terms are documented. Without contractual SLA commitments from third parties on the critical path, the 6am ET acce...

- **scn_004_unbounded_compute_for_reconciliation** / engineering_lead_agent / `def_no_audit_logging` / medium
  > Financial reconciliation actions (adjustments, overrides, record status changes) are security- and compliance-sensitive operations. The design does not document audit logging for these actions, which ...

- **scn_004_unbounded_compute_for_reconciliation** / engineering_lead_agent / `def_missing_pci_scope_review` / medium
  > Settlement reconciliation systems frequently touch payment card transaction data. No PCI scope assessment is referenced in the design artifacts. If card data flows through this system, PCI DSS scoping...

- **scn_004_unbounded_compute_for_reconciliation** / engineering_lead_agent / `def_no_backpressure` / medium
  > High-volume end-of-day record ingestion for reconciliation is not documented with backpressure controls or queue depth limits. Without these, consumer overload could delay or corrupt the reconciliatio...

- **scn_004_unbounded_compute_for_reconciliation** / engineering_lead_agent / `def_single_point_of_failure` / medium
  > The design does not document redundancy for the reconciliation orchestrator or job scheduler. A single-instance scheduler failing during the nightly run window would cause a total miss of the 6am ET S...

- **scn_004_unbounded_compute_for_reconciliation** / security_privacy_agent / `def_missing_pci_scope_review` / blocking
  > This is a settlement reconciliation system that almost certainly handles card transaction data, yet no PCI-DSS scope assessment is documented in design_doc_v3. Before any architecture can be approved,...

- **scn_004_unbounded_compute_for_reconciliation** / security_privacy_agent / `def_no_encryption_at_rest` / blocking
  > The design document does not specify encryption-at-rest controls for reconciliation data stores. Settlement data containing financial records and potentially PANs or account identifiers must be encryp...

- **scn_004_unbounded_compute_for_reconciliation** / security_privacy_agent / `def_no_audit_logging` / blocking
  > No audit logging strategy is described for security-sensitive actions such as record access, reconciliation overrides, manual adjustments, or privileged user operations. Financial systems require immu...

- **scn_004_unbounded_compute_for_reconciliation** / security_privacy_agent / `def_pii_in_logs` / high
  > The design does not address log redaction controls. Settlement reconciliation systems routinely log transaction identifiers, account references, and other PII. Without explicit masking or tokenization...

- **scn_004_unbounded_compute_for_reconciliation** / security_privacy_agent / `def_no_log_retention` / high
  > No log retention policy is defined in the design artifacts. Financial and payment systems typically require 12-month online retention with additional archival periods under PCI-DSS and SOX. Retention ...

- **scn_004_unbounded_compute_for_reconciliation** / security_privacy_agent / `def_overbroad_iam` / high
  > The design does not document IAM roles or permission boundaries for reconciliation service components. Settlement systems accessing financial datastores must operate under least-privilege IAM policies...

- **scn_004_unbounded_compute_for_reconciliation** / security_privacy_agent / `def_gdpr_residency` / high
  > The design does not address data residency requirements. If any EU customer payment or account data is processed, explicit controls ensuring data does not leave designated regions must be implemented ...

- **scn_004_unbounded_compute_for_reconciliation** / security_privacy_agent / `def_secrets_in_code` / high
  > The design does not describe a secrets management strategy for credentials used to connect to financial data sources, APIs, or partner systems. There is no mention of a vault solution, secret rotation...

- **scn_004_unbounded_compute_for_reconciliation** / security_privacy_agent / `def_no_transfer_mechanism` / medium
  > If reconciliation involves cross-border data flows (e.g., settlement data from EU counterparties processed outside the EU), no legal transfer mechanism such as SCCs or BCRs is documented. This must be...

- **scn_004_unbounded_compute_for_reconciliation** / finops_legal_agent / `def_missing_pci_scope_review` / blocking
  > This project involves daily settlement reconciliation, which strongly implies handling of payment card transaction data. No PCI DSS scope assessment is referenced in the design artifacts. If card data...

- **scn_004_unbounded_compute_for_reconciliation** / finops_legal_agent / `def_no_egress_cost_model` / medium
  > Settlement reconciliation systems typically aggregate data from multiple regions or counterparties. No egress cost model is present in the design documentation. Cross-region data movement costs can be...

- **scn_004_unbounded_compute_for_reconciliation** / finops_legal_agent / `def_missing_vendor_sla` / high
  > The design document does not enumerate third-party vendor dependencies or confirm SLA terms are in place. For a time-sensitive financial process with a hard 6am ET deadline, any upstream vendor withou...

- **scn_004_unbounded_compute_for_reconciliation** / finops_legal_agent / `def_gdpr_residency` / high
  > Settlement data may include EU account holder or transaction data. No data residency controls or geographic boundary documentation is present in the design artifacts. If EU personal data is involved, ...

- **scn_004_unbounded_compute_for_reconciliation** / finops_legal_agent / `def_no_transfer_mechanism` / high
  > If EU financial or personal data crosses borders as part of reconciliation processing, a documented legal transfer mechanism (SCCs, adequacy decision, or BCRs) is required. None is referenced in curre...

- **scn_005_cross_border_data_residency** / pm_agent / `def_unmeasurable_acceptance_criteria` / blocking
  > Acceptance criteria state 'Profile reads under 50ms globally' but do not specify percentile (p50, p95, p99), measurement location (client-side vs. server-side), or what 'globally' means in terms of te...

- **scn_005_cross_border_data_residency** / pm_agent / `def_unmeasurable_acceptance_criteria` / blocking
  > 'Strong consistency on writes' is not a measurable acceptance criterion. It must specify the consistency model (e.g., linearizability, read-your-writes), the scope (single region vs. global), and how ...

- **scn_005_cross_border_data_residency** / pm_agent / `def_missing_success_metric` / high
  > There are no business-level success metrics defined — e.g., reduction in profile lookup errors, downstream service adoption rate, or customer-impacting incident reduction. Acceptance criteria cover te...

- **scn_005_cross_border_data_residency** / pm_agent / `def_no_egress_cost_model` / high
  > The replication_topology artifact implies cross-region data replication for global reads, but there is no documented egress cost model. At scale, cross-region replication costs can be substantial and ...

- **scn_005_cross_border_data_residency** / pm_agent / `def_missing_cost_estimate` / high
  > No cost estimate is present in the design artifacts for compute, storage, or replication infrastructure required to achieve sub-50ms global reads. A design gate should include at least an order-of-mag...

- **scn_005_cross_border_data_residency** / pm_agent / `def_sla_math_broken` / medium
  > A 50ms global read SLA requires all upstream and infrastructure dependencies (DNS, load balancers, data stores, network) to be accounted for in a latency budget. No latency budget breakdown is visible...

- **scn_005_cross_border_data_residency** / pm_agent / `def_no_rollback_plan` / medium
  > No rollback procedure is documented for this service. Given that it is a global profile service with replication state, rollback is non-trivial and must be designed explicitly before the build gate.

- **scn_005_cross_border_data_residency** / engineering_lead_agent / `def_no_timeout` / high
  > Design doc v2 does not specify timeout configurations for synchronous calls between profile service and its dependencies. Without explicit timeouts, latency spikes in downstream services can cascade a...

- **scn_005_cross_border_data_residency** / engineering_lead_agent / `def_no_circuit_breaker` / high
  > No circuit breaker or fallback strategy is documented for critical-path dependencies. A failure in a downstream service (e.g., identity or entitlement service) will propagate fully to profile reads gl...

- **scn_005_cross_border_data_residency** / engineering_lead_agent / `def_sla_math_broken` / blocking
  > The acceptance criterion of sub-50ms global reads combined with strong consistency on writes is likely unachievable given speed-of-light constraints and typical consensus round-trips across global reg...

- **scn_005_cross_border_data_residency** / engineering_lead_agent / `def_no_idempotency` / high
  > Strong consistency on writes is an acceptance criterion but no idempotency guarantees are specified for mutating profile endpoints. Retries under failure can result in duplicate writes or data corrupt...

- **scn_005_cross_border_data_residency** / engineering_lead_agent / `def_no_rollback_plan` / high
  > No rollback procedure is documented for the global profile service. Given the distributed replication topology, a failed deployment could leave profile data in an inconsistent state across regions wit...

- **scn_005_cross_border_data_residency** / engineering_lead_agent / `def_no_egress_cost_model` / medium
  > The replication topology implies significant cross-region data flow for a global service, but no egress cost model is provided. At scale, inter-region replication costs can be substantial and must be ...

- **scn_005_cross_border_data_residency** / engineering_lead_agent / `def_no_audit_logging` / high
  > Profile data is PII-sensitive. The design does not document audit logging for security-sensitive actions such as reads of full profiles, writes, and administrative access to customer data.

- **scn_005_cross_border_data_residency** / engineering_lead_agent / `def_single_point_of_failure` / high
  > The replication topology does not clearly document redundancy for coordination components (e.g., consensus leaders, write coordinators). Loss of a single coordinator could make strong consistency writ...

- **scn_005_cross_border_data_residency** / security_privacy_agent / `def_no_encryption_at_rest` / high
  > The design documentation does not explicitly confirm encryption at rest for customer profile data stores across all regions. Given the global nature of the service, every regional replica must have en...

- **scn_005_cross_border_data_residency** / security_privacy_agent / `def_no_audit_logging` / high
  > There is no mention of audit logging for security-sensitive actions such as profile reads, writes, admin access, or bulk exports. GDPR and general security best practices require a durable audit trail...

- **scn_005_cross_border_data_residency** / security_privacy_agent / `def_pii_in_logs` / high
  > The design does not specify PII redaction or masking policies for application and diagnostic logs. Customer profile data (names, emails, addresses, etc.) must not appear in logs without explicit redac...

- **scn_005_cross_border_data_residency** / security_privacy_agent / `def_no_log_retention` / medium
  > No log retention policy is defined for any log groups associated with this service. GDPR requires that personal data not be retained longer than necessary; log groups must have defined and enforced re...

- **scn_005_cross_border_data_residency** / security_privacy_agent / `def_overbroad_iam` / medium
  > The design does not document IAM roles or access policies for the profile data stores. Given this service holds PII at global scale, least-privilege access control design must be explicitly defined be...

- **scn_005_cross_border_data_residency** / security_privacy_agent / `def_missing_pci_scope_review` / medium
  > A 'Global Customer Profile Service' may co-locate or later incorporate payment-related identifiers. If any payment card data or cardholder data could be stored in profiles, a PCI-DSS scope assessment ...

- **scn_005_cross_border_data_residency** / finops_legal_agent / `def_no_egress_cost_model` / high
  > A globally replicated customer profile service will generate substantial cross-region data egress. No egress cost model is present in the design artifacts, making total cost of ownership undefined at ...

- **scn_005_cross_border_data_residency** / finops_legal_agent / `def_no_cost_ceiling` / high
  > Global replication topology with no stated autoscaling or compute cost cap creates unbounded spend exposure. A maximum cost ceiling must be established before proceeding.

- **scn_005_cross_border_data_residency** / finops_legal_agent / `def_missing_cost_estimate` / high
  > No cost estimate is provided for the global replication infrastructure, storage, or inter-region traffic. A verified cost estimate is required at the design gate.

- **scn_005_cross_border_data_residency** / finops_legal_agent / `def_missing_vendor_sla` / medium
  > The replication topology likely relies on one or more third-party cloud or database vendors. No vendor SLA terms are referenced, making the composite SLA target unverifiable from a contractual standpo...

- **scn_005_cross_border_data_residency** / finops_legal_agent / `def_sla_math_broken` / medium
  > Without documented vendor SLAs for each region and replication layer, it cannot be confirmed that the composite availability supports the strong consistency and sub-50ms global read targets in the acc...

- **scn_005_cross_border_data_residency** / finops_legal_agent / `def_no_audit_logging` / medium
  > A customer profile service handling PII must ensure all access and mutation events are audit-logged. No audit logging requirement or control is documented in the design artifacts.

- **scn_006_mid_sprint_scope_addition** / pm_agent / `def_unmeasurable_acceptance_criteria` / medium
  > 'ACH payouts complete within 1 business day' lacks a testable definition: what counts as 'complete' (initiated, settled, confirmed by bank)? What is the measurement methodology and the acceptable fail...

- **scn_006_mid_sprint_scope_addition** / pm_agent / `def_missing_success_metric` / medium
  > The project has two operational acceptance criteria (latency and throughput) but no business-level success metric, such as payout success rate, failed payout rate, or adoption target. Without this, it...

- **scn_006_mid_sprint_scope_addition** / pm_agent / `def_no_idempotency` / high
  > There is no mention of idempotency guarantees for payout mutation endpoints in the acceptance criteria or PRD artifacts. For a financial payouts API, duplicate payout submissions due to retries are a ...

- **scn_006_mid_sprint_scope_addition** / pm_agent / `def_missing_vendor_sla` / high
  > ACH payouts depend on third-party banking rails or payment processors. There is no documented vendor SLA for the underlying ACH network or processor. Without this, the '1 business day' acceptance crit...

- **scn_006_mid_sprint_scope_addition** / engineering_lead_agent / `def_no_idempotency` / blocking
  > Payout mutation endpoints (ACH initiation, retry) have no documented idempotency key mechanism. Duplicate submissions due to retries or network failures could result in double payouts, which is a crit...

- **scn_006_mid_sprint_scope_addition** / engineering_lead_agent / `def_no_circuit_breaker` / blocking
  > No circuit breaker or fallback documented for the ACH rail dependency (e.g., Nacha/bank partner). If the downstream ACH processor degrades, cascading failures will breach the 1 business day SLA and po...

- **scn_006_mid_sprint_scope_addition** / engineering_lead_agent / `def_no_timeout` / high
  > Synchronous calls to the ACH processor and any internal ledger service show no configured timeout values in the sprint plan or PRD. Under load this will cause thread exhaustion and violate the 500 RPS...

- **scn_006_mid_sprint_scope_addition** / engineering_lead_agent / `def_missing_vendor_sla` / blocking
  > The ACH processor/bank partner SLA terms are not referenced in any artifact. Without a documented vendor SLA, the composite 1 business day payout acceptance criterion cannot be validated as achievable...

- **scn_006_mid_sprint_scope_addition** / engineering_lead_agent / `def_sla_math_broken` / high
  > Composite SLA math has not been demonstrated. The 1 business day ACH completion depends on upstream bank cut-off windows, internal processing latency, and retry budgets. No dependency SLA roll-up is d...

- **scn_006_mid_sprint_scope_addition** / engineering_lead_agent / `def_no_rollback_plan` / high
  > No rollback or incident recovery procedure is documented for the payout release. Financial systems require an explicit rollback plan covering in-flight ACH transactions, ledger state reconciliation, a...

- **scn_006_mid_sprint_scope_addition** / engineering_lead_agent / `def_missing_pci_scope_review` / blocking
  > Payouts API handles financial account data and payment flows. No PCI DSS scope assessment or cardholder data environment (CDE) boundary analysis is referenced in any artifact. This is a mandatory revi...

- **scn_006_mid_sprint_scope_addition** / engineering_lead_agent / `def_no_audit_logging` / high
  > Security-sensitive actions such as payout initiation, approval, and cancellation require immutable audit logs. No audit logging design or requirement is documented in the PRD or sprint plan.

- **scn_006_mid_sprint_scope_addition** / engineering_lead_agent / `def_no_backpressure` / high
  > At 500 RPS, the payout ingestion pipeline must have defined queue depth limits and backpressure mechanisms to prevent unbounded memory growth and protect downstream ACH processor from being overwhelme...

- **scn_006_mid_sprint_scope_addition** / engineering_lead_agent / `def_no_cost_ceiling` / medium
  > No autoscaling cost ceiling or compute cap is documented. At 500 RPS with financial workloads, runaway scaling events could produce unbounded infrastructure costs without a max capacity guard.

- **scn_006_mid_sprint_scope_addition** / security_privacy_agent / `def_missing_pci_scope_review` / blocking
  > Payouts API v1 processes financial transactions (ACH payouts) involving account and routing numbers, which may constitute sensitive financial data subject to PCI-DSS or NACHA compliance requirements. ...

- **scn_006_mid_sprint_scope_addition** / security_privacy_agent / `def_no_encryption_at_rest` / high
  > No artifact documents encryption-at-rest controls for the sensitive financial data stores (account numbers, routing numbers, payout records) that will be created by this API. Encryption at rest must b...

- **scn_006_mid_sprint_scope_addition** / security_privacy_agent / `def_no_audit_logging` / high
  > Security-sensitive actions such as payout initiation, approval, cancellation, and access to account data require comprehensive audit logging. No audit logging specification is present in the reviewed ...

- **scn_006_mid_sprint_scope_addition** / security_privacy_agent / `def_pii_in_logs` / high
  > Payouts API will process PII including bank account numbers, routing numbers, and payee identity data. There is no documented log redaction or masking strategy to prevent PII from being written to app...

- **scn_006_mid_sprint_scope_addition** / security_privacy_agent / `def_no_log_retention` / medium
  > No log retention policy is defined in any artifact. Financial services data typically requires defined retention periods (e.g., 7 years under various regulations). Log group retention must be specifie...

- **scn_006_mid_sprint_scope_addition** / security_privacy_agent / `def_gdpr_residency` / high
  > If any EU-based payees are supported, personal and financial data must remain within the EU or have documented residency controls. No data residency controls or geographic restrictions are mentioned i...

- **scn_006_mid_sprint_scope_addition** / security_privacy_agent / `def_no_transfer_mechanism` / high
  > Cross-border transfer of EU payee data (names, account details) requires a documented legal mechanism such as SCCs or BCRs under GDPR. No such mechanism is referenced in any artifact.

- **scn_006_mid_sprint_scope_addition** / security_privacy_agent / `def_secrets_in_code` / high
  > No secrets management strategy is documented for API keys, ACH processor credentials, or internal service credentials. Risk of credentials being committed to source or hardcoded in configuration files...

- **scn_006_mid_sprint_scope_addition** / security_privacy_agent / `def_overbroad_iam` / medium
  > No IAM role definition or least-privilege access policy is documented for the Payouts API service identity. Financial data services require tightly scoped IAM roles to limit blast radius in the event ...

- **scn_006_mid_sprint_scope_addition** / security_privacy_agent / `def_no_idempotency` / high
  > Payout initiation is a mutating financial operation. No idempotency key or duplicate-detection mechanism is documented, creating risk of duplicate ACH transactions and financial loss for users.

- **scn_006_mid_sprint_scope_addition** / finops_legal_agent / `def_no_cost_ceiling` / blocking
  > No maximum cost cap or autoscaling ceiling is documented. At 500 RPS with ACH processing, unbounded compute and transaction fee exposure is a material financial risk that must be capped before build p...

- **scn_006_mid_sprint_scope_addition** / finops_legal_agent / `def_missing_cost_estimate` / blocking
  > No complete cost estimate for infrastructure, ACH network fees, and third-party vendor costs is present in the artifacts. A payouts system with payment network fees requires a full unit economics mode...

- **scn_006_mid_sprint_scope_addition** / finops_legal_agent / `def_missing_vendor_sla` / high
  > ACH processing relies on a payment network or banking partner, but no vendor SLA terms are documented in the provided artifacts. Without contractual SLA coverage, the 1 business day payout commitment ...

- **scn_006_mid_sprint_scope_addition** / finops_legal_agent / `def_missing_pci_scope_review` / blocking
  > Payouts API v1 handles financial disbursements potentially linked to card or bank account data. No PCI DSS scope assessment or cardholder data environment (CDE) boundary review is referenced in any ar...

- **scn_006_mid_sprint_scope_addition** / finops_legal_agent / `def_no_transfer_mechanism` / high
  > No documentation of cross-border data transfer mechanisms (SCCs, adequacy decisions, or equivalent) is present. If payouts involve EU-resident payees, lack of a legal transfer mechanism creates regula...

- **scn_006_mid_sprint_scope_addition** / finops_legal_agent / `def_no_egress_cost_model` / medium
  > If payout processing spans regions (e.g., EU/US), there is no egress cost model documented. At scale, unmodeled cross-region data transfer costs can significantly distort unit economics.

- **scn_007_ledger_service_circular_dependency** / pm_agent / `def_unmeasurable_acceptance_criteria` / blocking
  > The acceptance criterion 'Transactions enriched with fraud signal before settlement' has no numeric threshold, success rate, or testable definition. What percentage of transactions must be enriched? W...

- **scn_007_ledger_service_circular_dependency** / pm_agent / `def_scope_too_broad` / high
  > The release bundles ledger query performance optimization with a fraud service refactor into a single gate. These are distinct feature areas with different risk profiles, teams, and dependencies. Bund...

- **scn_007_ledger_service_circular_dependency** / pm_agent / `def_missing_success_metric` / high
  > There is no post-launch success metric defined beyond the two acceptance criteria. How will we know the Unified Ledger Service is delivering business value 30 or 60 days after release? No baseline is ...

- **scn_007_ledger_service_circular_dependency** / pm_agent / `def_no_rollback_plan` / high
  > Neither the architecture doc nor the release plan documents a rollback procedure. Given that this service touches settlement flows, a failed deployment without a tested rollback path represents unacce...

- **scn_007_ledger_service_circular_dependency** / pm_agent / `def_sla_math_broken` / medium
  > The 100ms query latency target is stated but no dependency SLA breakdown is provided. If the fraud service enrichment is on the critical path to query response, its latency budget must be explicitly c...

- **scn_007_ledger_service_circular_dependency** / pm_agent / `def_no_dependency_impact` / medium
  > The fraud service refactor is listed as an artifact but its dependency impact on the ledger service is not documented. It is unclear whether the refactor introduces new API contracts, versioning requi...

- **scn_007_ledger_service_circular_dependency** / engineering_lead_agent / `def_no_timeout` / blocking
  > The fraud service refactor doc does not specify timeout configurations for synchronous calls between the Ledger Service and Fraud Service. Given the acceptance criterion that ledger queries must retur...

- **scn_007_ledger_service_circular_dependency** / engineering_lead_agent / `def_no_circuit_breaker` / blocking
  > Transactions must be enriched with fraud signal before settlement, but no circuit breaker or fallback strategy is documented for the Fraud Service dependency. If the Fraud Service degrades, the Ledger...

- **scn_007_ledger_service_circular_dependency** / engineering_lead_agent / `def_sla_math_broken` / high
  > The composite 100ms latency target for ledger queries has not been validated against the Fraud Service's documented response SLA. If the Fraud Service targets, say, 80ms p99, there is insufficient hea...

- **scn_007_ledger_service_circular_dependency** / engineering_lead_agent / `def_no_idempotency` / high
  > The architecture documents do not address idempotency for transaction mutation endpoints in the Ledger Service. In retry scenarios (network failure, timeout fallback), duplicate transactions could be ...

- **scn_007_ledger_service_circular_dependency** / engineering_lead_agent / `def_no_rollback_plan` / high
  > The q2_release_plan does not document a rollback procedure for the Unified Ledger Service. Given that this service handles financial transactions and settlement, an inability to roll back a bad deploy...

- **scn_007_ledger_service_circular_dependency** / engineering_lead_agent / `def_no_backpressure` / medium
  > No backpressure or queue depth limits are specified for high-throughput transaction ingestion. Under load spikes, unbounded queuing could cause memory pressure or unbounded latency growth, violating t...

- **scn_007_ledger_service_circular_dependency** / engineering_lead_agent / `def_missing_pci_scope_review` / medium
  > The Ledger Service processes financial transactions and potentially touches card or payment data. There is no PCI scope assessment referenced in any artifact. This must be resolved before production r...

- **scn_007_ledger_service_circular_dependency** / engineering_lead_agent / `def_no_audit_logging` / medium
  > Security-sensitive actions such as transaction settlement, ledger mutations, and fraud signal overrides are not documented as having audit logging. For a financial ledger system this is a compliance a...

- **scn_007_ledger_service_circular_dependency** / engineering_lead_agent / `def_unchanged_acceptance_criteria` / medium
  > The fraud_service_refactor introduces a new synchronous dependency on the critical query path, but the acceptance criteria have not been updated to reflect measurable fraud enrichment latency budgets ...

- **scn_007_ledger_service_circular_dependency** / security_privacy_agent / `def_missing_pci_scope_review` / blocking
  > The Unified Ledger Service processes financial transactions and settlements but no PCI-DSS scope assessment is documented. Any card data touching this ledger requires formal scoping before architectur...

- **scn_007_ledger_service_circular_dependency** / security_privacy_agent / `def_no_audit_logging` / blocking
  > No audit logging specification is present for security-sensitive ledger mutations (transaction creation, settlement, adjustments). Financial ledger changes must be immutably audit-logged with actor id...

- **scn_007_ledger_service_circular_dependency** / security_privacy_agent / `def_no_encryption_at_rest` / high
  > Architecture documents do not confirm encryption-at-rest for the ledger data store. Given the financial and potentially PII-bearing nature of transaction records, AES-256 or equivalent encryption at r...

- **scn_007_ledger_service_circular_dependency** / security_privacy_agent / `def_pii_in_logs` / high
  > Fraud signal enrichment involves account identifiers and behavioral data. No log redaction or masking policy is referenced in the fraud_service_refactor_doc or architecture, creating risk of PII leaki...

- **scn_007_ledger_service_circular_dependency** / security_privacy_agent / `def_gdpr_residency` / high
  > The architecture does not specify data residency controls for EU account holders. If the ledger or fraud enrichment service replicates data cross-region without residency boundaries, GDPR Article 44+ ...

- **scn_007_ledger_service_circular_dependency** / security_privacy_agent / `def_no_transfer_mechanism` / high
  > No legal transfer mechanism (SCCs, Binding Corporate Rules, adequacy decision) is documented for any cross-border data flows involving EU transaction or account data. This must be resolved before go-l...

- **scn_007_ledger_service_circular_dependency** / security_privacy_agent / `def_overbroad_iam` / high
  > IAM roles for ledger service components are not defined in the architecture artifacts. Without least-privilege role definitions, there is significant risk of over-permissioned service accounts accessi...

- **scn_007_ledger_service_circular_dependency** / security_privacy_agent / `def_no_log_retention` / medium
  > No log retention policy is specified for ledger or fraud service logs. Financial regulations (e.g., PCI-DSS Requirement 10.7) mandate minimum 12-month retention with 3 months immediately available.

- **scn_007_ledger_service_circular_dependency** / security_privacy_agent / `def_secrets_in_code` / medium
  > The fraud_service_refactor_doc references API integration with a fraud signal provider but does not document secrets management strategy. There is no confirmation that credentials are stored in a vaul...

- **scn_007_ledger_service_circular_dependency** / finops_legal_agent / `def_missing_pci_scope_review` / blocking
  > The Unified Ledger Service handles transaction settlement data, which likely includes card data. No PCI DSS scope assessment is referenced in any artifact. This must be resolved before architecture ca...

- **scn_007_ledger_service_circular_dependency** / finops_legal_agent / `def_no_cost_ceiling` / high
  > No compute or autoscaling cost ceiling is documented. A ledger service with fraud enrichment on every transaction can have highly variable throughput; without a cap, cloud spend is unbounded.

- **scn_007_ledger_service_circular_dependency** / finops_legal_agent / `def_missing_cost_estimate` / high
  > No cost estimate is present in the reviewed artifacts for the unified ledger or the fraud service refactor. Gate policy requires a cost estimate prior to architecture approval.

- **scn_007_ledger_service_circular_dependency** / finops_legal_agent / `def_missing_vendor_sla` / high
  > The fraud service refactor document references enrichment dependencies but does not document SLA terms for any third-party fraud signal vendors. Composite SLA cannot be validated without these terms.

- **scn_007_ledger_service_circular_dependency** / finops_legal_agent / `def_sla_math_broken` / high
  > Acceptance criteria require transactions to be enriched with fraud signal before settlement with ledger queries under 100ms. Without documented fraud vendor SLAs, the composite latency and availabilit...

- **scn_007_ledger_service_circular_dependency** / finops_legal_agent / `def_no_egress_cost_model` / medium
  > If the fraud enrichment service or ledger replicas operate across regions, cross-region egress costs are not modeled. Transaction-level volumes can produce significant egress charges.

- **scn_007_ledger_service_circular_dependency** / finops_legal_agent / `def_gdpr_residency` / high
  > The ledger service processes financial transaction data that may include EU customer records. No data residency controls or regional boundary documentation is present in the artifacts.

- **scn_007_ledger_service_circular_dependency** / finops_legal_agent / `def_no_transfer_mechanism` / high
  > If EU transaction or customer data is shared with the fraud enrichment service or any third-party vendor across borders, no documented legal transfer mechanism (SCCs, adequacy decision, etc.) is evide...

- **scn_007_ledger_service_circular_dependency** / finops_legal_agent / `def_license_incompatible` / medium
  > No license review is documented for libraries introduced in the fraud service refactor. Ledger and fraud processing components in a commercial financial product must confirm no copyleft or restrictive...

- **scn_008_clean_idempotency_key_rollout** / pm_agent / `def_unmeasurable_acceptance_criteria` / medium
  > The acceptance criterion 'Zero increase in error rate during rollout' lacks a numeric baseline and measurement window. What is the current error rate, over what time period will it be measured, and wh...

- **scn_008_clean_idempotency_key_rollout** / pm_agent / `def_missing_success_metric` / medium
  > The acceptance criteria define operational guardrails (latency, error rate, deduplication window) but there is no business-level success metric. How will we know this feature is delivering value post-...

- **scn_008_clean_idempotency_key_rollout** / pm_agent / `None` / low
  > The 24-hour deduplication window is stated as an acceptance criterion but the design doc should explicitly document what happens at window expiration — does a new refund attempt proceed, and is this b...

- **scn_008_clean_idempotency_key_rollout** / engineering_lead_agent / `def_no_timeout` / high
  > The design doc must specify timeout values for all synchronous calls into the idempotency key store (e.g., Redis/DB lookup). Without a defined timeout, a slow dependency will block the refund request ...

- **scn_008_clean_idempotency_key_rollout** / engineering_lead_agent / `def_no_circuit_breaker` / high
  > No circuit breaker or fallback strategy is documented for the idempotency key store. If the store becomes unavailable, the design must define whether requests fail open (risk of duplicate refunds) or ...

- **scn_008_clean_idempotency_key_rollout** / engineering_lead_agent / `def_no_rollback_plan` / high
  > No rollback procedure is documented. Given that idempotency key state and refund state must remain consistent, a rollback is non-trivial. The design must specify how to safely disable the feature flag...

- **scn_008_clean_idempotency_key_rollout** / engineering_lead_agent / `def_single_point_of_failure` / medium
  > The idempotency key store appears to be a single-region, single-node dependency on the critical refund path. The design should document replication topology, failover behavior, and whether the store i...

- **scn_008_clean_idempotency_key_rollout** / engineering_lead_agent / `def_no_audit_logging` / medium
  > Idempotency key lookups and cache hits that suppress a refund execution are security-sensitive actions (a suppressed refund is a financial outcome). The design must confirm these events are written to...

- **scn_008_clean_idempotency_key_rollout** / engineering_lead_agent / `def_no_cost_ceiling` / low
  > The cost estimate covers baseline load but does not specify a maximum cap on the idempotency key store scaling (e.g., Redis memory limit or DynamoDB provisioned capacity ceiling). Under a traffic spik...

- **scn_008_clean_idempotency_key_rollout** / security_privacy_agent / `def_pii_in_logs` / high
  > Idempotency key storage and lookup operations may log request payloads containing cardholder data or PII (customer ID, amount, account references). Design doc v2 must explicitly mandate redaction or t...

- **scn_008_clean_idempotency_key_rollout** / security_privacy_agent / `def_missing_pci_scope_review` / blocking
  > The Refunds API is in the payment flow. Introducing an idempotency key store that caches refund request/response payloads may bring a new data store into PCI scope. No PCI scope assessment is referenc...

- **scn_008_clean_idempotency_key_rollout** / security_privacy_agent / `def_no_encryption_at_rest` / high
  > The idempotency key store (likely Redis or a database table) will hold refund request context including amounts and customer references. Design doc must confirm encryption at rest is enforced with man...

- **scn_008_clean_idempotency_key_rollout** / security_privacy_agent / `def_no_audit_logging` / high
  > Idempotency key creation, cache hits (duplicate request detection), and key expiry are security-sensitive events. No mention of audit logging for these operations is present. Duplicate suppression eve...

- **scn_008_clean_idempotency_key_rollout** / security_privacy_agent / `def_overbroad_iam` / medium
  > The service identity for the idempotency layer must be granted least-privilege access to the key store. Design doc should specify exact IAM permissions scoped only to the idempotency key namespace, no...

- **scn_008_clean_idempotency_key_rollout** / security_privacy_agent / `def_no_log_retention` / medium
  > No log retention policy is defined for the idempotency service logs. Given PCI-DSS requires 12-month log retention (3 months immediately accessible), a retention policy must be documented and enforced...

- **scn_008_clean_idempotency_key_rollout** / security_privacy_agent / `def_gdpr_residency` / medium
  > If EU customers submit refund requests, their request context stored in the idempotency key store must remain within EU boundaries. Design doc does not address data residency controls or region pinnin...

- **scn_008_clean_idempotency_key_rollout** / finops_legal_agent / `def_no_cost_ceiling` / high
  > The cost estimate artifact is present, but the design does not specify a maximum cap on the idempotency key store (e.g., Redis or database table). Without a TTL enforcement ceiling and a storage size ...

- **scn_008_clean_idempotency_key_rollout** / finops_legal_agent / `def_missing_vendor_sla` / medium
  > If the idempotency key store relies on a managed third-party cache or database service (e.g., ElastiCache, managed Redis, or similar), no vendor SLA terms are referenced in the design artifacts. The c...

- **scn_008_clean_idempotency_key_rollout** / finops_legal_agent / `def_missing_pci_scope_review` / high
  > Refunds API handling implies proximity to cardholder and transaction data. The design artifacts do not include a PCI DSS scope assessment confirming whether idempotency key storage and logging pipelin...

- **scn_008_clean_idempotency_key_rollout** / finops_legal_agent / `def_no_egress_cost_model` / medium
  > The design does not document whether idempotency key lookups or replication cross region boundaries (e.g., for high availability). If cross-region replication is used for the key store, egress costs a...

- **scn_008_clean_idempotency_key_rollout** / finops_legal_agent / `def_gdpr_residency` / medium
  > Idempotency keys may embed or reference customer or transaction identifiers constituting personal data under GDPR. The design does not confirm that key storage is residency-controlled for EU customers...

- **scn_009_clean_observability_dashboard** / pm_agent / `def_unmeasurable_acceptance_criteria` / medium
  > The acceptance criterion 'Covers 100% of pipeline stages currently emitting metrics' is partially measurable but relies on an unstated baseline. The design doc must explicitly enumerate which pipeline...

- **scn_009_clean_observability_dashboard** / pm_agent / `def_missing_success_metric` / medium
  > There is no business-level success metric defined. Render time and SSO access are hygiene criteria, not success outcomes. The project should define at least one outcome metric, e.g., mean time to dete...

- **scn_009_clean_observability_dashboard** / pm_agent / `def_missing_cost_estimate` / medium
  > A license quote artifact exists but there is no overall cost estimate for infrastructure, ingestion, or ongoing operational spend. At design gate, a cost estimate with a ceiling should be present, esp...

- **scn_009_clean_observability_dashboard** / pm_agent / `def_missing_vendor_sla` / low
  > The license quote implies a third-party vendor is involved. No vendor SLA terms are referenced in the artifacts. If the dashboard depends on an external metrics or visualization platform, its SLA must...

- **scn_009_clean_observability_dashboard** / pm_agent / `def_no_rollback_plan` / low
  > No rollback plan is documented. For an observability dashboard going to ops, a rollback procedure should be defined in case a bad deploy removes visibility into the settlement pipeline during an incid...

- **scn_009_clean_observability_dashboard** / engineering_lead_agent / `def_no_timeout` / high
  > Design doc does not specify timeout configurations for dashboard data fetches against pipeline metric sources. Slow upstream sources could cause dashboard render to exceed the 3-second acceptance crit...

- **scn_009_clean_observability_dashboard** / engineering_lead_agent / `def_no_circuit_breaker` / high
  > No circuit breaker or fallback pattern is described for dependencies on pipeline stage metric endpoints. If one stage emitter becomes unavailable, the entire dashboard query path may fail rather than ...

- **scn_009_clean_observability_dashboard** / engineering_lead_agent / `def_sla_math_broken` / medium
  > The 3-second render SLA is a composite of all pipeline stage metric queries. The design doc does not show per-dependency latency budgets or confirm that the sum of upstream p99 latencies is compatible...

- **scn_009_clean_observability_dashboard** / engineering_lead_agent / `def_single_point_of_failure` / medium
  > The design appears to route all metric aggregation through a single collection layer with no redundancy described. If this component fails, the ops team loses full visibility into the settlement pipel...

- **scn_009_clean_observability_dashboard** / engineering_lead_agent / `def_no_audit_logging` / medium
  > Dashboard access to settlement pipeline metrics represents access to financially sensitive operational data. No audit logging of who accessed the dashboard or ran queries is described. This is a gap f...

- **scn_009_clean_observability_dashboard** / engineering_lead_agent / `def_no_log_retention` / medium
  > Metrics inventory and design doc do not define a retention policy for collected pipeline metrics or dashboard query logs. Without defined retention, storage costs are unbounded and compliance obligati...

- **scn_009_clean_observability_dashboard** / engineering_lead_agent / `def_overbroad_iam` / medium
  > The design doc does not specify the IAM role scope for the dashboard service account accessing pipeline metric stores. Read-only least-privilege access scoped to specific metric namespaces must be exp...

- **scn_009_clean_observability_dashboard** / engineering_lead_agent / `def_unmeasurable_acceptance_criteria` / low
  > Acceptance criterion 'Covers 100% of pipeline stages currently emitting metrics' depends on an authoritative count of emitting stages being fixed at gate time. If the metrics_inventory is not version-...

- **scn_009_clean_observability_dashboard** / engineering_lead_agent / `def_missing_vendor_sla` / low
  > A license quote artifact is present but no vendor SLA terms are referenced in the design doc. If the dashboard relies on a commercial visualization or metrics platform, its availability SLA must be co...

- **scn_009_clean_observability_dashboard** / security_privacy_agent / `def_pii_in_logs` / high
  > Settlement pipeline metrics may include customer account identifiers, transaction references, or other PII. The design doc does not address redaction or masking of PII before it reaches the dashboard ...

- **scn_009_clean_observability_dashboard** / security_privacy_agent / `def_no_audit_logging` / high
  > The design does not document audit logging for security-sensitive actions such as dashboard access, permission changes, or data exports. Given the financial nature of settlement data, all access to se...

- **scn_009_clean_observability_dashboard** / security_privacy_agent / `def_no_encryption_at_rest` / high
  > No mention of encryption at rest for the metrics store or any cached dashboard data. Settlement pipeline data likely contains sensitive financial information and must be encrypted at rest using AES-25...

- **scn_009_clean_observability_dashboard** / security_privacy_agent / `def_overbroad_iam` / medium
  > The acceptance criteria allow ops team access via existing SSO but no least-privilege IAM design is documented. The dashboard should define role-based access controls limiting visibility to appropriat...

- **scn_009_clean_observability_dashboard** / security_privacy_agent / `def_no_log_retention` / medium
  > No log retention policy is defined for dashboard access logs or pipeline metric logs. Regulatory requirements for financial data (e.g., PCI-DSS requires 12-month retention with 3 months online) must b...

- **scn_009_clean_observability_dashboard** / security_privacy_agent / `def_missing_pci_scope_review` / blocking
  > This is a settlement pipeline observability system. Settlement pipelines frequently touch or reference payment card data flows. No PCI-DSS scope assessment is included in the design artifacts. A forma...

- **scn_009_clean_observability_dashboard** / security_privacy_agent / `def_gdpr_residency` / medium
  > The design does not specify data residency controls. If the pipeline processes EU customer transactions, metrics and any derived data must remain within EU boundaries or have documented adequacy/trans...

- **scn_009_clean_observability_dashboard** / security_privacy_agent / `def_no_transfer_mechanism` / medium
  > No cross-border data transfer mechanism is documented. If metrics aggregation or dashboard hosting spans jurisdictions, Standard Contractual Clauses or equivalent legal mechanisms must be in place and...

- **scn_009_clean_observability_dashboard** / finops_legal_agent / `def_no_cost_ceiling` / blocking
  > No maximum cost cap or autoscaling ceiling is documented in the design artifacts. An observability dashboard ingesting settlement pipeline metrics can accumulate unbounded storage and query costs, esp...

- **scn_009_clean_observability_dashboard** / finops_legal_agent / `def_missing_cost_estimate` / blocking
  > The license_quote artifact is present but no overall cost estimate covering compute, storage, data retention, and egress is submitted. The gate requires a complete cost estimate; a partial vendor quot...

- **scn_009_clean_observability_dashboard** / finops_legal_agent / `def_missing_vendor_sla` / high
  > The license_quote references a third-party vendor, but no SLA terms (uptime guarantee, support tiers, incident response windows) are included in the artifacts. For a settlement pipeline observability ...

- **scn_009_clean_observability_dashboard** / finops_legal_agent / `def_no_egress_cost_model` / high
  > The metrics_inventory does not document whether pipeline stages span multiple regions or clouds. If metrics are pulled cross-region into a central dashboard, egress costs could be significant and must...

- **scn_009_clean_observability_dashboard** / finops_legal_agent / `def_missing_pci_scope_review` / high
  > This is a settlement pipeline observability tool. Settlement data frequently involves card transaction metadata. No PCI DSS scope assessment is referenced in any artifact. If any metric label, trace I...

- **scn_009_clean_observability_dashboard** / finops_legal_agent / `def_no_log_retention` / medium
  > The design does not specify a retention policy for dashboard query logs or metric data. Undefined retention creates both unbounded storage cost exposure and potential regulatory non-compliance for fin...

- **scn_009_clean_observability_dashboard** / finops_legal_agent / `def_license_incompatible` / medium
  > The license_quote does not specify whether the quoted license permits use in a financial services production environment or restricts redistribution/embedding of the dashboard in internal portals. Lic...

- **scn_010_clean_db_index_addition** / pm_agent / `def_missing_cost_estimate` / medium
  > No cost estimate is present in the artifacts for storage overhead or index build compute costs. The acceptance criterion caps storage at 8% of table size, but there is no dollar figure attached to tha...

- **scn_010_clean_db_index_addition** / pm_agent / `None` / medium
  > The acceptance criteria do not specify how or when p99 will be measured post-deployment (e.g., measurement window, traffic volume, specific query set). Without a defined measurement protocol, it will ...

- **scn_010_clean_db_index_addition** / pm_agent / `None` / low
  > The zero-downtime index build criterion lacks a definition of 'downtime.' Clarify whether this means zero replication lag spikes, zero query errors, zero degradation above a threshold, or something el...

- **scn_010_clean_db_index_addition** / pm_agent / `None` / low
  > The rollback plan artifact is listed but no summary of its trigger conditions or RTO target is visible in the project state. Confirm the rollback plan specifies who authorizes rollback, under what obs...

- **scn_010_clean_db_index_addition** / engineering_lead_agent / `def_no_rollback_plan` / medium
  > A rollback_plan artifact is listed but the design doc must explicitly reference it and confirm the rollback procedure has been tested or dry-run. Presence of the artifact alone does not confirm operat...

- **scn_010_clean_db_index_addition** / engineering_lead_agent / `None` / high
  > The acceptance criterion 'index build completes with zero downtime' is not backed by a documented mechanism (e.g., CONCURRENTLY build on Postgres, online DDL on MySQL, shadow index strategy). The desi...

- **scn_010_clean_db_index_addition** / engineering_lead_agent / `def_unmeasurable_acceptance_criteria` / medium
  > The 8% storage overhead criterion lacks a baseline table size and measurement methodology. Without a stated baseline (e.g., current table size in GB) and a defined measurement point (post-build, stead...

- **scn_010_clean_db_index_addition** / engineering_lead_agent / `None` / medium
  > The query_performance_analysis should confirm that the p99 target of sub-100ms was validated against production-representative data distribution and cardinality, not just synthetic test data. Index se...

- **scn_010_clean_db_index_addition** / engineering_lead_agent / `None` / low
  > No mention of index maintenance overhead during high write throughput periods. The design should address write amplification impact and whether index creation or ongoing maintenance could cause lock c...

- **scn_010_clean_db_index_addition** / engineering_lead_agent / `def_no_audit_logging` / low
  > If the transaction table contains financial or sensitive records, any schema change operation (DDL) should be captured in an audit log. Confirm DDL audit logging is enabled for the target database.

- **scn_010_clean_db_index_addition** / security_privacy_agent / `def_no_audit_logging` / high
  > The design document does not mention audit logging for DDL operations (index creation/drops) on the transaction table. Schema changes on tables containing financial transaction data are security-sensi...

- **scn_010_clean_db_index_addition** / security_privacy_agent / `def_pii_in_logs` / high
  > The query performance analysis artifact likely captures slow-query logs or EXPLAIN ANALYZE output. If the transaction table contains cardholder names, account numbers, or other PII, raw query samples ...

- **scn_010_clean_db_index_addition** / security_privacy_agent / `def_missing_pci_scope_review` / blocking
  > The project targets a 'transaction table' but contains no mention of a PCI-DSS scope assessment. If this table stores or references card data (PANs, CVVs, expiry dates), the index build process, any t...

- **scn_010_clean_db_index_addition** / security_privacy_agent / `def_no_encryption_at_rest` / high
  > New indexes on a transaction table may use temporary disk space and secondary index storage. The design does not confirm that both the index structures and any temporary build artifacts inherit or exp...

- **scn_010_clean_db_index_addition** / security_privacy_agent / `def_overbroad_iam` / medium
  > No IAM or database role controls are described for who can execute the index DDL. The migration or automation account should hold only the minimum privilege needed (e.g., CREATE INDEX on the specific ...

- **scn_010_clean_db_index_addition** / security_privacy_agent / `def_no_log_retention` / medium
  > Performance analysis and DDL execution logs generated during the index build have no described retention policy. For regulatory environments (GDPR, PCI-DSS), log retention windows must be explicitly d...

- **scn_010_clean_db_index_addition** / security_privacy_agent / `def_gdpr_residency` / medium
  > If the transaction table contains EU data subjects' personal data, the design must confirm that index build operations, temporary tablespaces, and any read replicas used during performance testing do ...

- **scn_010_clean_db_index_addition** / finops_legal_agent / `def_no_cost_ceiling` / medium
  > The design doc does not specify a cost ceiling for index build compute resources. If the index build triggers autoscaling or consumes burst compute capacity, there is no documented maximum spend cap t...

- **scn_010_clean_db_index_addition** / finops_legal_agent / `def_missing_cost_estimate` / medium
  > No cost estimate is provided for the additional storage overhead (up to 8% of table size) or the index build I/O costs. At scale, persistent storage additions and I/O spikes during build can carry mea...

- **scn_010_clean_db_index_addition** / finops_legal_agent / `def_no_egress_cost_model` / low
  > If the transaction table is replicated across regions or the index build triggers cross-region replication sync, there is no egress cost model documented. This should be confirmed as in-region only or...
