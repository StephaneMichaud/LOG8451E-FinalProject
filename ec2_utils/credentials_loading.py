import os
from configparser import ConfigParser

def load_credentials(dotenv_path):
    config = ConfigParser()
    config.read(dotenv_path)

    aws_access_key_id = config.get('default', 'aws_access_key_id')
    aws_secret_access_key = config.get('default', 'aws_secret_access_key')
    aws_session_token = config.get('default', 'aws_session_token')
    aws_region = config.get("us-east-1", 'aws_region')

    # Set up AWS credentials
    os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    os.environ['AWS_SESSION_TOKEN'] = aws_session_token
    os.environ['AWS_DEFAULT_REGION'] = aws_region


