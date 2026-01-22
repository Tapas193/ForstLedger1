# utils.py - Utility functions
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import hashlib
import json

class Utils:
    @staticmethod
    def generate_sample_data(hours: int = 24, device_id: str = "fridge-01"):
        """Generate sample temperature data for demo"""
        timestamps = []
        temperatures = []
        
        base_time = datetime.now() - timedelta(hours=hours)
        
        for i in range(hours * 12):  # 5-minute intervals
            current_time = base_time + timedelta(minutes=i*5)
            timestamps.append(current_time)
            
            # Create realistic temperature pattern with daily cycle
            hour_of_day = current_time.hour
            daily_variation = 1.5 * np.sin((hour_of_day - 14) * np.pi / 12)
            
            # Base temperature with slight upward trend
            base_temp = 5.0 + (i * 0.001)
            
            # Add some random noise
            noise = np.random.normal(0, 0.3)
            
            temperature = base_temp + daily_variation + noise
            temperatures.append(round(temperature, 2))
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'temperature': temperatures,
            'device_id': device_id
        })
    
    @staticmethod
    def validate_csv_file(df: pd.DataFrame) -> tuple:
        """Validate CSV file format"""
        if len(df.columns) < 2:
            return False, "CSV must have at least 2 columns"
        
        # Try to identify timestamp and temperature columns
        timestamp_col = None
        temp_col = None
        
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['time', 'date', 'timestamp']):
                timestamp_col = col
            elif any(keyword in col_lower for keyword in ['temp', 'temperature', 'celsius']):
                temp_col = col
        
        if timestamp_col is None or temp_col is None:
            return False, "Could not identify timestamp and temperature columns"
        
        # Convert timestamp column
        try:
            df[timestamp_col] = pd.to_datetime(df[timestamp_col])
        except:
            return False, "Could not parse timestamp column"
        
        # Convert temperature column
        try:
            df[temp_col] = pd.to_numeric(df[temp_col])
        except:
            return False, "Could not parse temperature column"
        
        # Rename columns
        df = df.rename(columns={timestamp_col: 'timestamp', temp_col: 'temperature'})
        
        return True, df
    
    @staticmethod
    def calculate_statistics(temperature_data: pd.DataFrame) -> dict:
        """Calculate temperature statistics"""
        if temperature_data.empty:
            return {
                'mean': 0,
                'min': 0,
                'max': 0,
                'std': 0,
                'breach_count': 0
            }
        
        temps = temperature_data['temperature']
        
        return {
            'mean': round(temps.mean(), 2),
            'min': round(temps.min(), 2),
            'max': round(temps.max(), 2),
            'std': round(temps.std(), 2),
            'breach_count': len(temps[(temps < 2) | (temps > 8)])
        }
    
    @staticmethod
    def format_timestamp(timestamp: datetime) -> str:
        """Format timestamp for display"""
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def get_time_ago(timestamp: datetime) -> str:
        """Get human-readable time ago"""
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