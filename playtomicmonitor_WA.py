import requests
import time
import urllib.parse # Needed to format the message safely
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
                
                # Filter: Ignore Outdoor Courts
                if court_id in self.config['ignored_courts']:
                    continue

                for slot in resource.get('slots', []):
                    start_time = slot.get('start_time')
                    price = slot.get('price')
                    
                    # Filter: Time Check (After 17:00)
                    hour = int(start_time.split(':')[0])
                    if hour < self.config['min_hour']:
                        continue 

                    slot_id = f"{date_str}_{court_id}_{start_time}"
                    current_cycle_ids.add(slot_id)
                    
                    found_slots.append({
                        'date': date_str,
                        'time': start_time[:5],
                        'price': price
                    })

        new_openings = current_cycle_ids - self.known_available
        
        if found_slots:
            print(f"Valid Indoor Slots (>17:00): {len(found_slots)}")
            
            if new_openings:
                print(f"FOUND {len(new_openings)} NEW SLOTS! Sending WhatsApp...")
                
                found_slots.sort(key=lambda x: (x['date'], x['time']))
                
                # Format message for WhatsApp (simple text, no HTML)
                msg_lines = ["🎾 *Padel Courts Available!*"]
                msg_lines.append(f"Found {len(found_slots)} indoor slots after {self.config['min_hour']}:00")
                msg_lines.append("") # Empty line
                
                # Show top 10 slots
                for s in found_slots[:10]:
                    msg_lines.append(f"📅 {s['date']} @ {s['time']} ({s['price']})")
                
                msg_lines.append("")
                msg_lines.append("Book: https://playtomic.io")
                
                full_message = "\n".join(msg_lines)
                
                self.send_whatsapp(full_message)
            else:
                print("Slots exist, but you were already notified. Staying quiet.")
        else:
            print("No matching courts available.")

        self.known_available = current_cycle_ids

    def send_whatsapp(self, message):
        """Sends a WhatsApp message via CallMeBot"""
        try:
            phone = self.config['whatsapp_phone']
            apikey = self.config['whatsapp_apikey']
            
            # URL Encode the message (turn spaces into %20, etc.)
            encoded_msg = urllib.parse.quote(message)
            
            url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_msg}&apikey={apikey}"
            
            # Send the request
            requests.get(url, timeout=10)
            print("✅ WhatsApp sent successfully!")
            return True
            
        except Exception as e:
            print(f"❌ WhatsApp Failed: {e}")
            return False

    def run(self):
        print(f"Starting Monitor...")
        print(f"Filtering: Indoor courts only, after {self.config['min_hour']}:00")
        
        # Test WhatsApp
        print("Sending startup test message...")
        self.send_whatsapp("🤖 Padel Monitor Started! I will text you when courts open.")
        
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
        # --- WHATSAPP CONFIG ---
        'whatsapp_phone': '4915112345678', # Your number with country code (e.g., 49 for Germany), NO + symbol
        'whatsapp_apikey': '123456',       # The code you got from the bot
        
        'tenant_ids': ['5bb4ad71-dbd9-499e-88fb-c9a5e7df6db6'], 
        'check_interval': 300,
        
        'min_hour': 17, 
        'ignored_courts': [
            '75318066-28dd-40a1-8936-acb5cb61f652', 
            'c1110cfb-350d-48e6-8669-57e432fe27c9', 
            'da5e34ea-c4e3-489d-8e99-a19de7933f10'
        ]
    }
    
    monitor = PlaytomicMonitor(config)
    monitor.run()