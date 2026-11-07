locals {
  indian_regions = ["ap-south-1", "ap-south-2"]

  tags = {
    project     = "red-tape-navigator"
    environment = var.environment
    data_region = var.region
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}

# Data residency guard: refuse to plan outside India unless explicitly disabled.
resource "terraform_data" "region_guard" {
  lifecycle {
    precondition {
      condition     = !var.data_region_guard || contains(local.indian_regions, var.region)
      error_message = "region must be an Indian region (ap-south-1 or ap-south-2) while data_region_guard is true."
    }
  }
}

# Modules are added here as they are implemented, for example:
# module "network"  { source = "./modules/network"  environment = var.environment }
# module "database" { source = "./modules/database" environment = var.environment }
