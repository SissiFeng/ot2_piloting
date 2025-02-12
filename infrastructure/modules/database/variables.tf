variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "The ID of the VPC"
  type        = string
}

variable "vpc_name" {
  description = "The name of the VPC"
  type        = string
}

# PostgreSQL variables
variable "postgresql_tier" {
  description = "The machine type to use for PostgreSQL"
  type        = string
  default     = "db-custom-2-4096" # 2 vCPU, 4GB RAM
}

variable "postgresql_db_name" {
  description = "The name of the PostgreSQL database"
  type        = string
  default     = "ot2db"
}

variable "postgresql_user" {
  description = "The PostgreSQL user"
  type        = string
  default     = "ot2admin"
}

variable "postgresql_password" {
  description = "The PostgreSQL user password"
  type        = string
  sensitive   = true
}

# MongoDB Atlas variables
variable "mongodb_atlas_project_id" {
  description = "The MongoDB Atlas project ID"
  type        = string
}

variable "mongodb_region" {
  description = "The MongoDB Atlas region"
  type        = string
  default     = "CENTRAL_US"
}

variable "mongodb_instance_size" {
  description = "The MongoDB Atlas instance size"
  type        = string
  default     = "M10" # 2GB RAM, 10GB storage
}

variable "mongodb_min_instance_size" {
  description = "The minimum instance size for auto-scaling"
  type        = string
  default     = "M10"
}

variable "mongodb_max_instance_size" {
  description = "The maximum instance size for auto-scaling"
  type        = string
  default     = "M20"
} 