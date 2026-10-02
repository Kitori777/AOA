from __future__ import annotations

from AOA.core.optimization.models import Job


def sequence_mt(jobs: list[Job]) -> list[Job]:
    return sorted(jobs, key=lambda job: (job.deadline, job.processing_time, job.job_id))


def sequence_mo(jobs: list[Job]) -> list[Job]:
    return sorted(jobs, key=lambda job: (job.processing_time, job.deadline, job.job_id))


def sequence_mzo(jobs: list[Job]) -> list[Job]:
    return sorted(jobs, key=lambda job: (-job.processing_time, job.deadline, job.job_id))


def sequence_slack(jobs: list[Job]) -> list[Job]:
    return sorted(jobs, key=lambda job: (job.deadline - job.processing_time, job.deadline, job.job_id))


def sequence_cr(jobs: list[Job]) -> list[Job]:
    return sorted(
        jobs,
        key=lambda job: (job.deadline / max(job.processing_time, 1e-9), job.deadline, job.job_id),
    )


def sequence_edd_spt(jobs: list[Job]) -> list[Job]:
    return sequence_mt(jobs)


def sequence_spt_edd(jobs: list[Job]) -> list[Job]:
    return sequence_mo(jobs)


def sequence_lpt_edd(jobs: list[Job]) -> list[Job]:
    return sequence_mzo(jobs)
