import uuid
from datetime import datetime
from typing import Dict, List, Optional

from src.services.exam_generation_service.database_service import DatabaseService


class DocumentService:
    def __init__(self, db_service: DatabaseService = None):
        self.db_service = db_service or DatabaseService()
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create tables if not exists (MySQL Schema)"""
        queries = [
            # 1. RagDocument
            """
            CREATE TABLE IF NOT EXISTS RagDocument (
                id VARCHAR(100) PRIMARY KEY,
                name VARCHAR(255),
                status ENUM('uploaded','processing','indexed','failed') DEFAULT 'uploaded',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            # 2. RagChunk
            """
            CREATE TABLE IF NOT EXISTS RagChunk (
                id VARCHAR(100) PRIMARY KEY,
                document_id VARCHAR(100) NOT NULL,
                chunk_index INT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES RagDocument(id) ON DELETE CASCADE
            )
            """,
            # 3. RagQuestion
            """
            CREATE TABLE IF NOT EXISTS RagQuestion (
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
                FOREIGN KEY (document_id) REFERENCES RagDocument(id) ON DELETE CASCADE,
                FOREIGN KEY (chunk_id) REFERENCES RagChunk(id) ON DELETE CASCADE
            )
            """,
            # 4. RagTest
            """
            CREATE TABLE IF NOT EXISTS RagTest (
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
                FOREIGN KEY (document_id) REFERENCES RagDocument(id) ON DELETE CASCADE
            )
            """,
            # 5. RagTestQuestion
            """
            CREATE TABLE IF NOT EXISTS RagTestQuestion (
                id VARCHAR(100) PRIMARY KEY,
                rag_test_id VARCHAR(100) NOT NULL,
                question_id VARCHAR(100) NOT NULL,
                score INT DEFAULT 1,
                question_order INT,
                FOREIGN KEY (rag_test_id) REFERENCES RagTest(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES RagQuestion(id) ON DELETE CASCADE
            )
            """
        ]
        
        for q in queries:
            try:
                self.db_service.execute_query(q)
            except Exception as e:
                print(f"Schema error: {e}")
                pass
        
        self._run_migrations()

    def _run_migrations(self):
        """Handle schema updates for existing tables"""
        try:
            # Check if max_attempts exists in RagTest
            check_col = "SHOW COLUMNS FROM RagTest LIKE 'max_attempts'"
            res = self.db_service.execute_query(check_col)
            if not res.get("rows"):
                print("Migrating RagTest: Adding max_attempts...")
                alter_q = "ALTER TABLE RagTest ADD COLUMN max_attempts INT DEFAULT 1"
                self.db_service.execute_query(alter_q)
        except Exception as e:
            print(f"Migration error: {e}")
            
    # --- CRUD Methods ---

    def create_document(self, name: str, status: str = "uploaded") -> str:
        doc_id = str(uuid.uuid4())
        query = """
            INSERT INTO RagDocument (id, name, status)
            VALUES (%s, %s, %s)
        """
        self.db_service.execute_query(query, (doc_id, name, status))
        return doc_id

    def create_chunks(self, document_id: str, chunks_data: List[Dict]) -> List[str]:
        if not chunks_data:
            return []
            
        ids = []
        for chunk in chunks_data:
            c_id = str(uuid.uuid4())
            query = """
                INSERT INTO RagChunk (id, document_id, chunk_index, content)
                VALUES (%s, %s, %s, %s)
            """
            self.db_service.execute_query(query, (c_id, document_id, chunk['chunk_index'], chunk['text']))
            ids.append(c_id)
        return ids

    def create_question(self, document_id: str, chunk_id: str, content: str, 
                       answer_a: str, answer_b: str, answer_c: str, answer_d: str, 
                       correct_answer: str, difficulty: str = "medium", explanation: str = None) -> str:
        q_id = str(uuid.uuid4())
        query = """
            INSERT INTO RagQuestion (id, document_id, chunk_id, content, answer_a, answer_b, answer_c, answer_d, correct_answer, difficulty, explanation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db_service.execute_query(query, (
            q_id, document_id, chunk_id, content, 
            answer_a, answer_b, answer_c, answer_d, 
            correct_answer, difficulty, explanation
        ))
        return q_id

    def create_test(self, title: str, description: str, document_id: str, num_questions: int, 
                    difficulty: str = "medium", duration_minutes: int = 45, total_score: int = 10, class_id: int = None, max_attempts: int = 1) -> str:
        t_id = str(uuid.uuid4())
        query = """
            INSERT INTO RagTest (id, title, description, document_id, num_questions, duration_minutes, total_score, class_id, max_attempts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db_service.execute_query(query, (t_id, title, description, document_id, num_questions, duration_minutes, total_score, class_id, max_attempts))
        return t_id

    def add_question_to_test(self, test_id: str, question_id: str, score: int = 1, order: int = 0) -> str:
        mapping_id = str(uuid.uuid4())
        query = """
            INSERT INTO RagTestQuestion (id, rag_test_id, question_id, score, question_order)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.db_service.execute_query(query, (mapping_id, test_id, question_id, score, order))
        return mapping_id
        
    def update_document_status(self, document_id: str, status: str):
        query = "UPDATE RagDocument SET status = %s WHERE id = %s"
        self.db_service.execute_query(query, (status, document_id))
    
    def get_chunks_by_document(self, document_id: str) -> List[Dict]:
        query = "SELECT id, chunk_index, content FROM RagChunk WHERE document_id = %s ORDER BY chunk_index"
        result = self.db_service.execute_query(query, (document_id,))
        chunks = []
        rows = result.get("rows", [])
        for row in rows:
            chunks.append({
                "id": row[0],
                "chunk_index": row[1],
                "content": row[2]
            })
        return chunks

    def get_tests_by_class(self, class_id: int, student_id: int = None) -> List[Dict]:
        """
        Get tests by class, optionally with attempt info for a specific student.
        """
        if student_id:
            # Join with Attempts count
            query = """
                SELECT t.id, t.title, t.description, t.num_questions, t.duration_minutes, t.total_score, 
                       t.created_at, t.is_published, t.mode, t.max_attempts,
                       COALESCE(s.attempt_count, 0) as user_attempt_count
                FROM RagTest t
                LEFT JOIN RagTestStatus s ON t.id = s.rag_test_id AND s.student_id = %s
                WHERE t.class_id = %s 
                ORDER BY t.created_at DESC
            """
            params = (student_id, class_id)
        else:
            query = """
                SELECT id, title, description, num_questions, duration_minutes, total_score, created_at, is_published, mode, max_attempts, 0 as user_attempt_count
                FROM RagTest 
                WHERE class_id = %s 
                ORDER BY created_at DESC
            """
            params = (class_id,)
            
        result = self.db_service.execute_query(query, params)
        tests = []
        rows = result.get("rows", [])
        for row in rows:
            tests.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "num_questions": row[3],
                "duration_minutes": row[4],
                "total_score": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "is_published": bool(row[7]),
                "mode": row[8],
                "max_attempts": row[9] if len(row) > 9 else 1,
                "user_attempt_count": row[10] if len(row) > 10 else 0
            })
        return tests

    def get_test_details(self, test_id: str, student_id: int = None) -> Optional[Dict]:
        # 1. Get Test Info (including max_attempts)
        query_test = """
            SELECT id, title, description, num_questions, duration_minutes, total_score, created_at, is_published, mode, document_id, max_attempts
            FROM RagTest WHERE id = %s
        """
        res_test = self.db_service.execute_query(query_test, (test_id,))
        if not res_test.get("rows"):
            return None
        
        row = res_test["rows"][0]
        max_attempts = row[10]

        # 1.1 Check Attempts if student_id is provided
        if student_id:
            # Check for existing 'in_progress' attempt first. 
            # If they have an active attempt, they CAN see questions.
            check_active = """
                SELECT id FROM RagTestAttempt 
                WHERE rag_test_id = %s AND student_id = %s AND status = 'in_progress'
            """
            active_res = self.db_service.execute_query(check_active, (test_id, student_id))
            
            if not active_res.get("rows"):
                # No active attempt, check if they can start a new one
                status_q = "SELECT attempt_count FROM RagTestStatus WHERE rag_test_id = %s AND student_id = %s"
                status_res = self.db_service.execute_query(status_q, (test_id, student_id))
                
                current_count = 0
                if status_res.get("rows"):
                    current_count = status_res["rows"][0][0]
                
                if max_attempts > 0 and current_count >= max_attempts:
                    raise ValueError(f"Bạn đã hết lượt làm bài bài thi này (Tối đa {max_attempts} lần).")
        test_data = {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "num_questions": row[3],
            "duration_minutes": row[4],
            "total_score": row[5],
            "created_at": row[6].isoformat() if row[6] else None,
            "is_published": bool(row[7]),
            "mode": row[8],
            "document_id": row[9],
            "max_attempts": row[10], # Thêm trường này
            "questions": []
        }

        # 2. Get Questions
        query_questions = """
            SELECT q.id, q.content, q.answer_a, q.answer_b, q.answer_c, q.answer_d, q.correct_answer, q.explanation, tq.score, tq.question_order
            FROM RagQuestion q
            JOIN RagTestQuestion tq ON q.id = tq.question_id
            WHERE tq.rag_test_id = %s
            ORDER BY tq.question_order ASC
        """
        res_qs = self.db_service.execute_query(query_questions, (test_id,))
        for r in res_qs.get("rows", []):
            test_data["questions"].append({
                "id": r[0],
                "content": r[1],
                "options": [r[2], r[3], r[4], r[5]],
                "correct_answer": r[6],
                "explanation": r[7],
                "score": r[8],
                "order": r[9]
            })
        
        return test_data

    def delete_test(self, test_id: str) -> bool:
        """
        Delete a Test and its associated question mappings (Transactionally)
        """
        try:
            # 1. Delete mappings in RagTestQuestion
            q1 = "DELETE FROM RagTestQuestion WHERE rag_test_id = %s"
            # 2. Delete the test itself
            q2 = "DELETE FROM RagTest WHERE id = %s"
            
            self.db_service.execute_query(q1, (test_id,))
            self.db_service.execute_query(q2, (test_id,))
            
            return True
        except Exception as e:
            print(f"Error deleting test {test_id}: {e}")
            self.db_service.rollback()
            return False
