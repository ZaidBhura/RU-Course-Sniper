"""catalog schema

Revision ID: 0001
Revises:
Create Date: 2026-09-30

Advisor milestone 1: public course catalog from the SOC API, in the `advisor`
schema. Not tenant-scoped (public data). Downgrade drops every catalog table;
the data can be rebuilt by re-running `python -m advisor.ingest`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('core_code',
    sa.Column('code', sa.String(length=16), nullable=False),
    sa.Column('description', sa.String(length=256), server_default='', nullable=False),
    sa.PrimaryKeyConstraint('code', name=op.f('pk_core_code')),
    schema='advisor'
    )
    op.create_table('course',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('course_string', sa.String(length=16), nullable=False),
    sa.Column('supplement_code', sa.String(length=4), server_default='', nullable=False),
    sa.Column('school_code', sa.String(length=2), nullable=False),
    sa.Column('subject_code', sa.String(length=3), nullable=False),
    sa.Column('course_number', sa.String(length=3), nullable=False),
    sa.Column('title', sa.String(length=256), server_default='', nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_course')),
    sa.UniqueConstraint('course_string', 'supplement_code', name=op.f('uq_course_course_string')),
    schema='advisor'
    )
    op.create_index(op.f('ix_advisor_course_school_code'), 'course', ['school_code', 'subject_code'], unique=False, schema='advisor')
    op.create_table('instructor',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('soc_name', sa.String(length=128), nullable=False),
    sa.Column('normalized_name', sa.String(length=128), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_instructor')),
    sa.UniqueConstraint('normalized_name', name=op.f('uq_instructor_normalized_name')),
    schema='advisor'
    )
    op.create_table('term',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('year', sa.SmallInteger(), nullable=False),
    sa.Column('term', sa.SmallInteger(), nullable=False),
    sa.Column('campus', sa.String(length=4), nullable=False),
    sa.Column('last_ingested_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('course_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('section_count', sa.Integer(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_term')),
    sa.UniqueConstraint('year', 'term', 'campus', name=op.f('uq_term_year')),
    schema='advisor'
    )
    op.create_table('course_offering',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('term_id', sa.Integer(), nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=256), server_default='', nullable=False),
    sa.Column('expanded_title', sa.String(length=512), server_default='', nullable=False),
    sa.Column('school_description', sa.String(length=256), server_default='', nullable=False),
    sa.Column('subject_description', sa.String(length=256), server_default='', nullable=False),
    sa.Column('level', sa.String(length=2), server_default='', nullable=False),
    sa.Column('credits', sa.Numeric(precision=4, scale=1), nullable=True),
    sa.Column('credits_code', sa.String(length=16), server_default='', nullable=False),
    sa.Column('prereq_raw', sa.Text(), server_default='', nullable=False),
    sa.Column('prereq_tree', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('prereq_parse_ok', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('prereq_parse_error', sa.Text(), nullable=True),
    sa.Column('synopsis_url', sa.String(length=512), server_default='', nullable=False),
    sa.Column('course_notes', sa.Text(), server_default='', nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['advisor.course.id'], name=op.f('fk_course_offering_course_id_course'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['term_id'], ['advisor.term.id'], name=op.f('fk_course_offering_term_id_term'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_course_offering')),
    sa.UniqueConstraint('term_id', 'course_id', name=op.f('uq_course_offering_term_id')),
    schema='advisor'
    )
    op.create_index(op.f('ix_advisor_course_offering_course_id'), 'course_offering', ['course_id'], unique=False, schema='advisor')
    op.create_table('offering_core_code',
    sa.Column('offering_id', sa.Integer(), nullable=False),
    sa.Column('core_code', sa.String(length=16), nullable=False),
    sa.ForeignKeyConstraint(['core_code'], ['advisor.core_code.code'], name=op.f('fk_offering_core_code_core_code_core_code')),
    sa.ForeignKeyConstraint(['offering_id'], ['advisor.course_offering.id'], name=op.f('fk_offering_core_code_offering_id_course_offering'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('offering_id', 'core_code', name=op.f('pk_offering_core_code')),
    schema='advisor'
    )
    op.create_index(op.f('ix_advisor_offering_core_code_core_code'), 'offering_core_code', ['core_code'], unique=False, schema='advisor')
    op.create_table('section',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('offering_id', sa.Integer(), nullable=False),
    sa.Column('index_number', sa.String(length=8), nullable=False),
    sa.Column('section_number', sa.String(length=8), server_default='', nullable=False),
    sa.Column('open_status', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('course_type', sa.String(length=4), server_default='', nullable=False),
    sa.Column('campus_code', sa.String(length=8), server_default='', nullable=False),
    sa.Column('exam_code', sa.String(length=4), server_default='', nullable=False),
    sa.Column('final_exam', sa.String(length=128), server_default='', nullable=False),
    sa.Column('cross_listed', sa.String(length=512), server_default='', nullable=False),
    sa.Column('notes', sa.Text(), server_default='', nullable=False),
    sa.Column('eligibility', sa.Text(), server_default='', nullable=False),
    sa.Column('subtitle', sa.String(length=256), server_default='', nullable=False),
    sa.ForeignKeyConstraint(['offering_id'], ['advisor.course_offering.id'], name=op.f('fk_section_offering_id_course_offering'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_section')),
    sa.UniqueConstraint('offering_id', 'index_number', name=op.f('uq_section_offering_id')),
    schema='advisor'
    )
    op.create_index(op.f('ix_advisor_section_index_number'), 'section', ['index_number'], unique=False, schema='advisor')
    op.create_table('meeting',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('section_id', sa.Integer(), nullable=False),
    sa.Column('day', sa.String(length=2), server_default='', nullable=False),
    sa.Column('start_min', sa.SmallInteger(), nullable=True),
    sa.Column('end_min', sa.SmallInteger(), nullable=True),
    sa.Column('campus_name', sa.String(length=64), server_default='', nullable=False),
    sa.Column('campus_abbrev', sa.String(length=16), server_default='', nullable=False),
    sa.Column('building', sa.String(length=16), server_default='', nullable=False),
    sa.Column('room', sa.String(length=16), server_default='', nullable=False),
    sa.Column('mode_code', sa.String(length=8), server_default='', nullable=False),
    sa.Column('mode_desc', sa.String(length=64), server_default='', nullable=False),
    sa.ForeignKeyConstraint(['section_id'], ['advisor.section.id'], name=op.f('fk_meeting_section_id_section'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_meeting')),
    schema='advisor'
    )
    op.create_index(op.f('ix_advisor_meeting_section_id'), 'meeting', ['section_id'], unique=False, schema='advisor')
    op.create_table('section_instructor',
    sa.Column('section_id', sa.Integer(), nullable=False),
    sa.Column('instructor_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['instructor_id'], ['advisor.instructor.id'], name=op.f('fk_section_instructor_instructor_id_instructor'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['section_id'], ['advisor.section.id'], name=op.f('fk_section_instructor_section_id_section'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('section_id', 'instructor_id', name=op.f('pk_section_instructor')),
    schema='advisor'
    )
    op.create_index(op.f('ix_advisor_section_instructor_instructor_id'), 'section_instructor', ['instructor_id'], unique=False, schema='advisor')


def downgrade() -> None:
    op.drop_index(op.f('ix_advisor_section_instructor_instructor_id'), table_name='section_instructor', schema='advisor')
    op.drop_table('section_instructor', schema='advisor')
    op.drop_index(op.f('ix_advisor_meeting_section_id'), table_name='meeting', schema='advisor')
    op.drop_table('meeting', schema='advisor')
    op.drop_index(op.f('ix_advisor_section_index_number'), table_name='section', schema='advisor')
    op.drop_table('section', schema='advisor')
    op.drop_index(op.f('ix_advisor_offering_core_code_core_code'), table_name='offering_core_code', schema='advisor')
    op.drop_table('offering_core_code', schema='advisor')
    op.drop_index(op.f('ix_advisor_course_offering_course_id'), table_name='course_offering', schema='advisor')
    op.drop_table('course_offering', schema='advisor')
    op.drop_table('term', schema='advisor')
    op.drop_table('instructor', schema='advisor')
    op.drop_index(op.f('ix_advisor_course_school_code'), table_name='course', schema='advisor')
    op.drop_table('course', schema='advisor')
    op.drop_table('core_code', schema='advisor')
