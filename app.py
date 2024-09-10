from flask import Flask, request, jsonify, send_file, render_template_string, redirect, url_for, session
from fpdf import FPDF
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import logging
import matplotlib.pyplot as plt
import requests
import tempfile
import random
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import os
import json
import pdb

app = Flask(__name__)

app.secret_key = 'your_secret_key_here'


app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript from accessing the cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  

# Configure SQLAlchemy for PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://nivi_user:R9q17MQwi3rXUVO3vGVCvyXdfNOEGSuM@dpg-crc4s9jv2p9s73dm93eg-a.oregon-postgres.render.com/nivi'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configure logging
# logging.basicConfig(level=logging.DEBUG)

# Define the User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    scores = db.Column(db.Text)

user_details = {}
responses = {
    'empathy': [],
    'adaptability': [],
    'communication': []
}

def process_responses(responses):
    suggestions = {}
    for category, answers in responses.items():
        score = sum(answers) // len(answers) if answers else 0
        if category == 'empathy':
            if score >= 4:
                suggestions[category] = "High Empathy: You are highly empathetic, understanding, and supportive. You are very aware of others' emotions and needs and respond with care and compassion."
            elif score >= 3:
                suggestions[category] = "Moderate Empathy: You have a good level of empathy. You generally understand and care about others' feelings but may occasionally miss subtle cues."
            elif score >= 2:
                suggestions[category] = "Average Empathy: Your empathy is average. You show concern for others but might not always fully understand their emotions or respond appropriately."
            elif score >= 1:
                suggestions[category] = "Low Empathy: You might struggle to understand and relate to others' feelings. You may need to work on being more attentive and responsive to the emotions of those around you."
            else:
                suggestions[category] = "Very Low Empathy: You have significant difficulty in understanding and relating to others' emotions. Developing greater emotional awareness and sensitivity could benefit your relationships."

        elif category == 'adaptability':
            if score >= 4:
                suggestions[category] = "Highly Adaptable: You excel in adapting to new situations and changes. You are flexible, resilient, and thrive in dynamic environments."
            elif score >= 3:
                suggestions[category] = "Moderately Adaptable: You are fairly adaptable and can handle changes well, though there may be times when you find adjustments challenging."
            elif score >= 2:
                suggestions[category] = "Average Adaptability: Your adaptability is average. You manage changes adequately but may feel uncomfortable with significant or sudden shifts."
            elif score >= 1:
                suggestions[category] = "Low Adaptability: You might find it challenging to adapt to new situations and changes. Working on being more open to new experiences could help improve your adaptability."
            else:
                suggestions[category] = "Very Low Adaptability: You struggle significantly with adapting to change. Developing greater flexibility and resilience can help you navigate changes more effectively."
        elif category == 'communication':
            if score >= 4:
                suggestions[category] = "Excellent Communication: You have excellent communication skills. You express yourself clearly, listen well, and effectively resolve conflicts."
            elif score >= 3:
                suggestions[category] = "Good Communication: Your communication skills are strong. You generally convey your thoughts well and are good at interacting with others."
            elif score >= 2:
                suggestions[category] = "Average Communication: Your communication skills are average. You manage basic communication well but might need to improve in areas like feedback and conflict resolution."
            elif score >= 1:
                suggestions[category] = "Poor Communication: You may find it difficult to communicate effectively. Working on clarity, listening, and adaptability in your communication style could benefit you."
            else:
                suggestions[category] = "Very Poor Communication: You have significant difficulties with communication. Improving your skills in expressing thoughts, listening, and adapting your style to different audiences is essential."
    return suggestions

@app.route('/')
def index():
    return render_template_string(open('indexx.html').read())

@app.route('/about')
def about():
    return render_template_string(open('about.html').read())

@app.route('/home')
def home():
    return render_template_string(open('home.html').read())
@app.route('/assesment')
def assessment ():
    return render_template_string(open('assessment.html').read())
@app.route('/thank_you')
def thank_you():
    return render_template_string(open('thank_you.html').read())
@app.route('/login')
def login():
    return render_template_string(open('login.html').read())
@app.route('/submit_user_details', methods=['POST'])
def submit_user_details():
    try:
        global user_details
        user_details = request.form.to_dict()
        print(user_details, 'uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu')
        # session['user_details'] = user_details
        # print(session['user_details'],'u1u1u1u1u1uu1u1u1u1')
        email = user_details.get('email')

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()

        if email:
             session['email'] = email
        if existing_user:
            # User already exists, show results
            return redirect(url_for('show_results', email=email))

        # Insert new user details
        new_user = User(name=user_details['name'], email=user_details['email'], age=user_details['age'], gender=user_details['gender'])
        db.session.add(new_user)
        db.session.commit()

        return render_template_string(open('index.html').read())

    except IntegrityError as e:
        logging.error(f"Database integrity error: {e}")
        return "A database error occurred. Please try again later.", 500
        return "A database error occurred. Please try again later.", 500
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return "An unexpected error occurred. Please try again later.", 500

@app.route('/submit_responses', methods=['POST'])
def submit_responses():
    global responses
    responses = request.json
    logging.debug(f"Responses submitted: {responses}")

    plot_buffer = fetch_plot_image(user_details=user_details, ngrok_url="https://cognitive-web.onrender.com")
    # Process responses and generate PDF
    suggestions = process_responses(responses)
    pdf_buffer = generate_pdf_report(user_details, suggestions, plot_buffer)
    email = user_details.get('email')

    if not email:
        return jsonify({'status': 'error', 'message': 'No email address found.'}), 400

    try:
        send_report_via_email(email, pdf_buffer)
        logging.info(f"Report sent to {email}")
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return jsonify({'status': 'error', 'message': 'Error sending email.'}), 500

    return jsonify({'status': 'success'})

@app.route('/dashboard')
def dashboard():
    suggestions = process_responses(responses)
    scores = calculate_scores()
    plot_url = url_for('plot', **user_details)
    logging.debug(f"Plot URL: {plot_url}")
    return render_template_string(open('new_user_result.html').read(), user_details=user_details, scores=scores, suggestions=suggestions, plot_url=plot_url)

def calculate_scores():
    scores = {
        'empathy': sum(responses['empathy']),
        'adaptability': sum(responses['adaptability']),
        'communication': sum(responses['communication'])
    }
    logging.debug(f"Scores calculated: {scores}")
    return scores

class CustomPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Skill Assessment Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf_report(user_details, suggestions, plot_buffer):
    try:
        pdf = CustomPDF()
        pdf.add_page()

        # Title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Skill Assessment Report", 0, 1, 'C')
        pdf.ln(10)

        # User Details
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "User Details", 0, 1, 'L')
        pdf.set_font("Arial", size=12)
        for key, value in user_details.items():
            pdf.cell(0, 10, f"{key.capitalize()}: {value}", 0, 1, 'L')
        pdf.ln(10)

        # Save plot_buffer to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_plot_file:
            temp_plot_file.write(plot_buffer.getvalue())
            temp_plot_file_path = temp_plot_file.name

        # Add plot image and ensure there's enough space
        image_x = 10
        image_y = pdf.get_y() + 10  # Add some space below the user details
        image_w = 180
        image_h = 120  # Specify height to ensure the image fits properly

        # Check if the image fits the remaining space
        if image_y + image_h > 270:
            pdf.add_page()
            image_y = 10
        pdf.image('static/plot.png', x=image_x, y=image_y, w=image_w, h=image_h)
        pdf.ln(image_h + 10)  # Add space below the image

        # Suggestions
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Suggestions", 0, 1, 'L')
        pdf.set_font("Arial", size=12)
        for category, suggestion in suggestions.items():
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, category.capitalize(), 0, 1, 'L')
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, suggestion)
            pdf.ln(5)

        # Save PDF to buffer
        pdf_string = pdf.output(dest='S').encode('latin1')
        buffer = io.BytesIO(pdf_string)
        buffer.seek(0)
        logging.debug("PDF report generated successfully.")
        return buffer

    except Exception as e:
        logging.error(f"Error generating PDF: {e}")
        raise


def send_report_via_email(email, pdf_buffer):
    try:
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_user = 'brainbuzzteamavengers@gmail.com'
        smtp_password = 'dsku cfca envt dkug'
        # smtp_password = 'boka wcwk ctas nfec'  # Use the generated app password

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = 'Your Skill Assessment Report'

        body = 'Please find attached your skill assessment report.'
        msg.attach(MIMEText(body, 'plain'))

        pdf_attachment = MIMEApplication(pdf_buffer.getvalue(), _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename='assessment_report.pdf')
        msg.attach(pdf_attachment)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            logging.info(f"Email sent to {email}")
            server.quit()  # Ensure the server is closed properly

    except smtplib.SMTPAuthenticationError as e:
        logging.error("SMTP Authentication Error: Check your username/password.")
        logging.error(f"Exception details: {e}")
        raise
    except smtplib.SMTPRecipientsRefused as e:
        logging.error("Recipient refused: Check the recipient email address.")
        logging.error(f"Exception details: {e}")
        raise
    except smtplib.SMTPSenderRefused as e:
        logging.error("Sender refused: Check the sender email address.")
        logging.error(f"Exception details: {e}")
        raise
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error occurred: {e}")
        raise
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        raise

@app.route('/download_report')
def download_report():
    try:
        suggestions = process_responses(responses)
        plot_buffer = fetch_plot_image(ngrok_url='https://cognitive-web.onrender.com')
        pdf_buffer = generate_pdf_report(user_details, suggestions, plot_buffer)
        email = user_details.get('email')
        if not email:
            return "No email address found.", 400
        send_report_via_email(email, pdf_buffer)
        pdf_buffer.seek(0)
        response = send_file(pdf_buffer, as_attachment=True, download_name='assessment_report.pdf')
        response.headers["Content-Disposition"] += "; filename=assessment_report.pdf"
        return response
    except Exception as e:
        logging.error(f"Error in download_report: {e}")
        return jsonify({'status': 'error', 'message': 'Internal Server Error'}), 500

@app.route('/post_download_redirect')
def post_download_redirect():
    return redirect(url_for('dashboard'))

@app.errorhandler(500)
def internal_error(error):
    return "500 error: An internal server error occurred.", 500


@app.route('/result')
def result():
    scores = calculate_scores()
    plot_url = create_dashboard_plot(scores)
    try:
        query_params = '&'.join([f"{key}={value}" for key, value in user_details.items()])
        full_url = f'{ngrok_url}/plot?{query_params}'
        requests.get(full_url)
    except Exception as e:
        logging.debug(e)
        logging.debug('=======================================')
    
    print(scores)
    if 'email' not in session:  # Check if the user is logged in
        return redirect(url_for('login'))
        
    suggestions = process_responses(responses)
    
    return render_template_string(open('new_user_result.html').read(), user_details=user_details, scores=scores, suggestions=suggestions, plot_url=plot_url)

@app.route('/plot')
def plot():
    scores = calculate_scores()
    user_details = request.args.to_dict()
    email = user_details.get('email')
    logging.debug(email, user_details)
    existing_user = User.query.filter_by(email=email).first()
    serialized_scores = json.dumps(scores)

    # Check if the user already exists

    if existing_user:
        existing_user.scores = serialized_scores
        db.session.commit()
    else:
        if ('name' in user_details) and ('email' in user_details):

            new_user = User(name=user_details['name'], email=user_details['email'], age=user_details['age'], gender=user_details['gender'], scores=serialized_scores)
            db.session.add(new_user)
            db.session.commit()
        # Insert a new user record if they don't exist
        
    return create_dashboard_plot(scores)


def create_dashboard_plot(scores):
    try:
        plt.figure(figsize=(6, 4))
        categories = list(scores.keys())
        values = list(scores.values())
        plt.bar(categories, values, color=['#007bff', '#28a745', '#dc3545'])
        plt.xlabel('Category')
        plt.ylabel('Score')
        plt.title('Assessment Scores')

        # Save plot to a file in the static folder
        plot_path = os.path.join('static', 'plot.png')
        plt.savefig(plot_path, format='png')
        plt.close()

        # Return the URL to access the image
        return url_for('static', filename='plot.png')
    except Exception as e:
        logging.error(f"Error creating dashboard plot: {e}")
        raise

def fetch_plot_image(user_details={} , ngrok_url="https://cognitive-web.onrender.com/"):
    try:
        query_params = '&'.join([f"{key}={value}" for key, value in user_details.items()])
        full_url = f'{ngrok_url}/plot?{query_params}'

        # Send GET request with the query params
        response = requests.get(full_url)
        print(ngrok_url,'lllllllllllll')
        response.raise_for_status()
        return io.BytesIO(response.content)
    except requests.RequestException as e:
        logging.error(f"Error fetching plot image: {e}")
        raise
@app.route('/show_results')
def show_results():
    email = request.args.get('email')
    user = User.query.filter_by(email=email).first()


    if not user:
        return "User not found", 404

    return render_template_string(open('result.html').read(), user_details=user)

otp_store = {}

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    user_otp = data.get('otp')

    if email in otp_store and otp_store[email] == int(user_otp):
        return jsonify({"success": True}), 200
    else:
        #  return jsonify({"success": True}), 200
    
        return jsonify({"success": False, "message": "Invalid OTP"}), 400


@app.route('/send_verification_email', methods=['POST'])
def send_verification_email():
    data = request.get_json()
    email = data.get('email')
    name = data.get('name')
    otp = random.randint(100000, 999999)  # Generate a 6-digit OTP
    otp_store[email] = otp  # Store the OTP

    try:
        send_otp_via_email(email, otp, name)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def send_otp_via_email(email, verification_code, user_name):
    try:
        smtp_server = 'smtp.gmail.com'
        smtp_port = 587
        smtp_user = 'brainbuzzteamavengers@gmail.com'
        smtp_password = 'dsku cfca envt dkug'

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email
        msg['Subject'] = 'Your Verification Code'

        # Create the email body
        body = f"""
        Dear {user_name},

        Thank you for registering with us! To complete the verification process, please use the following code:

        {verification_code}

        Enter this code on our website or app to verify your account. If you did not initiate this request, please disregard this message. For any questions or concerns, feel free to contact our support team.

        Best regards,
        Team Avengers,
        BrainBuzz,
        brainbuzzteamavengers@gmail.com

        """
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            print(f"Verification email sent to {email}")
            server.quit()

    except smtplib.SMTPAuthenticationError as e:
        print("SMTP Authentication Error: Check your username/password.")
        print(f"Exception details: {e}")
    except smtplib.SMTPRecipientsRefused as e:
        print("Recipient refused: Check the recipient email address.")
        print(f"Exception details: {e}")
    except smtplib.SMTPSenderRefused as e:
        print("Sender refused: Check the sender email address.")
        print(f"Exception details: {e}")
    except smtplib.SMTPException as e:
        print(f"SMTP error occurred: {e}")
    except Exception as e:
        print(f"Error sending email: {e}")
if __name__ == '__main__':
    
    ngrok_url = "https://cognitive-web.onrender.com"
    print(f" * ngrok tunnel \ -> \"https://cognitive-web.onrender.com\"")
    app.run(port=5000)