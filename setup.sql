-- CIVICSENSE - Fresh MySQL schema
-- This script is for a new CIVICSENSE database.
-- The Flask app also auto-creates/migrates the same tables at startup.
-- Never store real passwords in this file.

CREATE DATABASE IF NOT EXISTS civicsense_prod
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE civicsense_prod;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  email VARCHAR(255) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  phone VARCHAR(30) DEFAULT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'user',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS issues (
  issue_id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  category VARCHAR(100) NOT NULL,
  latitude DECIMAL(10,8) DEFAULT NULL,
  longitude DECIMAL(11,8) DEFAULT NULL,
  location_accuracy DECIMAL(10,2) DEFAULT NULL,
  reported_by INT DEFAULT NULL,
  upvotes INT NOT NULL DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'not_opened',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_issues_category (category),
  INDEX idx_issues_status (status),
  INDEX idx_issues_reporter (reported_by),
  INDEX idx_issues_created (created_at),
  CONSTRAINT fk_issues_reporter FOREIGN KEY (reported_by) REFERENCES users(id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS issue_votes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  issue_id INT NOT NULL,
  user_id INT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_issue_user_vote (issue_id,user_id),
  CONSTRAINT fk_votes_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_votes_user FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS comments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  issue_id INT NOT NULL,
  user_id INT NOT NULL,
  comment_text VARCHAR(1000) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_comments_issue (issue_id),
  CONSTRAINT fk_comments_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_comments_user FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS issue_images (
  issue_id INT PRIMARY KEY,
  image_data LONGBLOB NOT NULL,
  mime_type VARCHAR(50) NOT NULL DEFAULT 'image/jpeg',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_issue_images_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS issue_status_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  issue_id INT NOT NULL,
  status VARCHAR(20) NOT NULL,
  changed_by INT DEFAULT NULL,
  note VARCHAR(500) DEFAULT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_status_history_issue (issue_id),
  INDEX idx_status_history_created (created_at),
  CONSTRAINT fk_status_history_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_status_history_user FOREIGN KEY (changed_by) REFERENCES users(id)
    ON DELETE SET NULL ON UPDATE CASCADE
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
  INDEX idx_notifications_unread (user_id,is_read),
  CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_notifications_issue FOREIGN KEY (issue_id) REFERENCES issues(issue_id)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Configure the first admin through environment variables:
-- ADMIN_EMAIL=admin@example.com
-- ADMIN_PASSWORD=change-this-password
-- The Flask application provisions/promotes the account at startup.
