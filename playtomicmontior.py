import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
from datetime import datetime
import json

class PlaytomicMonitor:
    def __init__(self, config):
        """
        Initialize the Playtomic monitor
        
        config should contain:
        - email_from: sender email
        - email_password: sender email password (app-specific password recommended)
        - email_to: recipient email
        - smtp_server: SMTP server (e.g., 'smtp.gmail.com')
        - smtp_port: SMTP port (e.g., 587)
        - location: your location/city
        - check_interval: seconds between checks (default: 300 = 5 minutes)
        """
        self.config = config
        self.known_available = set()
        self.base_url = "https://playtomic.io/api/v1"
        
    def get_available_courts(self):
        """
        Check Playtomic API for available courts
        Note: You'll need to inspect Playtomic's actual API endpoints
        This is a template - adjust based on actual API structure
        """
        try:
            # Example endpoint - you'll need to find the actual one
            # You may need to use browser dev tools to find the real API calls
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            }
            
            # This is a placeholder - replace with actual API endpoint
            # You'll likely need tenant_id, sport_id, and location parameters
            params = {
                'tenant_id': 'YOUR_TENANT_ID',  # Find this from browser network tab
                'sport_id': 'PADEL',  # or whatever sport ID they use
                'location': self.config.get('location')
            }
            
            # Placeholder endpoint - inspect the actual Playtomic website
            response = requests.get(
                f"{self.base_url}/venues",
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error: Status code {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error fetching courts: {e}")
            return None
    
    def send_email(self, subject, body):
        """Send email notification"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['email_to']
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(
                self.config['smtp_server'], 
                self.config['smtp_port']
            )
            server.starttls()
            server.login(
                self.config['email_from'], 
                self.config['email_password']
            )
            
            server.send_message(msg)
            server.quit()
            
            print(f"Email sent: {subject}")
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def format_notification(self, available_courts):
        """Format the email notification"""
        html = "<h2>🎾 Paddle Courts Available!</h2>"
        html += f"<p>Found {len(available_courts)} available court(s) at {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>"
        html += "<ul>"
        
        for court in available_courts:
            # Adjust these fields based on actual API response
            venue = court.get('venue_name', 'Unknown Venue')
            time_slot = court.get('time', 'Unknown Time')
            price = court.get('price', 'N/A')
            
            html += f"<li><strong>{venue}</strong> - {time_slot} - €{price}</li>"
        
        html += "</ul>"
        html += "<p>Book now at <a href='https://playtomic.io'>Playtomic</a></p>"
        
        return html
    
    def check_and_notify(self):
        """Main monitoring logic"""
        print(f"Checking for available courts at {datetime.now()}")
        
        data = self.get_available_courts()
        
        if data is None:
            return
        
        # Parse available courts - adjust based on actual API structure
        available_courts = []
        # This is placeholder logic - modify based on actual response
        if isinstance(data, dict) and 'courts' in data:
            available_courts = [c for c in data['courts'] if c.get('available')]
        
        # Create unique identifiers for courts
        current_available = set()
        for court in available_courts:
            # Create a unique ID based on venue, time, and court
            court_id = f"{court.get('venue_id')}_{court.get('court_id')}_{court.get('time')}"
            current_available.add(court_id)
        
        # Find newly available courts
        new_courts = current_available - self.known_available
        
        if new_courts:
            print(f"Found {len(new_courts)} new available court(s)!")
            # Filter to just the new courts
            new_court_details = [c for c in available_courts 
                                 if f"{c.get('venue_id')}_{c.get('court_id')}_{c.get('time')}" in new_courts]
            
            notification = self.format_notification(new_court_details)
            self.send_email("New Paddle Courts Available!", notification)
        else:
            print("No new courts available")
        
        # Update known available courts
        self.known_available = current_available
    
    def run(self):
        """Start the monitoring loop"""
        check_interval = self.config.get('check_interval', 300)
        
        print(f"Starting Playtomic monitor...")
        print(f"Checking every {check_interval} seconds")
        print(f"Location: {self.config.get('location')}")
        print(f"Notifications to: {self.config['email_to']}")
        print("-" * 50)
        
        while True:
            try:
                self.check_and_notify()
                time.sleep(check_interval)
            except KeyboardInterrupt:
                print("\nMonitor stopped by user")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait a minute before retrying

# Example usage
if __name__ == "__main__":
    # Configuration
    config = {
        'email_from': 'your_email@gmail.com',
        'email_password': 'your_app_specific_password',  # Use app-specific password!
        'email_to': 'recipient@gmail.com',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'location': 'Mannheim',  # Your location
        'check_interval': 300,  # Check every 5 minutes
    }
    
    monitor = PlaytomicMonitor(config)
    monitor.run()