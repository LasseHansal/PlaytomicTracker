import requests
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

class PlaytomicMonitor:
    def __init__(self, config):
        self.config = config
        self.known_available = set()
        
    def get_available_courts(self):
        try:
            url = "https://playtomic.com/api/clubs/availability"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json'
            }
            
            # Check today and the next 4 days
            dates_to_check = [
                (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
                for i in range(5)
            ]
            
            all_results = []
            
            for tenant_id in self.config['tenant_ids']:
                for date_str in dates_to_check:
                    print(f"Checking {date_str}...", end=" ")
                    
                    params = {
                        'tenant_id': tenant_id,
                        'sport_id': 'PADEL', 
                        'date': date_str
                    }
                    
                    try:
                        response = requests.get(url, headers=headers, params=params, timeout=10)
                        
                        if response.status_code == 200:
                            data = response.json()
                            if isinstance(data, list) and len(data) > 0:
                                print("Data found.")
                                all_results.append({'date': date_str, 'data': data})
                            else:
                                print("No slots.")
                        else:
                            print(f"Status {response.status_code}")
                            
                    except Exception as e:
                        print(f"Error: {e}")
                    
                    time.sleep(1)
            
            return all_results
            
        except Exception as e:
            print(f"Global Error: {e}")
            return None

    def check_and_notify(self):
        print(f"\n--- Cycle Start: {datetime.now().strftime('%H:%M:%S')} ---")
        availability_data = self.get_available_courts()
        
        if not availability_data:
            print("Status: No open courts found this cycle.")
            return

        found_slots = []
        current_cycle_ids = set()

        for day in availability_data:
            date_str = day['date']
            
            for resource in day['data']:
                court_id = resource.get('resource_id', 'Unknown')
                
                for slot in resource.get('slots', []):
                    start_time = slot.get('start_time')
                    price = slot.get('price')
                    duration = slot.get('duration')
                    
                    slot_id = f"{date_str}_{court_id}_{start_time}"
                    current_cycle_ids.add(slot_id)
                    
                    found_slots.append({
                        'date': date_str,
                        'time': start_time[:5],
                        'price': price,
                        'duration': duration
                    })

        new_openings = current_cycle_ids - self.known_available
        
        if found_slots:
            print(f"Total slots visible: {len(found_slots)}")
            
            if new_openings:
                print(f"FOUND {len(new_openings)} NEW SLOTS! Sending email...")
                
                display_list = found_slots[:20]
                
                html_rows = ""
                for s in display_list:
                    html_rows += f"<li><b>{s['date']}</b> {s['time']} ({s['duration']} min) - {s['price']}</li>"
                
                email_body = f"""
                <h2>Courts Available!</h2>
                <p>Found {len(found_slots)} slots. Here are the first few:</p>
                <ul>{html_rows}</ul>
                <p><a href="https://playtomic.io">Book Now</a></p>
                """
                
                self.send_email("Padel Availability Alert!", email_body)
            else:
                print("Slots exist, but you were already notified.")
        else:
            print("No courts available.")

        self.known_available = current_cycle_ids

    def send_email(self, subject, body):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['email_to']
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP_SSL(self.config['smtp_server'], 465, timeout=30)
            server.login(self.config['email_from'], self.config['email_password'])
            server.send_message(msg)
            server.quit()
            
            print(f"Email sent successfully!")
            return True
        except Exception as e:
            print(f"Email Failed: {e}")
            return False

    def run(self):
        print(f"Starting Monitor...")
        # Send a test email on startup to verify connection immediately
        print("Sending startup test email...")
        self.send_email("Monitor Started", "The Padel Monitor is online.")
        
        while True:
            try:
                self.check_and_notify()
                time.sleep(self.config['check_interval'])
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Loop Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    config = {
        'email_from': 'hansallasse@gmail.com',
        'email_password': 'isushgbcdiasldcn',
        'email_to': 'matteo@kalmund.com',
        'smtp_server': 'smtp.gmail.com',
        'tenant_ids': ['5bb4ad71-dbd9-499e-88fb-c9a5e7df6db6'], 
        'check_interval': 300 
    }
    
    monitor = PlaytomicMonitor(config)
    monitor.run()