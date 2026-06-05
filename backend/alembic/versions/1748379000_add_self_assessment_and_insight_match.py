"""1748379000_add_self_assessment_and_insight_match

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-27 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create self_assessments table
    op.create_table(
        "self_assessments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("video_id", UUID(as_uuid=True), sa.ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("hook_score", sa.Integer(), nullable=True),
        sa.Column("structure_score", sa.Integer(), nullable=True),
        sa.Column("clarity_score", sa.Integer(), nullable=True),
        sa.Column("cta_score", sa.Integer(), nullable=True),
        sa.Column("energy_score", sa.Integer(), nullable=True),
        sa.Column("pacing_score", sa.Integer(), nullable=True),
        sa.Column("visual_score", sa.Integer(), nullable=True),
        sa.Column("best_part", sa.Text(), nullable=True),
        sa.Column("would_change", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Add creator_match columns to insights table
    op.add_column("insights", sa.Column("creator_match", sa.String(20), nullable=True))
    op.add_column("insights", sa.Column("creator_match_note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("insights", "creator_match_note")
    op.drop_column("insights", "creator_match")
    op.drop_table("self_assessments")
