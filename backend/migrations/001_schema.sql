CREATE DATABASE IF NOT EXISTS dealer_renewal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE dealer_renewal;
CREATE TABLE IF NOT EXISTS users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  email VARCHAR(120) NOT NULL UNIQUE,
  password VARCHAR(120) NOT NULL,
  name VARCHAR(80) NOT NULL,
  role ENUM('advisor','manager','admin') NOT NULL,
  active TINYINT NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS owners (
  id INT PRIMARY KEY AUTO_INCREMENT,
  owner_code VARCHAR(32) NOT NULL UNIQUE,
  name VARCHAR(80) NOT NULL,
  phone VARCHAR(30) NOT NULL,
  vehicle_model VARCHAR(80) NOT NULL,
  plate_no VARCHAR(16) NOT NULL,
  policy_expires DATE NOT NULL,
  contact_status ENUM('open','rejected') NOT NULL DEFAULT 'open',
  preferred_channel ENUM('phone','wechat','sms') NOT NULL DEFAULT 'phone',
  region VARCHAR(50) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS service_events (
  id INT PRIMARY KEY AUTO_INCREMENT,
  owner_id INT NOT NULL,
  service_date DATE NOT NULL,
  mileage INT NOT NULL,
  service_type VARCHAR(80) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  satisfaction DECIMAL(4,2) NOT NULL,
  advisor_name VARCHAR(80) NOT NULL,
  notes VARCHAR(255) NOT NULL,
  UNIQUE KEY uq_service (owner_id, service_date, service_type),
  CONSTRAINT fk_service_owner FOREIGN KEY (owner_id) REFERENCES owners(id)
);
CREATE TABLE IF NOT EXISTS renewal_leads (
  id INT PRIMARY KEY AUTO_INCREMENT,
  owner_id INT NOT NULL UNIQUE,
  score DECIMAL(6,4) NOT NULL DEFAULT 0,
  status ENUM('predicted','reviewed','queued','frozen','expired','rejected') NOT NULL DEFAULT 'predicted',
  last_prediction_at DATETIME NULL,
  reviewed_by INT NULL,
  reviewed_at DATETIME NULL,
  review_note VARCHAR(255) NULL,
  feature_contrib JSON NULL,
  CONSTRAINT fk_lead_owner FOREIGN KEY (owner_id) REFERENCES owners(id),
  CONSTRAINT fk_lead_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS followups (
  id INT PRIMARY KEY AUTO_INCREMENT,
  lead_id INT NOT NULL,
  owner_id INT NOT NULL,
  assignee_id INT NOT NULL,
  scheduled_for DATETIME NOT NULL,
  channel ENUM('phone','wechat','sms') NOT NULL,
  status ENUM('scheduled','contacted','declined','completed') NOT NULL DEFAULT 'scheduled',
  outcome_note VARCHAR(255) NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_followup_lead FOREIGN KEY (lead_id) REFERENCES renewal_leads(id),
  CONSTRAINT fk_followup_owner FOREIGN KEY (owner_id) REFERENCES owners(id),
  CONSTRAINT fk_followup_assignee FOREIGN KEY (assignee_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS audit_logs (
  id INT PRIMARY KEY AUTO_INCREMENT,
  user_id INT NULL,
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(50) NOT NULL,
  entity_id INT NULL,
  detail JSON NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(id)
);
