variable "region" {
  description = "AWS region. Default is Mumbai for Indian data residency."
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "pilot"
}

variable "data_region_guard" {
  description = "When true, planning fails if region is not an Indian region."
  type        = bool
  default     = true
}
