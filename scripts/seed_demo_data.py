"""Seed the 6 synthetic benchmark patients and insurance plans into Postgres.

Idempotent — safe to re-run (patients/plans are upserted by the repositories). This only seeds
`patients` and `insurance_plans`; `authorization_cases` rows are created on demand via
`POST /api/v1/cases` when a demo user picks a benchmark patient from the dashboard, because
`CreateAuthorizationCaseService` requires the patient and plan to already exist.

Run: python scripts/seed_demo_data.py  (requires DATABASE_URL, or defaults to local dev Postgres)
"""

from __future__ import annotations

from healthflow_domain.entities import InsurancePlan, Patient
from healthflow_domain.identifiers import PatientId, PlanId
from healthflow_infrastructure.database import create_db_engine, create_session_factory
from healthflow_infrastructure.repositories import PostgresUnitOfWork
from healthflow_infrastructure.simulators import ALL_BENCHMARK_FIXTURES


def seed() -> None:
    engine = create_db_engine()
    session_factory = create_session_factory(engine)
    uow = PostgresUnitOfWork(session_factory)

    with uow:
        for fixture in ALL_BENCHMARK_FIXTURES.values():
            patient_id = PatientId(fixture.patient.patient_id)
            uow.patients.save(
                Patient(
                    id=patient_id,
                    name_reference=fixture.patient.name_reference,
                    ehr_reference=fixture.patient.ehr_reference,
                    is_synthetic=fixture.patient.is_synthetic,
                )
            )
            uow.insurance_plans.save(
                InsurancePlan(
                    id=PlanId(fixture.coverage.plan_id),
                    patient_id=patient_id,
                    insurer_reference=fixture.coverage.insurer_name,
                    # Matches the synthesis convention in AgentTools.get_insurance_plan
                    # (packages/application/src/healthflow_application/tools.py).
                    plan_type="PPO"
                    if fixture.coverage.in_network
                    else "OUT_OF_NETWORK",
                    member_reference=f"MEM-{fixture.patient.patient_id.upper()}",
                )
            )
        uow.commit()

    print(
        f"Seeded {len(ALL_BENCHMARK_FIXTURES)} synthetic patients and insurance plans."
    )


if __name__ == "__main__":
    seed()
