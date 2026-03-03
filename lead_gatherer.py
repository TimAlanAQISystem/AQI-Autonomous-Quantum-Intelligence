# Lead Gathering System for Monday Campaigns
# Integrates with North API and other sources

import os
import requests
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any
import time

class LeadGatherer:
    def __init__(self):
        self.north_api_key = os.getenv('NORTH_API_KEY', 'D232BA67A0FF48EBE053320F180A5797')
        self.leads_db = 'monday_leads.db'
        self.setup_database()

    def setup_database(self):
        """Initialize leads database"""
        conn = sqlite3.connect(self.leads_db)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY,
                source TEXT,
                business_name TEXT,
                contact_name TEXT,
                phone TEXT,
                email TEXT,
                industry TEXT,
                location TEXT,
                priority INTEGER DEFAULT 1,
                status TEXT DEFAULT 'new',
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def gather_north_leads(self) -> List[Dict]:
        """Gather leads from North API"""
        leads = []

        try:
            # North API endpoints (assuming REST API)
            headers = {'Authorization': f'Bearer {self.north_api_key}'}

            # Example endpoints - adjust based on actual North API
            endpoints = [
                'https://api.north.com/merchants/prospects',
                'https://api.north.com/leads/hot',
                'https://api.north.com/businesses/new'
            ]

            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        leads.extend(self.parse_north_data(data, endpoint))
                    else:
                        print(f"North API error for {endpoint}: {response.status_code}")
                except Exception as e:
                    print(f"Error fetching from {endpoint}: {e}")

                time.sleep(1)  # Rate limiting

        except Exception as e:
            print(f"North API gathering failed: {e}")

        return leads

    def parse_north_data(self, data: Dict, source: str) -> List[Dict]:
        """Parse North API response into lead format"""
        leads = []

        # Adjust parsing based on actual API response structure
        if 'merchants' in data:
            for merchant in data['merchants']:
                lead = {
                    'source': 'north_api',
                    'business_name': merchant.get('business_name', ''),
                    'contact_name': merchant.get('contact_name', ''),
                    'phone': merchant.get('phone', ''),
                    'email': merchant.get('email', ''),
                    'industry': merchant.get('industry', ''),
                    'location': merchant.get('location', ''),
                    'priority': merchant.get('priority', 1),
                    'notes': f"From {source}"
                }
                leads.append(lead)

        return leads

    def gather_additional_leads(self) -> List[Dict]:
        """Gather leads from other sources"""
        leads = []

        # Example: Local business directories, Yellow Pages API, etc.
        # For now, return sample leads
        sample_leads = [
            {
                'source': 'local_directory',
                'business_name': 'Downtown Cafe',
                'contact_name': 'Sarah Wilson',
                'phone': '+14062102346',
                'email': 'info@downtowncafe.com',
                'industry': 'restaurant',
                'location': 'Downtown',
                'priority': 2,
                'notes': 'High foot traffic location'
            },
            {
                'source': 'referral',
                'business_name': 'Tech Solutions Inc',
                'contact_name': 'Mike Johnson',
                'phone': '+14062102347',
                'email': 'mike@techsolutions.com',
                'industry': 'technology',
                'location': 'Business District',
                'priority': 3,
                'notes': 'Existing client referral'
            }
        ]

        leads.extend(sample_leads)
        return leads

    def save_leads(self, leads: List[Dict]):
        """Save leads to database"""
        conn = sqlite3.connect(self.leads_db)
        cursor = conn.cursor()

        for lead in leads:
            cursor.execute('''
                INSERT OR REPLACE INTO leads
                (source, business_name, contact_name, phone, email, industry, location, priority, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                lead.get('source', ''),
                lead.get('business_name', ''),
                lead.get('contact_name', ''),
                lead.get('phone', ''),
                lead.get('email', ''),
                lead.get('industry', ''),
                lead.get('location', ''),
                lead.get('priority', 1),
                lead.get('notes', '')
            ))

        conn.commit()
        conn.close()
        print(f"Saved {len(leads)} leads to database")

    def get_campaign_leads(self, limit: int = 100) -> List[Dict]:
        """Get leads ready for campaigns"""
        conn = sqlite3.connect(self.leads_db)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM leads
            WHERE status = 'new'
            ORDER BY priority DESC, created_at ASC
            LIMIT ?
        ''', (limit,))

        leads = []
        for row in cursor.fetchall():
            leads.append({
                'id': row[0],
                'source': row[1],
                'business_name': row[2],
                'contact_name': row[3],
                'phone': row[4],
                'email': row[5],
                'industry': row[6],
                'location': row[7],
                'priority': row[8],
                'status': row[9],
                'notes': row[10],
                'created_at': row[11]
            })

        conn.close()
        return leads

    def run_full_gathering(self):
        """Run complete lead gathering process"""
        print("Starting Monday lead gathering...")

        # Gather from all sources
        north_leads = self.gather_north_leads()
        additional_leads = self.gather_additional_leads()

        all_leads = north_leads + additional_leads

        # Save to database
        self.save_leads(all_leads)

        # Report results
        total_leads = len(all_leads)
        print(f"Gathered {total_leads} total leads")
        print(f"North API: {len(north_leads)} leads")
        print(f"Additional sources: {len(additional_leads)} leads")

        return all_leads

# Global instance
lead_gatherer = LeadGatherer()

if __name__ == "__main__":
    leads = lead_gatherer.run_full_gathering()
    campaign_leads = lead_gatherer.get_campaign_leads(10)
    print(f"Ready for campaigns: {len(campaign_leads)} leads")
    for lead in campaign_leads[:3]:
        print(f"- {lead['business_name']} ({lead['phone']})")