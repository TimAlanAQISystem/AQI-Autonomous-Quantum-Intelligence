#!/usr/bin/env python3
"""
AQI LEAD IMPORT SYSTEM
======================
Import merchant leads from Excel files and integrate with AQI calling system
"""

import os
import pandas as pd
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import sys

class AQILeadImporter:
    """
    Import system for merchant leads from Excel files
    """

    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Database and file paths
        self.db_path = self.data_dir / "aqi_merchant_services.db"
        self.prospects_file = self.data_dir / "business_prospects.json"
        self.leads_file = self.data_dir / "leads.json"
        self.processed_batches_file = self.data_dir / "processed_lead_batches.json"

        # Load existing data
        self.existing_prospects = self._load_existing_prospects()
        self.existing_leads = self._load_existing_leads()
        self.processed_batches = self._load_processed_batches()

        print("🔍 AQI LEAD IMPORTER INITIALIZED")
        print(f"📍 Data Directory: {self.data_dir}")
        print(f"📍 Existing Prospects: {len(self.existing_prospects)}")
        print(f"📍 Existing Leads: {len(self.existing_leads)}")

    def _load_existing_prospects(self) -> List[Dict[str, Any]]:
        """Load existing business prospects"""
        if self.prospects_file.exists():
            try:
                with open(self.prospects_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _load_existing_leads(self) -> List[Dict[str, Any]]:
        """Load existing leads"""
        if self.leads_file.exists():
            try:
                with open(self.leads_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _load_processed_batches(self) -> List[str]:
        """Load list of processed batch files"""
        if self.processed_batches_file.exists():
            try:
                with open(self.processed_batches_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []

    def import_batch_files(self, batch_files: List[str], force_reimport: bool = False) -> Dict[str, Any]:
        """Import multiple batch files"""

        results = []
        total_stats = {
            "total_files": len(batch_files),
            "successful_imports": 0,
            "failed_imports": 0,
            "total_prospects": 0,
            "total_leads": 0,
            "total_duplicates": 0
        }

        print(f"\n🚀 Starting import of {len(batch_files)} batch files...")

        for batch_file in batch_files:
            if os.path.exists(batch_file):
                batch_name = Path(batch_file).stem.replace('_aqi_batch_20260107_', '')
                result = self.import_excel_batch(batch_file, batch_name, force_reimport)
                results.append(result)

                if result.get("status") == "success":
                    total_stats["successful_imports"] += 1
                    total_stats["total_prospects"] += result.get("new_prospects", 0)
                    total_stats["total_leads"] += result.get("new_leads", 0)
                    total_stats["total_duplicates"] += result.get("duplicates", 0)
                else:
                    total_stats["failed_imports"] += 1
            else:
                print(f"❌ File not found: {batch_file}")
                total_stats["failed_imports"] += 1

        print("\n📊 Import Summary:")
        print(f"   Files Processed: {total_stats['successful_imports']}/{total_stats['total_files']}")
        print(f"   New Prospects: {total_stats['total_prospects']}")
        print(f"   New Leads: {total_stats['total_leads']}")
        print(f"   Duplicates Skipped: {total_stats['total_duplicates']}")

        return {
            "overall_status": "success" if total_stats["successful_imports"] > 0 else "failed",
            "stats": total_stats,
            "results": results
        }

    def import_excel_batch(self, excel_path: str, batch_name: str = None, force_reimport: bool = False) -> Dict[str, Any]:
        """Import leads from Excel file"""

        if batch_name is None:
            batch_name = Path(excel_path).stem

        # Check if already processed (unless force reimport)
        if not force_reimport and batch_name in self.processed_batches:
            print(f"⚠️ Batch {batch_name} already processed, skipping")
            return {"status": "skipped", "batch": batch_name, "reason": "already_processed"}

        print(f"📥 Importing batch: {batch_name}")
        print(f"   File: {excel_path}")
        print(f"   Current working directory: {os.getcwd()}")
        print(f"   Data directory: {self.data_dir}")
        print(f"   Prospects file: {self.prospects_file}")
        print(f"   File exists: {os.path.exists(excel_path)}")

        try:
            # Read Excel file
            df = pd.read_excel(excel_path)
            # Normalize columns to lowercase to ensure case-insensitive matching
            df.columns = df.columns.astype(str).str.lower()
            
            print(f"   Found {len(df)} rows in Excel file")
            print(f"   Columns: {list(df.columns)}")
            if len(df) > 0:
                print(f"   First row sample: {df.iloc[0].to_dict()}")

            # Process leads
            new_prospects = []
            new_leads = []
            duplicates = 0

            for _, row in df.iterrows():
                prospect, lead = self._process_lead_row(row, batch_name)

                # Check for duplicates
                if self._is_duplicate_prospect(prospect):
                    duplicates += 1
                    continue

                new_prospects.append(prospect)
                new_leads.append(lead)

            # Save to files
            self._save_new_prospects(new_prospects)
            self._save_new_leads(new_leads)
            self._mark_batch_processed(batch_name)

            result = {
                "status": "success",
                "batch": batch_name,
                "total_rows": len(df),
                "new_prospects": len(new_prospects),
                "new_leads": len(new_leads),
                "duplicates": duplicates
            }

            print(f"✅ Batch {batch_name} imported successfully")
            print(f"   New prospects: {len(new_prospects)}")
            print(f"   New leads: {len(new_leads)}")
            print(f"   Duplicates skipped: {duplicates}")

            return result

        except Exception as e:
            error_result = {
                "status": "error",
                "batch": batch_name,
                "error": str(e)
            }
            print(f"❌ Error importing batch {batch_name}: {e}")
            return error_result

    def _process_lead_row(self, row, batch_name: str) -> tuple:
        """Process a single lead row from Excel"""

        # Extract data with fallbacks
        name = str(row.get('contact_name', row.get('name', row.get('owner', 'Unknown')))).strip()
        company = str(row.get('business_name', row.get('company', row.get('business', 'Unknown Business')))).strip()
        phone = str(row.get('phone', row.get('phone_number', row.get('mobile', '')))).strip()
        email = str(row.get('email', row.get('email_address', ''))).strip()
        industry = str(row.get('industry', row.get('business_type', row.get('category', 'Business')))).strip()
        volume = float(row.get('monthly_volume', row.get('volume', row.get('sales', 0))))
        current_processor = str(row.get('current_processor', row.get('processor', 'Unknown'))).strip()
        pain_points = str(row.get('pain_points', row.get('issues', row.get('problems', '')))).strip()

        # Create prospect entry
        prospect = {
            "name": name,
            "company": company,
            "phone": phone,
            "industry": industry,
            "last_called": None,
            "call_count": 0,
            "priority": self._determine_priority(volume, industry),
            "batch_source": batch_name,
            "imported_date": datetime.now().isoformat()
        }

        # Create lead entry
        lead = {
            "id": f"lead_{len(self.existing_leads) + len(self.existing_prospects) + 1:04d}",
            "name": name,
            "phone": phone,
            "email": email,
            "company": company,
            "status": "new",
            "created_at": datetime.now().isoformat(),
            "monthly_volume": volume,
            "current_processor": current_processor,
            "pain_points": pain_points,
            "lead_source": batch_name,
            "industry": industry,
            "priority": self._determine_priority(volume, industry)
        }

        return prospect, lead

    def _determine_priority(self, volume: float, industry: str) -> str:
        """Determine lead priority based on volume and industry"""
        if volume >= 100000:
            return "critical"
        elif volume >= 50000:
            return "high"
        elif volume >= 25000:
            return "medium"
        elif industry.lower() in ['restaurant', 'retail', 'healthcare']:
            return "medium"
        else:
            return "low"

    def _is_duplicate_prospect(self, prospect: Dict[str, Any]) -> bool:
        """Check if prospect already exists"""
        for existing in self.existing_prospects:
            if (existing.get('phone') == prospect.get('phone') and
                existing.get('company') == prospect.get('company')):
                return True
        return False

    def _save_new_prospects(self, new_prospects: List[Dict[str, Any]]):
        """Save new prospects to file"""
        all_prospects = self.existing_prospects + new_prospects

        with open(self.prospects_file, 'w') as f:
            json.dump(all_prospects, f, indent=2)

        print(f"💾 Saved {len(new_prospects)} new prospects to {self.prospects_file}")

    def _save_new_leads(self, new_leads: List[Dict[str, Any]]):
        """Save new leads to file"""
        all_leads = self.existing_leads + new_leads

        with open(self.leads_file, 'w') as f:
            json.dump(all_leads, f, indent=2)

        print(f"💾 Saved {len(new_leads)} new leads to {self.leads_file}")

    def _mark_batch_processed(self, batch_name: str):
        """Mark batch as processed"""
        self.processed_batches.append(batch_name)

        with open(self.processed_batches_file, 'w') as f:
            json.dump(self.processed_batches, f, indent=2)

    def import_leads_from_excel(self) -> List[Dict[str, Any]]:
        """Import leads from all configured Excel and CSV files"""

        all_leads = []
        
        # Define default paths if not present
        if not hasattr(self, 'excel_paths'):
             self.excel_paths = []
        if not hasattr(self, 'rse_csv_paths'):
             self.rse_csv_paths = []

        # 1. Import from Legacy Excel Files
        for excel_path in self.excel_paths:
            if os.path.exists(excel_path):
                print(f"📖 Reading Excel file: {os.path.basename(excel_path)}")
                try:
                    leads = self._read_excel_file(excel_path)
                    all_leads.extend(leads)
                    print(f"✅ Imported {len(leads)} leads from {os.path.basename(excel_path)}")
                except Exception as e:
                    print(f"❌ Error reading {os.path.basename(excel_path)}: {e}")
            # else:
            #     print(f"⚠️ Excel file not found: {os.path.basename(excel_path)}")

        # 2. Import from RSE Agent CSV Files (Cloud Connection)
        for csv_path in self.rse_csv_paths:
            if os.path.exists(csv_path):
                print(f"☁️  Reading RSE Cloud Export: {os.path.basename(csv_path)}")
                try:
                    leads = self._read_rse_csv_file(csv_path)
                    all_leads.extend(leads)
                    print(f"✅ Imported {len(leads)} high-quality leads from {os.path.basename(csv_path)}")
                except Exception as e:
                    print(f"❌ Error reading RSE export {os.path.basename(csv_path)}: {e}")
            else:
                print(f"⚠️ RSE Export not found (waiting for Mac sync): {os.path.basename(csv_path)}")

        print(f"🎯 Total leads imported: {len(all_leads)}")
        return all_leads

    def _read_rse_csv_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Read and parse RSE Agent CSV export"""
        
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f"Error reading CSV: {e}")
            return []

        leads = []
        for _, row in df.iterrows():
            lead = self._parse_rse_row(row)
            if lead:
                leads.append(lead)
        
        return leads

    def _parse_rse_row(self, row) -> Dict[str, Any]:
        """Parse RSE CSV row into lead format"""
        try:
            # Map RSE columns to Agent X format
            # RSE Headers: 'Business Name', 'Surplus Score', 'Ethical Flag', 'Owner Name', 'Phone Number', 'Email', 'Business Type'
            
            business_name = str(row.get('Business Name', row.get('Company', ''))).strip()
            if not business_name or business_name.lower() in ['nan', 'none', '']:
                return None

            contact_name = str(row.get('Owner Name', 'Owner')).strip()
            if contact_name.lower() in ['nan', 'none', 'n/a', '']:
                contact_name = "Owner"

            phone = str(row.get('Phone Number', row.get('Phone', ''))).strip()
            if phone.lower() in ['nan', 'none', 'n/a', '']:
                return None # Skip if no phone
            
            phone = self._clean_phone_number(phone)
            if not phone:
                return None

            email = str(row.get('Email', '')).strip()
            if email.lower() in ['nan', 'none', 'n/a', '']:
                email = f"contact@{business_name.lower().replace(' ', '').replace('&', 'and')}.com"

            industry = str(row.get('Business Type', 'Retail')).strip()
            if industry.lower() in ['nan', 'none', 'n/a', '']:
                industry = 'Retail'

            # Parse Surplus Score (e.g., "85.5%" or 85.5)
            raw_score = str(row.get('Surplus Score', '70')).replace('%', '').strip()
            try:
                lead_score = int(float(raw_score))
            except:
                lead_score = 70

            # Generate ID
            merchant_id = f"RSE-{industry.upper()}-{hash(business_name) % 10000:04d}"

            # Estimate volume
            import random
            monthly_volume = random.randint(25000, 150000) # RSE leads are higher quality

            lead = {
                'merchant_id': merchant_id,
                'business_name': business_name,
                'contact_name': contact_name,
                'phone': phone,
                'email': email,
                'business_type': industry,
                'industry': industry,
                'monthly_volume': monthly_volume,
                'current_processor': 'Unknown',
                'current_rate': 2.9,
                'pain_points': 'High Fees',
                'lead_source': 'rse_cloud_sync',
                'lead_score': lead_score,
                'status': 'prospect'
            }
            return lead

        except Exception as e:
            # print(f"Error parsing RSE row: {e}")
            return None


    def _read_excel_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Read and parse Excel file"""

        # Read Excel file
        df = pd.read_excel(file_path)

        leads = []
        for _, row in df.iterrows():
            lead = self._parse_excel_row(row)
            if lead:
                leads.append(lead)

        return leads

    def _parse_excel_row(self, row) -> Dict[str, Any]:
        """Parse Excel row into lead format"""

        try:
            # Extract business information - try multiple column name variations
            business_name = str(row.get('Company Name', row.get('Company', row.get('Business Name', '')))).strip()
            if not business_name or business_name.lower() in ['nan', 'none', '']:
                return None

            # Extract contact information
            first_name = str(row.get('First Name', '')).strip()
            last_name = str(row.get('Last Name', '')).strip()
            contact_name = f"{first_name} {last_name}".strip()
            if not contact_name or contact_name.lower() in ['nan', 'none', '']:
                contact_name = "Owner"

            # Extract phone number - try multiple phone columns
            phone = str(row.get('Contact Phone 1', row.get('Contact Mobile Phone', row.get('Phone', '')))).strip()
            if phone.lower() in ['nan', 'none', '']:
                return None

            # Clean phone number
            phone = self._clean_phone_number(phone)
            if not phone:
                return None

            # Extract email
            email = str(row.get('Email 1', row.get('Email', ''))).strip()
            if email.lower() in ['nan', 'none', '']:
                # Generate email from business name
                email = f"contact@{business_name.lower().replace(' ', '').replace('&', 'and')}.com"

            # Extract business type/industry - infer from company name or use default
            industry = 'retail'  # Default for retail list

            # Estimate monthly volume based on industry
            import random
            min_vol, max_vol = (20000, 100000)  # Retail range
            monthly_volume = random.randint(min_vol, max_vol)

            # Generate merchant ID
            merchant_id = f"EXCEL-{industry.upper()}-{hash(business_name) % 10000:04d}"

            lead = {
                'merchant_id': merchant_id,
                'business_name': business_name,
                'contact_name': contact_name,
                'phone': phone,
                'email': email,
                'business_type': industry,
                'industry': industry,
                'monthly_volume': monthly_volume,
                'current_processor': random.choice(['Stripe', 'Square', 'First Data', 'TSYS', 'Authorize.net']),
                'current_rate': round(random.uniform(2.5, 3.2), 2),
                'pain_points': random.choice([
                    'High processing rates',
                    'Too many fees',
                    'Poor customer service',
                    'Slow settlement',
                    'Complex setup'
                ]),
                'lead_source': 'excel_import',
                'lead_score': random.randint(70, 95),
                'status': 'prospect'
            }

            return lead

        except Exception as e:
            print(f"❌ Error parsing Excel row: {e}")
            return None

    def _clean_phone_number(self, phone: str) -> str:
        """Clean and format phone number"""

        # Remove all non-digit characters
        digits = ''.join(filter(str.isdigit, phone))

        # Handle different phone number formats
        if len(digits) == 10:
            # Add +1 for US numbers
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            # Already has country code
            return f"+{digits}"
        elif len(digits) == 7:
            # Local number, assume area code 555
            return f"+1555{digits}"
        else:
            # Invalid phone number
            return None

    def save_leads_to_database(self, leads: List[Dict[str, Any]]):
        """Save imported leads to database"""

        if not leads:
            print("⚠️ No leads to save")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        saved_count = 0
        duplicate_count = 0

        for lead in leads:
            try:
                # Check if merchant already exists
                cursor.execute("SELECT id FROM merchants WHERE merchant_id = ?", (lead['merchant_id'],))
                if cursor.fetchone():
                    duplicate_count += 1
                    continue

                # Insert new lead
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

                saved_count += 1

            except Exception as e:
                print(f"❌ Error saving lead {lead.get('merchant_id', 'unknown')}: {e}")

        conn.commit()
        conn.close()

        print(f"💾 Saved {saved_count} new leads to database")
        if duplicate_count > 0:
            print(f"⏭️ Skipped {duplicate_count} duplicate leads")

    def get_import_stats(self) -> Dict[str, Any]:
        """Get statistics about imported leads"""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count leads by source
        cursor.execute("""
            SELECT lead_source, COUNT(*) as count
            FROM merchants
            WHERE lead_source = 'excel_import'
            GROUP BY lead_source
        """)

        excel_leads = cursor.fetchone()
        excel_count = excel_leads[1] if excel_leads else 0

        # Count by industry
        cursor.execute("""
            SELECT industry, COUNT(*) as count
            FROM merchants
            WHERE lead_source = 'excel_import'
            GROUP BY industry
            ORDER BY count DESC
        """)

        industry_stats = cursor.fetchall()

        conn.close()

        return {
            'excel_imported_leads': excel_count,
            'industry_breakdown': dict(industry_stats),
            'import_timestamp': datetime.now().isoformat()
        }

def import_excel_leads():
    """Main function to import leads from Excel files"""

    print("🚀 AQI EXCEL LEAD IMPORT SYSTEM")
    print("=" * 40)

    importer = AQILeadImporter()
    
    # Auto-add files from leads_inbox
    import glob
    inbox_files = glob.glob("leads_inbox/*.xlsx")
    if hasattr(importer, 'excel_paths'):
        importer.excel_paths.extend(inbox_files)
    else:
        importer.excel_paths = inbox_files
        
    if inbox_files:
        print(f"📥 Found {len(inbox_files)} files in leads_inbox: {inbox_files}")

    # Import leads from Excel files
    print("\n📊 IMPORTING LEADS FROM EXCEL FILES...")
    leads = importer.import_leads_from_excel()

    if not leads:
        print("❌ No leads found in Excel files")
        return

    # Save to database
    print("\n💾 SAVING LEADS TO DATABASE...")
    importer.save_leads_to_database(leads)

    # Show statistics
    print("\n📈 IMPORT STATISTICS:")
    stats = importer.get_import_stats()

    print(f"Excel Leads Imported: {stats['excel_imported_leads']}")
    print("Industry Breakdown:")
    for industry, count in stats['industry_breakdown'].items():
        print(f"  • {industry.title()}: {count} leads")

    print(f"\n✅ EXCEL LEAD IMPORT COMPLETED SUCCESSFULLY!")
    print(f"🎯 {stats['excel_imported_leads']} merchant leads now available for calling campaigns")

if __name__ == "__main__":
    import_excel_leads()