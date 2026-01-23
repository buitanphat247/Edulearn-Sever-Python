import sys
import os
import mysql.connector
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

# Load env
load_dotenv()

class LightDatabaseService:
    def __init__(self):
        self.connection = None
    
    def _get_connection_params(self) -> Dict[str, str]:
        return {
            "host": os.getenv("DB_MYSQL_HOST", os.getenv("DB_HOST", "127.0.0.1")),
            "port": os.getenv("DB_MYSQL_PORT", os.getenv("DB_PORT", "3306")),
            "database": os.getenv("DB_MYSQL_NAME", os.getenv("DB_NAME", "edulearning")),
            "user": os.getenv("DB_MYSQL_USER", os.getenv("DB_USER", "root")),
            "password": os.getenv("DB_MYSQL_PASS", os.getenv("DB_PASSWORD", ""))
        }
    
    def _connect(self):
        if self.connection and self.connection.is_connected():
            return
        
        try:
            params = self._get_connection_params()
            print(f"Connecting to DB: {params['host']}:{params['port']} user={params['user']} db={params['database']}")
            self.connection = mysql.connector.connect(**params)
            self.connection.autocommit = False 
        except mysql.connector.Error as e:
            raise ValueError(f"MySQL Error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Connection Error: {str(e)}")

    def execute_query(self, query: str, params: Optional[Tuple] = None):
        self._connect()
        cursor = self.connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            query_type = query.strip().upper()
            if query_type.startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")):
                results = cursor.fetchall()
                self.connection.commit()
                cursor.close()
                return {
                    "rows": results,
                    "row_count": len(results)
                }
            else:
                affected = cursor.rowcount
                self.connection.commit()
                cursor.close()
                return {"affected_rows": affected}
        except Exception as e:
            if cursor: cursor.close()
            if self.connection: self.connection.rollback()
            raise ValueError(f"Query Error: {str(e)}")

def update_ragtest_data():
    print("Starting data migration (Lightweight Mode)...")
    
    db_service = LightDatabaseService()
    
    # 1. Check Columns
    print("Checking columns...")
    check_col_query = """
        SELECT count(*) 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'ragtest' 
        AND COLUMN_NAME = 'end_at'
    """
    res = db_service.execute_query(check_col_query)
    if res['rows'][0][0] == 0:
        print("Adding column 'end_at'...")
        db_service.execute_query("ALTER TABLE ragtest ADD COLUMN end_at TIMESTAMP NULL")
    
    check_col_2 = """
        SELECT count(*) 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = DATABASE() 
        AND TABLE_NAME = 'ragtest' 
        AND COLUMN_NAME = 'max_violations'
    """
    res2 = db_service.execute_query(check_col_2)
    if res2['rows'][0][0] == 0:
        print("Adding column 'max_violations'...")
        db_service.execute_query("ALTER TABLE ragtest ADD COLUMN max_violations INT DEFAULT 3")

    # 2. Update Data
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    tomorrow_midnight = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_str = tomorrow_midnight.strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"Updating data: max_violations=1, end_at={tomorrow_str}")
    
    update_query_all = f"""
        UPDATE ragtest 
        SET 
            max_violations = 1,
            end_at = '{tomorrow_str}'
        WHERE id IS NOT NULL
    """
    
    res_update = db_service.execute_query(update_query_all)
    print(f"Completed. Affected rows: {res_update.get('affected_rows', 0)}")

if __name__ == "__main__":
    try:
        update_ragtest_data()
    except Exception as e:
        print(f"Failed: {e}")
