# database.py - Updated for PostgreSQL
import hashlib
import json
from datetime import datetime
import pandas as pd
import bcrypt
from typing import Optional, List, Dict, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text
from config import DatabaseConfig

class VaccineDatabase:
    def __init__(self):
        self.engine = create_engine(DatabaseConfig.DATABASE_URL)
        self.init_database()
    
    def get_connection(self):
        """Get PostgreSQL connection"""
        return psycopg2.connect(**DatabaseConfig.get_connection_params())
    
    def get_sqlalchemy_connection(self):
        """Get SQLAlchemy connection for pandas"""
        return self.engine.connect()
    
    def init_database(self):
        """Initialize all PostgreSQL tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Enable UUID extension
            cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
            
            # Doctors table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS doctors (
                    id SERIAL PRIMARY KEY,
                    doctor_id VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    hospital VARCHAR(100),
                    department VARCHAR(100),
                    phone VARCHAR(20),
                    verified BOOLEAN DEFAULT FALSE,
                    verification_code VARCHAR(10),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Temperature logs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS temperature_logs (
                    id SERIAL PRIMARY KEY,
                    doctor_id VARCHAR(50) NOT NULL,
                    device_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    temperature DECIMAL(5,2) NOT NULL,
                    vaccine_type VARCHAR(50),
                    location VARCHAR(100),
                    prev_hash VARCHAR(64),
                    current_hash VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE CASCADE
                )
            ''')
            
            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    doctor_id VARCHAR(50) NOT NULL,
                    device_id VARCHAR(50),
                    timestamp TIMESTAMP NOT NULL,
                    alert_type VARCHAR(50),
                    temperature DECIMAL(5,2),
                    predicted_temp DECIMAL(5,2),
                    alert_message TEXT,
                    action_suggested TEXT,
                    status VARCHAR(20) DEFAULT 'active',
                    severity VARCHAR(20),
                    minutes_to_breach INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE CASCADE
                )
            ''')
            
            # Audit trail table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id SERIAL PRIMARY KEY,
                    doctor_id VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    previous_hash VARCHAR(64),
                    current_hash VARCHAR(64),
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_temperature_logs_doctor_id 
                ON temperature_logs(doctor_id);
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_temperature_logs_timestamp 
                ON temperature_logs(timestamp);
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_doctor_id 
                ON alerts(doctor_id);
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                ON alerts(timestamp);
            ''')
            
            conn.commit()
            
            # Check if sample doctor exists
            cursor.execute("SELECT COUNT(*) FROM doctors WHERE doctor_id='DOC001'")
            if cursor.fetchone()[0] == 0:
                hashed_pw = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt())
                cursor.execute('''
                    INSERT INTO doctors 
                    (doctor_id, name, email, password, hospital, department, phone, verified)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', ('DOC001', 'Dr. Priya Sharma', 'dr.priya@example.com', 
                      hashed_pw.decode('utf-8'), 'Apollo Hospital', 
                      'Pediatrics', '+91-9876543210', True))
                conn.commit()
                
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def add_doctor(self, doctor_id: str, name: str, email: str, password: str, 
                   hospital: str, department: str, phone: str) -> Tuple[bool, str]:
        """Register a new doctor in PostgreSQL"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Check if doctor ID or email already exists
            cursor.execute("SELECT COUNT(*) FROM doctors WHERE doctor_id=%s", (doctor_id,))
            if cursor.fetchone()[0] > 0:
                return False, "Doctor ID already exists"
            
            cursor.execute("SELECT COUNT(*) FROM doctors WHERE email=%s", (email,))
            if cursor.fetchone()[0] > 0:
                return False, "Email already registered"
            
            # Hash password
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Generate verification code
            import numpy as np
            verification_code = str(np.random.randint(100000, 999999))
            
            cursor.execute('''
                INSERT INTO doctors 
                (doctor_id, name, email, password, hospital, department, phone, verification_code)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (doctor_id, name, email, hashed_pw.decode('utf-8'), 
                  hospital, department, phone, verification_code))
            
            conn.commit()
            return True, verification_code
            
        except psycopg2.Error as e:
            conn.rollback()
            return False, str(e)
        finally:
            cursor.close()
            conn.close()
    
    def verify_doctor_email(self, doctor_id: str, code: str) -> bool:
        """Verify doctor's email with code"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT verification_code FROM doctors WHERE doctor_id=%s", (doctor_id,))
            result = cursor.fetchone()
            
            if result and result[0] == code:
                cursor.execute("UPDATE doctors SET verified=TRUE WHERE doctor_id=%s", (doctor_id,))
                conn.commit()
                return True
            
            return False
            
        finally:
            cursor.close()
            conn.close()
    
    def authenticate_doctor(self, doctor_id: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """Authenticate doctor login"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT doctor_id, name, password, verified 
                FROM doctors WHERE doctor_id=%s
            ''', (doctor_id,))
            
            result = cursor.fetchone()
            
            if not result:
                return False, None
            
            if not result['verified']:
                return False, {"error": "Email not verified"}
            
            stored_pw = result['password'].encode('utf-8') if isinstance(result['password'], str) else result['password']
            
            if bcrypt.checkpw(password.encode('utf-8'), stored_pw):
                return True, {
                    "doctor_id": result['doctor_id'],
                    "name": result['name']
                }
            
            return False, {"error": "Invalid password"}
            
        finally:
            cursor.close()
            conn.close()
    
    def add_temperature_log(self, doctor_id: str, device_id: str, temperature: float, 
                           vaccine_type: str = "General", location: str = "Unknown") -> str:
        """Add temperature log with hash chain"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get previous hash
            cursor.execute('''
                SELECT current_hash FROM temperature_logs 
                WHERE doctor_id=%s 
                ORDER BY id DESC LIMIT 1
            ''', (doctor_id,))
            
            result = cursor.fetchone()
            previous_hash = result[0] if result else "0" * 64
            
            # Create current hash
            timestamp = datetime.now().isoformat()
            data_string = f"{timestamp}|{doctor_id}|{device_id}|{temperature}|{vaccine_type}|{location}|{previous_hash}"
            current_hash = hashlib.sha256(data_string.encode()).hexdigest()
            
            cursor.execute('''
                INSERT INTO temperature_logs 
                (doctor_id, device_id, timestamp, temperature, vaccine_type, location, prev_hash, current_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (doctor_id, device_id, timestamp, float(temperature), 
                  vaccine_type, location, previous_hash, current_hash))
            
            conn.commit()
            return current_hash
            
        except psycopg2.Error as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def get_temperature_data(self, doctor_id: str, device_id: str = None, 
                           hours: int = 24) -> pd.DataFrame:
        """Get temperature data for a doctor"""
        with self.get_sqlalchemy_connection() as conn:
            if device_id:
                query = text('''
                    SELECT timestamp, temperature, device_id, vaccine_type, location
                    FROM temperature_logs 
                    WHERE doctor_id=:doctor_id AND device_id=:device_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                ''')
                params = {
                    'doctor_id': doctor_id,
                    'device_id': device_id,
                    'limit': hours * 12  # Assuming 5-minute intervals
                }
            else:
                query = text('''
                    SELECT timestamp, temperature, device_id, vaccine_type, location
                    FROM temperature_logs 
                    WHERE doctor_id=:doctor_id
                    ORDER BY timestamp DESC
                    LIMIT :limit
                ''')
                params = {
                    'doctor_id': doctor_id,
                    'limit': hours * 12
                }
            
            df = pd.read_sql(query, conn, params=params)
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp')
            
            return df
    
    def add_alert(self, doctor_id: str, device_id: str, alert_type: str, 
                 temperature: float, predicted_temp: float, severity: str,
                 minutes_to_breach: int) -> int:
        """Add a new alert"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            alert_messages = {
                "HIGH_TEMP": f"Temperature predicted to breach upper limit ({predicted_temp:.1f}°C)",
                "LOW_TEMP": f"Temperature predicted to breach lower limit ({predicted_temp:.1f}°C)",
                "SENSOR_ERROR": "Possible sensor malfunction detected"
            }
            
            action_suggestions = {
                "HIGH_TEMP_CRITICAL": "Transfer vaccines immediately, add ice packs",
                "HIGH_TEMP_WARNING": "Add extra ice packs, move to cooler location",
                "LOW_TEMP_CRITICAL": "Remove ice packs immediately, move to warmer area",
                "LOW_TEMP_WARNING": "Reduce ice packs, monitor closely"
            }
            
            alert_key = f"{alert_type}_{severity}"
            action = action_suggestions.get(alert_key, "Monitor the situation")
            
            cursor.execute('''
                INSERT INTO alerts 
                (doctor_id, device_id, timestamp, alert_type, temperature, 
                 predicted_temp, alert_message, action_suggested, status, severity, minutes_to_breach)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                doctor_id, device_id, datetime.now().isoformat(), alert_type, 
                float(temperature), float(predicted_temp), 
                alert_messages.get(alert_type, "Alert"),
                action, 'active', severity, int(minutes_to_breach)
            ))
            
            alert_id = cursor.fetchone()[0]
            conn.commit()
            return alert_id
            
        except psycopg2.Error as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def get_recent_alerts(self, doctor_id: str, limit: int = 10) -> pd.DataFrame:
        """Get recent alerts for a doctor"""
        with self.get_sqlalchemy_connection() as conn:
            query = text('''
                SELECT * FROM alerts 
                WHERE doctor_id=:doctor_id 
                ORDER BY timestamp DESC 
                LIMIT :limit
            ''')
            
            df = pd.read_sql(query, conn, params={'doctor_id': doctor_id, 'limit': limit})
            return df
    
    def add_audit_entry(self, doctor_id: str, action: str, details: str = "") -> str:
        """Add entry to audit trail"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get previous hash
            cursor.execute('''
                SELECT current_hash FROM audit_trail 
                WHERE doctor_id=%s 
                ORDER BY id DESC LIMIT 1
            ''', (doctor_id,))
            
            result = cursor.fetchone()
            previous_hash = result[0] if result else "0" * 64
            
            # Create current hash
            timestamp = datetime.now().isoformat()
            data_string = f"{timestamp}|{doctor_id}|{action}|{details}|{previous_hash}"
            current_hash = hashlib.sha256(data_string.encode()).hexdigest()
            
            cursor.execute('''
                INSERT INTO audit_trail 
                (doctor_id, timestamp, action, previous_hash, current_hash, details)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (doctor_id, timestamp, action, previous_hash, current_hash, details))
            
            conn.commit()
            return current_hash
            
        except psycopg2.Error as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    def verify_audit_trail(self, doctor_id: str) -> Tuple[bool, Optional[int], List[Dict]]:
        """Verify integrity of audit trail"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, timestamp, action, previous_hash, current_hash, details
                FROM audit_trail 
                WHERE doctor_id=%s 
                ORDER BY id
            ''', (doctor_id,))
            
            entries = cursor.fetchall()
            verification_results = []
            previous_hash = "0" * 64
            
            for entry in entries:
                entry_id, timestamp, action, stored_prev_hash, stored_current_hash, details = entry
                
                # Verify previous hash chain
                if stored_prev_hash != previous_hash:
                    return False, entry_id, verification_results
                
                # Verify current hash
                data_string = f"{timestamp}|{doctor_id}|{action}|{details}|{stored_prev_hash}"
                calculated_hash = hashlib.sha256(data_string.encode()).hexdigest()
                
                if calculated_hash != stored_current_hash:
                    return False, entry_id, verification_results
                
                verification_results.append({
                    'id': entry_id,
                    'timestamp': timestamp,
                    'action': action,
                    'status': 'VALID'
                })
                
                previous_hash = stored_current_hash
            
            return True, None, verification_results
            
        finally:
            cursor.close()
            conn.close()
    
    def get_doctor_profile(self, doctor_id: str) -> Optional[Dict]:
        """Get doctor profile information"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT doctor_id, name, email, hospital, department, phone, created_at
                FROM doctors WHERE doctor_id=%s
            ''', (doctor_id,))
            
            result = cursor.fetchone()
            
            if result:
                return dict(result)
            return None
            
        finally:
            cursor.close()
            conn.close()
    
    def update_doctor_password(self, doctor_id: str, current_password: str, 
                             new_password: str) -> Tuple[bool, str]:
        """Update doctor password"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Verify current password
            cursor.execute("SELECT password FROM doctors WHERE doctor_id=%s", (doctor_id,))
            result = cursor.fetchone()
            
            if not result:
                return False, "Doctor not found"
            
            stored_password = result[0]
            
            if not bcrypt.checkpw(current_password.encode('utf-8'), stored_password.encode('utf-8')):
                return False, "Current password is incorrect"
            
            # Update to new password
            new_hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            cursor.execute("UPDATE doctors SET password=%s WHERE doctor_id=%s", 
                          (new_hashed_pw.decode('utf-8'), doctor_id))
            
            conn.commit()
            return True, "Password updated successfully"
            
        except psycopg2.Error as e:
            conn.rollback()
            return False, str(e)
        finally:
            cursor.close()
            conn.close()