from sqlalchemy import Column, ForeignKey, Index, Integer, Table, Text, text

from .base import metadata

resumes = Table(
    "resumes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("title", Text, nullable=False),
    Column("content", Text, nullable=False),
    Column("file_path", Text),
    Column("file_type", Text),
    Column("analysis_result", Text),
    Column("tailored_result", Text),
    Column("parent_resume_id", ForeignKey("resumes.id")),
    Column("version_label", Text),
    Column("target_job_title", Text),
    # Kept as an identifier rather than a second FK to avoid a cyclic DDL graph:
    # job_applications.resume_id is the canonical database constraint.
    Column("application_id", Integer),
    Column("status", Text, server_default=text("'active'")),
    Column("source_type", Text, server_default=text("'manual'")),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

job_applications = Table(
    "job_applications",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("company", Text, nullable=False),
    Column("job_title", Text, nullable=False),
    Column("status", Text, server_default=text("'已投递'")),
    Column("city", Text),
    Column("salary_min", Integer),
    Column("salary_max", Integer),
    Column("notes", Text),
    Column("applied_at", Text, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", Text, server_default=text("CURRENT_TIMESTAMP")),
    Column("deleted_at", Text),
    Column("jd_text", Text),
    Column("source_url", Text),
    Column("channel", Text),
    Column("resume_id", ForeignKey("resumes.id")),
    Column("priority", Integer, server_default=text("0")),
    Column("contact_name", Text),
    Column("contact_info", Text),
    Column("next_action_at", Text),
    Column("interview_at", Text),
    Column("deadline_at", Text),
    Column("rejection_reason", Text),
    Column("offer_details", Text),
    Column("created_by", Text, server_default=text("'user'")),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

job_matches = Table(
    "job_matches",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("resume_id", ForeignKey("resumes.id"), nullable=False),
    Column("job_title", Text, nullable=False),
    Column("match_score", Integer),
    Column("analysis", Text),
    Column("application_id", ForeignKey("job_applications.id")),
    Column("jd_text", Text),
    Column("details_json", Text),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

Index("idx_resumes_application", resumes.c.application_id)
Index("idx_applications_user_status", job_applications.c.user_id, job_applications.c.status)
Index("idx_applications_next_action", job_applications.c.next_action_at)
Index("idx_job_matches_application", job_matches.c.application_id)
Index("idx_job_matches_user_created", job_matches.c.user_id, job_matches.c.created_at)
