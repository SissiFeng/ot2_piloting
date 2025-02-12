-- Create user activity log table
CREATE TABLE structured.user_activity_log (
    id UUID PRIMARY KEY DEFAULT public.uuid_generate_v4(),
    user_id UUID REFERENCES structured.users(id),
    action VARCHAR(50) NOT NULL,
    details JSONB,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for activity log
CREATE INDEX idx_activity_user_id ON structured.user_activity_log(user_id);
CREATE INDEX idx_activity_action ON structured.user_activity_log(action);
CREATE INDEX idx_activity_created_at ON structured.user_activity_log(created_at);
CREATE INDEX idx_activity_details ON structured.user_activity_log USING GIN (details jsonb_path_ops);

-- Create view for activity statistics
CREATE VIEW structured.activity_statistics AS
WITH daily_stats AS (
    SELECT 
        date_trunc('day', created_at) as day,
        action,
        COUNT(*) as action_count
    FROM structured.user_activity_log
    GROUP BY date_trunc('day', created_at), action
)
SELECT 
    day,
    action,
    action_count,
    SUM(action_count) OVER (PARTITION BY action ORDER BY day) as cumulative_count
FROM daily_stats;

-- Create materialized view for experiment analysis
CREATE MATERIALIZED VIEW semi_structured.experiment_analysis AS
WITH experiment_stats AS (
    SELECT 
        date_trunc('hour', e.created_at) as time_bucket,
        e.status,
        COUNT(*) as experiment_count,
        AVG(EXTRACT(EPOCH FROM (e.completed_at - e.started_at))) as avg_duration,
        COUNT(*) FILTER (WHERE e.error_message IS NULL) as successful_count,
        COUNT(*) FILTER (WHERE e.error_message IS NOT NULL) as failed_count
    FROM semi_structured.experiments e
    GROUP BY time_bucket, status
),
color_stats AS (
    SELECT 
        date_trunc('hour', e.created_at) as time_bucket,
        CASE 
            WHEN (e.metadata->>'red')::float > 60 THEN 'high'
            WHEN (e.metadata->>'red')::float > 30 THEN 'medium'
            ELSE 'low'
        END || '_' ||
        CASE 
            WHEN (e.metadata->>'yellow')::float > 60 THEN 'high'
            WHEN (e.metadata->>'yellow')::float > 30 THEN 'medium'
            ELSE 'low'
        END || '_' ||
        CASE 
            WHEN (e.metadata->>'blue')::float > 60 THEN 'high'
            WHEN (e.metadata->>'blue')::float > 30 THEN 'medium'
            ELSE 'low'
        END as color_combination,
        COUNT(*) as combination_count
    FROM semi_structured.experiments e
    GROUP BY time_bucket, color_combination
)
SELECT 
    es.time_bucket,
    es.status,
    es.experiment_count,
    es.avg_duration,
    es.successful_count,
    es.failed_count,
    jsonb_object_agg(cs.color_combination, cs.combination_count) as color_combinations
FROM experiment_stats es
LEFT JOIN color_stats cs ON es.time_bucket = cs.time_bucket
GROUP BY 
    es.time_bucket,
    es.status,
    es.experiment_count,
    es.avg_duration,
    es.successful_count,
    es.failed_count;

-- Create index for materialized view
CREATE UNIQUE INDEX idx_experiment_analysis_time_bucket 
ON semi_structured.experiment_analysis(time_bucket, status);

-- Create function to refresh materialized view
CREATE OR REPLACE FUNCTION public.refresh_experiment_analysis()
RETURNS trigger AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY semi_structured.experiment_analysis;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to refresh materialized view
CREATE TRIGGER refresh_experiment_analysis_trigger
AFTER INSERT OR UPDATE OR DELETE ON semi_structured.experiments
FOR EACH STATEMENT
EXECUTE FUNCTION public.refresh_experiment_analysis(); 