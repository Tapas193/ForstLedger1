# auth.py - User authentication and session management
import streamlit as st
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import VaccineDatabase
from typing import Tuple, Optional, Dict

class AuthenticationSystem:
    def __init__(self):
        self.db = VaccineDatabase()
        self.init_session_state()
    
    def init_session_state(self):
        """Initialize session state variables"""
        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False
        if 'doctor_id' not in st.session_state:
            st.session_state.doctor_id = None
        if 'doctor_name' not in st.session_state:
            st.session_state.doctor_name = None
        if 'verification_code' not in st.session_state:
            st.session_state.verification_code = None
        if 'verification_email' not in st.session_state:
            st.session_state.verification_email = None
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if not any(char.isdigit() for char in password):
            return False, "Password must contain at least one number"
        
        if not any(char.isalpha() for char in password):
            return False, "Password must contain at least one letter"
        
        return True, "Password is valid"
    
    def send_verification_email(self, to_email: str, verification_code: str) -> bool:
        """
        Send verification email to doctor
        Note: For hackathon demo, we simulate email sending
        """
        try:
            # In production, uncomment and configure SMTP
            '''
            EMAIL_CONFIG = {
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'sender_email': 'your_email@gmail.com',
                'sender_password': 'your_password'
            }
            
            msg = MIMEMultipart()
            msg['From'] = EMAIL_CONFIG['sender_email']
            msg['To'] = to_email
            msg['Subject'] = 'Vaccine Vitals Monitor - Email Verification'
            
            body = f"""
            Dear Doctor,
            
            Thank you for registering with Vaccine Vitals Monitor.
            
            Your verification code is: {verification_code}
            
            Enter this code in the app to complete your registration.
            
            This is an automated message. Please do not reply.
            
            Best regards,
            Vaccine Vitals Monitor Team
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)
            server.quit()
            '''
            
            # For demo purposes, store verification code in session
            st.session_state.verification_code = verification_code
            st.session_state.verification_email = to_email
            
            return True
        except Exception as e:
            st.error(f"Error sending email: {str(e)}")
            return False
    
    def register_doctor(self, doctor_id: str, name: str, email: str, password: str,
                       hospital: str, department: str, phone: str) -> Tuple[bool, str]:
        """Register a new doctor"""
        # Validate inputs
        if not all([doctor_id, name, email, password, hospital, department, phone]):
            return False, "Please fill all required fields"
        
        if not self.validate_email(email):
            return False, "Invalid email format"
        
        is_valid, msg = self.validate_password(password)
        if not is_valid:
            return False, msg
        
        # Register in database
        success, result = self.db.add_doctor(doctor_id, name, email, password,
                                           hospital, department, phone)
        
        if success:
            # Send verification email
            if self.send_verification_email(email, result):
                return True, f"Registration successful! Verification code sent to {email}"
            else:
                return False, "Registration saved but failed to send verification email"
        else:
            return False, result
    
    def verify_email(self, doctor_id: str, verification_code: str) -> bool:
        """Verify doctor's email with code"""
        return self.db.verify_doctor_email(doctor_id, verification_code)
    
    def login(self, doctor_id: str, password: str) -> Tuple[bool, str]:
        """Login doctor"""
        success, doctor_info = self.db.authenticate_doctor(doctor_id, password)
        
        if success and doctor_info:
            st.session_state.logged_in = True
            st.session_state.doctor_id = doctor_info['doctor_id']
            st.session_state.doctor_name = doctor_info['name']
            
            # Add audit log
            self.db.add_audit_entry(doctor_id, "LOGIN", "Doctor logged in successfully")
            return True, "Login successful!"
        elif not success and doctor_info:
            return False, doctor_info.get('error', 'Login failed')
        else:
            return False, "Invalid Doctor ID or password"
    
    def logout(self):
        """Logout current doctor"""
        if st.session_state.logged_in:
            self.db.add_audit_entry(st.session_state.doctor_id, "LOGOUT", "Doctor logged out")
        
        st.session_state.logged_in = False
        st.session_state.doctor_id = None
        st.session_state.doctor_name = None
        st.rerun()
    
    def get_current_doctor(self) -> Optional[Dict]:
        """Get current doctor's information"""
        if st.session_state.logged_in and st.session_state.doctor_id:
            return self.db.get_doctor_profile(st.session_state.doctor_id)
        return None
    
    def change_password(self, doctor_id: str, current_password: str, 
                       new_password: str) -> Tuple[bool, str]:
        """Change doctor's password"""
        is_valid, msg = self.validate_password(new_password)
        if not is_valid:
            return False, msg
        
        success, message = self.db.update_doctor_password(doctor_id, current_password, new_password)
        
        if success:
            self.db.add_audit_entry(doctor_id, "PASSWORD_CHANGE", "Password updated successfully")
        
        return success, message
    
    def show_login_page(self):
        """Display login page"""
        st.markdown("""
        <div style='text-align: center; padding: 2rem;'>
            <h1 style='color: #1E3A8A;'>🩺 VACCINE VITALS MONITOR</h1>
            <p style='color: #3B82F6;'>HLTH-505: Proactive Cold Chain Alerts</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Create tabs for Login and Register
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
        
        with tab1:
            self.show_login_form()
        
        with tab2:
            self.show_registration_form()
        
        # Demo credentials
        st.markdown("---")
        st.info("**Demo Credentials:** Doctor ID: `DOC001`, Password: `password123`")
    
    def show_login_form(self):
        """Display login form"""
        st.subheader("Doctor Login")
        
        with st.form("login_form"):
            doctor_id = st.text_input("Doctor ID", placeholder="Enter your Doctor ID")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            submitted = st.form_submit_button("Login", type="primary")
            
            if submitted:
                if doctor_id and password:
                    success, message = self.login(doctor_id, password)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please enter both Doctor ID and Password")
    
    def show_registration_form(self):
        """Display registration form"""
        st.subheader("New Doctor Registration")
        
        with st.form("registration_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                doctor_id = st.text_input("Doctor ID*", help="Unique ID assigned by hospital")
                name = st.text_input("Full Name*")
                email = st.text_input("Email*")
                password = st.text_input("Password*", type="password")
            
            with col2:
                hospital = st.text_input("Hospital/Clinic*")
                department = st.text_input("Department*")
                phone = st.text_input("Phone Number*")
            
            submitted = st.form_submit_button("Register", type="primary")
            
            if submitted:
                if not all([doctor_id, name, email, password, hospital, department, phone]):
                    st.error("Please fill all required fields (*)")
                else:
                    success, message = self.register_doctor(
                        doctor_id, name, email, password, hospital, department, phone
                    )
                    
                    if success:
                        st.success(message)
                        
                        # Show verification code input
                        verification_code = st.text_input(
                            "Enter Verification Code", 
                            placeholder="6-digit code from email"
                        )
                        
                        if st.button("Verify Email"):
                            if self.verify_email(doctor_id, verification_code):
                                st.success("✅ Email verified successfully! You can now login.")
                            else:
                                st.error("Invalid verification code")
                    else:
                        st.error(message)