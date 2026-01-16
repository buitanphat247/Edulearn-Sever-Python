TABLE_SCHEMAS = [
    # 1. ragdocument (Gốc)
    """
    CREATE TABLE IF NOT EXISTS ragdocument (
        id VARCHAR(100) PRIMARY KEY,
        name VARCHAR(255),
        status ENUM('uploaded','processing','indexed','failed') DEFAULT 'uploaded',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # 2. ragchunk (Con của ragdocument)
    """
    CREATE TABLE IF NOT EXISTS ragchunk (
        id VARCHAR(100) PRIMARY KEY,
        document_id VARCHAR(100) NOT NULL,
        chunk_index INT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES ragdocument(id) ON DELETE CASCADE
    )
    """,
    # 3. ragquestion (Con của ragdocument & ragchunk)
    """
    CREATE TABLE IF NOT EXISTS ragquestion (
        id VARCHAR(100) PRIMARY KEY,
        document_id VARCHAR(100) NOT NULL,
        chunk_id VARCHAR(100) NOT NULL,
        content TEXT,
        answer_a TEXT,
        answer_b TEXT,
        answer_c TEXT,
        answer_d TEXT,
        correct_answer CHAR(1),
        difficulty ENUM('easy','medium','hard'),
        explanation TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES ragdocument(id) ON DELETE CASCADE,
        FOREIGN KEY (chunk_id) REFERENCES ragchunk(id) ON DELETE CASCADE
    )
    """,
    # 4. ragtest (Con của ragdocument) - Quan trọng: Phải tạo trước ragtestattempt
    """
    CREATE TABLE IF NOT EXISTS ragtest (
        id VARCHAR(100) PRIMARY KEY,
        class_id BIGINT,
        document_id VARCHAR(100) NOT NULL,
        title VARCHAR(255),
        description TEXT,
        mode ENUM('practice','official') NOT NULL DEFAULT 'practice',
        duration_minutes INT DEFAULT 45,
        total_score INT DEFAULT 10,
        num_questions INT,
        max_attempts INT DEFAULT 1,
        created_by ENUM('AI','teacher') DEFAULT 'AI',
        is_published BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (document_id) REFERENCES ragdocument(id) ON DELETE CASCADE
    )
    """,
    # 5. ragtestquestion (Liên kết Test & Question)
    """
    CREATE TABLE IF NOT EXISTS ragtestquestion (
        id VARCHAR(100) PRIMARY KEY,
        rag_test_id VARCHAR(100) NOT NULL,
        question_id VARCHAR(100) NOT NULL,
        score INT DEFAULT 1,
        question_order INT,
        FOREIGN KEY (rag_test_id) REFERENCES ragtest(id) ON DELETE CASCADE,
        FOREIGN KEY (question_id) REFERENCES ragquestion(id) ON DELETE CASCADE
    )
    """,
    # 6. ragtestattempt (Lượt làm bài - Con của ragtest)
    """
    CREATE TABLE IF NOT EXISTS ragtestattempt (
        id VARCHAR(100) PRIMARY KEY,
        rag_test_id VARCHAR(100) NOT NULL,
        class_id BIGINT NOT NULL,
        student_id BIGINT NOT NULL,
        mode ENUM('practice','official') NOT NULL,
        status ENUM('in_progress','submitted','expired') DEFAULT 'in_progress',
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NULL,
        last_heartbeat_at TIMESTAMP NULL,
        answers JSON,
        score FLOAT DEFAULT 0,
        submitted_at TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (rag_test_id) REFERENCES ragtest(id) ON DELETE CASCADE
    )
    """,
    # 7. ragteststatus (Theo dõi số lần làm bài)
    """
    CREATE TABLE IF NOT EXISTS ragteststatus (
        id VARCHAR(100) PRIMARY KEY,
        rag_test_id VARCHAR(100) NOT NULL,
        student_id BIGINT NOT NULL,
        attempt_count INT DEFAULT 0,
        last_attempt_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY unique_progress (rag_test_id, student_id),
        FOREIGN KEY (rag_test_id) REFERENCES ragtest(id) ON DELETE CASCADE
    )
    """,
    # 8. ragtestattemptsecurity (Bảo mật phòng thi)
    """
    CREATE TABLE IF NOT EXISTS ragtestattemptsecurity (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        attempt_id VARCHAR(100) NOT NULL,
        reload_count INT DEFAULT 0,
        tab_hidden_count INT DEFAULT 0,
        disconnect_count INT DEFAULT 0,
        last_event VARCHAR(50),
        violation_logs JSON,
        suspicious_level INT DEFAULT 0,
        is_terminated BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP NULL ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (attempt_id) REFERENCES ragtestattempt(id) ON DELETE CASCADE
    )
    """
]
