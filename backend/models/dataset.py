from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON, Enum as SAEnum, BigInteger, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from core.database import Base


class DatasetStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # csv, xlsx, json
    file_size_bytes = Column(BigInteger, nullable=False)
    file_hash = Column(String(64), nullable=True, index=True)  # SHA-256 for audit
    status = Column(SAEnum(DatasetStatus), default=DatasetStatus.UPLOADING, index=True)
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    schema_json = Column(JSON, nullable=True)         # Detected schema metadata
    stats_json = Column(JSON, nullable=True)           # Descriptive statistics
    insights_json = Column(JSON, nullable=True)        # Auto-detected insights
    viz_metadata_json = Column(JSON, nullable=True)    # Visualization recommendations
    data_json = Column(JSON, nullable=True)            # DataFrame stored as JSON (for predictions)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant", back_populates="datasets")
    owner = relationship("User", back_populates="datasets")
    jobs = relationship("AnalyticsJob", back_populates="dataset")


class AnalyticsJob(Base):
    __tablename__ = "analytics_jobs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)   # analytics, prediction, query
    model_type = Column(String(50), nullable=True)  # linear_regression, kmeans, etc.
    parameters = Column(JSON, nullable=True)
    status = Column(SAEnum(JobStatus), default=JobStatus.PENDING, index=True)
    result_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    dataset = relationship("Dataset", back_populates="jobs")
