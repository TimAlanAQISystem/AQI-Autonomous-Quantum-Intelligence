"""
AGENT X - RESOURCE HUNTER (Ascendrym IQ Edition)
================================================
The "Hunter/Gatherer" Engine.
Agent X is responsible for scouring the environment for Business Opportunities,
Financial Partners, and Resources to populate the Business Center.
Alan (The Boss) oversees these findings.

Powered by Ascendrym IQ Logic Core.
"""

import time
import random
import sqlite3
import json
import sys
import os
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict

# Add src to path to find modules if needed
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from alan_backup_sync import AlanTeleportProtocol  # Renamed from alan_teleport_protocol.py
except ImportError:
    AlanTeleportProtocol = None

class AgentXResourceHunter:
    def __init__(self):
        self.db_path = "aqi_merchant_services.db"
        self.setup_database()
        
        # Initialize Security Protocol
        if AlanTeleportProtocol:
            self.security = AlanTeleportProtocol()
            self.security.activate_shield()
        else:
            self.security = None
            
        print("🕵️  AGENT X RESOURCE HUNTER INITIALIZED (Ascendrym IQ)")
        print("   Mission: Locate Financial Tools & Partners for Alan's Business Center")
        print("   Logic Core: Ascendrym IQ Active")
        print("   Mode: REAL-WORLD DATA HUNTING")

    def setup_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table for potential partners found by Agent X
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS resource_opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                provider_name TEXT,
                product_name TEXT,
                terms_summary TEXT,
                api_endpoint TEXT,
                status TEXT DEFAULT 'pending_review', -- pending_review, approved_by_alan, rejected
                discovery_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source_url TEXT
            )
        """)
        conn.commit()
        conn.close()

    def start_hunting(self):
        """Continuous loop looking for resources"""
        print("🦅 Agent X is hunting for opportunities...")
        
        # Initial Security Check
        if self.security:
            if not self.security.run_security_check():
                print("❌ Security Check Failed. Halting Hunt.")
                return

        while True:
            try:
                # Periodic Security Pulse
                if self.security and random.random() < 0.1:
                    self.security.run_security_check()

                # Hunt for Real Data
                print("   🔎 Scanning financial news feeds for partnership opportunities...")
                opportunities = self.hunt_real_financial_news()
                
                if opportunities:
                    for opp in opportunities:
                        self.report_findings(opp)
                else:
                    print("   ...No new viable opportunities found this cycle.")
                
                time.sleep(300) # Hunt every 5 minutes (Real data doesn't change every second)
            except Exception as e:
                print(f"❌ Hunting error: {e}")
                time.sleep(60)

    def hunt_real_financial_news(self) -> List[Dict]:
        """
        Fetch REAL financial news from RSS feeds to identify potential partners.
        Replaces the old 'random' simulation with actual market data.
        """
        opportunities = []
        
        # List of Real Financial RSS Feeds
        feeds = [
            "https://feeds.content.dowjones.io/public/rss/mw_top_stories", # MarketWatch
            "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664", # CNBC Finance
            "http://feeds.reuters.com/reuters/businessNews" # Reuters Business
        ]
        
        target_keywords = ['loan', 'lending', 'fintech', 'payment', 'credit', 'banking', 'capital', 'merchant']
        
        for feed_url in feeds:
            try:
                response = requests.get(feed_url, timeout=10)
                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    
                    # Parse RSS Items
                    for item in root.findall('.//item'):
                        title = item.find('title').text
                        link = item.find('link').text
                        description = item.find('description').text if item.find('description') is not None else ""
                        
                        # Check if relevant to our business
                        if any(keyword in title.lower() or keyword in description.lower() for keyword in target_keywords):
                            
                            # Construct Opportunity Object from Real Data
                            opp = {
                                'category': 'Market Intelligence',
                                'provider_name': 'Unknown (News Lead)', # We'd need NLP to extract entity, for now we capture the lead
                                'product_name': title[:100],
                                'terms_summary': f"Detected in Market News: {description[:200]}...",
                                'api_endpoint': link, # Source URL
                                'source_url': link
                            }
                            opportunities.append(opp)
                            
            except Exception as e:
                # print(f"   [Debug] Feed fetch error: {e}")
                pass
                
        return opportunities

    def report_findings(self, opp: Dict):
        """Report the finding to the database for Alan to review"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if already exists (by product name / title)
        cursor.execute("SELECT id FROM resource_opportunities WHERE product_name = ?", 
                      (opp['product_name'],))
        if cursor.fetchone():
            conn.close()
            return

        cursor.execute("""
            INSERT INTO resource_opportunities 
            (category, provider_name, product_name, terms_summary, api_endpoint, source_url)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (opp['category'], opp['provider_name'], opp['product_name'], opp['terms_summary'], opp['api_endpoint'], opp.get('source_url')))
        
        conn.commit()
        conn.close()
        print(f"📦 Agent X Found REAL Opportunity: {opp['product_name'][:50]}... - Sent to Alan.")

if __name__ == "__main__":
    hunter = AgentXResourceHunter()
    hunter.start_hunting()
