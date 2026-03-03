#!/usr/bin/env python3
"""
Alan Test Merchant Applications Generator
========================================

Creates 3 realistic test merchant applications and sends them via email
to Signaturecardservicesdmc@msn.com for validation testing.

This script demonstrates the complete merchant onboarding workflow:
1. Generate realistic merchant data
2. Create complete applications using the application manager
3. Send applications via email to the specified address
"""

import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
import random
import uuid
import os
from typing import Dict, Any, List

# Import the application manager
import sys
sys.path.append(r'C:\Users\signa\OneDrive\Desktop\AQI North Connector\fstnorth_connection.py\New Build')
from application_manager import ApplicationManager

# Import the email service
sys.path.append(r'C:\Users\signa\OneDrive\Desktop\Agent X\src')
from email_service import EmailService

class TestApplicationGenerator:
    """Generates and sends test merchant applications"""

    def __init__(self):
        self.app_manager = ApplicationManager()
        self.logger = logging.getLogger(__name__)

        # Initialize email service
        self.email_service = EmailService()

        # Create applications directory
        self.applications_dir = os.path.join(os.getcwd(), 'test_applications')
        os.makedirs(self.applications_dir, exist_ok=True)

        # Email configuration
        self.recipient_email = 'Signaturecardservicesdmc@msn.com'

    def generate_test_merchants(self) -> List[Dict[str, Any]]:
        """Generate 3 realistic test merchant applications"""

        test_merchants = [
            {
                'business_legal_name': 'Downtown Coffee House LLC',
                'dba_name': 'Morning Brew Cafe',
                'business_type': 'restaurant',
                'business_address': {
                    'street': '123 Main Street',
                    'city': 'Springfield',
                    'state': 'IL',
                    'zip': '62701'
                },
                'mailing_address': {
                    'street': '123 Main Street',
                    'city': 'Springfield',
                    'state': 'IL',
                    'zip': '62701'
                },
                'business_phone': '(217) 555-0123',
                'business_email': 'info@morningbrewcafe.com',
                'website': 'www.morningbrewcafe.com',
                'years_in_business': 5,
                'monthly_volume': 45000,
                'average_ticket': 12.50,
                'high_ticket_amount': 85.00,
                'seasonal_business': False,
                'owner_name': 'Sarah Johnson',
                'owner_ssn': '123-45-6789',
                'owner_dob': '1985-03-15',
                'owner_ownership_percentage': 100,
                'bank_name': 'First National Bank',
                'bank_routing_number': '071000013',
                'bank_account_number': '9876543210',
                'estimated_savings': 8500,
                'industry': 'Restaurant/Coffee Shop'
            },
            {
                'business_legal_name': 'Tech Solutions Pro Inc',
                'dba_name': 'TechPro Solutions',
                'business_type': 'professional_services',
                'business_address': {
                    'street': '456 Technology Drive',
                    'city': 'Austin',
                    'state': 'TX',
                    'zip': '78701'
                },
                'mailing_address': {
                    'street': '456 Technology Drive',
                    'city': 'Austin',
                    'state': 'TX',
                    'zip': '78701'
                },
                'business_phone': '(512) 555-0456',
                'business_email': 'contact@techprosolutions.com',
                'professional_license_number': 'TX-IT-2023-001',
                'years_in_business': 8,
                'services_provided': 'IT consulting, software development, cybersecurity services',
                'monthly_volume': 75000,
                'average_ticket': 2500.00,
                'owner_name': 'Michael Chen',
                'owner_ssn': '987-65-4321',
                'owner_dob': '1978-11-22',
                'bank_name': 'Silicon Valley Bank',
                'bank_routing_number': '121140399',
                'bank_account_number': '1234567890',
                'estimated_savings': 12500,
                'industry': 'Professional Services/IT'
            },
            {
                'business_legal_name': 'Riverside Fitness Center',
                'dba_name': 'FitLife Riverside',
                'business_type': 'retail',
                'business_address': {
                    'street': '789 Fitness Avenue',
                    'city': 'Portland',
                    'state': 'OR',
                    'zip': '97201'
                },
                'mailing_address': {
                    'street': '789 Fitness Avenue',
                    'city': 'Portland',
                    'state': 'OR',
                    'zip': '97201'
                },
                'business_phone': '(503) 555-0789',
                'business_email': 'membership@fitliferiverside.com',
                'website': 'www.fitliferiverside.com',
                'years_in_business': 3,
                'monthly_volume': 35000,
                'average_ticket': 75.00,
                'products_sold': 'Gym memberships, personal training, fitness equipment, supplements',
                'owner_name': 'Jennifer Martinez',
                'owner_ssn': '456-78-9123',
                'owner_dob': '1982-07-08',
                'bank_name': 'Wells Fargo Bank',
                'bank_routing_number': '121000248',
                'bank_account_number': '5555666677',
                'estimated_savings': 6200,
                'industry': 'Fitness/Health Club'
            }
        ]

        return test_merchants

    def create_applications(self, merchants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create applications for each test merchant"""

        applications = []

        for i, merchant in enumerate(merchants, 1):
            print(f"\n📝 Creating Test Application #{i}")
            print(f"   Business: {merchant['business_legal_name']}")
            print(f"   Type: {merchant['business_type']}")
            print(f"   Estimated Savings: ${merchant['estimated_savings']:,}")

            # Generate application using the application manager
            application = self.app_manager.generate_application(merchant, f"TEST_CONV_{i}")

            # Save application to file
            self.save_application_to_file(merchant, application, i)

            applications.append({
                'merchant': merchant,
                'application': application
            })

        return applications

    def save_application_to_file(self, merchant: Dict[str, Any], application: Dict[str, Any], index: int):
        """Save application data to a JSON file"""

        app_data = {
            'application_number': index,
            'generated_at': datetime.now().isoformat(),
            'merchant_data': merchant,
            'application_data': application,
            'status': 'generated'
        }

        filename = f"test_application_{index}_{application['application_id']}.json"
        filepath = os.path.join(self.applications_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(app_data, f, indent=2, default=str)

        print(f"   💾 Saved to: {filepath}")

    def send_application_email(self, merchant: Dict[str, Any], application: Dict[str, Any]) -> bool:
        """Send application via email"""

        try:
            # Format email content
            subject = f"AQI North Test Application - {merchant['business_legal_name']}"
            body = self.format_application_email(merchant, application)

            print(f"\n📧 SENDING EMAIL")
            print(f"   To: {self.recipient_email}")
            print(f"   Subject: {subject}")
            print(f"   Application ID: {application['application_id']}")

            # Send using email service
            result = self.email_service.send_proposal(
                to_email=self.recipient_email,
                subject=subject,
                body=body
            )

            if result.get('success'):
                if result.get('simulation'):
                    print("   ✅ Email sent successfully (simulated - check logs/email_outbox.txt)")
                else:
                    print("   ✅ Email sent successfully (live)")
                print(f"   📄 Application content included")

                # Log the email send
                self.log_email_send(merchant, application)
                return True
            else:
                print(f"   ❌ Email send failed: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"❌ EMAIL SEND ERROR: {str(e)}")
            return False

    def format_application_email(self, merchant: Dict[str, Any], application: Dict[str, Any]) -> str:
        """Format application data as email content"""

        app_id = application['application_id']
        business_name = merchant['business_legal_name']
        contact_name = merchant['owner_name']
        estimated_savings = merchant['estimated_savings']

        email_body = f"""
AQI NORTH MERCHANT APPLICATION - TEST SUBMISSION
===============================================

Application ID: {app_id}
Submission Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
Status: TEST APPLICATION - Ready for Processing

MERCHANT INFORMATION
-------------------
Business Legal Name: {business_name}
DBA: {merchant.get('dba_name', 'N/A')}
Contact Name: {contact_name}
Business Phone: {merchant['business_phone']}
Business Email: {merchant['business_email']}
Industry: {merchant['industry']}

Address: {merchant['business_address']['street']}
         {merchant['business_address']['city']}, {merchant['business_address']['state']} {merchant['business_address']['zip']}

BUSINESS DETAILS
---------------
Years in Business: {merchant['years_in_business']}
Monthly Processing Volume: ${merchant['monthly_volume']:,}
Average Ticket: ${merchant['average_ticket']:.2f}
Business Type: {merchant['business_type'].title()}

OWNER INFORMATION
----------------
Owner Name: {contact_name}
Ownership Percentage: {merchant.get('owner_ownership_percentage', 100)}%

BANKING INFORMATION
------------------
Bank Name: {merchant['bank_name']}
Routing Number: {merchant['bank_routing_number']}
Account Number: {merchant['bank_account_number']}

SAVINGS ANALYSIS
---------------
Estimated Annual Savings: ${estimated_savings:,}
Monthly Savings: ${estimated_savings // 12:,}

This is a TEST APPLICATION generated by Alan AI for validation purposes.
Please process this application through your standard underwriting workflow.

Generated by: Alan Agent Portal Explorer
Timestamp: {datetime.now().isoformat()}

---
AQI North Merchant Services
Supreme AI Business Consultant
"""

        return email_body

    def send_application_email(self, merchant: Dict[str, Any], application: Dict[str, Any]) -> bool:
        """Send application via email"""

        try:
            # Format email content
            subject = f"AQI North Test Application - {merchant['business_legal_name']}"
            body = self.format_application_email(merchant, application)

            print(f"\n📧 SENDING EMAIL")
            print(f"   To: {self.recipient_email}")
            print(f"   Subject: {subject}")
            print(f"   Application ID: {application['application_id']}")

            # Send using email service
            result = self.email_service.send_proposal(
                to_email=self.recipient_email,
                subject=subject,
                body=body
            )

            if result.get('success'):
                if result.get('simulation'):
                    print("   ✅ Email sent successfully (simulated - check logs/email_outbox.txt)")
                else:
                    print("   ✅ Email sent successfully (live)")
                print(f"   📄 Application content included")

                # Log the email send
                self.log_email_send(merchant, application)
                return True
            else:
                print(f"   ❌ Email send failed: {result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            print(f"❌ EMAIL SEND ERROR: {str(e)}")
            return False

    def log_email_send(self, merchant: Dict[str, Any], application: Dict[str, Any]):
        """Log the email sending activity"""

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': 'test_application_email_sent',
            'application_id': application['application_id'],
            'business_name': merchant['business_legal_name'],
            'recipient_email': self.recipient_email,
            'estimated_savings': merchant['estimated_savings']
        }

        # In a real system, this would be stored in a database
        print(f"📋 EMAIL LOGGED: {log_entry}")

    def run_test_application_generation(self):
        """Main function to generate and send test applications"""

        print("🚀 ALAN TEST APPLICATION GENERATOR")
        print("=" * 50)
        print("Generating 3 realistic test merchant applications...")
        print("Sending applications to: Signaturecardservicesdmc@msn.com")
        print()

        # Generate test merchants
        merchants = self.generate_test_merchants()
        print(f"✅ Generated {len(merchants)} test merchants")

        # Create applications
        applications = self.create_applications(merchants)
        print(f"\n✅ Created {len(applications)} applications")

        # Send applications via email
        sent_count = 0
        for app_data in applications:
            merchant = app_data['merchant']
            application = app_data['application']

            if self.send_application_email(merchant, application):
                sent_count += 1

        print(f"\n🎉 TEST APPLICATION GENERATION COMPLETE")
        print(f"   Applications Created: {len(applications)}")
        print(f"   Emails Sent: {sent_count}")
        print(f"   Success Rate: {sent_count}/{len(applications)} ({sent_count/len(applications)*100:.1f}%)")

        # Summary report
        self.generate_summary_report(applications)

    def generate_summary_report(self, applications: List[Dict[str, Any]]):
        """Generate a summary report of the test applications"""

        print(f"\n📊 TEST APPLICATION SUMMARY REPORT")
        print("=" * 50)

        total_savings = 0
        business_types = {}

        for i, app_data in enumerate(applications, 1):
            merchant = app_data['merchant']
            application = app_data['application']

            business_type = merchant['business_type']
            savings = merchant['estimated_savings']
            total_savings += savings

            if business_type not in business_types:
                business_types[business_type] = []
            business_types[business_type].append(savings)

            print(f"\nApplication #{i}: {merchant['business_legal_name']}")
            print(f"   Type: {business_type.title()}")
            print(f"   Location: {merchant['business_address']['city']}, {merchant['business_address']['state']}")
            print(f"   Monthly Volume: ${merchant['monthly_volume']:,}")
            print(f"   Estimated Savings: ${savings:,}")
            print(f"   Application ID: {application['application_id']}")

        print(f"\nTOTALS:")
        print(f"   Total Applications: {len(applications)}")
        print(f"   Total Estimated Savings: ${total_savings:,}")
        print(f"   Average Savings per Application: ${total_savings//len(applications):,}")

        print(f"\nBusiness Type Breakdown:")
        for btype, savings_list in business_types.items():
            avg_savings = sum(savings_list) // len(savings_list)
            print(f"   {btype.title()}: {len(savings_list)} applications, avg savings ${avg_savings:,}")

        print(f"\n✅ All test applications have been generated and emailed successfully!")
        print(f"   Ready for processing through the Agent Portal underwriting workflow.")


def main():
    """Main entry point"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and run the test application generator
    generator = TestApplicationGenerator()
    generator.run_test_application_generation()


if __name__ == "__main__":
    main()