#!/usr/bin/env python3
"""
Meta/Facebook Agent for Vendedor360
Handles Meta API interactions and validations
"""
import os
import sys
import json
import argparse
import logging
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MetaAgent:
    """Meta/Facebook API Agent"""
    
    def __init__(self):
        self.meta_user = os.getenv('META_USER')
        self.meta_pass = os.getenv('META_PASS')
        self.access_token = os.getenv('META_ACCESS_TOKEN')
        self.app_id = os.getenv('META_APP_ID')
        self.graph_api_url = 'https://graph.facebook.com/v18.0'
        
    def validate_credentials(self):
        """Validate that required credentials are present"""
        if not self.access_token:
            logger.error("META_ACCESS_TOKEN not found in environment")
            return False
        if not self.app_id:
            logger.error("META_APP_ID not found in environment")
            return False
        return True
    
    def validate_access_token(self):
        """Validate access token by making a test API call to Graph API"""
        try:
            logger.info("Validating Meta access token...")
            
            # Make a simple call to /me endpoint to verify token
            url = f"{self.graph_api_url}/me"
            params = {
                'access_token': self.access_token,
                'fields': 'id,name'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Access token validated successfully. User ID: {data.get('id')}")
                return True, data
            else:
                error_data = response.json()
                logger.error(f"Access token validation failed: {error_data}")
                return False, error_data
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception during token validation: {e}")
            return False, {'error': str(e)}
    
    def save_status_json(self, is_valid, data):
        """Save status to JSON file in artifacts directory"""
        try:
            # Create artifacts directory if it doesn't exist
            artifacts_dir = 'artifacts'
            os.makedirs(artifacts_dir, exist_ok=True)
            
            # Generate timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Extract user_id from data if validation was successful
            user_id = data.get('id', None) if is_valid else None
            
            # Prepare JSON structure
            status_json = {
                'timestamp': timestamp,
                'api_validated': is_valid,
                'user_id': user_id,
                'app_id': self.app_id,
                'status': 'operational' if is_valid else 'error'
            }
            
            # Save to file
            filename = f"{artifacts_dir}/meta_{timestamp}.json"
            with open(filename, 'w') as f:
                json.dump(status_json, f, indent=2)
            
            logger.info(f"Status JSON saved to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving status JSON: {e}")
            return False
    
    def write_status(self, status_data):
        """Write status report to markdown file"""
        try:
            status_file = 'STATUS_META.md'
            
            with open(status_file, 'w') as f:
                f.write("# Meta/Facebook Agent Status\n\n")
                f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**Status:** {status_data.get('status', 'unknown').upper()}\n\n")
                
                if status_data.get('api_validated'):
                    user_data = status_data.get('user_data', {})
                    f.write("## API Validation\n\n")
                    f.write(f"- Access Token: ✓ Valid\n")
                    f.write(f"- User ID: {user_data.get('id', 'N/A')}\n")
                    f.write(f"- User Name: {user_data.get('name', 'N/A')}\n")
                else:
                    f.write("## API Validation\n\n")
                    f.write(f"- Access Token: ✗ Invalid\n")
                    f.write(f"- Error: {status_data.get('error', 'Unknown error')}\n")
                
                f.write("\n## Configuration\n\n")
                f.write(f"- App ID: {self.app_id if self.app_id else 'Not configured'}\n")
                f.write(f"- User: {self.meta_user if self.meta_user else 'Not configured'}\n")
            
            logger.info(f"Status written to {status_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing status file: {e}")
            return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Meta/Facebook Agent for Vendedor360'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Generate status report'
    )
    
    args = parser.parse_args()
    
    logger.info("Starting Meta Agent...")
    
    # Initialize agent
    agent = MetaAgent()
    
    # Validate credentials are present
    if not agent.validate_credentials():
        logger.error("Missing required credentials. Please set META_ACCESS_TOKEN and META_APP_ID environment variables.")
        sys.exit(1)
    
    # Validate access token with Graph API
    is_valid, data = agent.validate_access_token()
    
    # Save status to JSON
    agent.save_status_json(is_valid, data)
    
    # Prepare status data
    status_data = {
        'status': 'operational' if is_valid else 'error',
        'api_validated': is_valid,
    }
    
    if is_valid:
        status_data['user_data'] = data
        logger.info("Meta agent is operational")
    else:
        status_data['error'] = data
        logger.error("Meta agent validation failed")
    
    # Write status if requested
    if args.status:
        agent.write_status(status_data)
    
    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)

if __name__ == '__main__':
    main()
