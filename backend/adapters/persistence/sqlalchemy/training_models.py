from sqlalchemy import Column, Float, ForeignKey, Index, Integer, Table, Text, text

from .base import metadata

interviews = Table(
    "interviews",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("resume_id", Integer),
    Column("job_title", Text, nullable=False),
    Column("conversation", Text),
    Column("score", Integer),
    Column("feedback", Text),
    Column("source_session_id", Text),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

practice_records = Table(
    "practice_records",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, server_default=text("1")),
    Column("category", Text),
    Column("question", Text),
    Column("answer", Text),
    Column("correct_count", Integer),
    Column("total_count", Integer),
    Column("score", Integer),
    Column("feedback", Text),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

audio_records = Table(
    "audio_records",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, server_default=text("1")),
    Column("transcript", Text),
    Column("audio_file", Text),
    Column("duration", Float),
    Column("analysis_result", Text),
    Column("score", Integer),
    Column("metrics", Text),
    Column("feedback", Text),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

interview_sessions = Table(
    "interview_sessions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, nullable=False),
    Column("application_id", ForeignKey("job_applications.id")),
    Column("resume_id", ForeignKey("resumes.id")),
    Column("job_title", Text, nullable=False),
    Column("mode", Text),
    Column("status", Text, server_default=text("'active'")),
    Column("current_stage", Text),
    Column("conversation_json", Text),
    Column("score", Integer),
    Column("feedback", Text),
    Column("started_at", Text, server_default=text("CURRENT_TIMESTAMP")),
    Column("completed_at", Text),
    Column("created_at", Text, server_default=text("CURRENT_TIMESTAMP")),
    Column("updated_at", Text, server_default=text("CURRENT_TIMESTAMP")),
)

Index("idx_interviews_user_created", interviews.c.user_id, interviews.c.created_at)
Index(
    "idx_practice_records_user_created",
    practice_records.c.user_id,
    practice_records.c.created_at,
)
Index("idx_audio_records_user_created", audio_records.c.user_id, audio_records.c.created_at)
Index("idx_interview_sessions_application", interview_sessions.c.application_id)
Index(
    "idx_interview_sessions_user_status",
    interview_sessions.c.user_id,
    interview_sessions.c.status,
)
