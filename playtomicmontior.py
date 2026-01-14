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
            print("Status: No data received.")
            return

        found_slots = []
        current_cycle_ids = set()

        for day in availability_data:
            date_str = day['date']
            
            for resource in day['data']:
                court_id = resource.get('resource_id', 'Unknown')
                
                # FILTER 1: Skip Outdoor Courts
                if court_id in self.config['ignored_courts']:
                    continue

                for slot in resource.get('slots', []):
                    start_time = slot.get('start_time') # Format "17:30:00"
                    price = slot.get('price')
                    duration = slot.get('duration')
                    
                    # FILTER 2: Time Check (After 17:00)
                    # We take the first 2 characters of time ("17") and convert to int
                    hour = int(start_time.split(':')[0])
                    if hour < self.config['min_hour']:
                        continue 

                    # If we survived the filters, add to list
                    slot_id = f"{date_str}_{court_id}_{start_time}"
                    current_cycle_ids.add(slot_id)
                    
                    found_slots.append({
                        'date': date_str,
                        'time': start_time[:5],
                        'price': price,
                        'duration': duration
                    })

        # Identify NEW openings only
        # This prevents spam. If we already saw this slot 5 mins ago, we ignore it.
        new_openings = current_cycle_ids - self.known_available
        
        if found_slots:
            print(f"Valid Indoor Slots (>17:00): {len(found_slots)}")
            
            if new_openings:
                print(f"FOUND {len(new_openings)} NEW SLOTS! Sending email...")
                
                # Sort by date and time
                found_slots.sort(key=lambda x: (x['date'], x['time']))
                display_list = found_slots[:20]
                
                html_rows = ""
                for s in display_list:
                    html_rows += f"<li><b>{s['date']}</b> {s['time']} ({s['duration']} min) - {s['price']}</li>"
                
                email_body = f"""
                <h2>Indoor Courts Available!</h2>
                <p>Found {len(found_slots)} slots after {self.config['min_hour']}:00.</p>
                <ul>{html_rows}</ul>
                <p><a href="https://playtomic.io">Book Now</a></p>
                """
                
                self.send_email(f"Padel Alert: {len(new_openings)} New Slots!", email_body)
            else:
                print("Slots exist, but you were already notified. Staying quiet.")
        else:
            print("No matching courts (Indoor & >17:00) available.")

        # Update memory so we remember these for next time
        self.known_available = current_cycle_ids

    def send_email(self, subject, body):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['email_to']
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            # Using SMTP_SSL (Port 465) for better firewall compatibility
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
        print(f"Filtering: Indoor courts only, after {self.config['min_hour']}:00")
        
        # Test email
        print("Sending startup test email...")
        self.send_email("Padel Bot Started", "The Monitor is online and filtering for evening indoor courts.")
        
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
        'check_interval': 300, # 5 Minutes
        
        'min_hour': 17, # Only show courts at 17:00 or later
        'ignored_courts': [
            '75318066-28dd-40a1-8936-acb5cb61f652', # Outdoor 1
            'c1110cfb-350d-48e6-8669-57e432fe27c9', # Outdoor 2
            'da5e34ea-c4e3-489d-8e99-a19de7933f10'  # Outdoor 3
        ]
    }
    
    monitor = PlaytomicMonitor(config)
    monitor.run()