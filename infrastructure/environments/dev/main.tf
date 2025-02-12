terraform {
  required_version = ">= 1.0.0"
  
  backend "gcs" {
    bucket = "ot2-terraform-state-dev"
    prefix = "terraform/state"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    mongodbatlas = {
      source  = "mongodb/mongodbatlas"
      version = "~> 1.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "mongodbatlas" {
  public_key  = var.mongodb_atlas_public_key
  private_key = var.mongodb_atlas_private_key
}

module "networking" {
  source = "../../modules/networking"

  project_id  = var.project_id
  region      = var.region
  vpc_name    = "ot2-vpc-dev"
  subnet_name = "ot2-subnet-dev"
}

module "database" {
  source = "../../modules/database"

  project_id              = var.project_id
  region                 = var.region
  environment            = var.environment
  vpc_id                 = module.networking.vpc_id
  vpc_name               = module.networking.vpc_name
  
  # PostgreSQL configuration
  postgresql_password     = var.postgresql_password
  
  # MongoDB Atlas configuration
  mongodb_atlas_project_id = var.mongodb_atlas_project_id
} 