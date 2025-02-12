-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA public;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS structured;
CREATE SCHEMA IF NOT EXISTS semi_structured;

-- Structured Schema (Traditional relational data)
SET search_path TO structured, public;

-- Create plate_types table
CREATE TABLE plate_types (
    id UUID PRIMARY KEY DEFAULT public.uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    wells_count INTEGER NOT NULL,
    description TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT public.uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    quota_remaining INTEGER DEFAULT 10,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create audit log table
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT public.uuid_generate_v4(),
    table_name VARCHAR(50) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_data JSONB,
    new_data JSONB,
    user_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Semi-structured Schema (JSON/Document-like data)
SET search_path TO semi_structured, public;

-- Create experiments table
CREATE TABLE experiments (
    id UUID PRIMARY KEY DEFAULT public.uuid_generate_v4(),
    user_id UUID REFERENCES structured.users(id),
    plate_type_id UUID REFERENCES structured.plate_types(id),
    status VARCHAR(50) NOT NULL,
    metadata JSONB,
    protocol_data JSONB,
    results_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

-- Create wells table
CREATE TABLE wells (
    id UUID PRIMARY KEY DEFAULT public.uuid_generate_v4(),
    experiment_id UUID REFERENCES experiments(id),
    well_id VARCHAR(10) NOT NULL,
    status VARCHAR(50) NOT NULL,
    metadata JSONB,
    measurement_data JSONB,
    analysis_results JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create ML analysis table
CREATE TABLE ml_analysis (
    id UUID PRIMARY KEY DEFAULT public.uuid_generate_v4(),
    experiment_id UUID REFERENCES experiments(id),
    model_version VARCHAR(50) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    review_status VARCHAR(50) DEFAULT 'pending',
    reviewed_by UUID REFERENCES structured.users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_plate_types_name ON structured.plate_types(name);
CREATE INDEX idx_users_email ON structured.users(email);
CREATE INDEX idx_experiments_user_id ON experiments(user_id);
CREATE INDEX idx_experiments_status ON experiments(status);
CREATE INDEX idx_wells_experiment_id ON wells(experiment_id);
CREATE INDEX idx_ml_analysis_experiment_id ON ml_analysis(experiment_id);

-- Create JSONB indexes
CREATE INDEX idx_experiments_metadata ON experiments USING GIN (metadata jsonb_path_ops);
CREATE INDEX idx_wells_metadata ON wells USING GIN (metadata jsonb_path_ops);
CREATE INDEX idx_wells_analysis_results ON wells USING GIN (analysis_results jsonb_path_ops);
CREATE INDEX idx_ml_analysis_output ON ml_analysis USING GIN (output_data jsonb_path_ops);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON structured.users
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_plate_types_updated_at
    BEFORE UPDATE ON structured.plate_types
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_wells_updated_at
    BEFORE UPDATE ON wells
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column(); 