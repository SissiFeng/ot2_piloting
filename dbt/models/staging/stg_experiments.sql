with source as (
    select * from {{ source('raw', 'experiments') }}
),

renamed as (
    select
        id as experiment_id,
        user_id,
        plate_type_id,
        status,
        metadata,
        protocol_data,
        results_data,
        created_at,
        started_at,
        completed_at,
        error_message
    from source
)

select * from renamed 