-- CIVICSENSE - Existing database migration helper
-- The application automatically performs these changes at startup.
-- Use this file only when you prefer manual migration.

USE civicsense_prod;

ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user';
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE issues ADD COLUMN IF NOT EXISTS reported_by INT DEFAULT NULL;
ALTER TABLE issues ADD COLUMN IF NOT EXISTS upvotes INT NOT NULL DEFAULT 0;
ALTER TABLE issues ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'open';
ALTER TABLE issues ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

UPDATE issues SET status='open' WHERE status IS NULL OR TRIM(status)='';
UPDATE issues SET status='in_progress' WHERE LOWER(TRIM(status)) IN ('in progress','in-progress');
UPDATE issues SET status='open' WHERE LOWER(TRIM(status)) NOT IN ('open','in_progress','resolved');

CREATE TABLE IF NOT EXISTS issue_images (
  issue_id INT PRIMARY KEY,
  image_data LONGBLOB NOT NULL,
  mime_type VARCHAR(50) NOT NULL DEFAULT 'image/jpeg',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS issue_status_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  issue_id INT NOT NULL,
  status VARCHAR(20) NOT NULL,
  changed_by INT DEFAULT NULL,
  note VARCHAR(500) DEFAULT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_status_history_issue (issue_id),
  INDEX idx_status_history_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS notifications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  issue_id INT DEFAULT NULL,
  notification_type VARCHAR(50) NOT NULL DEFAULT 'general',
  title VARCHAR(200) NOT NULL,
  message VARCHAR(500) NOT NULL,
  is_read TINYINT(1) NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_notifications_user (user_id),
  INDEX idx_notifications_unread (user_id,is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Add GPS accuracy metadata to existing issue records.
ALTER TABLE issues ADD COLUMN location_accuracy DECIMAL(10,2) DEFAULT NULL;
-- New reports are created by the application as NOT OPENED. Existing valid statuses are preserved.
