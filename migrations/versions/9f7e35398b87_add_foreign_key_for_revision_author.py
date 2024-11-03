"""Add foreign key for revision_author

Revision ID: 9f7e35398b87
Revises: dfbe1de0090c
Create Date: 2024-11-03 17:44:10.778596

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f7e35398b87'
down_revision = 'dfbe1de0090c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('prompt', schema=None) as batch_op:
        batch_op.create_foreign_key(batch_op.f('fk_prompt_revision_author_id_user'), 'user', ['revision_author_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('prompt', schema=None) as batch_op:
        batch_op.drop_constraint(batch_op.f('fk_prompt_revision_author_id_user'), type_='foreignkey')

    # ### end Alembic commands ###
