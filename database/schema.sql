/* OCSS GT LOBBY Check-In - SQL Schema (SQL Server compatible) */

CREATE TABLE gt_appointments (
  appointment_key VARCHAR(64) NOT NULL PRIMARY KEY,
  status_from_onbase VARCHAR(32) NULL,
  testing_datetime DATETIME2 NOT NULL,
  sets_number VARCHAR(32) NOT NULL,
  related_cases VARCHAR(256) NULL,
  part_type VARCHAR(64) NULL,
  first_name VARCHAR(128) NULL,
  last_name VARCHAR(128) NULL,
  appointment_type VARCHAR(64) NULL,
  coc VARCHAR(16) NULL,
  pre_call VARCHAR(16) NULL,
  assigned_to VARCHAR(128) NULL,
  scheduled_by VARCHAR(128) NULL,
  created_date DATETIME2 NULL,
  export_batch_id VARCHAR(64) NULL
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
