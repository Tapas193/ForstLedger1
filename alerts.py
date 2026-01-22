# alerts.py - Alert generation and management
import pandas as pd
from datetime import datetime
from typing import List, Dict
from database import VaccineDatabase

class AlertManager:
    def __init__(self):
        self.db = VaccineDatabase()
    
    def generate_alert(self, doctor_id: str, device_id: str, alert_type: str,
                      current_temp: float, predicted_temp: float,
                      severity: str, minutes_to_breach: int) -> int:
        """Generate and store a new alert"""
        return self.db.add_alert(
            doctor_id, device_id, alert_type, 
            current_temp, predicted_temp, severity, minutes_to_breach
        )
    
    def get_recent_alerts(self, doctor_id: str, limit: int = 10) -> pd.DataFrame:
        """Get recent alerts for display"""
        alerts_df = self.db.get_recent_alerts(doctor_id, limit)
        
        if not alerts_df.empty:
            # Format timestamp
            alerts_df['timestamp'] = pd.to_datetime(alerts_df['timestamp'])
            alerts_df['time_ago'] = alerts_df['timestamp'].apply(self.get_time_ago)
            
            # Color coding for severity
            def get_severity_color(severity):
                if severity == 'CRITICAL':
                    return '🔴'
                elif severity == 'WARNING':
                    return '🟡'
                else:
                    return '⚪'
            
            alerts_df['severity_icon'] = alerts_df['severity'].apply(get_severity_color)
        
        return alerts_df
    
    def get_time_ago(self, timestamp: datetime) -> str:
        """Convert timestamp to human-readable time ago"""
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    def get_alert_statistics(self, doctor_id: str) -> Dict:
        """Get alert statistics for dashboard"""
        alerts_df = self.db.get_recent_alerts(doctor_id, 1000)  # Get all alerts
        
        if alerts_df.empty:
            return {
                'total_alerts': 0,
                'critical_alerts': 0,
                'warning_alerts': 0,
                'resolved_alerts': 0,
                'false_positives': 0,
                'false_positive_rate': 0,
                'avg_response_time': 0
            }
        
        total_alerts = len(alerts_df)
        critical_alerts = len(alerts_df[alerts_df['severity'] == 'CRITICAL'])
        warning_alerts = len(alerts_df[alerts_df['severity'] == 'WARNING'])
        resolved_alerts = len(alerts_df[alerts_df['status'] == 'resolved'])
        
        # Calculate false positives (alerts that were resolved quickly without action)
        false_positives = len(alerts_df[
            (alerts_df['status'] == 'resolved') & 
            (alerts_df['severity'] == 'WARNING')
        ])
        
        # Calculate average response time (simulated)
        avg_response_time = 18  # Simulated average response time in minutes
        
        return {
            'total_alerts': total_alerts,
            'critical_alerts': critical_alerts,
            'warning_alerts': warning_alerts,
            'resolved_alerts': resolved_alerts,
            'false_positives': false_positives,
            'false_positive_rate': round((false_positives / total_alerts * 100), 1) if total_alerts > 0 else 0,
            'avg_response_time': avg_response_time
        }
    
    def mark_alert_resolved(self, alert_id: int):
        """Mark an alert as resolved"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("UPDATE alerts SET status='resolved' WHERE id=?", (alert_id,))
        conn.commit()
        conn.close()
    
    def get_active_alerts(self, doctor_id: str) -> pd.DataFrame:
        """Get all active alerts"""
        conn = self.db.get_connection()
        query = '''
            SELECT * FROM alerts 
            WHERE doctor_id=? AND status='active'
            ORDER BY timestamp DESC
        '''
        df = pd.read_sql_query(query, conn, params=(doctor_id,))
        conn.close()
        return df