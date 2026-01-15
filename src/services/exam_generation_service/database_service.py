import os
import mysql.connector
from typing import Dict, Optional, Tuple


class DatabaseService:
    def __init__(self):
        self.connection = None
    
    def _get_connection_params(self) -> Dict[str, str]:
        # Priority to SQLALCHEMY_DATABASE_URI parsing if available, 
        # but for simplicity keep existing env mapping
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
            self.connection = mysql.connector.connect(**params)
            self.connection.autocommit = False # Disable autocommit for transactions
        except mysql.connector.Error as e:
            raise ValueError(f"Không thể kết nối đến MySQL: {str(e)}")
        except Exception as e:
            raise ValueError(f"Lỗi khi kết nối database: {str(e)}")
    
    def check_connection(self) -> Dict:
        try:
            self._connect()
            cursor = self.connection.cursor()
            
            cursor.execute("SELECT VERSION();")
            version = cursor.fetchone()[0]
            
            cursor.execute("SELECT DATABASE();")
            database = cursor.fetchone()[0]
            
            cursor.execute("SELECT CURRENT_USER();")
            user = cursor.fetchone()[0]
            
            cursor.close()
            
            return {
                "status": "connected",
                "database": database,
                "user": user,
                "version": version,
                "host": self.connection.get_server_info()
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
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
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                self.connection.commit() # Ensure fresh data for next read
                cursor.close()
                return {
                    "columns": columns,
                    "rows": results,
                    "row_count": len(results)
                }
            else:
                affected = cursor.rowcount
                self.connection.commit() # Commit changes
                cursor.close()
                return {"affected_rows": affected}
        except Exception as e:
            if cursor:
                cursor.close()
            if self.connection and self.connection.is_connected():
                self.connection.rollback()
            raise ValueError(f"Lỗi khi thực thi query: {str(e)}")

    def get_cursor(self):
        self._connect()
        return self.connection.cursor()

    def commit(self):
        if self.connection and self.connection.is_connected():
            self.connection.commit()

    def rollback(self):
        if self.connection and self.connection.is_connected():
            self.connection.rollback()
    
    def close(self):
        if self.connection and self.connection.is_connected():
            try:
                self.connection.close()
            except:
                pass
