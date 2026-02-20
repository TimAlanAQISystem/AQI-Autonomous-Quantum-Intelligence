"""
Data Ingestion Engine for AQI Meta-Layer
Integrates with existing AQI data sources for real merchant signals.
"""

import os
import sys
from typing import Dict, List, Any, Optional
import requests
import json
import time

class DataIngestionEngine:
    """
    Handles ingestion of real merchant data from various AQI sources.
    """
    
    def __init__(self):
        self.sources = {
            'crunchbase': self._fetch_crunchbase,
            'bombora': self._fetch_bombora,
            'linkedin': self._fetch_linkedin,
            'merchant_locator': self._fetch_merchant_locator
        }
        self.api_keys = self._load_api_keys()
        
    def _load_api_keys(self) -> Dict[str, str]:
        """Load API keys from environment"""
        return {
            'crunchbase': os.environ.get('CRUNCHBASE_API_KEY', ''),
            'bombora': os.environ.get('BOMBORA_API_KEY', ''),
            'linkedin': os.environ.get('LINKEDIN_ACCESS_TOKEN', ''),
        }
    
    def fetch_merchant_signals(self, company_name: str) -> Dict[str, Any]:
        """
        Fetch comprehensive merchant signals for a company.
        
        Args:
            company_name: Target company name
            
        Returns:
            Consolidated signal data
        """
        signals = {}
        
        for source_name, fetch_func in self.sources.items():
            try:
                signal_data = fetch_func(company_name)
                if signal_data:
                    signals[source_name] = signal_data
            except Exception as e:
                print(f"Warning: Failed to fetch from {source_name}: {e}")
        
        return {
            'company': company_name,
            'signals': signals,
            'timestamp': time.time(),
            'sources_attempted': list(self.sources.keys())
        }
    
    def _fetch_crunchbase(self, company_name: str) -> Optional[Dict]:
        """Fetch funding and company data from Crunchbase"""
        if not self.api_keys['crunchbase']:
            return None
            
        # Placeholder - would implement actual Crunchbase API call
        return {
            'funding_rounds': [],
            'total_funding': 0,
            'investors': [],
            'last_funding_date': None
        }
    
    def _fetch_bombora(self, company_name: str) -> Optional[Dict]:
        """Fetch intent signals from Bombora"""
        if not self.api_keys['bombora']:
            return None
            
        # Placeholder - would implement actual Bombora API call
        return {
            'intent_signals': [],
            'engagement_score': 0,
            'topics': []
        }
    
    def _fetch_linkedin(self, company_name: str) -> Optional[Dict]:
        """Fetch professional signals from LinkedIn"""
        if not self.api_keys['linkedin']:
            return None
            
        # Placeholder - would implement actual LinkedIn API call
        return {
            'employee_count': 0,
            'growth_signals': [],
            'industry': '',
            'headquarters': ''
        }
    
    def _fetch_merchant_locator(self, company_name: str) -> Optional[Dict]:
        """Fetch from local merchant locator database"""
        try:
            # Try to import and use existing merchant locator
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            from aqi_merchant_signal_locator import MerchantSignalLocator
            
            locator = MerchantSignalLocator()
            # This would need actual implementation based on locator methods
            return {
                'retail_signals': [],
                'business_type': '',
                'location': '',
                'monthly_volume_estimate': 0
            }
        except ImportError:
            return None
        except Exception as e:
            print(f"Merchant locator error: {e}")
            return None
    
    def score_merchant_potential(self, signal_data: Dict) -> float:
        """
        Score merchant potential based on collected signals.
        
        Args:
            signal_data: Consolidated signal data
            
        Returns:
            Potential score (0-100)
        """
        score = 0
        signals = signal_data.get('signals', {})
        
        # Crunchbase signals (funding indicates growth potential)
        if 'crunchbase' in signals:
            cb_data = signals['crunchbase']
            funding = cb_data.get('total_funding', 0)
            if funding > 10000000:  # $10M+
                score += 30
            elif funding > 1000000:  # $1M+
                score += 20
        
        # Bombora signals (intent indicates buying readiness)
        if 'bombora' in signals:
            bombora_data = signals['bombora']
            engagement = bombora_data.get('engagement_score', 0)
            score += min(engagement * 20, 25)  # Up to 25 points
        
        # LinkedIn signals (company size and growth)
        if 'linkedin' in signals:
            li_data = signals['linkedin']
            employees = li_data.get('employee_count', 0)
            if employees > 100:
                score += 15
            elif employees > 10:
                score += 10
            
            growth_signals = len(li_data.get('growth_signals', []))
            score += min(growth_signals * 5, 15)
        
        # Merchant locator signals (retail readiness)
        if 'merchant_locator' in signals:
            ml_data = signals['merchant_locator']
            volume = ml_data.get('monthly_volume_estimate', 0)
            if volume > 50000:
                score += 15
            elif volume > 10000:
                score += 10
        
        return float(min(score, 100))  # Cap at 100 and ensure float return