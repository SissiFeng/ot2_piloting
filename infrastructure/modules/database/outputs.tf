output "postgresql_instance_name" {
  description = "The name of the PostgreSQL instance"
  value       = google_sql_database_instance.postgresql.name
}

output "postgresql_connection_name" {
  description = "The connection name of the PostgreSQL instance"
  value       = google_sql_database_instance.postgresql.connection_name
}

output "postgresql_public_ip" {
  description = "The public IP address of the PostgreSQL instance"
  value       = google_sql_database_instance.postgresql.public_ip_address
}

output "postgresql_private_ip" {
  description = "The private IP address of the PostgreSQL instance"
  value       = google_sql_database_instance.postgresql.private_ip_address
}

output "postgresql_database_name" {
  description = "The name of the PostgreSQL database"
  value       = google_sql_database.database.name
}

output "mongodb_cluster_id" {
  description = "The ID of the MongoDB Atlas cluster"
  value       = mongodbatlas_cluster.cluster.cluster_id
}

output "mongodb_connection_string" {
  description = "The connection string for MongoDB Atlas"
  value       = mongodbatlas_cluster.cluster.connection_strings[0].standard
  sensitive   = true
}

output "mongodb_srv_address" {
  description = "The srv address for MongoDB Atlas"
  value       = mongodbatlas_cluster.cluster.connection_strings[0].standard_srv
  sensitive   = true
} 