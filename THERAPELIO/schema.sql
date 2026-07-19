CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =================================================================
-- Table: companies
-- =================================================================
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    subscription_status VARCHAR(50) NOT NULL DEFAULT 'inactive' CHECK (subscription_status IN ('active', 'inactive', 'trial')),
    registration_code VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =================================================================
-- Table: users
-- =================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deactivated')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =================================================================
-- Table: therapists
-- =================================================================
CREATE TABLE IF NOT EXISTS therapists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cal_com_user_id VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    specialties JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'on_leave')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =================================================================
-- Table: resources
-- =================================================================
CREATE TABLE IF NOT EXISTS resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL CHECK (type IN ('audio', 'guide', 'podcast', 'video', 'exercise')),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    content_url VARCHAR(512) NOT NULL,
    duration_seconds INTEGER,
    tags JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =================================================================
-- Table: conversations
-- =================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'flagged')),
    summary TEXT,
    outcome_type VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =================================================================
-- Table: conversation_messages
-- =================================================================
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type VARCHAR(10) NOT NULL CHECK (sender_type IN ('user', 'ai')),
    content_encrypted TEXT NOT NULL,
    ai_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =================================================================
-- Table: bookings
-- =================================================================
CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    therapist_id UUID NOT NULL REFERENCES therapists(id) ON DELETE RESTRICT,
    cal_com_booking_id BIGINT NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled', 'pending', 'rescheduled')),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =================================================================
-- Table: crisis_logs
-- =================================================================
CREATE TABLE IF NOT EXISTS crisis_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    triggering_message_id UUID REFERENCES conversation_messages(id) ON DELETE SET NULL,
    action_taken VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =================================================================
-- Auto-update updated_at timestamp
-- =================================================================
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attaching triggers to tables
CREATE TRIGGER set_timestamp
BEFORE UPDATE ON companies
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON conversations
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON therapists
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON bookings
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON resources
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

-- =================================================================
-- Indexes for performance
-- =================================================================
CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_therapist_id ON bookings(therapist_id);
CREATE INDEX IF NOT EXISTS idx_bookings_start_time ON bookings(start_time);
CREATE INDEX IF NOT EXISTS idx_crisis_logs_conversation_id ON crisis_logs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_crisis_logs_triggering_message_id ON crisis_logs(triggering_message_id);
CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(type);