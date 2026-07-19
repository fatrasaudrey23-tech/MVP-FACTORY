CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Table: companies
CREATE TABLE IF NOT EXISTS companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    subscription_status VARCHAR(50) NOT NULL DEFAULT 'inactive' CHECK (subscription_status IN ('active', 'inactive', 'trial', 'cancelled')),
    registration_code VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON companies
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Table: users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'deactivated')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_company_id ON users(company_id);

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Table: therapists
CREATE TABLE IF NOT EXISTS therapists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cal_com_user_id VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    specialties JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'on_leave')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON therapists
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Table: conversations
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'flagged_for_review')),
    summary TEXT,
    outcome_type VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON conversations
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Table: conversation_messages
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_type VARCHAR(10) NOT NULL CHECK (sender_type IN ('user', 'ai')),
    content_encrypted TEXT NOT NULL,
    ai_metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);

-- Table: bookings
CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    therapist_id UUID NOT NULL REFERENCES therapists(id) ON DELETE CASCADE,
    cal_com_booking_id BIGINT NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled', 'completed')),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_therapist_id ON bookings(therapist_id);

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON bookings
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Table: resources
CREATE TABLE IF NOT EXISTS resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type VARCHAR(50) NOT NULL CHECK (type IN ('meditation_audio', 'breathing_exercise', 'podcast', 'article')),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    content_url VARCHAR(512) NOT NULL,
    duration_seconds INTEGER,
    tags JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(type);
CREATE INDEX IF NOT EXISTS idx_resources_tags ON resources USING GIN (tags);

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON resources
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();

-- Table: crisis_logs
CREATE TABLE IF NOT EXISTS crisis_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    triggering_message_id UUID REFERENCES conversation_messages(id) ON DELETE SET NULL,
    action_taken VARCHAR(255) NOT NULL CHECK (action_taken IN ('hotline_suggested', 'therapist_contact_suggested', 'escalated_to_human_support')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crisis_logs_conversation_id ON crisis_logs(conversation_id);