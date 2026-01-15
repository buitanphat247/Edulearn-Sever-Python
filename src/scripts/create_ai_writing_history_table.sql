-- SQL Script để tạo bảng AIwritingHistory
-- Chạy script này trong MySQL để tạo bảng

CREATE TABLE IF NOT EXISTS `ai_writing_history` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` BIGINT UNSIGNED NOT NULL COMMENT 'Người dùng tạo nội dung',
  `data` JSON NOT NULL COMMENT 'Lưu NGUYÊN JSON AI trả về (nội dung practice)',
  `current_index` INT NOT NULL DEFAULT 0 COMMENT 'Đang làm tới sentence thứ mấy (index hiện tại)',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_user_created` (`user_id`, `created_at`),
  CONSTRAINT `fk_ai_writing_history_user` 
    FOREIGN KEY (`user_id`) 
    REFERENCES `users` (`user_id`) 
    ON DELETE CASCADE 
    ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

