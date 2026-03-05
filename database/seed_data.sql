-- ============================================================
-- OCSS GT Lobby Check-In System – Seed Data
-- Provides initial admin user and sample appointments for
-- development / testing purposes.
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- Default admin user
-- Username : admin
-- Password : Admin1234!  (bcrypt hash below)
-- IMPORTANT: Change this password before deploying to production.
-- ------------------------------------------------------------
INSERT OR IGNORE INTO staff_users (username, password_hash, first_name, last_name, email, role)
VALUES (
    'admin',
    '$2b$12$fEGrySLe2f1y4GwClcfWv.gt0nOgAEPPHrQXRG8Pu9PJ7OAoSylHu',
    'System',
    'Administrator',
    'admin@ocss.gatech.edu',
    'admin'
);

-- Default staff user
-- Username : staff1
-- Password : Staff1234!
INSERT OR IGNORE INTO staff_users (username, password_hash, first_name, last_name, email, role)
VALUES (
    'staff1',
    '$2b$12$oC2J1oWj7Mt0z/zr.Nf.yuyaBkNuHrVxHAkkbNaYJ6PHTfZqZyL9e',
    'Front',
    'Desk',
    'frontdesk@ocss.gatech.edu',
    'staff'
);

-- ------------------------------------------------------------
-- Sample appointments (for development use only)
-- ------------------------------------------------------------
INSERT OR IGNORE INTO appointments
    (appointment_id, student_gt_id, student_first_name, student_last_name,
     student_email, appointment_date, appointment_time, appointment_type, counselor, status)
VALUES
    ('APT-001', 'gt123456', 'Jane',    'Doe',      'jdoe3@gatech.edu',      date('now'), '09:00', 'Academic Advising',  'Dr. Smith',    'Scheduled'),
    ('APT-002', 'gt789012', 'John',    'Smith',    'jsmith6@gatech.edu',    date('now'), '09:30', 'Career Counseling',  'Ms. Johnson',  'Scheduled'),
    ('APT-003', 'gt345678', 'Maria',   'Garcia',   'mgarcia9@gatech.edu',   date('now'), '10:00', 'Financial Aid',      'Mr. Williams', 'Scheduled'),
    ('APT-004', 'gt901234', 'David',   'Lee',      'dlee2@gatech.edu',      date('now'), '10:30', 'Academic Advising',  'Dr. Smith',    'Scheduled'),
    ('APT-005', 'gt567890', 'Sarah',   'Brown',    'sbrown7@gatech.edu',    date('now'), '11:00', 'Disability Services','Dr. Patel',    'Scheduled'),
    ('APT-006', 'gt111222', 'Michael', 'Wilson',   'mwilson4@gatech.edu',   date('now'), '11:30', 'Career Counseling',  'Ms. Johnson',  'Scheduled'),
    ('APT-007', 'gt333444', 'Emily',   'Taylor',   'etaylor8@gatech.edu',   date('now'), '13:00', 'Financial Aid',      'Mr. Williams', 'Scheduled'),
    ('APT-008', 'gt555666', 'Chris',   'Anderson', 'canderson1@gatech.edu', date('now'), '13:30', 'Academic Advising',  'Dr. Smith',    'Scheduled'),
    ('APT-009', 'gt777888', 'Ashley',  'Thomas',   'athomas5@gatech.edu',   date('now'), '14:00', 'Disability Services','Dr. Patel',    'Scheduled'),
    ('APT-010', 'gt999000', 'James',   'Jackson',  'jjackson0@gatech.edu',  date('now'), '14:30', 'Career Counseling',  'Ms. Johnson',  'Scheduled');
