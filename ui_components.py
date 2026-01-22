# ui_components.py - Reusable UI components
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

class UIComponents:
    @staticmethod
    def apply_custom_css():
        """Apply custom CSS styles"""
        st.markdown("""
        <style>
            .main-header {
                font-size: 2.5rem;
                color: #1E3A8A;
                font-weight: 700;
                margin-bottom: 1rem;
            }
            .sub-header {
                font-size: 1.5rem;
                color: #3B82F6;
                font-weight: 600;
                margin-bottom: 1rem;
            }
            .alert-box {
                padding: 1rem;
                border-radius: 0.5rem;
                margin: 1rem 0;
                border-left: 5px solid;
            }
            .critical-alert {
                background-color: #FEE2E2;
                border-left-color: #DC2626;
                color: #991B1B;
            }
            .warning-alert {
                background-color: #FEF3C7;
                border-left-color: #F59E0B;
                color: #92400E;
            }
            .info-alert {
                background-color: #DBEAFE;
                border-left-color: #3B82F6;
                color: #1E40AF;
            }
            .success-alert {
                background-color: #D1FAE5;
                border-left-color: #10B981;
                color: #065F46;
            }
            .metric-card {
                background-color: #F8FAFC;
                padding: 1rem;
                border-radius: 0.5rem;
                border: 1px solid #E2E8F0;
                text-align: center;
                margin: 0.5rem;
            }
            .doctor-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 1.5rem;
                border-radius: 1rem;
                margin: 1rem 0;
            }
            .stButton > button {
                background-color: #3B82F6;
                color: white;
                font-weight: 600;
                border: none;
                padding: 0.5rem 1rem;
                border-radius: 0.5rem;
            }
            .stButton > button:hover {
                background-color: #2563EB;
            }
            .tab-container {
                background-color: #f8f9fa;
                border-radius: 0.5rem;
                padding: 1rem;
                margin: 1rem 0;
            }
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def create_temperature_plot(historical_data: pd.DataFrame, 
                               predictions: list = None,
                               prediction_times: list = None,
                               device_name: str = "Device") -> go.Figure:
        """Create temperature visualization plot"""
        fig = go.Figure()
        
        # Add historical data
        fig.add_trace(go.Scatter(
            x=historical_data['timestamp'],
            y=historical_data['temperature'],
            mode='lines+markers',
            name='Historical Temperature',
            line=dict(color='blue', width=2),
            marker=dict(size=4, color='blue'),
            fill='tozeroy',
            fillcolor='rgba(59, 130, 246, 0.1)'
        ))
        
        # Add predictions if available
        if predictions is not None and prediction_times is not None:
            fig.add_trace(go.Scatter(
                x=prediction_times,
                y=predictions,
                mode='lines+markers',
                name='2-Hour Forecast',
                line=dict(color='orange', width=3, dash='dash'),
                marker=dict(size=6, color='orange')
            ))
        
        # Add safe zone
        fig.add_hrect(
            y0=2.0, y1=8.0,
            fillcolor="rgba(0, 255, 0, 0.1)",
            layer="below",
            line_width=0,
            annotation_text="Safe Zone (2°C - 8°C)",
            annotation_position="top left"
        )
        
        # Add threshold lines
        fig.add_hline(
            y=8.0,
            line_dash="dot",
            line_color="red",
            annotation_text="Upper Limit (8°C)",
            annotation_position="bottom right"
        )
        
        fig.add_hline(
            y=2.0,
            line_dash="dot",
            line_color="red",
            annotation_text="Lower Limit (2°C)",
            annotation_position="bottom right"
        )
        
        # Update layout
        fig.update_layout(
            title=f"Temperature Monitoring - {device_name}",
            xaxis_title="Time",
            yaxis_title="Temperature (°C)",
            height=500,
            hovermode='x unified',
            showlegend=True,
            template="plotly_white",
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        return fig
    
    @staticmethod
    def create_metric_card(title: str, value: str, delta: str = None, 
                          delta_color: str = "normal", help_text: str = None):
        """Create a metric card"""
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
            st.metric(label=title, value=value, delta=delta, delta_color=delta_color)
            if help_text:
                st.caption(help_text)
            st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    def show_alert_box(alert_type: str, severity: str, message: str, actions: list):
        """Display an alert box"""
        if severity == 'CRITICAL':
            alert_class = "critical-alert"
            icon = "🔴"
        elif severity == 'WARNING':
            alert_class = "warning-alert"
            icon = "🟡"
        else:
            alert_class = "info-alert"
            icon = "ℹ️"
        
        st.markdown(f'<div class="alert-box {alert_class}">', unsafe_allow_html=True)
        st.markdown(f"### {icon} {severity} ALERT: {alert_type.replace('_', ' ')}")
        st.markdown(f"**{message}**")
        st.markdown("**Recommended Actions:**")
        for action in actions:
            st.markdown(f"- {action}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    @staticmethod
    def create_dashboard_header(doctor_name: str):
        """Create dashboard header with doctor info"""
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f'<h1 class="main-header">Welcome, Dr. {doctor_name}!</h1>', 
                       unsafe_allow_html=True)
        
        with col3:
            if st.button("🚪 Logout", type="secondary"):
                st.session_state.logged_in = False
                st.session_state.doctor_id = None
                st.session_state.doctor_name = None
                st.rerun()
        
        st.markdown("---")
    
    @staticmethod
    def create_tabs():
        """Create tabbed interface"""
        return st.tabs(["📊 Live Monitor", "🚨 Alerts", "📋 Audit Log", "👨‍⚕️ Profile"])
    
    @staticmethod
    def create_demo_data_button():
        """Create demo data button for hackathon"""
        if st.button("🎬 LOAD HACKATHON DEMO DATA", type="primary"):
            # Generate demo data showing temperature breach
            import numpy as np
            from datetime import datetime, timedelta
            
            demo_times = []
            demo_temps = []
            
            # Create 6 hours of data with rising trend
            for i in range(72):  # 72 readings at 5-minute intervals = 6 hours
                time = datetime.now() - timedelta(minutes=(71-i)*5)
                demo_times.append(time)
                
                # Base temperature with rising trend
                base_temp = 5.0 + (i * 0.05)  # Gradual rise
                
                # Add some noise
                noise = np.random.normal(0, 0.3)
                temp = base_temp + noise
                
                # Ensure final temperatures are near breach
                if i > 60:
                    temp = min(8.5, temp + 0.1 * (i-60))
                
                demo_temps.append(round(temp, 2))
            
            demo_df = pd.DataFrame({
                'timestamp': demo_times,
                'temperature': demo_temps
            })
            
            return demo_df
        
        return None