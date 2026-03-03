import sqlite3

conn = sqlite3.connect('aqi_merchant_services.db')
cursor = conn.cursor()

# Get high-potential leads (high volume, not called recently)
cursor.execute('''
SELECT business_name, contact_name, phone, monthly_volume 
FROM merchants 
WHERE monthly_volume > 50000 
ORDER BY monthly_volume DESC 
LIMIT 10
''')
high_leads = cursor.fetchall()
print(f'High-potential leads ({len(high_leads)}):')
for lead in high_leads:
    print(f"- {lead[0]} ({lead[1]}) - Phone: {lead[2]} - Volume: ${lead[3]:,.0f}")

# Check if any have been called
cursor.execute('SELECT COUNT(*) FROM merchant_calls')
calls_count = cursor.fetchone()[0]
print(f'\nTotal calls made: {calls_count}')

conn.close()