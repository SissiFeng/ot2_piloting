with experiment_metrics as (
    select * from {{ ref('int_experiment_metrics') }}
),

daily_metrics as (
    select
        date_trunc('day', experiment_date) as date,
        count(*) as total_experiments,
        sum(case when status = 'completed' then 1 else 0 end) as successful_experiments,
        avg(duration_seconds) as avg_duration,
        avg(completed_wells::float / nullif(total_wells, 0)) as completion_rate,
        avg(avg_intensity) as avg_intensity,
        sum(total_wells) as total_wells_processed
    from experiment_metrics
    group by 1
),

final as (
    select
        date,
        total_experiments,
        successful_experiments,
        round(avg_duration::numeric, 2) as avg_duration_seconds,
        round(completion_rate * 100, 2) as completion_rate_pct,
        round(avg_intensity::numeric, 2) as avg_intensity,
        total_wells_processed,
        round((successful_experiments::float / nullif(total_experiments, 0) * 100)::numeric, 2) as success_rate_pct,
        lag(total_experiments) over (order by date) as prev_day_experiments,
        round(((total_experiments::float - lag(total_experiments) over (order by date))
            / nullif(lag(total_experiments) over (order by date), 0) * 100)::numeric, 2) as experiment_growth_pct
    from daily_metrics
)

select * from final 