"""
Business Logic Engine for AQI Meta-Layer
Handles SCSDMC merchant services business rules, commission calculations, and revenue projections.
"""

import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class BusinessEngine:
    """
    Implements SCSDMC business logic for merchant services operations.
    """
    
    def __init__(self):
        self.equipment_bonus = 300.00  # $300 per boarding
        self.residual_share = 0.70     # 70% residual share
        self.monthly_volume_threshold = 10000  # Minimum monthly volume for qualification
        
    def calculate_commission(self, monthly_volume: float, equipment_cost: float = 0) -> Dict[str, float]:
        """
        Calculate commissions based on SCSDMC model.
        
        Args:
            monthly_volume: Merchant's monthly processing volume
            equipment_cost: Cost of equipment (if applicable)
            
        Returns:
            Dict with commission breakdown
        """
        # Base commission on volume (simplified model)
        base_rate = 0.0025  # 0.25% base rate
        commission = monthly_volume * base_rate
        
        # Equipment bonus
        equipment_bonus = self.equipment_bonus
        
        # Residual share (70% of ongoing commissions)
        residual_monthly = commission * self.residual_share
        
        return {
            'base_commission': commission,
            'equipment_bonus': equipment_bonus,
            'residual_monthly': residual_monthly,
            'first_month_total': commission + equipment_bonus,
            'annual_residual': residual_monthly * 12
        }
    
    def project_revenue(self, monthly_boardings: int, avg_monthly_volume: float, 
                       months: int = 12) -> Dict[str, Any]:
        """
        Project revenue based on boarding targets.
        
        Args:
            monthly_boardings: Number of new merchants per month
            avg_monthly_volume: Average monthly volume per merchant
            months: Projection period in months
            
        Returns:
            Revenue projection data
        """
        cumulative_boardings = 0
        monthly_revenue = []
        cumulative_revenue = 0
        
        for month in range(1, months + 1):
            # New boardings this month
            new_boardings = monthly_boardings
            
            # Calculate revenue from new boardings
            new_revenue = 0
            for _ in range(new_boardings):
                calc = self.calculate_commission(avg_monthly_volume)
                new_revenue += calc['first_month_total']
            
            # Residual from previous boardings
            residual_revenue = cumulative_boardings * self.calculate_commission(avg_monthly_volume)['residual_monthly']
            
            total_monthly = new_revenue + residual_revenue
            cumulative_revenue += total_monthly
            cumulative_boardings += new_boardings
            
            monthly_revenue.append({
                'month': month,
                'new_boardings': new_boardings,
                'new_revenue': new_revenue,
                'residual_revenue': residual_revenue,
                'total_revenue': total_monthly,
                'cumulative_revenue': cumulative_revenue,
                'total_boardings': cumulative_boardings
            })
        
        return {
            'monthly_projections': monthly_revenue,
            'total_revenue': cumulative_revenue,
            'total_boardings': cumulative_boardings,
            'avg_monthly_revenue': cumulative_revenue / months
        }
    
    def qualify_merchant(self, merchant_data: Dict) -> Dict[str, Any]:
        """
        Qualify a merchant for SCSDMC services.
        
        Args:
            merchant_data: Merchant information dict
            
        Returns:
            Qualification result
        """
        monthly_volume = merchant_data.get('monthly_volume', 0)
        business_type = merchant_data.get('business_type', '').lower()
        risk_score = merchant_data.get('risk_score', 0)
        
        # Qualification criteria
        qualifies = (
            monthly_volume >= self.monthly_volume_threshold and
            risk_score <= 0.7 and  # Low to medium risk
            not any(restricted in business_type for restricted in 
                   ['gambling', 'tobacco', 'adult', 'weapons'])
        )
        
        if qualifies:
            commission_calc = self.calculate_commission(monthly_volume)
            return {
                'qualified': True,
                'reason': 'Meets all criteria',
                'commission_projection': commission_calc,
                'priority': 'high' if monthly_volume > 50000 else 'medium'
            }
        else:
            reasons = []
            if monthly_volume < self.monthly_volume_threshold:
                reasons.append(f'Volume too low: ${monthly_volume} < ${self.monthly_volume_threshold}')
            if risk_score > 0.7:
                reasons.append(f'Risk score too high: {risk_score}')
            if any(restricted in business_type for restricted in ['gambling', 'tobacco', 'adult', 'weapons']):
                reasons.append(f'Restricted business type: {business_type}')
            
            return {
                'qualified': False,
                'reason': '; '.join(reasons),
                'commission_projection': None,
                'priority': 'none'
            }
    
    def optimize_boarding_strategy(self, target_revenue: float, 
                                 avg_volume: float) -> Dict[str, Any]:
        """
        Calculate required monthly boardings to achieve revenue target.
        
        Args:
            target_revenue: Annual revenue target
            avg_volume: Average merchant monthly volume
            
        Returns:
            Strategy recommendations
        """
        # Calculate required monthly boardings
        avg_first_year_commission = self.calculate_commission(avg_volume)['first_month_total']
        avg_annual_residual = self.calculate_commission(avg_volume)['annual_residual']
        
        # Simplified calculation: target = (boardings * first_year) + (boardings * annual_residual)
        # Solve for boardings: boardings = target / (first_year + annual_residual)
        required_boardings = target_revenue / (avg_first_year_commission + avg_annual_residual)
        
        return {
            'target_revenue': target_revenue,
            'required_monthly_boardings': int(required_boardings / 12),
            'avg_first_year_value': avg_first_year_commission + avg_annual_residual,
            'break_even_months': int(avg_first_year_commission / (avg_annual_residual / 12))
        }