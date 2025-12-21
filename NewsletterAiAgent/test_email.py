
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

def test_smtp():
    load_dotenv()
    
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("FROM_EMAIL")
    
    # Use the username as recipient if no other is specific for test
    recipient = username
    
    print(f"Testing SMTP connection to {host}:{port}...")
    print(f"User: {username}")
    print(f"From: {from_email}")
    
    if not (username and password):
        print("ERROR: SMTP_USERNAME or SMTP_PASSWORD not set in .env")
        return

    try:
        server = smtplib.SMTP(host, port)
        server.set_debuglevel(1)  # Show full SMTP transaction
        server.starttls()
        print("Logging in...")
        server.login(username, password)
        print("Login successful!")
        
        msg = MIMEText("This is a test email to verify SMTP credentials.")
        msg['Subject'] = "SMTP Test"
        msg['From'] = from_email or username
        msg['To'] = recipient
        
        print(f"Sending test email to {recipient}...")
        server.sendmail(from_email or username, [recipient], msg.as_string())
        print("Email sent successfully!")
        server.quit()
    except Exception as e:
        print(f"\nERROR: Failed to send email.\n{e}")

if __name__ == "__main__":
    test_smtp()
