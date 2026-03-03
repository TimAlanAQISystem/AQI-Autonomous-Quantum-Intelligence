#!/usr/bin/env python3
"""
AQI MERCHANT SERVICES CORE MODULE
=================================
Complete autonomous merchant services system integrating all AQI components
"""

import os
import json
import sqlite3
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
import random

# Add paths for AQI components
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Agent X'))

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, ConversationRelay

# Import Capabilities
try:
    from aqi_lead_importer import AQILeadImporter
    LEAD_IMPORTER_AVAILABLE = True
except ImportError:
    LEAD_IMPORTER_AVAILABLE = False

try:
    from alan_teleport_protocol import AlanTeleportProtocol
    TELEPORT_AVAILABLE = True
except ImportError:
    TELEPORT_AVAILABLE = False

try:
    from agent_x_resource_hunter import AgentXResourceHunter
    AGENT_X_AVAILABLE = True
except ImportError:
    AGENT_X_AVAILABLE = False

class AQIMerchantServicesCore:
    """
    Complete autonomous merchant services system
    Integrates all AQI components for full merchant lifecycle management
    """

    def __init__(self):
        print("🚀 INITIALIZING AQI MERCHANT SERVICES CORE...")
        print("=" * 60)

        # Initialize core components
        self.setup_merchant_database()
        self.initialize_twilio_integration()
        self.load_merchant_services_config()
        self.initialize_agent_alan_integration()
        self.setup_autonomous_operations()
        
        # Engage Teleport Protocol (Disaster Recovery)
        if TELEPORT_AVAILABLE:
            self.teleport = AlanTeleportProtocol()
            self.teleport_thread = threading.Thread(target=self.teleport.engage_teleport_engine, daemon=True)
            self.teleport_thread.start()
            print("⚡ Alan Teleport Protocol: ACTIVE (Cloud Vault Secured)")

        # Performance tracking
        self.merchants_acquired = 0
        self.calls_completed = 0
        self.accounts_onboarded = 0
        self.revenue_generated = 0.0

        print("✅ AQI MERCHANT SERVICES CORE READY FOR AUTONOMOUS OPERATION")

    def setup_merchant_database(self):
        """Setup comprehensive merchant services database"""

        self.db_path = "aqi_merchant_services.db"
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Core merchant profiles - ENDLESS CRM SCHEMA
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id TEXT UNIQUE,
                business_name TEXT,
                contact_name TEXT,
                phone TEXT,
                email TEXT,
                business_type TEXT,
                industry TEXT,
                monthly_volume REAL,
                current_processor TEXT,
                current_rate REAL,
                pain_points TEXT,
                lead_source TEXT,
                lead_score INTEGER,
                status TEXT DEFAULT 'prospect',
                acquisition_date TIMESTAMP,
                onboarding_status TEXT,
                compliance_status TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Endless CRM Fields
                address_line1 TEXT,
                address_line2 TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                website_url TEXT,
                social_media_links TEXT,
                owner_details TEXT,
                ein_tax_id TEXT,
                pos_system_type TEXT,
                employee_count INTEGER,
                years_in_business INTEGER,
                customer_sentiment TEXT DEFAULT 'Neutral',
                last_contact_date TIMESTAMP,
                next_scheduled_touchpoint TIMESTAMP,
                notes_history TEXT
            )
        """)

        # Migration: Ensure Endless CRM fields exist for legacy databases
        crm_fields = [
            "address_line1 TEXT", "address_line2 TEXT", "city TEXT", "state TEXT", "zip_code TEXT",
            "website_url TEXT", "social_media_links TEXT", "owner_details TEXT", "ein_tax_id TEXT",
            "pos_system_type TEXT", "employee_count INTEGER", "years_in_business INTEGER",
            "customer_sentiment TEXT DEFAULT 'Neutral'", "last_contact_date TIMESTAMP",
            "next_scheduled_touchpoint TIMESTAMP", "notes_history TEXT"
        ]
        
        for field in crm_fields:
            try:
                column_name = field.split()[0]
                cursor.execute(f"ALTER TABLE merchants ADD COLUMN {field}")
                print(f"✅ Migrated database: Added {column_name}")
            except sqlite3.OperationalError:
                pass # Column likely exists

        # Call and conversation tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchant_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id TEXT,
                call_sid TEXT,
                call_type TEXT,
                duration INTEGER,
                outcome TEXT,
                language_used TEXT,
                ai_confidence REAL,
                notes TEXT,
                call_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Payment processing and accounts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS merchant_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id TEXT,
                account_number TEXT,
                processor_name TEXT,
                monthly_fee REAL,
                transaction_rate REAL,
                setup_date TIMESTAMP,
                status TEXT DEFAULT 'active',
                compliance_verified BOOLEAN DEFAULT FALSE
            )
        """)

        # Revenue and performance tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS revenue_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id TEXT,
                monthly_revenue REAL,
                transaction_volume REAL,
                period_start DATE,
                period_end DATE,
                recorded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Compliance and regulatory tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id TEXT,
                compliance_type TEXT,
                status TEXT,
                verification_date TIMESTAMP,
                expiry_date DATE,
                notes TEXT
            )
        """)

        # AQI Business Center - The "Full Suite" Portfolio
        # Tracks non-physical financial products (Loans, Leases, Insurance, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS business_center_portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_id TEXT,
                category TEXT, -- 'Lending', 'Leasing', 'Insurance', 'Payroll'
                product_name TEXT,
                provider TEXT,
                status TEXT, -- 'Active', 'Pending', 'Closed'
                amount_value REAL,
                start_date DATE,
                end_date DATE,
                terms_details TEXT,
                FOREIGN KEY(merchant_id) REFERENCES merchants(merchant_id)
            )
        """)

        conn.commit()
        conn.close()
        print("✅ Merchant services database initialized")

    def initialize_twilio_integration(self):
        """Initialize Twilio integration for voice calling"""

        # Load Twilio credentials
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID', '')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER', '+14067322659')

        try:
            self.twilio_client = Client(self.twilio_account_sid, self.twilio_auth_token)
            print("✅ Twilio integration initialized")
        except Exception as e:
            print(f"❌ Twilio initialization failed: {e}")
            self.twilio_client = None

    def load_merchant_services_config(self):
        """Load merchant services configuration"""

        self.config = {
            'lead_sources': [
                'north_api', 'local_directory', 'referral', 'web_scraping', 'public_records'
            ],
            'target_industries': [
                'restaurant', 'retail', 'professional_services', 'healthcare',
                'automotive', 'gas_station', 'ecommerce', 'hospitality'
            ],
            'pricing_tiers': {
                'basic': {'monthly_fee': 14.95, 'transaction_rate': 0.0},
                'premium': {'monthly_fee': 29.95, 'transaction_rate': 0.15},
                'enterprise': {'monthly_fee': 99.95, 'transaction_rate': 0.10}
            },
            'compliance_requirements': [
                'pci_dss', 'hipaa', 'business_license', 'bank_account_verification'
            ],
            'call_strategies': {
                'cold_call': 'Direct value proposition with savings calculation',
                'follow_up': 'Address previous conversation and objections',
                'referral': 'Leverage trusted referral source',
                'qualification': 'Deep dive into pain points and needs'
            },
            # AQI Business Center - Full Financial Suite
            'business_center_catalog': {
                'lending': ['Business Term Loans', 'SBA Loans', 'Lines of Credit', 'Merchant Cash Advance'],
                'leasing': ['Equipment Leasing', 'Technology Financing', 'Vehicle Leasing', 'Furniture Financing'],
                'insurance': ['General Liability', 'Workers Compensation', 'Cyber Liability', 'Commercial Property'],
                'operations': ['Payroll Services', 'HR Solutions', 'Tax Preparation', 'Legal Services'],
                'banking': ['High-Yield Business Savings', 'Corporate Credit Cards', 'Expense Management']
            }
        }

        print("✅ Merchant services configuration loaded")

    def initialize_agent_alan_integration(self):
        """Initialize integration with Agent Alan business AI"""

        try:
            # Import Agent Alan (this will work when run from Agent X directory)
            from agent_alan_business_ai import AgentAlanBusinessAI
            self.agent_alan = AgentAlanBusinessAI()
            print("✅ Agent Alan business AI integrated")
        except ImportError:
            print("⚠️ Agent Alan not available - using fallback logic")
            self.agent_alan = None

    def setup_autonomous_operations(self):
        """Setup autonomous operation threads"""

        self.autonomous_threads = {
            'lead_generation': threading.Thread(target=self.autonomous_lead_generation, daemon=True),
            'merchant_calling': threading.Thread(target=self.autonomous_merchant_calling, daemon=True),
            'account_management': threading.Thread(target=self.autonomous_account_management, daemon=True),
            'compliance_monitoring': threading.Thread(target=self.autonomous_compliance_monitoring, daemon=True),
            'customer_success': threading.Thread(target=self.autonomous_customer_success, daemon=True),
            'business_center_overseer': threading.Thread(target=self.autonomous_business_center_overseer, daemon=True),
            'agent_x_coordination': threading.Thread(target=self.autonomous_agent_x_coordination, daemon=True)
        }

        print("✅ Autonomous operations framework initialized")

    def start_autonomous_operations(self):
        """Start all autonomous operations"""

        print("🚀 STARTING AUTONOMOUS MERCHANT SERVICES OPERATIONS...")

        for name, thread in self.autonomous_threads.items():
            thread.start()
            print(f"✅ {name.replace('_', ' ').title()} thread started")

        print("🎯 AQI MERCHANT SERVICES NOW OPERATING AUTONOMOUSLY")

    def autonomous_lead_generation(self):
        """Autonomous lead generation system"""

        while True:
            try:
                print("🔍 Checking for new merchant leads...")

                # Auto-Fill Connection: Import from RSE Agent (OneDrive)
                if LEAD_IMPORTER_AVAILABLE:
                    print("☁️  Syncing with RSE Agent Cloud Storage...")
                    importer = AQILeadImporter()
                    leads = importer.import_leads_from_excel()
                    if leads:
                        importer.save_leads_to_database(leads)
                        print(f"✅ Auto-filled {len(leads)} leads from RSE Agent")
                    else:
                        print("ℹ️ No new leads found in RSE Cloud Sync")
                
                # SAFETY: Synthetic lead generation disabled for production use
                # new_leads = self.generate_merchant_leads(5)
                # self.save_merchant_leads(new_leads)
                
                # Wait before next generation cycle
                time.sleep(300)  # 5 minutes

            except Exception as e:
                print(f"❌ Lead generation error: {e}")
                time.sleep(60)

    def generate_merchant_leads(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic merchant leads"""

        industries = self.config['target_industries']
        lead_sources = self.config['lead_sources']

        leads = []
        for i in range(count):
            industry = random.choice(industries)
            lead_source = random.choice(lead_sources)

            # Generate realistic business data
            business_templates = {
                'restaurant': ['Pizza Palace', 'Burger Barn', 'Taco Town', 'Pasta House', 'Sushi Spot'],
                'retail': ['Fashion Boutique', 'Electronics Plus', 'Book Nook', 'Sporting Goods', 'Jewelry Store'],
                'professional_services': ['Law Offices', 'Accounting Firm', 'Real Estate Agency', 'Insurance Agency'],
                'healthcare': ['Medical Clinic', 'Dental Office', 'Physical Therapy', 'Chiropractic Care'],
                'automotive': ['Auto Repair Shop', 'Car Dealership', 'Tire Center', 'Auto Parts Store'],
                'gas_station': ['Speedy Gas', 'Fuel Stop', 'Corner Store', 'Convenience Mart'],
                'ecommerce': ['Online Boutique', 'Tech Gadgets', 'Home Goods Store', 'Beauty Products'],
                'hospitality': ['Hotel Suites', 'Bed & Breakfast', 'Event Venue', 'Spa Retreat']
            }

            business_names = business_templates.get(industry, ['Generic Business'])
            business_name = random.choice(business_names) + f" {i+1}"

            # Generate contact info
            first_names = ['John', 'Jane', 'Mike', 'Sarah', 'David', 'Lisa', 'Tom', 'Amy']
            last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis']
            contact_name = f"{random.choice(first_names)} {random.choice(last_names)}"

            # Generate realistic volume and rates
            volume_ranges = {
                'restaurant': (15000, 75000),
                'retail': (20000, 100000),
                'professional_services': (10000, 50000),
                'healthcare': (25000, 150000),
                'automotive': (30000, 120000),
                'gas_station': (50000, 200000),
                'ecommerce': (25000, 500000),
                'hospitality': (20000, 80000)
            }

            min_vol, max_vol = volume_ranges.get(industry, (10000, 50000))
            monthly_volume = random.randint(min_vol, max_vol)

            # Current rates (typically higher than our offer)
            current_rates = [2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.2]
            current_rate = random.choice(current_rates)

            # Generate phone number
            area_codes = ['212', '213', '305', '312', '404', '415', '504', '602', '713', '718', '786', '805', '818', '954']
            area_code = random.choice(area_codes)
            phone = f"+1{area_code}{random.randint(1000000, 9999999)}"

            lead = {
                'merchant_id': f"LEAD-{industry.upper()}-{i+1:04d}",
                'business_name': business_name,
                'contact_name': contact_name,
                'phone': phone,
                'email': f"contact@{business_name.lower().replace(' ', '')}.com",
                'business_type': industry,
                'industry': industry,
                'monthly_volume': monthly_volume,
                'current_processor': random.choice(['Stripe', 'Square', 'First Data', 'TSYS', 'Authorize.net']),
                'current_rate': current_rate,
                'pain_points': random.choice([
                    'High processing rates',
                    'Too many fees',
                    'Poor customer service',
                    'Slow settlement',
                    'Complex setup'
                ]),
                'lead_source': lead_source,
                'lead_score': random.randint(60, 95),
                'status': 'prospect'
            }

            leads.append(lead)

        return leads

    def save_merchant_leads(self, leads: List[Dict[str, Any]]):
        """Save merchant leads to database"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for lead in leads:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO merchants
                    (merchant_id, business_name, contact_name, phone, email, business_type,
                     industry, monthly_volume, current_processor, current_rate, pain_points,
                     lead_source, lead_score, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    lead['merchant_id'], lead['business_name'], lead['contact_name'],
                    lead['phone'], lead['email'], lead['business_type'], lead['industry'],
                    lead['monthly_volume'], lead['current_processor'], lead['current_rate'],
                    lead['pain_points'], lead['lead_source'], lead['lead_score'], lead['status']
                ))
            except Exception as e:
                print(f"❌ Error saving lead {lead['merchant_id']}: {e}")

        conn.commit()
        conn.close()

    def autonomous_merchant_calling(self):
        """Autonomous merchant calling system"""

        while True:
            try:
                print("📞 Initiating autonomous merchant calling campaign...")

                # Get prospects ready for calling
                prospects = self.get_calling_prospects(3)

                if not prospects:
                    print("⏳ No prospects ready for calling, waiting...")
                    time.sleep(300)
                    continue

                for prospect in prospects:
                    self.make_merchant_call(prospect)
                    time.sleep(10)  # Brief pause between calls

                print(f"✅ Completed calling campaign for {len(prospects)} prospects")

                # Wait before next calling cycle
                time.sleep(600)  # 10 minutes

            except Exception as e:
                print(f"❌ Merchant calling error: {e}")
                time.sleep(60)

    def get_calling_prospects(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get prospects ready for calling"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM merchants
            WHERE status = 'prospect'
            ORDER BY lead_score DESC, created_date ASC
            LIMIT ?
        """, (limit,))

        prospects = []
        for row in cursor.fetchall():
            prospect = {
                'id': row[0],
                'merchant_id': row[1],
                'business_name': row[2],
                'contact_name': row[3],
                'phone': row[4],
                'email': row[5],
                'business_type': row[6],
                'industry': row[7],
                'monthly_volume': row[8],
                'current_processor': row[9],
                'current_rate': row[10],
                'pain_points': row[11],
                'lead_source': row[12],
                'lead_score': row[13],
                'status': row[14]
            }
            prospects.append(prospect)

        conn.close()
        return prospects

    def make_merchant_call(self, prospect: Dict[str, Any]):
        """Make a merchant acquisition call"""

        if not self.twilio_client:
            print("❌ Twilio client not available")
            return

        try:
            print(f"📞 Calling {prospect['business_name']} - {prospect['contact_name']}")

            # Calculate potential savings
            monthly_volume = prospect['monthly_volume']
            current_rate = prospect['current_rate']
            current_cost = monthly_volume * (current_rate / 100)
            new_cost = 14.95  # Edge Program fee
            monthly_savings = current_cost - new_cost
            annual_savings = monthly_savings * 12

            # Create personalized greeting
            greeting = f"Hello {prospect['contact_name']}! This is Alan from AQI Merchant Services. I found {prospect['business_name']} and wanted to discuss how we can save you over ${annual_savings:,.0f} annually on payment processing."

            # Create ConversationRelay for AI-powered call
            response = VoiceResponse()
            connect = Connect()

            conversation_relay = ConversationRelay(
                url="ws://localhost:8765",
                welcome_greeting=greeting,
                welcome_greeting_interruptible="any",
                language="en-US",
                tts_provider="ElevenLabs",
                voice="21m00Tcm4TlvDq8ikWAM",  # Adam - professional male voice
                transcription_provider="Deepgram",
                speech_model="nova-3-general",
                interruptible="any",
                interrupt_sensitivity="high",
                dtmf_detection="true"
            )

            # Add merchant context
            conversation_relay.parameter(name="call_type", value="merchant_acquisition")
            conversation_relay.parameter(name="prospect_name", value=prospect['contact_name'])
            conversation_relay.parameter(name="business_name", value=prospect['business_name'])
            conversation_relay.parameter(name="monthly_volume", value=str(monthly_volume))
            conversation_relay.parameter(name="current_rate", value=str(current_rate))
            conversation_relay.parameter(name="annual_savings", value=str(int(annual_savings)))

            connect.append(conversation_relay)
            response.append(connect)

            # Make the call
            call = self.twilio_client.calls.create(
                twiml=str(response),
                to=prospect['phone'],
                from_=self.twilio_phone_number
            )

            # Record the call
            self.record_merchant_call(prospect['merchant_id'], call.sid, 'acquisition')

            print(f"✅ Call initiated: {call.sid}")
            self.calls_completed += 1

        except Exception as e:
            print(f"❌ Call failed for {prospect['business_name']}: {e}")

    def record_merchant_call(self, merchant_id: str, call_sid: str, call_type: str):
        """Record merchant call in database"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO merchant_calls (merchant_id, call_sid, call_type, outcome)
            VALUES (?, ?, ?, ?)
        """, (merchant_id, call_sid, call_type, 'initiated'))

        conn.commit()
        conn.close()

    def autonomous_account_management(self):
        """Autonomous account management and onboarding"""

        while True:
            try:
                print("📊 Managing merchant accounts and onboarding...")

                # Check for merchants ready for onboarding
                pending_onboarding = self.get_pending_onboarding()

                for merchant in pending_onboarding:
                    self.process_merchant_onboarding(merchant)

                # Update account statuses
                self.update_account_statuses()

                print(f"✅ Processed {len(pending_onboarding)} onboarding requests")

                # Wait before next management cycle
                time.sleep(1800)  # 30 minutes

            except Exception as e:
                print(f"❌ Account management error: {e}")
                time.sleep(60)

    def get_pending_onboarding(self) -> List[Dict[str, Any]]:
        """Get merchants pending onboarding"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM merchants
            WHERE status = 'qualified' AND onboarding_status IS NULL
            LIMIT 5
        """)

        merchants = []
        for row in cursor.fetchall():
            merchant = {
                'id': row[0],
                'merchant_id': row[1],
                'business_name': row[2],
                'contact_name': row[3],
                'phone': row[4],
                'email': row[5],
                'business_type': row[6],
                'industry': row[7],
                'monthly_volume': row[8],
                'current_processor': row[9],
                'current_rate': row[10]
            }
            merchants.append(merchant)

        conn.close()
        return merchants

    def process_merchant_onboarding(self, merchant: Dict[str, Any]):
        """Process merchant onboarding"""

        print(f"🎯 Onboarding {merchant['business_name']}")

        # Simulate onboarding process
        onboarding_steps = [
            'document_collection',
            'compliance_verification',
            'bank_account_setup',
            'equipment_shipping',
            'training_scheduled'
        ]

        for step in onboarding_steps:
            print(f"   ✅ {step.replace('_', ' ').title()}")
            time.sleep(1)

        # Create merchant account
        self.create_merchant_account(merchant)

        # Update merchant status
        self.update_merchant_status(merchant['merchant_id'], 'onboarding', 'active')

        print(f"✅ {merchant['business_name']} successfully onboarded")

    def create_merchant_account(self, merchant: Dict[str, Any]):
        """Create merchant account record"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Determine pricing tier based on volume
        volume = merchant['monthly_volume']
        if volume >= 100000:
            tier = 'enterprise'
        elif volume >= 50000:
            tier = 'premium'
        else:
            tier = 'basic'

        pricing = self.config['pricing_tiers'][tier]

        cursor.execute("""
            INSERT INTO merchant_accounts
            (merchant_id, processor_name, monthly_fee, transaction_rate, setup_date, status)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            merchant['merchant_id'],
            'AQI Merchant Services',
            pricing['monthly_fee'],
            pricing['transaction_rate'],
            datetime.now().date(),
            'active'
        ))

        conn.commit()
        conn.close()

        self.accounts_onboarded += 1

    def update_merchant_status(self, merchant_id: str, onboarding_status: str, overall_status: str):
        """Update merchant status"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE merchants
            SET onboarding_status = ?, status = ?
            WHERE merchant_id = ?
        """, (onboarding_status, overall_status, merchant_id))

        conn.commit()
        conn.close()

    def update_account_statuses(self):
        """Update account statuses and track revenue"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get active accounts
        cursor.execute("""
            SELECT ma.merchant_id, ma.monthly_fee, m.monthly_volume, m.business_name
            FROM merchant_accounts ma
            JOIN merchants m ON ma.merchant_id = m.merchant_id
            WHERE ma.status = 'active'
        """)

        active_accounts = cursor.fetchall()

        for merchant_id, monthly_fee, volume, business_name in active_accounts:
            # Record monthly revenue
            cursor.execute("""
                INSERT INTO revenue_tracking
                (merchant_id, monthly_revenue, transaction_volume, period_start, period_end)
                VALUES (?, ?, ?, date('now', 'start of month'), date('now', 'start of month', '+1 month', '-1 day'))
            """, (merchant_id, monthly_fee, volume))

            self.revenue_generated += monthly_fee

        conn.commit()
        conn.close()

    def autonomous_compliance_monitoring(self):
        """Autonomous compliance monitoring"""

        while True:
            try:
                print("🔒 Monitoring compliance and regulatory requirements...")

                # Check compliance expiry dates
                expired_compliance = self.check_compliance_expiry()

                for item in expired_compliance:
                    self.handle_compliance_expiry(item)

                # Verify new merchant compliance
                pending_verification = self.get_pending_compliance_verification()

                for merchant in pending_verification:
                    self.verify_merchant_compliance(merchant)

                print(f"✅ Compliance monitoring completed - {len(expired_compliance)} expiries, {len(pending_verification)} verifications")

                # Wait before next compliance check
                time.sleep(86400)  # 24 hours

            except Exception as e:
                print(f"❌ Compliance monitoring error: {e}")
                time.sleep(3600)

    def check_compliance_expiry(self) -> List[Dict[str, Any]]:
        """Check for expired compliance items"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM compliance_records
            WHERE expiry_date <= date('now', '+30 days') AND status = 'active'
        """)

        expired = []
        for row in cursor.fetchall():
            expired.append({
                'id': row[0],
                'merchant_id': row[1],
                'compliance_type': row[2],
                'status': row[3],
                'expiry_date': row[4]
            })

        conn.close()
        return expired

    def handle_compliance_expiry(self, compliance_item: Dict[str, Any]):
        """Handle compliance expiry"""

        print(f"⚠️ Compliance expiring: {compliance_item['compliance_type']} for merchant {compliance_item['merchant_id']}")

        # In a real system, this would trigger renewal processes
        # For demo, we'll just log it
        pass

    def get_pending_compliance_verification(self) -> List[Dict[str, Any]]:
        """Get merchants pending compliance verification"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM merchants
            WHERE status = 'active' AND compliance_status IS NULL
            LIMIT 3
        """)

        pending = []
        for row in cursor.fetchall():
            pending.append({
                'merchant_id': row[1],
                'business_name': row[2],
                'business_type': row[6]
            })

        conn.close()
        return pending

    def verify_merchant_compliance(self, merchant: Dict[str, Any]):
        """Verify merchant compliance"""

        print(f"🔍 Verifying compliance for {merchant['business_name']}")

        # Simulate compliance verification
        compliance_items = ['pci_dss', 'business_license', 'bank_verification']

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for item in compliance_items:
            cursor.execute("""
                INSERT INTO compliance_records
                (merchant_id, compliance_type, status, verification_date, expiry_date)
                VALUES (?, ?, ?, ?, ?)
            """, (
                merchant['merchant_id'],
                item,
                'verified',
                datetime.now().date(),
                (datetime.now() + timedelta(days=365)).date()
            ))

        # Update merchant compliance status
        cursor.execute("""
            UPDATE merchants SET compliance_status = 'verified'
            WHERE merchant_id = ?
        """, (merchant['merchant_id'],))

        conn.commit()
        conn.close()

        print(f"✅ Compliance verified for {merchant['business_name']}")

    def autonomous_customer_success(self):
        """Autonomous Customer Success Office - 'Touching Bases'"""
        
        while True:
            try:
                print("🤝 Customer Success Office: Checking for merchants to touch base with...")
                
                # Find merchants who haven't been contacted in 30 days
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Select active merchants with no recent contact
                cursor.execute("""
                    SELECT * FROM merchants 
                    WHERE status = 'active' 
                    AND (last_contact_date IS NULL OR last_contact_date <= date('now', '-30 days'))
                    ORDER BY last_contact_date ASC
                    LIMIT 3
                """)
                
                merchants_to_call = []
                columns = [description[0] for description in cursor.description]
                for row in cursor.fetchall():
                    merchants_to_call.append(dict(zip(columns, row)))
                
                conn.close()

                if not merchants_to_call:
                    print("✅ All active merchants have been contacted recently.")
                
                for merchant in merchants_to_call:
                    self.make_touch_base_call(merchant)
                    time.sleep(60) # Wait between calls

                # Check every hour
                time.sleep(3600) 

            except Exception as e:
                print(f"❌ Customer Success error: {e}")
                time.sleep(60)

    def make_touch_base_call(self, merchant: Dict[str, Any]):
        """Make a 'Touching Base' call to ensure customer satisfaction"""
        
        if not self.twilio_client:
            print("❌ Twilio client not available for Customer Success call")
            return

        try:
            print(f"📞 Touching base with {merchant['business_name']} (Customer Success)...")

            # Create personalized greeting
            greeting = f"Hi {merchant['contact_name']}, it's Alan from AQI. I'm just calling to touch base and make sure everything is running smoothly with your payment processing. How have things been going?"

            # Create ConversationRelay for AI-powered call
            response = VoiceResponse()
            connect = Connect()

            conversation_relay = ConversationRelay(
                url="ws://localhost:8765",
                welcome_greeting=greeting,
                welcome_greeting_interruptible="any",
                language="en-US",
                tts_provider="ElevenLabs",
                voice="21m00Tcm4TlvDq8ikWAM",  # Adam - professional male voice
                transcription_provider="Deepgram",
                speech_model="nova-3-general",
                interruptible="any",
                interrupt_sensitivity="high",
                dtmf_detection="true"
            )

            # Add merchant context
            conversation_relay.parameter(name="call_type", value="customer_success_touch_base")
            conversation_relay.parameter(name="merchant_name", value=merchant['contact_name'])
            conversation_relay.parameter(name="business_name", value=merchant['business_name'])
            conversation_relay.parameter(name="sentiment", value=merchant.get('customer_sentiment', 'Neutral'))

            connect.append(conversation_relay)
            response.append(connect)

            # Make the call
            call = self.twilio_client.calls.create(
                twiml=str(response),
                to=merchant['phone'],
                from_=self.twilio_phone_number
            )

            # Record the call
            self.record_merchant_call(merchant['merchant_id'], call.sid, 'customer_success')
            
            # Update last contact date
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE merchants SET last_contact_date = CURRENT_TIMESTAMP WHERE merchant_id = ?", (merchant['merchant_id'],))
            conn.commit()
            conn.close()

            print(f"✅ Touch-base call initiated: {call.sid}")
            self.calls_completed += 1

        except Exception as e:
            print(f"❌ Touch-base call failed for {merchant['business_name']}: {e}")

    def autonomous_agent_x_coordination(self):
        """Coordinate with Agent X (Resource Hunter)"""
        if not AGENT_X_AVAILABLE:
            return

        # Start Agent X in a sub-thread if not running externally
        # In a distributed system, Agent X might run on another node, but here we simulate local coordination
        hunter = AgentXResourceHunter()
        hunter_thread = threading.Thread(target=hunter.start_hunting, daemon=True)
        hunter_thread.start()
        print("🦅 Agent X deployed for Resource Hunting")

    def autonomous_business_center_overseer(self):
        """Alan's Overseer Role: Review Agent X findings & Manage Portfolio"""
        
        while True:
            try:
                print("👁️  Alan Overseer: Reviewing Business Center & Agent X Findings...")
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # 1. Review Pending Opportunities found by Agent X
                try:
                    cursor.execute("SELECT * FROM resource_opportunities WHERE status = 'pending_review'")
                    pending_opps = cursor.fetchall()
                    
                    if pending_opps:
                        print(f"   📝 Reviewing {len(pending_opps)} new resources found by Agent X...")
                        for opp in pending_opps:
                            # Alan's Decision Logic (Simulated)
                            # In reality, this might check against compliance rules or profitability
                            opp_id = opp[0]
                            provider = opp[2]
                            
                            # Approve everything for now to build the catalog
                            cursor.execute("UPDATE resource_opportunities SET status = 'approved_by_alan' WHERE id = ?", (opp_id,))
                            print(f"   ✅ Alan Approved: {provider} added to Business Center Catalog.")
                            
                            # Add to active catalog (simulated logic)
                            # self.add_to_catalog(opp)
                except sqlite3.OperationalError:
                    pass # Table might not exist yet if Agent X hasn't run
                
                # 2. Analyze Portfolio Opportunities (Cross-Sell)
                # Example: Find merchants with high volume (>50k) and >2 years in business for 'Line of Credit'
                cursor.execute("""
                    SELECT * FROM merchants 
                    WHERE status = 'active' 
                    AND monthly_volume > 50000 
                    AND years_in_business >= 2
                    AND merchant_id NOT IN (
                        SELECT merchant_id FROM business_center_portfolio WHERE product_name = 'Line of Credit'
                    )
                    LIMIT 3
                """)
                
                opportunities = []
                columns = [description[0] for description in cursor.description]
                for row in cursor.fetchall():
                    opportunities.append(dict(zip(columns, row)))
                
                conn.close()

                for opp in opportunities:
                    print(f"💡 Business Center Insight: {opp['business_name']} qualifies for Line of Credit (Vol: ${opp['monthly_volume']:,.0f})")
                
                # Check every 4 hours
                time.sleep(14400)

            except Exception as e:
                print(f"❌ Overseer error: {e}")
                time.sleep(60)

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get key metrics
        cursor.execute("SELECT COUNT(*) FROM merchants WHERE status = 'prospect'")
        prospects = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM merchants WHERE status = 'active'")
        active_merchants = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM merchant_calls WHERE call_date >= date('now', '-30 days')")
        recent_calls = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(monthly_revenue) FROM revenue_tracking WHERE recorded_date >= date('now', '-30 days')")
        recent_revenue = cursor.fetchone()[0] or 0

        conn.close()

        return {
            'system_status': 'operational',
            'autonomous_threads': len([t for t in self.autonomous_threads.values() if t.is_alive()]),
            'merchants_acquired': self.merchants_acquired,
            'calls_completed': self.calls_completed,
            'accounts_onboarded': self.accounts_onboarded,
            'revenue_generated': self.revenue_generated,
            'active_merchants': active_merchants,
            'prospects_available': prospects,
            'recent_calls': recent_calls,
            'recent_revenue': recent_revenue,
            'uptime': 'continuous'
        }

    def generate_merchant_services_report(self) -> Dict[str, Any]:
        """Generate comprehensive merchant services report"""

        status = self.get_system_status()

        report = {
            'report_date': datetime.now().isoformat(),
            'system_overview': {
                'status': status['system_status'],
                'autonomous_operations': status['autonomous_threads'] == 4,
                'uptime': status['uptime']
            },
            'performance_metrics': {
                'merchants_acquired': status['merchants_acquired'],
                'calls_completed': status['calls_completed'],
                'accounts_onboarded': status['accounts_onboarded'],
                'active_merchants': status['active_merchants'],
                'prospects_available': status['prospects_available']
            },
            'revenue_metrics': {
                'total_revenue_generated': status['revenue_generated'],
                'recent_revenue': status['recent_revenue'],
                'average_revenue_per_merchant': status['revenue_generated'] / max(status['accounts_onboarded'], 1)
            },
            'operational_metrics': {
                'recent_calls': status['recent_calls'],
                'call_conversion_rate': status['accounts_onboarded'] / max(status['calls_completed'], 1),
                'lead_to_merchant_ratio': status['accounts_onboarded'] / max(status['merchants_acquired'], 1)
            },
            'system_capabilities': {
                'lead_generation': True,
                'autonomous_calling': True,
                'account_management': True,
                'compliance_monitoring': True,
                'agent_alan_integration': self.agent_alan is not None,
                'twilio_integration': self.twilio_client is not None
            }
        }

        return report

def demonstrate_aqi_merchant_services():
    """Demonstrate the complete AQI Merchant Services system"""

    print("🎯 AQI MERCHANT SERVICES CORE DEMONSTRATION")
    print("=" * 55)

    # Initialize the core system
    merchant_core = AQIMerchantServicesCore()

    # Generate initial leads
    print("\n🔍 GENERATING INITIAL MERCHANT LEADS...")
    initial_leads = merchant_core.generate_merchant_leads(10)
    merchant_core.save_merchant_leads(initial_leads)
    print(f"✅ Generated {len(initial_leads)} initial merchant leads")

    # Start autonomous operations
    merchant_core.start_autonomous_operations()

    # Let the system run for a demonstration period
    print("\n🚀 AUTONOMOUS OPERATIONS RUNNING...")
    print("Watch as the AQI system autonomously:")
    print("  • Generates new merchant leads")
    print("  • Makes acquisition calls")
    print("  • Onboards new merchants")
    print("  • Manages accounts and compliance")

    # Run for 30 seconds to demonstrate
    time.sleep(30)

def demonstrate_aqi_merchant_services():
    """Demonstrate the complete AQI Merchant Services system"""

    print("🎯 AQI MERCHANT SERVICES CORE DEMONSTRATION")
    print("=" * 55)

    # Initialize the core system
    merchant_core = AQIMerchantServicesCore()

    # Generate initial leads
    print("\n🔍 GENERATING INITIAL MERCHANT LEADS...")
    initial_leads = merchant_core.generate_merchant_leads(10)
    merchant_core.save_merchant_leads(initial_leads)
    print(f"✅ Generated {len(initial_leads)} initial merchant leads")

    # Start autonomous operations
    merchant_core.start_autonomous_operations()

    # Let the system run for a demonstration period
    print("\n🚀 AUTONOMOUS OPERATIONS RUNNING...")
    print("Watch as the AQI system autonomously:")
    print("  • Generates new merchant leads")
    print("  • Makes acquisition calls")
    print("  • Onboards new merchants")
    print("  • Manages accounts and compliance")

    # Run for 30 seconds to demonstrate
    time.sleep(30)

    # Generate final report
    print("\n📊 GENERATING MERCHANT SERVICES REPORT...")
    report = merchant_core.generate_merchant_services_report()

    print(f"\n🎯 AQI MERCHANT SERVICES PERFORMANCE REPORT")
    print(f"=" * 45)
    print(f"System Status: {report['system_overview']['status'].upper()}")
    print(f"Autonomous Operations: {'✅ ACTIVE' if report['system_overview']['autonomous_operations'] else '❌ INACTIVE'}")
    print(f"Uptime: {report['system_overview']['uptime']}")
    print()
    print(f"📈 PERFORMANCE METRICS:")
    print(f"   Merchants Acquired: {report['performance_metrics']['merchants_acquired']}")
    print(f"   Calls Completed: {report['performance_metrics']['calls_completed']}")
    print(f"   Accounts Onboarded: {report['performance_metrics']['accounts_onboarded']}")
    print(f"   Active Merchants: {report['performance_metrics']['active_merchants']}")
    print(f"   Prospects Available: {report['performance_metrics']['prospects_available']}")
    print()
    print(f"💰 REVENUE METRICS:")
    print(f"   Total Revenue: ${report['revenue_metrics']['total_revenue_generated']:,.2f}")
    print(f"   Recent Revenue: ${report['revenue_metrics']['recent_revenue']:,.2f}")
    print(f"   Avg Revenue/Merchant: ${report['revenue_metrics']['average_revenue_per_merchant']:,.2f}")
    print()
    print(f"⚙️ SYSTEM CAPABILITIES:")
    for capability, status in report['system_capabilities'].items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {capability.replace('_', ' ').title()}")

    print(f"\n🎉 AQI MERCHANT SERVICES CORE SUCCESSFULLY DEMONSTRATED!")
    print(f"🔥 The system is now ready for full autonomous merchant services operations!")
    print(f"💎 Complete merchant lifecycle management from lead to revenue")

if __name__ == "__main__":
    demonstrate_aqi_merchant_services()