#!/usr/bin/env python3
"""
EXCEL LEAD IMPORTER — Feed Alan His Call Lists
================================================
Imports merchant leads from Excel (.xlsx/.xls) and CSV files into the SQLite lead database.

Flexible column mapping — auto-detects common column names:
  Phone:     phone, phone_number, telephone, cell, mobile, number, phone #
  Name:      name, business_name, company, business, merchant, dba, legal_name
  Type:      type, business_type, industry, category, mcc, vertical
  Contact:   contact, contact_name, owner, first_name + last_name
  Volume:    volume, monthly_volume, monthly_sales, annual_volume
  Priority:  priority, tier, rank, grade
  Source:    source, lead_source, origin, campaign, list_name

Usage:
    # From Python
    from excel_lead_importer import import_leads
    result = import_leads("path/to/leads.xlsx")
    
    # From command line
    python excel_lead_importer.py leads.xlsx
    
    # API endpoint (POST /leads/import with file upload)
"""

import os
import re
import csv
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Quality gate integration
try:
    from lead_quality_gate import screen_lead
    QUALITY_GATE_AVAILABLE = True
except ImportError:
    QUALITY_GATE_AVAILABLE = False

logger = logging.getLogger("EXCEL_IMPORTER")

# Column name mappings — any of these headers will map to the canonical field
COLUMN_MAPPINGS = {
    "phone_number": [
        "phone", "phone_number", "telephone", "cell", "mobile", "number",
        "phone #", "phone#", "tel", "phone number", "contact phone",
        "business phone", "main phone", "primary phone", "cell phone"
    ],
    "name": [
        "name", "business_name", "business name", "company", "business",
        "merchant", "dba", "legal_name", "legal name", "company name",
        "company_name", "merchant name", "store name", "store",
        "location name", "location"
    ],
    "business_type": [
        "type", "business_type", "business type", "industry", "category",
        "mcc", "vertical", "sector", "mcc code", "industry type",
        "business category", "merchant type"
    ],
    "contact_name": [
        "contact", "contact_name", "contact name", "owner", "owner name",
        "first_name", "first name", "decision maker", "manager", "principal"
    ],
    "monthly_volume": [
        "volume", "monthly_volume", "monthly volume", "monthly_sales",
        "monthly sales", "annual_volume", "annual volume", "avg monthly",
        "average monthly", "monthly processing", "monthly card volume",
        "est. monthly volume", "est monthly volume", "estimated monthly volume"
    ],
    "priority": [
        "priority", "tier", "rank", "grade", "level", "score", "quality"
    ],
    "lead_source": [
        "source", "lead_source", "lead source", "origin", "campaign",
        "list_name", "list name", "list", "batch", "file", "source_file"
    ],
    "email": [
        "email", "email_address", "email address", "e-mail", "contact email",
        "business email"
    ],
    "address": [
        "address", "street", "street_address", "street address", "location",
        "city", "state", "zip", "zip_code", "zipcode"
    ],
    "notes": [
        "notes", "note", "comments", "comment", "remarks", "memo", "info"
    ]
}


def normalize_phone(raw: str) -> str:
    """
    Normalize phone number to E.164 format (+1XXXXXXXXXX for US numbers).
    Strips all non-digit characters, adds country code if missing.
    Returns empty string if invalid.
    """
    if not raw:
        return ""
    
    # Strip everything except digits and leading +
    cleaned = re.sub(r'[^\d+]', '', str(raw).strip())
    
    # Remove leading + for processing
    has_plus = cleaned.startswith('+')
    digits = cleaned.lstrip('+')
    
    # Skip if too short
    if len(digits) < 7:
        return ""
    
    # US/Canada numbers
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    elif len(digits) > 11 and has_plus:
        return f"+{digits}"  # International — keep as-is
    elif len(digits) == 11:
        return f"+{digits}"
    
    return ""


def normalize_priority(raw: str) -> str:
    """Map various priority/tier labels to canonical values"""
    if not raw:
        return "medium"
    
    raw_lower = str(raw).lower().strip()
    
    if raw_lower in ("critical", "urgent", "hot", "a", "1", "highest", "platinum"):
        return "critical"
    elif raw_lower in ("high", "b", "2", "warm", "priority", "gold"):
        return "high"
    elif raw_lower in ("medium", "c", "3", "normal", "standard", "mid"):
        return "medium"
    elif raw_lower in ("low", "d", "4", "cold", "backlog"):
        return "low"
    
    return "medium"


def detect_columns(headers: List[str]) -> Dict[str, int]:
    """
    Auto-detect which column index maps to which canonical field.
    Returns {canonical_field: column_index}
    """
    mapping = {}
    header_lower = [h.strip().lower() if h else "" for h in headers]
    
    for canonical, aliases in COLUMN_MAPPINGS.items():
        for i, header in enumerate(header_lower):
            if header in aliases:
                mapping[canonical] = i
                break
    
    # Special case: first_name + last_name → contact_name via concatenation
    if "contact_name" not in mapping:
        first_idx = None
        last_idx = None
        for i, h in enumerate(header_lower):
            if h in ("first_name", "first name", "first"):
                first_idx = i
            if h in ("last_name", "last name", "last"):
                last_idx = i
        if first_idx is not None:
            mapping["_first_name_idx"] = first_idx
            if last_idx is not None:
                mapping["_last_name_idx"] = last_idx
    
    return mapping


def read_excel(filepath: str) -> Tuple[List[str], List[List[Any]]]:
    """Read an Excel file and return (headers, rows)"""
    import openpyxl
    
    wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
    ws = wb.active
    
    rows = []
    headers = []
    
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            headers = [str(c) if c else "" for c in row]
        else:
            rows.append(list(row))
    
    wb.close()
    return headers, rows


def read_csv(filepath: str) -> Tuple[List[str], List[List[Any]]]:
    """Read a CSV file and return (headers, rows)"""
    rows = []
    headers = []
    
    # Try different encodings
    for encoding in ['utf-8', 'latin-1', 'cp1252']:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i == 0:
                        headers = row
                    else:
                        rows.append(row)
            break
        except UnicodeDecodeError:
            continue
    
    return headers, rows


def import_leads(
    filepath: str,
    default_source: str = None,
    default_priority: str = "medium",
    skip_duplicates: bool = True,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Import leads from an Excel or CSV file into the SQLite database.
    
    Args:
        filepath: Path to .xlsx, .xls, or .csv file
        default_source: Override lead_source for all rows (default: filename)
        default_priority: Default priority if not in spreadsheet
        skip_duplicates: Skip leads with phone numbers already in DB
        dry_run: If True, parse and validate but don't import
    
    Returns:
        {
            "imported": int,
            "skipped_duplicate": int,
            "skipped_invalid": int,
            "skipped_no_phone": int,
            "total_rows": int,
            "columns_detected": {field: header_name},
            "errors": [str],
            "sample_leads": [first 3 leads for verification]
        }
    """
    filepath = str(filepath)
    ext = Path(filepath).suffix.lower()
    
    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}
    
    # Read file
    if ext in ('.xlsx', '.xls'):
        headers, rows = read_excel(filepath)
    elif ext == '.csv':
        headers, rows = read_csv(filepath)
    else:
        return {"error": f"Unsupported file format: {ext}. Use .xlsx, .xls, or .csv"}
    
    if not headers:
        return {"error": "No headers found in file"}
    
    if not rows:
        return {"error": "No data rows found in file"}
    
    # Detect columns
    col_map = detect_columns(headers)
    
    if "phone_number" not in col_map:
        return {
            "error": f"No phone number column detected. Headers found: {headers}",
            "hint": "Expected column named: phone, phone_number, telephone, cell, mobile, number"
        }
    
    # Map detected columns to readable names for reporting
    detected = {}
    for field, idx in col_map.items():
        if not field.startswith("_"):
            detected[field] = headers[idx]
    
    # Default source
    if not default_source:
        default_source = Path(filepath).stem
    
    # Import leads
    from lead_database import LeadDB
    db = LeadDB()
    
    imported = 0
    skipped_dup = 0
    skipped_invalid = 0
    skipped_no_phone = 0
    skipped_quality = 0
    errors = []
    sample_leads = []
    
    # Get existing phones for duplicate check
    existing_phones = set()
    if skip_duplicates:
        with db._conn() as conn:
            for row in conn.execute("SELECT phone_number FROM leads"):
                existing_phones.add(row["phone_number"])
    
    for row_idx, row in enumerate(rows):
        try:
            # Extract phone
            phone_idx = col_map["phone_number"]
            raw_phone = str(row[phone_idx]) if phone_idx < len(row) and row[phone_idx] else ""
            phone = normalize_phone(raw_phone)
            
            if not phone:
                skipped_no_phone += 1
                continue
            
            # Duplicate check
            if skip_duplicates and phone in existing_phones:
                skipped_dup += 1
                continue
            
            # Extract other fields
            def get_val(field: str, default: str = "") -> str:
                idx = col_map.get(field)
                if idx is not None and idx < len(row) and row[idx] is not None:
                    return str(row[idx]).strip()
                return default
            
            name = get_val("name", "Unknown")
            business_type = get_val("business_type", "Unknown")
            contact_name = get_val("contact_name", "")
            priority = normalize_priority(get_val("priority", default_priority))
            lead_source = get_val("lead_source", default_source)
            email = get_val("email", "")
            notes_raw = get_val("notes", "")
            address = get_val("address", "")
            
            # Handle first_name + last_name concatenation
            if not contact_name and "_first_name_idx" in col_map:
                first = ""
                last = ""
                fn_idx = col_map["_first_name_idx"]
                if fn_idx < len(row) and row[fn_idx]:
                    first = str(row[fn_idx]).strip()
                ln_idx = col_map.get("_last_name_idx")
                if ln_idx is not None and ln_idx < len(row) and row[ln_idx]:
                    last = str(row[ln_idx]).strip()
                contact_name = f"{first} {last}".strip()
            
            # If name is "Unknown" but we have contact_name, use it
            if name == "Unknown" and contact_name:
                name = contact_name
            
            # QUALITY GATE — Screen lead before importing
            if QUALITY_GATE_AVAILABLE:
                gate_result = screen_lead(name=name, phone=phone, business_type=business_type)
                if not gate_result["pass"]:
                    skipped_quality += 1
                    if len(errors) < 20:
                        errors.append(f"Row {row_idx + 2} REJECTED [{gate_result['reject_category']}]: {name} — {gate_result['reject_reason']}")
                    continue
            
            # Monthly volume parsing
            monthly_vol = None
            vol_raw = get_val("monthly_volume", "")
            if vol_raw:
                try:
                    # Remove $, commas, etc
                    vol_cleaned = re.sub(r'[^\d.]', '', vol_raw)
                    if vol_cleaned:
                        monthly_vol = float(vol_cleaned)
                        # If column said "annual", divide by 12
                        vol_header = headers[col_map.get("monthly_volume", 0)].lower()
                        if "annual" in vol_header:
                            monthly_vol = monthly_vol / 12
                except (ValueError, TypeError):
                    pass
            
            # Build notes
            notes_parts = []
            if notes_raw:
                notes_parts.append(notes_raw)
            if contact_name:
                notes_parts.append(f"Contact: {contact_name}")
            if email:
                notes_parts.append(f"Email: {email}")
            if address:
                notes_parts.append(f"Address: {address}")
            
            lead_data = {
                "phone_number": phone,
                "name": name,
                "business_type": business_type,
                "priority": priority,
                "lead_source": lead_source,
                "monthly_volume": monthly_vol,
                "notes": notes_parts
            }
            
            if len(sample_leads) < 5:
                sample_leads.append(lead_data)
            
            if not dry_run:
                lead_id = db.add_lead(
                    phone_number=phone,
                    name=name,
                    business_type=business_type,
                    priority=priority,
                    lead_source=lead_source
                )
                
                # Update extra fields that add_lead might not cover
                if monthly_vol or notes_parts:
                    with db._conn() as conn:
                        if monthly_vol:
                            conn.execute("UPDATE leads SET monthly_volume = ? WHERE id = ?", (monthly_vol, lead_id))
                        if notes_parts:
                            conn.execute("UPDATE leads SET notes = ? WHERE id = ?", (json.dumps(notes_parts), lead_id))
                
                existing_phones.add(phone)  # Prevent double-import within same file
            
            imported += 1
            
        except Exception as e:
            errors.append(f"Row {row_idx + 2}: {str(e)}")
            skipped_invalid += 1
    
    result = {
        "status": "dry_run" if dry_run else "imported",
        "imported": imported,
        "skipped_duplicate": skipped_dup,
        "skipped_invalid": skipped_invalid,
        "skipped_no_phone": skipped_no_phone,
        "skipped_quality_gate": skipped_quality,
        "total_rows": len(rows),
        "columns_detected": detected,
        "errors": errors[:20],  # Cap at 20
        "sample_leads": sample_leads,
        "file": Path(filepath).name,
        "timestamp": datetime.now().isoformat()
    }
    
    if not dry_run:
        # Get updated DB stats
        result["db_stats"] = db.get_stats()
    
    logger.info(f"[EXCEL IMPORT] {filepath}: {imported} imported, {skipped_dup} duplicates, {skipped_invalid} invalid, {skipped_no_phone} no phone")
    
    return result


def main():
    """CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: python excel_lead_importer.py <file.xlsx|file.csv> [--dry-run] [--source NAME]")
        print()
        print("Examples:")
        print("  python excel_lead_importer.py leads.xlsx")
        print("  python excel_lead_importer.py merchants.csv --source 'Feb Campaign'")
        print("  python excel_lead_importer.py data.xlsx --dry-run")
        return
    
    filepath = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    
    source = None
    if "--source" in sys.argv:
        idx = sys.argv.index("--source")
        if idx + 1 < len(sys.argv):
            source = sys.argv[idx + 1]
    
    print(f"{'DRY RUN — ' if dry_run else ''}Importing leads from: {filepath}")
    print("=" * 60)
    
    result = import_leads(filepath, default_source=source, dry_run=dry_run)
    
    if "error" in result:
        print(f"ERROR: {result['error']}")
        if "hint" in result:
            print(f"HINT: {result['hint']}")
        return
    
    print(f"File:            {result['file']}")
    print(f"Total Rows:      {result['total_rows']}")
    print(f"Imported:        {result['imported']}")
    print(f"Skipped (dupes): {result['skipped_duplicate']}")
    print(f"Skipped (bad #): {result['skipped_no_phone']}")
    print(f"Skipped (gate):  {result.get('skipped_quality_gate', 0)}")
    print(f"Skipped (error): {result['skipped_invalid']}")
    print()
    
    print("Columns Detected:")
    for field, header in result['columns_detected'].items():
        print(f"  {field:<20} <- '{header}'")
    print()
    
    if result['sample_leads']:
        print("Sample Leads (first 5):")
        for i, lead in enumerate(result['sample_leads'], 1):
            print(f"  {i}. {lead['name']} | {lead['phone_number']} | {lead['business_type']} | {lead['priority']}")
    
    if result['errors']:
        print(f"\nErrors ({len(result['errors'])}):")
        for err in result['errors']:
            print(f"  - {err}")
    
    if not dry_run and "db_stats" in result:
        stats = result['db_stats']
        print(f"\nDatabase Status:")
        print(f"  Total leads:   {stats['total_leads']}")
        print(f"  Callable now:  {stats['callable_now']}")
    
    print()
    print("Done." if not dry_run else "Dry run complete. No data was imported.")


if __name__ == "__main__":
    main()
