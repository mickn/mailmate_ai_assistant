#!/opt/homebrew/bin/python3
import os
import sys
import json
import urllib.request
import urllib.error
import ssl
import base64
import configparser

# Set up logging
import logging
logging.basicConfig(filename='/tmp/gpt_assist.log', level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

logging.info(f"Script started. Python version: {sys.version}")

# Load configuration
config = configparser.ConfigParser()
config.read(os.path.expanduser('~/Library/Application Support/MailMate/Bundles/GPTAssistant.mmbundle/config.ini'))

API_PROVIDER = config['DEFAULT']['ApiProvider']
API_KEY = config['DEFAULT']['ApiKey']
MODEL = config['DEFAULT']['Model']

def log_error(message):
    logging.error(message)
    print(json.dumps({"actions": [{"type": "notify", "message": message}]}))

def call_api(prompt):
    if API_PROVIDER == 'anthropic':
        return call_anthropic_api(prompt)
    elif API_PROVIDER == 'openai':
        return call_openai_api(prompt)
    else:
        raise ValueError(f"Unsupported API provider: {API_PROVIDER}")

def call_anthropic_api(prompt):
    url = "https://api.anthropic.com/v1/messages"
    data = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('X-Api-Key', API_KEY)
    req.add_header('anthropic-version', '2023-06-01')

    context = ssl._create_unverified_context()
    with urllib.request.urlopen(req, context=context) as response:
        response_data = json.loads(response.read().decode('utf-8'))

    return response_data['content'][0]['text'].strip()

def call_openai_api(prompt):
    url = "https://api.openai.com/v1/chat/completions"
    data = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1000
    }).encode('utf-8')

    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Authorization', f'Bearer {API_KEY}')

    context = ssl._create_unverified_context()
    with urllib.request.urlopen(req, context=context) as response:
        response_data = json.loads(response.read().decode('utf-8'))

    return response_data['choices'][0]['message']['content'].strip()

try:
    # Get email context from environment variables
    subject = os.environ.get('MM_SUBJECT', '')
    to_address = os.environ.get('MM_TO', '')
    from_address = os.environ.get('MM_FROM', '')
    content_type = os.environ.get('MM_CONTENT_TYPE', 'text/plain')

    logging.debug(f"Subject: {subject}")
    logging.debug(f"To: {to_address}")
    logging.debug(f"From: {from_address}")
    logging.debug(f"Content-Type: {content_type}")

    # Read the current email content from stdin
    email_content = sys.stdin.read()
    logging.debug(f"Email content length: {len(email_content)}")

    # If content is base64 encoded (likely for HTML), decode it
    if content_type.startswith('text/html'):
        email_content = base64.b64decode(email_content).decode('utf-8')

    # Prepare the prompt for AI
    prompt = f"""
    Your task is to create a brief, polished email response based on the given email thread. Follow these guidelines:

    Analyze the email thread to understand the context, including who you are (the sender) and who you're replying to.
    If there's any text above the most recent email, treat it as your draft response or additional instructions.
    Keep the response ultra-concise, aiming for 2-3 sentences maximum.
    Maintain a professional yet approachable tone appropriate for your role.
    Address only the most recent points or questions that require a response.
    Use clear, simple language.
    Include a brief greeting and sign-off appropriate for the conversation stage.

    Important: Do not introduce yourself or restate information already known to both parties. Respond as if continuing an ongoing conversation.
    To: {to_address}
    From: {from_address}

    Email thread:
    {email_content}

    Respond only with the refined email. Do not include any explanations or comments outside of the response.
    """

    # Call the appropriate API
    generated_text = call_api(prompt)

    logging.debug(f"Generated text: {generated_text}")

    # Combine original content with generated text
    if content_type.startswith('text/html'):
        combined_content = f"""
        <html>
        <body>
        {generated_text}
        <br />
        {email_content}
        </body>
        </html>
        """
    else:
        combined_content = f"{generated_text}\n\n{email_content}"

    # Prepare the action to create and open the new draft
    action = {
        "actions": [
            {
                "type": "createMessage",
                "headers": {
                    "subject": f"Re: {subject}",
                    "to": to_address,
                    "from": from_address,
                    "content-type": content_type
                },
                "body": combined_content,
                "resultActions": [
                    {
                        "type": "openMessage"
                    }
                ]
            }
        ]
    }

    # Output the action as JSON
    print(json.dumps(action))
    logging.info("Script completed successfully")

except Exception as e:
    log_error(f"Unexpected error: {str(e)}")
    logging.exception("An unexpected error occurred:")

logging.info("Script completed")