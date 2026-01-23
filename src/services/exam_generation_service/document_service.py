import uuid
from datetime import datetime
from typing import Dict, List, Optional

from src.services.exam_generation_service.database_service import DatabaseService


class DocumentService:
    def __init__(self, db_service: DatabaseService = None):
        self.db_service = db_service or DatabaseService()
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Tables are now managed centrally in src/config/database.py using TABLE_SCHEMAS"""
        self._run_migrations()

    def _run_migrations(self):
        """Handle schema updates for existing tables"""
        try:
            # Check if max_attempts exists in ragtest
            check_col = "SHOW COLUMNS FROM ragtest LIKE 'max_attempts'"
            res = self.db_service.execute_query(check_col)
            if not res.get("rows"):
                print("Migrating ragtest: Adding max_attempts...")
                alter_q = "ALTER TABLE ragtest ADD COLUMN max_attempts INT DEFAULT 1"
                self.db_service.execute_query(alter_q)

            # Check if teacher_id exists in ragtest
            check_teacher = "SHOW COLUMNS FROM ragtest LIKE 'teacher_id'"
            res_teacher = self.db_service.execute_query(check_teacher)
            if not res_teacher.get("rows"):
                print("Migrating ragtest: Adding teacher_id...")
                alter_teacher = "ALTER TABLE ragtest ADD COLUMN teacher_id BIGINT"
                self.db_service.execute_query(alter_teacher)
        except Exception as e:
            print(f"Migration error: {e}")
            
    # --- CRUD Methods ---

    def create_document(self, name: str, status: str = "uploaded") -> str:
        doc_id = str(uuid.uuid4())
        query = """
            INSERT INTO ragdocument (id, name, status)
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
                INSERT INTO ragchunk (id, document_id, chunk_index, content)
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
            INSERT INTO ragquestion (id, document_id, chunk_id, content, answer_a, answer_b, answer_c, answer_d, correct_answer, difficulty, explanation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db_service.execute_query(query, (
            q_id, document_id, chunk_id, content, 
            answer_a, answer_b, answer_c, answer_d, 
            correct_answer, difficulty, explanation
        ))
        return q_id

    def create_test(self, title: str, description: str, document_id: str, num_questions: int, 
                    difficulty: str = "medium", duration_minutes: int = 45, total_score: int = 10, 
                    class_id: int = None, max_attempts: int = 1, teacher_id: int = None) -> str:
        t_id = str(uuid.uuid4())
        query = """
            INSERT INTO ragtest (id, title, description, document_id, num_questions, duration_minutes, total_score, class_id, max_attempts, teacher_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db_service.execute_query(query, (t_id, title, description, document_id, num_questions, duration_minutes, total_score, class_id, max_attempts, teacher_id))
        return t_id

    def add_question_to_test(self, test_id: str, question_id: str, score: int = 1, order: int = 0) -> str:
        mapping_id = str(uuid.uuid4())
        query = """
            INSERT INTO ragtestquestion (id, rag_test_id, question_id, score, question_order)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.db_service.execute_query(query, (mapping_id, test_id, question_id, score, order))
        return mapping_id
        
    def update_document_status(self, document_id: str, status: str):
        query = "UPDATE ragdocument SET status = %s WHERE id = %s"
        self.db_service.execute_query(query, (status, document_id))
    
    def get_chunks_by_document(self, document_id: str) -> List[Dict]:
        query = "SELECT id, chunk_index, content FROM ragchunk WHERE document_id = %s ORDER BY chunk_index"
        self.db_service.execute_query(query, (document_id,))
        chunks = []
        rows = result.get("rows", [])
        for row in rows:
            chunks.append({
                "id": row[0],
                "chunk_index": row[1],
                "content": row[2]
            })
        return chunks

    def get_published_tests_by_class(self, class_id: int, student_id: int = None) -> List[Dict]:
        """
        [Học sinh] Lấy đề thi đã xuất bản trong lớp
        """
        query = """
            SELECT t.id, t.title, t.description, t.num_questions, t.duration_minutes, t.total_score, 
                   t.created_at, t.mode, t.max_attempts, t.end_at, t.max_violations,
                   COALESCE(s.attempt_count, 0) as user_attempt_count
            FROM ragtest t
            LEFT JOIN ragteststatus s ON t.id = s.rag_test_id AND s.student_id = %s
            WHERE t.class_id = %s AND t.is_published = 1
            ORDER BY t.created_at DESC
        """
        params = (student_id, class_id)
        result = self.db_service.execute_query(query, params)
        # ... (logic xử lý remaining_attempts giữ nguyên như cũ)
        tests = []
        for row in result.get("rows", []):
            max_attempts = row[8]
            user_attempts = row[11]
            remaining = max(0, max_attempts - user_attempts) if max_attempts > 0 else 999
            tests.append({
                "id": row[0], "title": row[1], "description": row[2],
                "num_questions": row[3], "duration_minutes": row[4], "total_score": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "mode": row[7], "max_attempts": max_attempts,
                "end_at": row[9].isoformat() if row[9] else None,
                "max_violations": row[10],
                "user_attempt_count": user_attempts, "remaining_attempts": remaining
            })
        return tests

    def get_teacher_tests(self, class_id: int) -> List[Dict]:
        """
        [Giáo viên] Lấy TOÀN BỘ đề thi trong lớp (bao gồm cả nháp và đã xuất bản)
        """
        query = """
            SELECT id, title, description, num_questions, duration_minutes, total_score, 
                   created_at, is_published, mode, max_attempts, class_id, end_at, max_violations
             FROM ragtest
            WHERE class_id = %s
            ORDER BY created_at DESC
        """
        result = self.db_service.execute_query(query, (class_id,))
        tests = []
        for row in result.get("rows", []):
            tests.append({
                "id": row[0], "title": row[1], "description": row[2],
                "num_questions": row[3], "duration_minutes": row[4], "total_score": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "is_published": bool(row[7]), "mode": row[8], "max_attempts": row[9],
                "class_id": row[10],
                "end_at": row[11].isoformat() if row[11] else None,
                "max_violations": row[12]
            })
        return tests

    def get_test_details(self, test_id: str, student_id: int = None) -> Optional[Dict]:
        # 1. Get Test Info (including max_attempts)
        # 1. Get Test Info (including max_attempts, end_at, max_violations)
        query_test = """
            SELECT id, title, description, num_questions, duration_minutes, total_score, created_at, 
                   is_published, mode, document_id, max_attempts, end_at, max_violations
            FROM ragtest WHERE id = %s
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
                SELECT id FROM ragtestattempt 
                WHERE rag_test_id = %s AND student_id = %s AND status = 'in_progress'
            """
            active_res = self.db_service.execute_query(check_active, (test_id, student_id))
            
            if not active_res.get("rows"):
                # No active attempt, check if they can start a new one
                status_q = "SELECT attempt_count FROM ragteststatus WHERE rag_test_id = %s AND student_id = %s"
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
            "max_attempts": row[10],
            "end_at": row[11].isoformat() if row[11] else None,
            "max_violations": row[12],
            "questions": []
        }

        # 2. Get Questions
        query_questions = """
            SELECT q.id, q.content, q.answer_a, q.answer_b, q.answer_c, q.answer_d, q.correct_answer, q.explanation, tq.score, tq.question_order
            FROM ragquestion q
            JOIN ragtestquestion tq ON q.id = tq.question_id
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
        Xóa đề thi và các tài nguyên liên quan một cách tuần tự (Sử dụng Manual Transaction)
        """
        cursor = self.db_service.get_cursor()
        try:
            # 1. Lấy document_id
            cursor.execute("SELECT document_id FROM ragtest WHERE id = %s", (test_id,))
            doc_row = cursor.fetchone()
            if not doc_row:
                cursor.close()
                return False
            
            doc_id = doc_row[0]

            # 2. Xóa bài thi (Sẽ trigger CASCADE xóa attempts, mappings, security)
            cursor.execute("DELETE FROM ragtest WHERE id = %s", (test_id,))

            # 3. Kiểm tra xem còn đề thi nào khác dùng chung document này không
            cursor.execute("SELECT COUNT(*) FROM ragtest WHERE document_id = %s", (doc_id,))
            count = cursor.fetchone()[0]

            # 4. Nếu không còn bài thi nào, dọn dẹp nốt Document
            if count == 0:
                print(f"Cleanup: Xóa tài liệu mồ côi (Document ID: {doc_id})")
                cursor.execute("DELETE FROM ragdocument WHERE id = %s", (doc_id,))
                # Cascades to ragchunk, ragquestion

            # Commit toàn bộ nếu thành công
            self.db_service.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Error atomic delete test {test_id}: {e}")
            self.db_service.rollback()
            if cursor: cursor.close()
            return False

    def delete_all_tests_by_class(self, class_id: int) -> bool:
        """
        Xóa toàn bộ đề thi thuộc về một lớp học (Dùng khi xóa lớp)
        """
        try:
            # 1. Lấy danh sách tất cả test của lớp này
            q_get_tests = "SELECT id FROM ragtest WHERE class_id = %s"
            res = self.db_service.execute_query(q_get_tests, (class_id,))
            
            test_ids = [row[0] for row in res.get("rows", [])]
            
            # 2. Xóa từng test (để tận dụng logic cleanup Document của delete_test)
            for tid in test_ids:
                self.delete_test(tid)
            
            return True
        except Exception as e:
            print(f"Error deleting all tests for class {class_id}: {e}")
            return False

    def update_test(self, test_id: str, data: Dict) -> bool:
        """Update test metadata"""
        try:
            print(f"DEBUG: update_test called for {test_id}")
            print(f"DEBUG: Data received: {data}")
            fields = []
            values = []
            for k, v in data.items():
                if k in ['title', 'description', 'duration_minutes', 'total_score', 'max_attempts', 'is_published', 'end_at', 'max_violations']:
                    fields.append(f"{k} = %s")
                    values.append(v)
            
            if not fields: 
                print("DEBUG: No valid fields to update")
                return False
            
            query = f"UPDATE ragtest SET {', '.join(fields)} WHERE id = %s"
            values.append(test_id)
            print(f"DEBUG: Executing Query: {query}")
            print(f"DEBUG: Values: {values}")
            
            result = self.db_service.execute_query(query, tuple(values))
            print(f"DEBUG: Query Result: {result}")
            
            if result and result.get("affected_rows", 0) > 0:
                print(f"DEBUG: Successfully updated {result['affected_rows']} rows.")
                return True
            else:
                print(f"DEBUG: No rows updated? rowcount: {result.get('affected_rows') if result else 'None'}")
                # Note: valid update with same values returns 0 affected_rows in some configs
                # but usually we want to know if 'id' existed. 
                # For now let's assume if it runs without exception it's 'successful' 
                # but we warn if 0.
                
                # Double check if ID exists
                check_q = "SELECT id FROM ragtest WHERE id = %s"
                check_res = self.db_service.execute_query(check_q, (test_id,))
                if check_res and check_res.get("rows"):
                    print("DEBUG: Test ID exists, but no rows changed (maybe data identical?)")
                    return True
                else:
                    print("DEBUG: Test ID NOT FOUND in database")
                    return False
                    
        except Exception as e:
            print(f"Error updating test: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_question(self, question_id: str, data: Dict) -> bool:
        """Update question content and options"""
        try:
            fields = []
            values = []
            valid_fields = ['content', 'answer_a', 'answer_b', 'answer_c', 'answer_d', 'correct_answer', 'explanation', 'difficulty']
            for k, v in data.items():
                if k in valid_fields:
                    fields.append(f"{k} = %s")
                    values.append(v)
            
            if not fields: return False
            
            query = f"UPDATE ragquestion SET {', '.join(fields)} WHERE id = %s"
            values.append(question_id)
            self.db_service.execute_query(query, tuple(values))
            return True
        except Exception as e:
            print(f"Error updating question: {e}")
            return False
