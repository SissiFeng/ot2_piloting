terraform {
  required_version = ">= 1.0.0"
}

# PostgreSQL Configuration
resource "google_sql_database_instance" "postgresql" {
  name             = "${var.environment}-postgresql"
  database_version = "POSTGRES_14"
  region           = var.region
  project         = var.project_id

  settings {
    tier = var.postgresql_tier
    
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "02:00"
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 7
      }
    }

    ip_configuration {
      ipv4_enabled    = true
      private_network = var.vpc_id
      require_ssl     = true
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length     = 1024
      record_application_tags = true
      record_client_address   = true
    }

    maintenance_window {
      day          = 7  # Sunday
      hour         = 3  # 3 AM
      update_track = "stable"
    }
  }

  deletion_protection = var.environment == "prod" ? true : false
}

# Create PostgreSQL database
resource "google_sql_database" "database" {
  name     = var.postgresql_db_name
  instance = google_sql_database_instance.postgresql.name
  project  = var.project_id
}

# Create PostgreSQL user
resource "google_sql_user" "user" {
  name     = var.postgresql_user
  instance = google_sql_database_instance.postgresql.name
  password = var.postgresql_password
  project  = var.project_id
}

# MongoDB Atlas Configuration
resource "mongodbatlas_cluster" "cluster" {
  project_id = var.mongodb_atlas_project_id
  name       = "${var.environment}-mongodb"

  provider_name               = "GCP"
  provider_region_name       = var.mongodb_region
  provider_instance_size_name = var.mongodb_instance_size

  mongo_db_major_version = "6.0"
  auto_scaling_disk_gb_enabled = true

  backup_enabled               = true
  pit_enabled                  = true
  
  # Advanced configuration
  advanced_configuration {
    javascript_enabled                   = true
    minimum_enabled_tls_protocol        = "TLS1_2"
    no_table_scan                       = false
    oplog_size_mb                       = 2048
    sample_size_bi_connector           = 100
    sample_refresh_interval_bi_connector = 300
  }

  # Network configuration
  replication_specs {
    num_shards = 1
    regions_config {
      region_name     = var.mongodb_region
      electable_nodes = 3
      priority        = 7
      read_only_nodes = 0
    }
  }
}

# MongoDB Atlas Network Peering
resource "mongodbatlas_network_peering" "peering" {
  project_id            = var.mongodb_atlas_project_id
  container_id         = mongodbatlas_cluster.cluster.container_id
  provider_name        = "GCP"
  gcp_project_id      = var.project_id
  network_name        = var.vpc_name
} 