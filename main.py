from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import mysql.connector
from mysql.connector import Error
from azure.communication.email import EmailClient

# Configuration
EMAIL_CONNECTION_STRING = "endpoint=https://ai-mailing.unitedstates.communication.azure.com/;accesskey=AVEVdvPHOzVUMAnXrGlm63cgvVPyWFuTQZLPxCona26mdeiqKif5JQQJ99AKACULyCphD9BDAAAAAZCSycfM"
SENDER_EMAIL = "DoNotReply@onmeridian.com"


# DB credentials
host_name = "mysqlai.mysql.database.azure.com"
user_name = "azureadmin"
user_password = "Meridian@123"
db_name = "chatbot"

# FastAPI app
app = FastAPI()

# CORS setup (optional, adjust as needed)
origins = ["*"]  # Allow all for development, restrict for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model
class Chat_User(BaseModel):
    full_Name: str
    email: str
    phone: str
    Inquiry_type: str
    company_name: str


# DB connection
def create_connection(host_name, user_name, user_password, db_name):
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
        return connection
    except Error as e:
        print(f"Error: '{e}'")
        return None

# Email sender function
async def send_email(recipient_email: str, subject: str, html_content: str):
    try:
        client = EmailClient.from_connection_string(EMAIL_CONNECTION_STRING)

        message = {
            "senderAddress": SENDER_EMAIL,
            "recipients": {
                "to": [{"address": recipient_email}],
            },
            "content": {
                "subject": subject,
                "plainText": "Please view this email in an HTML-enabled client.",
                "html": html_content,
            },
        }

        poller = client.begin_send(message)
        result = poller.result()
        print("GFdssd", result)
        print(f"Email sent to {recipient_email} with ID: {result['messageId']}")

        return True
    except Exception as ex:
        print(f"Failed to send email to {recipient_email}: {ex}")
        return False

# POST /insert endpoint
@app.post('/insert')
async def insert_data(user: Chat_User, background_tasks: BackgroundTasks):
    print("Received data:", user)

    connection = create_connection(host_name, user_name, user_password, db_name)
    if connection is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = connection.cursor()
    query = """
        INSERT INTO googleworkspace (full_name, email, phone, inquiry_type, company_name)
        VALUES (%s, %s, %s, %s, %s)
    """
    values = (
        user.full_Name,
        user.email,
        user.phone,
        user.Inquiry_type,
        user.company_name,
        
    )

    try:
        cursor.execute(query, values)
        connection.commit()

        # Email contents
        user_subject = "Thank you for contacting Meridian Solutions"
        user_html = f"""
        <html>
        <body>
            <h2>Hi {user.full_Name},</h2>
            <p>Thanks for reaching out. We’ve received your inquiry and will respond shortly.</p>
            <h3>Your Submitted Details:</h3>
            <ul>
                <li><strong>Email:</strong> {user.email}</li>
                <li><strong>Phone:</strong> {user.phone}</li>
                <li><strong>Inquiry Type:</strong> {user.Inquiry_type}</li>
                <li><strong>Company:</strong> {user.company_name}</li>
        
            </ul>
            <p>Best Regards,<br/>Meridian Solutions</p>
        </body>
        </html>
        """

        notify_subject = "New Inquiry Received - Meridian Website"
        notify_html = f"""
        <html>
        <body>
            <h2>New Inquiry for Google Workspace</h2>
            <ul>
                <li><strong>Name:</strong> {user.full_Name}</li>
                <li><strong>Email:</strong> {user.email}</li>
                <li><strong>Phone:</strong> {user.phone}</li>
                <li><strong>Inquiry Type:</strong> {user.Inquiry_type}</li>
                <li><strong>Company:</strong> {user.company_name}</li>
               

            </ul>
        </body>
        </html>
        """

        # Send both emails
        background_tasks.add_task(send_email, user.email, user_subject, user_html)
        background_tasks.add_task(send_email, "sales.gws@merdian.info", notify_subject, notify_html)

        return {"message": "Data inserted and emails sent successfully"}
    except Error as e:
        raise HTTPException(status_code=500, detail=f"MySQL error: {e}")
    finally:
        cursor.close()
        connection.close()
