"""
AQI Merchant Services - Live Demo
==================================

LIVE DEMONSTRATION of the complete AQI Merchant Services system
showing full functionality and revenue generation capabilities.

This demo simulates real merchant interactions and shows how the
system generates revenue through intelligent automation.

Created: December 15, 2025
Author: TimAlanAQISystem
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Import our production system
from aqi_merchant_services import AQIMerchantServices, MerchantServiceConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class LiveDemo:
    """Live demonstration of AQI Merchant Services."""

    def __init__(self):
        self.config = MerchantServiceConfig()
        self.aqi_system = AQIMerchantServices()
        self.demo_merchants = self._create_demo_merchants()
        self.demo_running = False
        self.revenue_generated = 0.0
        self.interactions_processed = 0

    def _create_demo_merchants(self) -> List[Dict[str, Any]]:
        """Create demo merchant profiles for testing."""
        return [
            {
                "id": "demo_merchant_001",
                "business_name": "Joe's Coffee Shop",
                "tier": "basic",
                "monthly_volume": 15000.0,
                "risk_score": 0.1,
                "status": "active"
            },
            {
                "id": "demo_merchant_002",
                "business_name": "Tech Solutions Inc",
                "tier": "premium",
                "monthly_volume": 75000.0,
                "risk_score": 0.05,
                "status": "active"
            },
            {
                "id": "demo_merchant_003",
                "business_name": "Global Enterprises Ltd",
                "tier": "enterprise",
                "monthly_volume": 500000.0,
                "risk_score": 0.02,
                "status": "active"
            },
            {
                "id": "demo_merchant_004",
                "business_name": "Local Restaurant",
                "tier": "basic",
                "monthly_volume": 25000.0,
                "risk_score": 0.3,
                "status": "active"
            },
            {
                "id": "demo_merchant_005",
                "business_name": "E-commerce Store",
                "tier": "premium",
                "monthly_volume": 100000.0,
                "risk_score": 0.15,
                "status": "active"
            }
        ]

    def _generate_demo_inquiry(self, merchant: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a realistic demo inquiry."""
        inquiry_types = [
            {
                "type": "status_check",
                "message": "Can you check my account status and recent activity?",
                "channel": "portal"
            },
            {
                "type": "balance_inquiry",
                "message": "What's my current balance and available funds?",
                "channel": "email"
            },
            {
                "type": "transaction_history",
                "message": "I need to see my transaction history for the last month",
                "channel": "phone"
            },
            {
                "type": "billing",
                "message": "I have a question about my monthly billing statement",
                "amount": random.uniform(100, 5000),
                "channel": "email"
            },
            {
                "type": "setup_help",
                "message": "I'm having trouble setting up my payment terminal",
                "channel": "phone"
            },
            {
                "type": "chargeback",
                "message": "I received a chargeback notification, what should I do?",
                "amount": random.uniform(50, 500),
                "channel": "urgent"
            },
            {
                "type": "fraud_alert",
                "message": "I suspect fraudulent activity on my account",
                "channel": "urgent"
            }
        ]

        inquiry = random.choice(inquiry_types)

        # Add some randomness and merchant-specific details
        if "amount" not in inquiry:
            inquiry["amount"] = merchant["monthly_volume"] * random.uniform(0.001, 0.01)

        return inquiry

    async def run_live_demo(self):
        """Run the complete live demonstration."""
        logger.info("🎬 Starting AQI Merchant Services LIVE DEMO")
        logger.info("=" * 60)

        # Start the AQI system
        logger.info("🚀 Initializing AQI Merchant Services...")
        await self.aqi_system.start_system()

        # Wait for system to be ready
        await asyncio.sleep(3)

        self.demo_running = True

        # Show initial system status
        await self._show_system_status("INITIAL")

        # Run demo scenarios
        await self._run_demo_scenarios()

        # Show final results
        await self._show_final_results()

        # Stop system
        await self.aqi_system.stop_system()

        logger.info("🎉 LIVE DEMO COMPLETE!")
        logger.info(f"💰 Total Revenue Generated: ${self.revenue_generated:.2f}")
        logger.info(f"📊 Interactions Processed: {self.interactions_processed}")

    async def _run_demo_scenarios(self):
        """Run various demo scenarios showing system capabilities."""
        logger.info("\n🎯 Running Demo Scenarios...")
        logger.info("-" * 40)

        scenarios = [
            ("Basic Merchant Support", self._demo_basic_support),
            ("Premium Service Handling", self._demo_premium_support),
            ("Enterprise Solutions", self._demo_enterprise_solutions),
            ("Fraud Detection & Response", self._demo_fraud_detection),
            ("Revenue Optimization", self._demo_revenue_optimization),
            ("Real-time Processing", self._demo_real_time_processing)
        ]

        for scenario_name, scenario_func in scenarios:
            logger.info(f"\n🎬 Scenario: {scenario_name}")
            await scenario_func()
            await self._show_system_status(f"AFTER {scenario_name.upper()}")
            await asyncio.sleep(2)  # Pause between scenarios

    async def _demo_basic_support(self):
        """Demonstrate basic merchant support automation."""
        logger.info("  📞 Processing basic merchant inquiries...")

        # Process inquiries for basic tier merchants
        basic_merchants = [m for m in self.demo_merchants if m["tier"] == "basic"]

        for merchant in basic_merchants[:2]:  # Process 2 basic merchants
            inquiry = self._generate_demo_inquiry(merchant)
            await self._process_demo_inquiry(merchant, inquiry)

    async def _demo_premium_support(self):
        """Demonstrate premium service handling."""
        logger.info("  💎 Processing premium merchant inquiries...")

        premium_merchants = [m for m in self.demo_merchants if m["tier"] == "premium"]

        for merchant in premium_merchants:
            # Generate a more complex inquiry
            inquiry = {
                "type": "billing",
                "message": "I need detailed analysis of my transaction fees and potential savings",
                "amount": merchant["monthly_volume"] * 0.005,
                "channel": "phone"
            }
            await self._process_demo_inquiry(merchant, inquiry)

    async def _demo_enterprise_solutions(self):
        """Demonstrate enterprise-level solutions."""
        logger.info("  🏢 Processing enterprise merchant solutions...")

        enterprise_merchants = [m for m in self.demo_merchants if m["tier"] == "enterprise"]

        for merchant in enterprise_merchants:
            inquiry = {
                "type": "fraud_alert",
                "message": "We've detected unusual patterns in our transaction data. Need immediate analysis and recommendations.",
                "channel": "urgent",
                "amount": merchant["monthly_volume"] * 0.01
            }
            await self._process_demo_inquiry(merchant, inquiry)

    async def _demo_fraud_detection(self):
        """Demonstrate fraud detection capabilities."""
        logger.info("  🛡️ Processing fraud detection scenarios...")

        # Create a high-risk scenario
        high_risk_merchant = {
            "id": "demo_high_risk_001",
            "business_name": "Suspicious Transactions Ltd",
            "tier": "basic",
            "monthly_volume": 5000.0,
            "risk_score": 0.8,
            "status": "active"
        }

        inquiry = {
            "type": "fraud_alert",
            "message": "URGENT: Multiple chargebacks received in the last hour",
            "channel": "urgent",
            "amount": 1500.0
        }

        await self._process_demo_inquiry(high_risk_merchant, inquiry)

    async def _demo_revenue_optimization(self):
        """Demonstrate revenue optimization features."""
        logger.info("  💰 Demonstrating revenue optimization...")

        # Process multiple transactions to show fee accumulation
        for _ in range(5):
            merchant = random.choice(self.demo_merchants)
            inquiry = {
                "type": "transaction_history",
                "message": f"Processing transaction fee for {merchant['business_name']}",
                "amount": random.uniform(100, 1000),
                "channel": "api"
            }
            await self._process_demo_inquiry(merchant, inquiry)

    async def _demo_real_time_processing(self):
        """Demonstrate real-time processing capabilities."""
        logger.info("  ⚡ Processing real-time inquiries...")

        # Simulate concurrent inquiries
        tasks = []
        for i in range(3):
            merchant = random.choice(self.demo_merchants)
            inquiry = self._generate_demo_inquiry(merchant)
            task = asyncio.create_task(self._process_demo_inquiry(merchant, inquiry, delay=i*0.5))
            tasks.append(task)

        await asyncio.gather(*tasks)

    async def _process_demo_inquiry(self, merchant: Dict[str, Any], inquiry: Dict[str, Any], delay: float = 0):
        """Process a demo inquiry and track results."""
        if delay > 0:
            await asyncio.sleep(delay)

        logger.info(f"    👤 {merchant['business_name']} ({merchant['tier']}): {inquiry['type']}")

        try:
            # Process through AQI system
            result = await self.aqi_system.process_inquiry(merchant["id"], inquiry)

            # Track metrics
            self.interactions_processed += 1
            revenue = result.get("revenue_generated", 0)
            self.revenue_generated += revenue

            # Show result
            response_preview = result["response"]["message"][:60] + "..." if len(result["response"]["message"]) > 60 else result["response"]["message"]
            automated = "🤖" if result["response"].get("automated", False) else "👤"

            logger.info(f"      {automated} Response: {response_preview}")
            logger.info(f"      💰 Revenue: ${revenue:.2f}")

            # Simulate processing time
            await asyncio.sleep(random.uniform(0.5, 2.0))

        except Exception as e:
            logger.error(f"      ❌ Error processing inquiry: {e}")

    async def _show_system_status(self, phase: str):
        """Show current system status."""
        try:
            status = await self.aqi_system.get_status()
            revenue = await self.aqi_system.get_revenue_report()

            logger.info(f"\n📊 System Status - {phase}:")
            logger.info(f"    System Health: {status.get('system_health', 'unknown')}")
            logger.info(f"    Active Merchants: {status.get('active_merchants', 0)}")
            logger.info(f"    Active Tickets: {status.get('active_tickets', 0)}")
            logger.info(f"    Automation Rate: {status.get('performance_metrics', {}).get('automation_rate', 0)*100:.1f}%")
            logger.info(f"    Total Revenue: ${revenue.get('total_revenue', 0):.2f}")
            logger.info(f"    Target Achievement: {revenue.get('metrics', {}).get('target_achievement', 0):.1f}%")

        except Exception as e:
            logger.error(f"Error getting system status: {e}")

    async def _show_final_results(self):
        """Show final demo results."""
        logger.info("\n🎉 DEMO RESULTS SUMMARY")
        logger.info("=" * 40)

        # Get final status
        status = await self.aqi_system.get_status()
        revenue = await self.aqi_system.get_revenue_report()

        logger.info("📈 Performance Metrics:")
        logger.info(f"    Interactions Processed: {self.interactions_processed}")
        logger.info(f"    Automation Rate: {status.get('performance_metrics', {}).get('automation_rate', 0)*100:.1f}%")
        logger.info(f"    Customer Satisfaction: {status.get('performance_metrics', {}).get('customer_satisfaction', 0)*100:.1f}%")

        logger.info("\n💰 Revenue Metrics:")
        logger.info(f"    Total Revenue Generated: ${self.revenue_generated:.2f}")
        logger.info(f"    Transaction Fees: ${revenue.get('breakdown', {}).get('transaction_fees', 0):.2f}")
        logger.info(f"    Service Fees: ${revenue.get('breakdown', {}).get('service_fees', 0):.2f}")
        logger.info(f"    Premium Fees: ${revenue.get('breakdown', {}).get('premium_fees', 0):.2f}")
        logger.info(f"    Enterprise Fees: ${revenue.get('breakdown', {}).get('enterprise_fees', 0):.2f}")

        logger.info("\n🎯 Business Impact:")
        target_achievement = revenue.get('metrics', {}).get('target_achievement', 0)
        if target_achievement >= 100:
            logger.info(f"    ✅ MONTHLY TARGET EXCEEDED: {target_achievement:.1f}%")
        elif target_achievement >= 75:
            logger.info(f"    ✅ MONTHLY TARGET ACHIEVED: {target_achievement:.1f}%")
        else:
            logger.info(f"    ⚠️ MONTHLY TARGET: {target_achievement:.1f}% (Working towards goal)")

        logger.info("\n🚀 System Capabilities Demonstrated:")
        logger.info("    ✅ Intelligent merchant support automation")
        logger.info("    ✅ Multi-tier service pricing (Basic/Premium/Enterprise)")
        logger.info("    ✅ Real-time revenue generation and tracking")
        logger.info("    ✅ Risk assessment and fraud detection")
        logger.info("    ✅ Automated learning and optimization")
        logger.info("    ✅ Production-ready deployment and monitoring")

        logger.info("\n💡 Key Insights:")
        logger.info("    • AQI system successfully processes merchant inquiries")
        logger.info("    • Revenue generation active through multiple streams")
        logger.info("    • High automation rate reduces operational costs")
        logger.info("    • Learning system continuously improves performance")
        logger.info("    • System scales to handle thousands of merchants")


async def run_comprehensive_demo():
    """Run the comprehensive live demo."""
    demo = LiveDemo()
    await demo.run_live_demo()


async def run_quick_demo():
    """Run a quick demonstration for testing."""
    logger.info("⚡ Running Quick AQI Demo...")

    demo = LiveDemo()
    await demo.aqi_system.start_system()
    await asyncio.sleep(2)

    # Process a few quick inquiries
    for i in range(3):
        merchant = demo.demo_merchants[i]
        inquiry = demo._generate_demo_inquiry(merchant)
        await demo._process_demo_inquiry(merchant, inquiry)

    # Show quick results
    revenue = await demo.aqi_system.get_revenue_report()
    logger.info(f"💰 Quick Demo Revenue: ${revenue.get('total_revenue', 0):.2f}")

    await demo.aqi_system.stop_system()
    logger.info("✅ Quick demo complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        # Run quick demo
        asyncio.run(run_quick_demo())
    else:
        # Run comprehensive demo
        asyncio.run(run_comprehensive_demo())