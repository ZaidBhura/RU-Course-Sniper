"""Course catalog tables (all in the `advisor` Postgres schema).

This data is public and global, so none of these tables are tenant-scoped.
Student data (transcripts, plans) will get separate, tenant-scoped tables.

Shape:
    term ─< course_offering >─ course
                 │  └─< offering_core_code >─ core_code
                 └─< section ─< meeting
                         └─< section_instructor >─ instructor

A course's core codes and prerequisites are stored per offering (per term),
because they change over time and a degree audit needs the codes a course
carried in the term the student took it.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from advisor.db import Base


class Term(Base):
    __tablename__ = "term"
    __table_args__ = (UniqueConstraint("year", "term", "campus"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    term: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0/1/7/9
    campus: Mapped[str] = mapped_column(String(4), nullable=False)
    last_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    course_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    section_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    offerings: Mapped[list[CourseOffering]] = relationship(
        back_populates="term", cascade="all, delete-orphan", passive_deletes=True
    )


class CoreCode(Base):
    __tablename__ = "core_code"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    description: Mapped[str] = mapped_column(String(256), nullable=False, server_default="")


class Course(Base):
    """Stable identity of a course across terms, e.g. 01:198:344."""

    __tablename__ = "course"
    __table_args__ = (
        UniqueConstraint("course_string", "supplement_code"),
        Index(None, "school_code", "subject_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_string: Mapped[str] = mapped_column(String(16), nullable=False)
    supplement_code: Mapped[str] = mapped_column(String(4), nullable=False, server_default="")
    school_code: Mapped[str] = mapped_column(String(2), nullable=False)
    subject_code: Mapped[str] = mapped_column(String(3), nullable=False)
    course_number: Mapped[str] = mapped_column(String(3), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False, server_default="")


class CourseOffering(Base):
    """A course as listed in one term's Schedule of Classes."""

    __tablename__ = "course_offering"
    __table_args__ = (UniqueConstraint("term_id", "course_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("term.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("course.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False, server_default="")
    expanded_title: Mapped[str] = mapped_column(String(512), nullable=False, server_default="")
    school_description: Mapped[str] = mapped_column(String(256), nullable=False, server_default="")
    subject_description: Mapped[str] = mapped_column(String(256), nullable=False, server_default="")
    level: Mapped[str] = mapped_column(String(2), nullable=False, server_default="")
    # NULL credits means "by arrangement" (credits_code = 'BA').
    credits: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    credits_code: Mapped[str] = mapped_column(String(16), nullable=False, server_default="")
    prereq_raw: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    prereq_tree: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    prereq_parse_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    prereq_parse_error: Mapped[str | None] = mapped_column(Text)
    synopsis_url: Mapped[str] = mapped_column(String(512), nullable=False, server_default="")
    course_notes: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    term: Mapped[Term] = relationship(back_populates="offerings")
    course: Mapped[Course] = relationship()
    core_codes: Mapped[list[OfferingCoreCode]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    sections: Mapped[list[Section]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class OfferingCoreCode(Base):
    __tablename__ = "offering_core_code"

    offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offering.id", ondelete="CASCADE"), primary_key=True
    )
    core_code: Mapped[str] = mapped_column(
        ForeignKey("core_code.code"), primary_key=True, index=True
    )


class Instructor(Base):
    """One row per distinct SOC instructor string, e.g. 'SELIM, SAMAH'.

    Rate My Professors matching will attach to this table later.
    """

    __tablename__ = "instructor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    soc_name: Mapped[str] = mapped_column(String(128), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Section(Base):
    __tablename__ = "section"
    __table_args__ = (UniqueConstraint("offering_id", "index_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    offering_id: Mapped[int] = mapped_column(
        ForeignKey("course_offering.id", ondelete="CASCADE"), nullable=False
    )
    index_number: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    section_number: Mapped[str] = mapped_column(String(8), nullable=False, server_default="")
    open_status: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    course_type: Mapped[str] = mapped_column(String(4), nullable=False, server_default="")
    campus_code: Mapped[str] = mapped_column(String(8), nullable=False, server_default="")
    exam_code: Mapped[str] = mapped_column(String(4), nullable=False, server_default="")
    final_exam: Mapped[str] = mapped_column(String(128), nullable=False, server_default="")
    cross_listed: Mapped[str] = mapped_column(String(512), nullable=False, server_default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    eligibility: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    subtitle: Mapped[str] = mapped_column(String(256), nullable=False, server_default="")

    meetings: Mapped[list[Meeting]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class SectionInstructor(Base):
    __tablename__ = "section_instructor"

    section_id: Mapped[int] = mapped_column(
        ForeignKey("section.id", ondelete="CASCADE"), primary_key=True
    )
    instructor_id: Mapped[int] = mapped_column(
        ForeignKey("instructor.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class Meeting(Base):
    __tablename__ = "meeting"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("section.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day: Mapped[str] = mapped_column(String(2), nullable=False, server_default="")
    start_min: Mapped[int | None] = mapped_column(SmallInteger)  # minutes after midnight
    end_min: Mapped[int | None] = mapped_column(SmallInteger)
    campus_name: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    campus_abbrev: Mapped[str] = mapped_column(String(16), nullable=False, server_default="")
    building: Mapped[str] = mapped_column(String(16), nullable=False, server_default="")
    room: Mapped[str] = mapped_column(String(16), nullable=False, server_default="")
    mode_code: Mapped[str] = mapped_column(String(8), nullable=False, server_default="")
    mode_desc: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
