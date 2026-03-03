#!/usr/bin/env python3
"""
AQI Product PDF Generator
Converts markdown content to professional PDF for sales
"""

import markdown
from weasyprint import HTML, CSS
import os

def create_product_pdf(markdown_file, output_pdf):
    """Convert markdown to PDF"""

    # Read markdown
    with open(markdown_file, 'r') as f:
        md_content = f.read()

    # Convert to HTML
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])

    # Add styling
    styled_html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: 'Helvetica', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #34495e;
                margin-top: 30px;
            }}
            code {{
                background-color: #f8f9fa;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }}
            pre {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
            }}
            .highlight {{
                background-color: #e8f4fd;
                padding: 15px;
                border-left: 4px solid #3498db;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    # Generate PDF
    HTML(string=styled_html).write_pdf(output_pdf)
    print(f"✅ PDF created: {output_pdf}")

if __name__ == "__main__":
    # Generate product PDF
    create_product_pdf(
        'aqi_merchant_accelerator_kit.md',
        'AQI_Merchant_Accelerator_Kit.pdf'
    )

    print("🎯 Product PDF ready for Gumroad upload!")