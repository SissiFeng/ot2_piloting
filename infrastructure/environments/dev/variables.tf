variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

# PostgreSQL variables
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

variable "mongodb_atlas_public_key" {
  description = "The MongoDB Atlas public key"
  type        = string
  sensitive   = true
}

variable "mongodb_atlas_private_key" {
  description = "The MongoDB Atlas private key"
  type        = string
  sensitive   = true
} 