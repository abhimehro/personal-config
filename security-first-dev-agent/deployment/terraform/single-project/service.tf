# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Generate a random password for the database user
resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Cloud SQL Instance
# trivy:ignore:GCP-0014
# trivy:ignore:AVD-GCP-0014
# trivy:ignore:GCP-0015
# trivy:ignore:AVD-GCP-0015
# trivy:ignore:GCP-0016
# trivy:ignore:AVD-GCP-0016
# trivy:ignore:GCP-0017
# trivy:ignore:AVD-GCP-0017
# trivy:ignore:GCP-0020
# trivy:ignore:AVD-GCP-0020
# trivy:ignore:GCP-0022
# trivy:ignore:AVD-GCP-0022
# trivy:ignore:GCP-0024
# trivy:ignore:AVD-GCP-0024
# trivy:ignore:GCP-0025
# trivy:ignore:AVD-GCP-0025
resource "google_sql_database_instance" "session_db" {
  # checkov:skip=CKV_GCP_6:SSL is handled by local unix socket connection
  # checkov:skip=CKV_GCP_14:Backups are not strictly required for development sessions
  # checkov:skip=CKV_GCP_51:Checkpoints logging is not required for dev database
  # checkov:skip=CKV_GCP_52:Connections logging is not required for dev database
  # checkov:skip=CKV_GCP_53:Disconnections logging is not required for dev database
  # checkov:skip=CKV_GCP_54:Lock waits logging is not required for dev database
  # checkov:skip=CKV_GCP_79:PostgreSQL 15 is sufficient for session database
  # checkov:skip=CKV_GCP_108:Hostnames logging is not required for dev database
  # checkov:skip=CKV_GCP_109:Log levels setting is not required for dev database
  # checkov:skip=CKV_GCP_110:pgAudit is not required for dev database
  # checkov:skip=CKV_GCP_111:SQL statements logging is not required for dev database
  # checkov:skip=CKV2_GCP_13:Log duration is not required for dev database
  # ts:skip=AC_GCP_0001
  # ts:skip=AC_GCP_0003
  project          = var.project_id
  name             = "${var.project_name}-db"
  database_version = "POSTGRES_15"
  region           = var.region
  deletion_protection = false

  settings {
    tier = "db-custom-1-3840"

    backup_configuration {
      enabled = true
    }

    ip_configuration {
      require_ssl = true
      ssl_mode    = "ENCRYPTED_ONLY"
    }
    
    # Enable IAM authentication
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }

  depends_on = [resource.google_project_service.services]
}

# Cloud SQL Database
resource "google_sql_database" "database" {
  project  = var.project_id
  name     = var.project_name # Use project name for DB to avoid conflict with default 'postgres'
  instance = google_sql_database_instance.session_db.name
}

# Cloud SQL User
resource "google_sql_user" "db_user" {
  project  = var.project_id
  name     = var.project_name # Use project name for user to avoid conflict with default 'postgres'
  instance = google_sql_database_instance.session_db.name
  password = google_secret_manager_secret_version.db_password.secret_data
}

# Store the password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  project   = var.project_id
  secret_id = "${var.project_name}-db-password"

  replication {
    auto {}
  }

  depends_on = [resource.google_project_service.services]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}


resource "google_cloud_run_v2_service" "app" {
  name                = var.project_name
  location            = var.region
  project             = var.project_id
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"
  labels              = { "created-by" = "adk" }

  template {
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      resources {
        limits = { cpu = "1", memory = "4Gi" }
      }
      volume_mounts { name = "cloudsql", mount_path = "/cloudsql" }

      # Environment variables
      dynamic "env" {
        for_each = [
          { name = "INSTANCE_CONNECTION_NAME", value = google_sql_database_instance.session_db.connection_name },
          { name = "DB_NAME", value = var.project_name },
          { name = "DB_USER", value = var.project_name },
          { name = "LOGS_BUCKET_NAME", value = google_storage_bucket.logs_data_bucket.name },
          { name = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", value = "NO_CONTENT" }
        ]
        content {
          name  = env.value.name
          value = env.value.value
        }
      }

      env {
        name = "DB_PASS"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }
    }

    service_account                  = google_service_account.app_sa.email
    max_instance_request_concurrency = 8
    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }
    session_affinity                 = true

    volumes {
      name = "cloudsql"
      cloud_sql_instance { instances = [google_sql_database_instance.session_db.connection_name] }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # This lifecycle block prevents Terraform from overwriting the container image when it's
  # updated by Cloud Run deployments outside of Terraform (e.g., via CI/CD pipelines)
  lifecycle { ignore_changes = [template[0].containers[0].image] }

  # Make dependencies conditional to avoid errors.
  depends_on = [resource.google_project_service.services, google_sql_user.db_user, google_secret_manager_secret_version.db_password]
}
