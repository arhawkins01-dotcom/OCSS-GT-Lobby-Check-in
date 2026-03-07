/* OCSS GT LOBBY Check-In - SQL Schema (SQL Server compatible) */

CREATE TABLE gt_appointments (
  appointment_key VARCHAR(64) NOT NULL PRIMARY KEY,
  status_from_onbase VARCHAR(32) NULL,
  testing_datetime DATETIME2 NOT NULL,
  sets_number VARCHAR(32) NOT NULL,
  p_number VARCHAR(64) NULL,
  related_cases VARCHAR(256) NULL,
  part_type VARCHAR(64) NULL,
  first_name VARCHAR(128) NULL,
  last_name VARCHAR(128) NULL,
  appointment_type VARCHAR(64) NULL,
  location VARCHAR(128) NULL,
  test_type VARCHAR(128) NULL,
  coc VARCHAR(16) NULL,
  pre_call VARCHAR(16) NULL,
  assigned_to VARCHAR(128) NULL,
  scheduled_by VARCHAR(128) NULL,
  created_date DATETIME2 NULL,
  export_batch_id VARCHAR(64) NULL,
  mobile_phone VARCHAR(32) NULL,
  email_address VARCHAR(256) NULL,
  preferred_contact_method VARCHAR(16) NULL,
  sms_opt_in BIT NULL,
  email_opt_in BIT NULL,
  last_sms_sent_at DATETIME2 NULL,
  last_email_sent_at DATETIME2 NULL,
  sms_status VARCHAR(32) NULL,
  email_status VARCHAR(32) NULL,
  notification_error VARCHAR(1024) NULL,
  late_flag BIT NULL,
  wait_minutes INT NULL
);

CREATE TABLE gt_visit_status (
  appointment_key VARCHAR(64) NOT NULL PRIMARY KEY,
  current_status VARCHAR(32) NOT NULL,
  checkin_time DATETIME2 NULL,
  in_process_time DATETIME2 NULL,
  completed_time DATETIME2 NULL,
  no_show_time DATETIME2 NULL,
  last_updated_by VARCHAR(128) NULL,
  last_updated_time DATETIME2 NULL
);

CREATE TABLE gt_events (
  event_id VARCHAR(64) NOT NULL PRIMARY KEY,
  appointment_key VARCHAR(64) NOT NULL,
  event_type VARCHAR(32) NOT NULL,
  event_time DATETIME2 NOT NULL,
  performed_by VARCHAR(128) NULL,
  notes VARCHAR(1024) NULL
);

CREATE TABLE coc_forms (
  coc_id VARCHAR(64) NOT NULL PRIMARY KEY,
  appointment_key VARCHAR(64) NOT NULL,
  sets_case_number VARCHAR(64) NULL,
  p_number VARCHAR(64) NULL,
  participant_name VARCHAR(256) NULL,
  participant_role VARCHAR(64) NULL,
  appointment_datetime DATETIME2 NULL,
  checkin_time DATETIME2 NULL,
  location VARCHAR(128) NULL,
  test_type VARCHAR(128) NULL,
  collector_name VARCHAR(128) NULL,
  collector_id VARCHAR(64) NULL,
  staff_user VARCHAR(128) NULL,
  generated_by VARCHAR(128) NULL,
  generated_at DATETIME2 NULL,
  document_ref VARCHAR(512) NULL,
  created_at DATETIME2 NOT NULL,
  updated_at DATETIME2 NULL,
  status VARCHAR(32) NOT NULL,
  notes VARCHAR(2048) NULL
);

CREATE TABLE gt_related_party_status (
  status_id VARCHAR(64) NOT NULL PRIMARY KEY,
  appointment_key VARCHAR(64) NOT NULL,
  related_appointment_key VARCHAR(64) NOT NULL,
  party_role VARCHAR(64) NULL,
  arrival_status VARCHAR(32) NOT NULL,
  identity_verified_flag BIT NOT NULL,
  coc_included_flag BIT NOT NULL,
  updated_by VARCHAR(128) NULL,
  updated_time DATETIME2 NULL,
  CONSTRAINT uq_gt_related_party_status UNIQUE (appointment_key, related_appointment_key)
);

CREATE TABLE gt_notification_log (
  log_id VARCHAR(64) NOT NULL PRIMARY KEY,
  appointment_key VARCHAR(64) NOT NULL,
  channel VARCHAR(16) NOT NULL,
  status VARCHAR(32) NOT NULL,
  provider VARCHAR(64) NULL,
  sent_at DATETIME2 NULL,
  error_message VARCHAR(2048) NULL,
  response_payload VARCHAR(4000) NULL,
  event_type VARCHAR(64) NULL,
  performed_by VARCHAR(128) NULL
);
