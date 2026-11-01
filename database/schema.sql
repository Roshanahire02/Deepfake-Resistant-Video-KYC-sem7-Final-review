-- ============================================================
-- Deepfake-Resistant Video KYC Verification System
-- PostgreSQL schema (production target)
--
-- Generated directly from the live SQLAlchemy ORM metadata
-- (backend/app/models/*.py) -- this file is a faithful DDL
-- export of the exact schema the application creates, not a
-- hand-maintained approximation. Regenerate after any model
-- change with:
--
--   cd backend && python -c "
--   from sqlalchemy.schema import CreateTable
--   from sqlalchemy.dialects import postgresql
--   from sqlalchemy import Enum as SAEnum
--   from app.core.database import Base
--   from app.models import user, kyc_case, document, results
--   seen = {}
--   for t in Base.metadata.sorted_tables:
--       for c in t.columns:
--           if isinstance(c.type, SAEnum):
--               seen[c.type.name] = c.type
--   for name, e in seen.items():
--       vals = ', '.join(f\"'{v}'\" for v in e.enums)
--       print(f'CREATE TYPE {name} AS ENUM ({vals});')
--   for t in Base.metadata.sorted_tables:
--       print(str(CreateTable(t).compile(dialect=postgresql.dialect())).strip() + ';')
--   "
--
-- Local development uses SQLite instead (see backend/.env.example,
-- DATABASE_URL) for zero-setup running on a laptop; this file
-- documents the intended production database.
--
-- Raw KYC video is NEVER stored -- every *_results table holds only
-- derived metadata (scores/statuses/timestamps), consistent with the
-- project's privacy design (see docs/rppg.md and app/utils/temp_file_manager.py).
-- ============================================================

CREATE TYPE userrole AS ENUM ('USER', 'REVIEWER', 'ADMIN');
CREATE TYPE casestatus AS ENUM ('CREATED', 'DOCUMENT_UPLOADED', 'DOCUMENT_ANALYZED', 'VIDEO_PROCESSING', 'RISK_CALCULATED', 'VERIFIED', 'MANUAL_REVIEW', 'FLAGGED', 'REJECTED');
CREATE TYPE revieweractiontype AS ENUM ('APPROVE', 'REJECT', 'MANUAL_REVIEW');
CREATE TYPE risklevel AS ENUM ('LOW', 'MEDIUM', 'HIGH');
CREATE TYPE decision AS ENUM ('VERIFIED', 'MANUAL_REVIEW', 'FLAGGED', 'REJECTED');

CREATE TABLE users (
	id UUID NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	full_name VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role userrole NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
);

CREATE TABLE kyc_cases (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	status casestatus NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	updated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE deepfake_results (
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	deepfake_probability FLOAT, 
	status VARCHAR(32), 
	frames_analyzed INTEGER, 
	suspicious_frame_indices JSONB, 
	model_version VARCHAR(64), 
	gradcam_ref VARCHAR(512), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (case_id), 
	FOREIGN KEY(case_id) REFERENCES kyc_cases (id) ON DELETE CASCADE
);

CREATE TABLE documents (
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	doc_type VARCHAR(64), 
	original_filename VARCHAR(255) NOT NULL, 
	file_ref_temp VARCHAR(512) NOT NULL, 
	uploaded_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES kyc_cases (id) ON DELETE CASCADE
);

CREATE TABLE face_verification (
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	similarity_score FLOAT, 
	match_status VARCHAR(32), 
	face_quality_score FLOAT, 
	multiple_faces_detected BOOLEAN, 
	threshold_used FLOAT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (case_id), 
	FOREIGN KEY(case_id) REFERENCES kyc_cases (id) ON DELETE CASCADE
);

CREATE TABLE liveness_results (
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	challenge_type VARCHAR(64), 
	passed BOOLEAN, 
	motion_score FLOAT, 
	blink_count INTEGER, 
	confidence FLOAT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (case_id), 
	FOREIGN KEY(case_id) REFERENCES kyc_cases (id) ON DELETE CASCADE
);

CREATE TABLE replay_results (
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	replay_probability FLOAT, 
	status VARCHAR(32), 
	signals JSONB, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (case_id), 
	FOREIGN KEY(case_id) REFERENCES kyc_cases (id) ON DELETE CASCADE
);

CREATE TABLE reviewer_actions (
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	reviewer_id UUID NOT NULL, 
	action revieweractiontype NOT NULL, 
	notes TEXT, 
	decided_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(case_id) REFERENCES kyc_cases (id) ON DELETE CASCADE, 
	FOREIGN KEY(reviewer_id) REFERENCES users (id)
);

CREATE TABLE risk_assessments (
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	fraud_risk_score FLOAT, 
	risk_level risklevel, 
	decision decision, 
	feature_contributions JSONB, 
	explanation_text TEXT, 
	model_version VARCHAR(64), 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (case_id), 
	FOREIGN KEY(case_id) REFERENCES kyc_cases (id) ON DELETE CASCADE
);

CREATE TABLE rppg_results (
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	status VARCHAR(32), 
	heart_rate_bpm FLOAT, 
	signal_quality FLOAT, 
	periodicity_score FLOAT, 
	temporal_consistency FLOAT, 
	rppg_score FLOAT, 
	usable_frames INTEGER, 
	usable_frame_ratio FLOAT, 
	roi_stability FLOAT, 
	method_version VARCHAR(64), 
	message TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (case_id), 
	FOREIGN KEY(case_id) REFERENCES kyc_cases (id) ON DELETE CASCADE
);

CREATE TABLE verification_reports (
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	report_snapshot JSONB, 
	generated_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (case_id), 
	FOREIGN KEY(case_id) REFERENCES kyc_cases (id) ON DELETE CASCADE
);

CREATE TABLE ocr_results (
	id UUID NOT NULL, 
	case_id UUID NOT NULL, 
	document_id UUID NOT NULL, 
	extracted_name VARCHAR(255), 
	extracted_dob VARCHAR(64), 
	extracted_doc_number VARCHAR(128), 
	raw_text_blocks JSONB, 
	authenticity_score FLOAT, 
	tampering_flag BOOLEAN, 
	tampering_probability FLOAT, 
	suspicious_regions JSONB, 
	notes TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	UNIQUE (case_id), 
	FOREIGN KEY(case_id) REFERENCES kyc_cases (id) ON DELETE CASCADE, 
	UNIQUE (document_id), 
	FOREIGN KEY(document_id) REFERENCES documents (id) ON DELETE CASCADE
);
