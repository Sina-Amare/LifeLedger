# test_smtp.py

import smtplib
from email.mime.text import MIMEText
import ssl # Import the ssl module for context

# --- Email Configuration ---
# Replace with your Gmail address and App Password
sender_email = "sinaamareh0263@gmail.com"
# IMPORTANT: Use your App Password here, NOT your regular Gmail password
sender_password = "gggimyogeubwmxtq" # Your App Password without spaces

# Replace with the recipient email address (can be the same as sender_email for testing)
recipient_email = "sinaamareh0263@gmail.com" # You can send a test email to yourself

# Gmail SMTP server details
smtp_server = "smtp.gmail.com"
smtp_port = 587 # Port for TLS

# --- Email Content ---
subject = "SMTP Test Email from LifeLedger Project"
body = "This is a test email sent from a Python script to check SMTP settings."

# Create a MIMEText object
msg = MIMEText(body)
msg['Subject'] = subject
msg['From'] = sender_email
msg['To'] = recipient_email

print(f"Attempting to send email from {sender_email} to {recipient_email}...")

try:
    # Create a secure SSL context
    context = ssl.create_default_context()

    # Connect to the SMTP server using TLS
    # Use smtplib.SMTP for port 587 (TLS)
    print(f"Connecting to {smtp_server} on port {smtp_port}...")
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        # Start TLS encryption
        server.starttls(context=context)
        print("TLS connection established.")

        # Log in to the email account
        print(f"Logging in as {sender_email}...")
        server.login(sender_email, sender_password)
        print("Login successful.")

        # Send the email
        print("Sending email...")
        server.sendmail(sender_email, recipient_email, msg.as_string())
        print("Email sent successfully!")

except smtplib.SMTPAuthenticationError as e:
    print(f"SMTP Authentication Error: {e}")
    print("Please check your email address and App Password in the script.")
    print("Ensure you are using an App Password if 2-Step Verification is enabled for your Gmail account.")
    print("Also check your Gmail security settings for any blocked sign-in attempts.")

except smtplib.SMTPException as e:
    print(f"An SMTP error occurred: {e}")

except Exception as e:
    print(f"An unexpected error occurred: {e}")

print("SMTP test script finished.")
