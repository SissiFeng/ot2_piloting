with experiments as (
    select * from {{ ref('stg_experiments') }}
),

wells as (
    select * from {{ ref('stg_wells') }}
),

experiment_metrics as (
    select
        e.experiment_id,
        e.status,
        count(w.well_id) as total_wells,
        sum(case when w.status = 'completed' then 1 else 0 end) as completed_wells,
        avg(cast(w.measurement_data->>'max_intensity' as float)) as avg_intensity,
        max(cast(w.measurement_data->>'max_intensity' as float)) as max_intensity,
        min(cast(w.measurement_data->>'max_intensity' as float)) as min_intensity,
        extract(epoch from (e.completed_at - e.started_at)) as duration_seconds,
        e.created_at as experiment_date
    from experiments e
    left join wells w on e.experiment_id = w.experiment_id
    where e.status != 'pending'
    group by 1, 2, e.created_at, e.completed_at, e.started_at
)

select * from experiment_metrics 