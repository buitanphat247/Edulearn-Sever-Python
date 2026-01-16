import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from src.services.exam_generation_service.database_service import DatabaseService

class ExamService:
    def __init__(self, db_service: DatabaseService = None):
        self.db_service = db_service or DatabaseService()
        self._ensure_tables()

    def _ensure_tables(self):
        # Tables are now managed centrally in src/config/database.py using TABLE_SCHEMAS
        pass

    # --- Core Logic ---

    def _parse_json(self, data):
        """Helper to handle JSON data which might be string or pre-parsed dict/list"""
        if data is None: return None
        if isinstance(data, (dict, list)): return data
        try:
            return json.loads(data)
        except:
            return None

    def start_attempt(self, rag_test_id: str, class_id: int, student_id: int, mode: str = "practice") -> Dict:
        """Bắt đầu hoặc Tiếp tục một lượt làm bài"""
        
        # 0. Check for existing 'in_progress' attempt to resume
        resume_query = "SELECT id, started_at, expires_at, answers FROM ragtestattempt WHERE rag_test_id = %s AND student_id = %s AND status = 'in_progress'"
        resume_res = self.db_service.execute_query(resume_query, (rag_test_id, student_id))
        
        if resume_res.get("rows"):
            row = resume_res["rows"][0]
            attempt_id, started_at, expires_at, answers_json = row

            # Fetch violation count
            sec_q = "SELECT violation_logs FROM ragtestattemptsecurity WHERE attempt_id = %s"
            sec_res = self.db_service.execute_query(sec_q, (attempt_id,))
            violation_count = 0
            if sec_res.get("rows"):
                logs = self._parse_json(sec_res["rows"][0][0]) or []
                violation_count = len(logs)

            # Verify if it's REALLY not expired yet
            if datetime.now() < expires_at:
                current_answers = self._parse_json(answers_json) or {}

                return {
                    "attempt_id": attempt_id,
                    "started_at": started_at.isoformat(),
                    "expires_at": expires_at.isoformat(),
                    "status": "in_progress",
                    "resumed": True,
                    "answers": current_answers,
                    "violation_count": violation_count
                }
            else:
                self._force_submit_expired(attempt_id)

        # 1. Check if test exists and get details
        test_query = "SELECT duration_minutes, max_attempts FROM ragtest WHERE id = %s"
        test_res = self.db_service.execute_query(test_query, (rag_test_id,))
        if not test_res.get("rows"):
            raise ValueError("Test not found")
        
        duration = test_res["rows"][0][0]
        max_attempts = test_res["rows"][0][1]
        
        # 2. Check Attempt Count (ragteststatus)
        status_query = "SELECT attempt_count FROM ragteststatus WHERE rag_test_id = %s AND student_id = %s"
        status_res = self.db_service.execute_query(status_query, (rag_test_id, student_id))
        
        current_count = 0
        if status_res.get("rows"):
            current_count = status_res["rows"][0][0]
            
        if max_attempts > 0 and current_count >= max_attempts:
             raise ValueError(f"Bạn đã hết số lần làm bài cho phép (Tối đa {max_attempts} lần).")

        # Update or Insert Status (Mark one attempt as 'started')
        upsert_query = """
            INSERT INTO ragteststatus (id, rag_test_id, student_id, attempt_count, last_attempt_at)
            VALUES (%s, %s, %s, 1, NOW())
            ON DUPLICATE KEY UPDATE attempt_count = attempt_count + 1, last_attempt_at = NOW()
        """
        status_id = str(uuid.uuid4())
        self.db_service.execute_query(upsert_query, (status_id, rag_test_id, student_id))

        # 3. Create Attempt Record
        started_at = datetime.now()
        expires_at = started_at + timedelta(minutes=duration)
        attempt_id = str(uuid.uuid4())
        
        query = """
            INSERT INTO ragtestattempt 
            (id, rag_test_id, class_id, student_id, mode, status, started_at, expires_at)
            VALUES (%s, %s, %s, %s, %s, 'in_progress', %s, %s)
        """
        self.db_service.execute_query(query, (
            attempt_id, rag_test_id, class_id, student_id, mode, started_at, expires_at
        ))

        # 4. Init Security Record
        sec_query = "INSERT INTO ragtestattemptsecurity (attempt_id) VALUES (%s)"
        self.db_service.execute_query(sec_query, (attempt_id,))

        return {
            "attempt_id": attempt_id,
            "started_at": started_at.isoformat(),
            "expires_at": expires_at.isoformat(),
            "status": "in_progress",
            "resumed": False,
            "violation_count": 0
        }

    def submit_attempt(self, attempt_id: str, answers: Dict, student_id: int) -> Dict:
        """Nộp bài (Submit)"""
        
        # 1. Get Attempt Info
        get_q = "SELECT rag_test_id, status FROM ragtestattempt WHERE id = %s AND student_id = %s"
        res = self.db_service.execute_query(get_q, (attempt_id, student_id))
        if not res.get("rows"):
            raise ValueError("Attempt not found or invalid user")
        
        rag_test_id, status = res["rows"][0]
        
        if status != 'in_progress':
            raise ValueError(f"Bài thi đã ở trạng thái {status}, không thể nộp lại.")

        # 2. Calculate Score
        # Fetch correct answers
        q_sql = """
            SELECT q.id, q.correct_answer, tq.score 
            FROM ragquestion q
            JOIN ragtestquestion tq ON q.id = tq.question_id
            WHERE tq.rag_test_id = %s
        """
        q_res = self.db_service.execute_query(q_sql, (rag_test_id,))
        
        total_score = 0
        earned_score = 0
        
        for row in q_res.get("rows", []):
            qid, correct_char, points = row[0], row[1], row[2]
            total_score += points
            user_ans = answers.get(qid)
            if user_ans and str(user_ans).upper() == str(correct_char).upper():
                earned_score += points
        
        final_score = earned_score

        # 3. Update Attempt
        update_q = """
            UPDATE ragtestattempt 
            SET status = 'submitted', submitted_at = %s, answers = %s, score = %s
            WHERE id = %s
        """
        self.db_service.execute_query(update_q, (
            datetime.now(), json.dumps(answers), final_score, attempt_id
        ))

        return {
            "status": "submitted",
            "score": final_score,
            "max_score": total_score
        }

    def log_security_event(self, attempt_id: str, event_type: str, details: str = None) -> Dict:
        """
        event_type: 'reload', 'tab_hidden', 'disconnect', etc.
        """
        # 1. Get current security record
        get_sec = "SELECT id, reload_count, tab_hidden_count, disconnect_count, violation_logs FROM ragtestattemptsecurity WHERE attempt_id = %s"
        res = self.db_service.execute_query(get_sec, (attempt_id,))
        if not res.get("rows"):
             # Create if missing (sanity check)
             self.db_service.execute_query("INSERT INTO ragtestattemptsecurity (attempt_id, violation_logs) VALUES (%s, '[]')", (attempt_id,))
             res = self.db_service.execute_query(get_sec, (attempt_id,))
        
        row = res["rows"][0]
        sec_id = row[0]
        reload_c, tab_c, disconnect_c = row[1], row[2], row[3]
        
        try:
             current_logs = self._parse_json(row[4]) or []
        except:
             current_logs = []

        update_field = ""
        new_val = 0
        
        if event_type == 'reload':
            reload_c += 1
            update_field = "reload_count = %s, "
            new_val = reload_c
        elif event_type == 'tab_hidden':
            tab_c += 1
            update_field = "tab_hidden_count = %s, "
            new_val = tab_c
        elif event_type == 'disconnect':
            disconnect_c += 1
            update_field = "disconnect_count = %s, "
            new_val = disconnect_c
        
        # Add new log entry
        new_log = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        current_logs.append(new_log)
        
        # Limit logs
        if len(current_logs) > 200:
             current_logs = current_logs[-200:]
             
        sql = f"""
            UPDATE ragtestattemptsecurity 
            SET {update_field} last_event = %s, violation_logs = %s, updated_at = %s
            WHERE id = %s
        """
        
        # Prepare params
        params = []
        if update_field:
            params.append(new_val)
        params.append(event_type)
        params.append(json.dumps(current_logs))
        params.append(datetime.now())
        params.append(sec_id)
        
        self.db_service.execute_query(sql, tuple(params))
        
        return {
            "status": "logged",
            "counts": {
                "reload": reload_c,
                "tab_hidden": tab_c,
                "disconnect": disconnect_c,
                "total_logs": len(current_logs)
            }
        }

    def update_heartbeat(self, attempt_id: str) -> Dict:
        """Cập nhật nhịp tim và kiểm tra thời gian làm bài"""
        query = "SELECT expires_at, status FROM ragtestattempt WHERE id = %s"
        res = self.db_service.execute_query(query, (attempt_id,))
        if not res.get("rows"):
            return {"status": "error", "message": "Attempt not found"}
        
        expires_at, status = res["rows"][0]
        if status != 'in_progress':
            return {"status": status, "is_expired": True, "remaining_seconds": 0}

        now = datetime.now()
        is_expired = now > expires_at
        remaining_seconds = max(0, int((expires_at - now).total_seconds()))

        # Update heartbeat timestamp
        update_q = "UPDATE ragtestattempt SET last_heartbeat_at = %s WHERE id = %s"
        self.db_service.execute_query(update_q, (now, attempt_id))

        if is_expired:
            self._force_submit_expired(attempt_id)
            return {"status": "expired", "is_expired": True, "remaining_seconds": 0}

        return {
            "status": "in_progress",
            "is_expired": False,
            "remaining_seconds": remaining_seconds
        }

    def get_remaining_time(self, attempt_id: str) -> Dict:
        """Lấy thời gian còn lại chính xác từ server"""
        query = "SELECT expires_at, status FROM ragtestattempt WHERE id = %s"
        res = self.db_service.execute_query(query, (attempt_id,))
        if not res.get("rows"):
            return {"status": "error", "message": "Attempt not found"}
        
        expires_at, status = res["rows"][0]
        now = datetime.now()
        remaining_seconds = max(0, int((expires_at - now).total_seconds()))
        
        return {
            "status": status,
            "remaining_seconds": remaining_seconds,
            "is_expired": now > expires_at
        }

    def _force_submit_expired(self, attempt_id: str):
        """Tự động nộp bài khi hết giờ"""
        # Mark as expired
        update_q = "UPDATE ragtestattempt SET status = 'expired', submitted_at = NOW() WHERE id = %s"
        self.db_service.execute_query(update_q, (attempt_id,))

    def save_answers(self, attempt_id: str, answers: Dict) -> Dict:
        """Lưu lại danh sách câu trả lời nháp"""
        try:
            query = "UPDATE ragtestattempt SET answers = %s WHERE id = %s AND status = 'in_progress'"
            self.db_service.execute_query(query, (json.dumps(answers), attempt_id))
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def auto_submit_expired_attempts(self):
        """Quét và tự động nộp tất cả bài thi hết hạn (Dùng cho Cron/Worker)"""
        query = """
            UPDATE ragtestattempt 
            SET status = 'expired', submitted_at = NOW()
            WHERE status = 'in_progress' AND expires_at < NOW()
        """
        res = self.db_service.execute_query(query)
        return res.get("affected_rows", 0)

    def get_test_attempts(self, rag_test_id: str) -> List[Dict]:
        """Lấy danh sách tất cả các lượt làm bài của một đề thi (Admin view)"""
        query = """
            SELECT a.id, a.student_id, u.fullname, a.status, a.score, a.started_at, a.submitted_at, 
                   s.reload_count, s.tab_hidden_count, s.disconnect_count, s.violation_logs,
                   a.answers, ts.attempt_count
            FROM ragtestattempt a
            JOIN users u ON a.student_id = u.user_id
            LEFT JOIN ragtestattemptsecurity s ON a.id = s.attempt_id
            LEFT JOIN ragteststatus ts ON a.rag_test_id = ts.rag_test_id AND a.student_id = ts.student_id
            WHERE a.rag_test_id = %s
            ORDER BY a.started_at DESC
        """
        result = self.db_service.execute_query(query, (rag_test_id,))
        attempts = []
        for row in result.get("rows", []):
            answers = self._parse_json(row[11]) or {}
            attempts.append({
                "id": row[0],
                "student_id": row[1],
                "student_name": row[2],
                "status": row[3],
                "score": row[4],
                "started_at": row[5].isoformat() if row[5] else None,
                "submitted_at": row[6].isoformat() if row[6] else None,
                "answered_count": len(answers),
                "attempt_count": row[12] or 1, # Thêm trường này, mặc định là 1 nếu chưa có trong Status
                "security": {
                    "reload": row[7] or 0,
                    "tab_hidden": row[8] or 0,
                    "disconnect": row[9] or 0,
                    "logs": self._parse_json(row[10]) or []
                }
            })
        return attempts
