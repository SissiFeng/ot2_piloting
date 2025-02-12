with source as (
    select * from {{ source('raw', 'wells') }}
),

renamed as (
    select
        id as well_id,
        experiment_id,
        well_id as well_position,
        status,
        raw_data_s3_path,
        metadata,
        measurement_data,
        analysis_results,
        created_at,
        updated_at
    from source
)

select * from renamed 