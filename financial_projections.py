
import pandas as pd

def calculate_projections():
    # Constants
    UPFRONT_BONUS = 300
    USER_RESIDUAL_SPLIT = 0.50
    
    # Assumptions (SMB Market)
    # Average Net Residual Profit per merchant (Total pot before split)
    # SMBs doing $20k-$50k/mo volume typically generate $60-$100 in net residuals.
    AVG_NET_RESIDUAL_TOTAL = 80 
    USER_MONTHLY_RESIDUAL = AVG_NET_RESIDUAL_TOTAL * USER_RESIDUAL_SPLIT # $40/mo
    
    # Agent Performance Assumptions
    # AI Agent: 150 calls/day * 22 days = 3300 calls/mo
    # Conversion Rate (Lead to Deal): 0.5% (Conservative for cold), 1.0% (Target)
    # Let's use a tiered approach for "Ramp Up"
    ACCOUNTS_PER_AGENT_MO = 12 # ~1 deal every ~2 days. Very achievable for an AI calling 8hrs/day.

    # Timeline
    months = 12
    
    data = []
    total_active_accounts = 0
    
    print(f"{'Month':<5} | {'Agents':<6} | {'New Accts':<10} | {'Upfront ($)':<12} | {'Residuals ($)':<14} | {'Total Rev ($)':<14}")
    print("-" * 75)

    for m in range(1, months + 1):
        # Agent Count Logic
        # User Request: Month 1 = 2 Agents (Alan + Agent X)
        # Then increase by 4 every month
        if m == 1:
            agents = 2
        else:
            # Previous month agents + 4
            # M1: 2
            # M2: 6
            # M3: 10
            agents = 2 + ((m - 1) * 4)
            
        # Monthly Calculations
        new_accounts = agents * ACCOUNTS_PER_AGENT_MO
        upfront_rev = new_accounts * UPFRONT_BONUS
        
        # Residuals are paid on ACTIVE accounts. 
        # Assuming accounts closed in Month M start paying residuals in Month M+1 usually, 
        # but for simplicity let's assume they start generating partial revenue same month or full next.
        # Let's calculate residuals based on Total Active Accounts at START of month + half of new?
        # Simpler: Residuals based on total accounts accumulated.
        
        residual_rev = total_active_accounts * USER_MONTHLY_RESIDUAL
        
        total_rev = upfront_rev + residual_rev
        
        # Update totals for next month
        total_active_accounts += new_accounts
        
        data.append({
            "Month": m,
            "Agents": agents,
            "New Accounts": new_accounts,
            "Total Accounts": total_active_accounts,
            "Upfront Revenue": upfront_rev,
            "Monthly Residuals": residual_rev,
            "Total Monthly Revenue": total_rev
        })
        
        print(f"{m:<5} | {agents:<6} | {new_accounts:<10} | ${upfront_rev:,.0f}       | ${residual_rev:,.0f}         | ${total_rev:,.0f}")

    # 12 Month Totals
    total_upfront = sum(d['Upfront Revenue'] for d in data)
    final_monthly_recurring = data[-1]['Monthly Residuals']
    total_revenue_year_1 = sum(d['Total Monthly Revenue'] for d in data)
    
    print("-" * 75)
    print(f"\nYEAR 1 SUMMARY:")
    print(f"Total Active Accounts: {total_active_accounts}")
    print(f"Total Upfront Bonuses: ${total_upfront:,.2f}")
    print(f"Exiting Monthly Recurring Revenue (MRR): ${final_monthly_recurring:,.2f}/mo")
    print(f"Total Year 1 Revenue: ${total_revenue_year_1:,.2f}")

if __name__ == "__main__":
    calculate_projections()
