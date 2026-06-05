"""1748378400_make_youtube_video_id_nullable

Revision ID: a1b2c3d4e5f6
Revises: e3671d97d897
Create Date: 2025-05-27 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9f3e90ef09bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("videos", "youtube_video_id", existing_type=sa.String(20), nullable=True)


def downgrade() -> None:
    op.alter_column("videos", "youtube_video_id", existing_type=sa.String(20), nullable=False)
