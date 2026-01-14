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
        Check Playtomic API for available courts using the actual API endpoint
        """
        try:
            from datetime import datetime, timedelta
            
            headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'application/json'
            }
            
            # Get today's date in the format Playtomic expects (YYYY-MM-DD)
            date_today = datetime.now().strftime('%Y-%m-%d')
            
            # List of tenant IDs for clubs in Mannheim (you'll need to add more)
            # Find these by clicking on different clubs and checking the network tab
            tenant_ids = self.config.get('tenant_ids', [
                '5bb4ad71-dbd9-499e-88fb-c9a5e7df6db6',  # Example club
                # Add more tenant IDs for Mannheim clubs here
            ])
            
            all_available = []
            
            for tenant_id in tenant_ids:
                params = {
                    'tenant_id': tenant_id,
                    'sport_id': 'PADEL',
                    'date': date_today
                }
                
                response = requests.get(
                    "https://playtomic.com/api/clubs/availability",
                    headers=headers,
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    # Store the availability data with tenant_id
                    if data:
                        all_available.append({
                            'tenant_id': tenant_id,
                            'data': data
                        })
                else:
                    print(f"Error for tenant {tenant_id}: Status code {response.status_code}")
            
            return all_available
                
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
        
        # Parse available courts from the API response
        available_courts = []
        
        for club_data in data:
            tenant_id = club_data['tenant_id']
            availability = club_data['data']
            
            # Playtomic API usually returns slots or resources
            # Parse the structure - this may need adjustment based on actual response
            if isinstance(availability, list):
                for slot in availability:
                    if slot.get('available'):
                        available_courts.append({
                            'tenant_id': tenant_id,
                            'court_id': slot.get('resource_id') or slot.get('id'),
                            'time': slot.get('start_time') or slot.get('time'),
                            'price': slot.get('price'),
                            'venue_name': slot.get('venue_name') or 'Unknown Club'
                        })
        
        # Create unique identifiers for courts
        current_available = set()
        for court in available_courts:
            court_id = f"{court['tenant_id']}_{court['court_id']}_{court['time']}"
            current_available.add(court_id)
        
        # Find newly available courts
        new_courts = current_available - self.known_available
        
        if new_courts:
            print(f"Found {len(new_courts)} new available court(s)!")
            # Filter to just the new courts
            new_court_details = [c for c in available_courts 
                                 if f"{c['tenant_id']}_{c['court_id']}_{c['time']}" in new_courts]
            
            notification = self.format_notification(new_court_details)
            self.send_email("🎾 New Padel Courts Available in Mannheim!", notification)
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
        'email_from': 'hansallasse@gmail.com',
        'email_password': 'isus hgbc dias ldcn',
        'email_to': 'matteo@kalmund.com',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'location': 'Mannheim',
        'check_interval': 300,  # Check every 5 minutes
        'tenant_ids': [
            '5bb4ad71-dbd9-499e-88fb-c9a5e7df6db6',
        ]
    }
    
    monitor = PlaytomicMonitor(config)
    monitor.run()