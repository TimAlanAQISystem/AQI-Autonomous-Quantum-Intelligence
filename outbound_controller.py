"""
Outbound Call Controller for Agent X Call Center
Handles outbound campaign management and Twilio call initiation.
"""

import os
import time
import logging
from typing import List, Dict, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from merchant_queue import merchant_queue, CallOutcome

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class OutboundController:
    def __init__(self):
        # Twilio credentials from environment
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.from_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.public_tunnel_url = os.getenv('PUBLIC_BASE_URL', os.getenv('PUBLIC_TUNNEL_URL'))
        
        if not all([self.account_sid, self.auth_token, self.from_number]):
            raise ValueError("Missing required Twilio environment variables")
        
        # PUBLIC_TUNNEL_URL can be None for local testing
        if not self.public_tunnel_url:
            logging.warning("PUBLIC_TUNNEL_URL not set - using fallback URL for testing")
            self.public_tunnel_url = "http://127.0.0.1:8777"  # Fallback to local control service
        
        self.client = Client(self.account_sid, self.auth_token)
        
        # Campaign settings
        self.call_delay = 5  # seconds between calls
        self.max_calls_per_campaign = 10  # limit for testing
        
    def load_call_list(self) -> List[str]:
        """
        Load list of target phone numbers for outbound calls.
        Now uses the merchant queue instead of hardcoded list.
        """
        merchants = merchant_queue.get_all_merchants()
        eligible_numbers = [m.phone_number for m in merchants if m.can_attempt_now()]
        return eligible_numbers
    
    def place_outbound_call(self, to_number: str) -> Optional[str]:
        """
        Place an outbound call using Twilio.
        
        Args:
            to_number: The phone number to call
            
        Returns:
            Call SID if successful, None if failed
        """
        try:
            logging.info(f"Placing outbound call to {to_number}")
            
            call = self.client.calls.create(
                to=to_number,
                from_=os.getenv('TWILIO_CALLER_ID', self.from_number),
                url=f"{self.public_tunnel_url}/twilio/voice",
                status_callback=f"{self.public_tunnel_url}/twilio/events",
                status_callback_method="POST",
                status_callback_event="initiated ringing answered completed",
                machine_detection="Enable"  # Detect voicemail
            )
            
            logging.info(f"Outbound call initiated: SID={call.sid}")
            return call.sid
            
        except TwilioException as e:
            logging.error(f"Twilio error placing call to {to_number}: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error placing call to {to_number}: {e}")
            return None
    
    def run_campaign(self, call_list: Optional[List[str]] = None) -> Dict[str, any]:
        """
        Run an outbound calling campaign.

        Args:
            call_list: Optional list of numbers to call. If None, loads from merchant queue.

        Returns:
            Campaign results summary
        """
        results = {
            "total_attempted": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "call_sids": [],
            "errors": []
        }

        logging.info(f"Starting outbound campaign")

        # Process merchants from queue
        for i in range(self.max_calls_per_campaign):
            merchant = merchant_queue.get_next_merchant()
            if not merchant:
                logging.info("No more eligible merchants to call")
                break

            logging.info(f"Processing call {i+1} to {merchant.name or merchant.phone_number}")

            results["total_attempted"] += 1
            call_sid = self.place_outbound_call(merchant.phone_number)

            if call_sid:
                results["successful_calls"] += 1
                results["call_sids"].append(call_sid)
                # Record attempt in merchant queue
                merchant_queue.update_merchant_outcome(merchant.id, CallOutcome.PENDING, f"Call initiated: {call_sid}")
            else:
                results["failed_calls"] += 1
                results["errors"].append(f"Failed to call {merchant.phone_number}")
                # Record failed attempt
                merchant_queue.update_merchant_outcome(merchant.id, CallOutcome.FAILED, "Call initiation failed")

            # Delay between calls to avoid rate limits
            if i < self.max_calls_per_campaign - 1:
                logging.info(f"Waiting {self.call_delay} seconds before next call...")
                time.sleep(self.call_delay)

        logging.info(f"Campaign completed: {results['successful_calls']} successful, {results['failed_calls']} failed")
        return results
    
    def add_test_merchants(self):
        """Add some test merchants to the queue for testing"""
        test_merchants = [
            ("+14062102346", "Test Merchant 1", "Retail"),
            ("+15551234567", "Test Merchant 2", "Restaurant"),
        ]

        for phone, name, biz_type in test_merchants:
            merchant_queue.add_merchant(phone, name, biz_type)

        logging.info("Added test merchants to queue")


def run_campaign():
    """
    Main function to run an outbound campaign.
    """
    try:
        controller = OutboundController()

        # Add test merchants if queue is empty
        stats = merchant_queue.get_queue_stats()
        if stats["total_merchants"] == 0:
            print("Adding test merchants to queue...")
            controller.add_test_merchants()

        results = controller.run_campaign()

        print("Outbound Campaign Results:")
        print(f"Total attempted: {results['total_attempted']}")
        print(f"Successful calls: {results['successful_calls']}")
        print(f"Failed calls: {results['failed_calls']}")
        print(f"Call SIDs: {results['call_sids']}")
        if results['errors']:
            print("Errors:")
            for error in results['errors']:
                print(f"  - {error}")

    except Exception as e:
        logging.error(f"Campaign failed: {e}")
        print(f"Campaign failed: {e}")


if __name__ == "__main__":
    run_campaign()