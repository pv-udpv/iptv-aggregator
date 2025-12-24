"""SQLAlchemy models for channels and EPG data"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Channel(Base):
    __tablename__ = "channels"
    
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    alt_names: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    categories: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_nsfw: Mapped[bool] = mapped_column(Boolean, default=False)
    xmltv_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    streams: Mapped[list["Stream"]] = relationship(back_populates="channel", cascade="all, delete-orphan")
    programmes: Mapped[list["Programme"]] = relationship(back_populates="channel", cascade="all, delete-orphan")


class Stream(Base):
    __tablename__ = "streams"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(ForeignKey("channels.id"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    quality: Mapped[str] = mapped_column(String(16), default="AUTO")
    is_working: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    
    channel: Mapped["Channel"] = relationship(back_populates="streams")


class Programme(Base):
    __tablename__ = "programmes"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[str] = mapped_column(ForeignKey("channels.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    stop: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    channel: Mapped["Channel"] = relationship(back_populates="programmes")