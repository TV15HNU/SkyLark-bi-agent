import re
import datetime
from typing import Any, Dict, List, Optional, Tuple
from dateutil import parser as date_parser

# Known canonical sectors
CANONICAL_SECTORS = {
    "renewables": "Renewables",
    "renewable": "Renewables",
    "solar": "Renewables",
    "wind": "Renewables",
    "mining": "Mining",
    "mines": "Mining",
    "railways": "Railways",
    "railway": "Railways",
    "powerline": "Powerline",
    "powerlines": "Powerline",
    "power": "Powerline",
    "transmission": "Powerline",
    "construction": "Construction",
    "infra": "Construction",
    "infrastructure": "Construction",
    "aviation": "Aviation",
    "manufacturing": "Manufacturing",
    "tender": "Tender",
    "dsp": "DSP",
    "security and surveillance": "Security and Surveillance",
    "security": "Security and Surveillance",
    "others": "Others",
    "other": "Others",
}

# Sector Macro Groups (e.g. "energy" -> Mining + Renewables)
SECTOR_TAXONOMY_GROUPS = {
    "energy": ["Mining", "Renewables", "Powerline"],
    "energy sector": ["Mining", "Renewables", "Powerline"],
    "utilities": ["Powerline", "Renewables"],
    "infrastructure": ["Railways", "Construction", "Powerline"],
    "heavy industry": ["Mining", "Manufacturing"],
}

# Canonical Deal Statuses
CANONICAL_DEAL_STATUSES = {
    "open": "Open",
    "won": "Won",
    "closed won": "Won",
    "dead": "Dead",
    "lost": "Dead",
    "closed lost": "Dead",
    "on hold": "On Hold",
    "hold": "On Hold",
}

def drop_embedded_header_rows(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int, List[str]]:
    """
    Filters out mid-sheet duplicate header rows where column values equal header labels.
    Returns (cleaned_items, dropped_count, notes).
    """
    cleaned: List[Dict[str, Any]] = []
    dropped_count = 0
    header_markers = {
        "deal status", "sector/service", "deal stage", "masked deal value", 
        "owner code", "deal name masked", "execution status"
    }

    for item in items:
        # Check if row looks like an embedded header
        is_header_row = False
        for k, v in item.items():
            if v is not None and str(v).strip().lower() in header_markers and str(k).strip().lower() in header_markers:
                is_header_row = True
                break
        
        # Also verify if deal name is literally "Deal Name" or "Deal name masked"
        deal_name = str(item.get("Deal Name", item.get("Deal name masked", ""))).strip().lower()
        if deal_name in ["deal name", "deal name masked"]:
            is_header_row = True

        if is_header_row:
            dropped_count += 1
        else:
            cleaned.append(item)

    notes = []
    if dropped_count > 0:
        notes.append(f"Filtered {dropped_count} duplicate embedded header rows from dataset.")
        
    return cleaned, dropped_count, notes

def normalize_status(value: Any, column_type: str = "deal") -> str:
    """
    Normalizes status values to canonical enums. Unmapped values become 'Unknown'.
    """
    if value is None:
        return "Unknown"
    
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ["nan", "none", "null", ""]:
        return "Unknown"
    
    val_lower = val_str.lower()
    
    if column_type == "deal":
        return CANONICAL_DEAL_STATUSES.get(val_lower, val_str)
    
    # Work Order execution status synonyms
    if "complete" in val_lower or "finished" in val_lower or "done" in val_lower:
        return "Completed"
    if "ongoing" in val_lower or "in progress" in val_lower or "executed until" in val_lower:
        return "Ongoing"
    if "not started" in val_lower or "unassigned" in val_lower:
        return "Not Started"
    if "pause" in val_lower or "struck" in val_lower or "stuck" in val_lower or "block" in val_lower:
        return "Paused / Stuck"
    if "client" in val_lower and "pending" in val_lower:
        return "Pending Client Details"
    if "partial" in val_lower:
        return "Partially Completed"
        
    return val_str

def normalize_date(value: Any) -> Tuple[Optional[str], bool]:
    """
    Defensively parses dates across multiple formats.
    Returns (ISO_date_str 'YYYY-MM-DD', is_valid).
    """
    if value is None:
        return None, True
    
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ["nan", "none", "null", "nat", ""]:
        return None, True
    
    # Try parsing
    try:
        dt = date_parser.parse(val_str, default=datetime.datetime(2025, 1, 1))
        return dt.strftime("%Y-%m-%d"), True
    except Exception:
        # Try regex patterns like YYYY-MM-DD or DD/MM/YYYY
        date_match = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", val_str)
        if date_match:
            try:
                y, m, d = date_match.groups()
                dt = datetime.datetime(int(y), int(m), int(d))
                return dt.strftime("%Y-%m-%d"), True
            except Exception:
                pass
        return None, False

def normalize_sector(value: Any) -> str:
    """
    Normalizes sector name with whitespace stripping, alias matching, and fallback to 'Unclassified'.
    """
    if value is None:
        return "Unclassified"
    
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ["nan", "none", "null", ""]:
        return "Unclassified"
        
    val_lower = val_str.lower()
    return CANONICAL_SECTORS.get(val_lower, val_str.title())

def format_inr(val: float) -> str:
    """
    Formats a numeric amount into standard Indian Rupees (₹) with Lakh / Crore / Million annotations.
    """
    if val is None or val == 0:
        return "₹0"
    abs_val = abs(val)
    if abs_val >= 10000000:  # >= 1 Crore
        return f"₹{val / 10000000:.2f} Cr (₹{val:,.0f})"
    elif abs_val >= 100000:   # >= 1 Lakh
        return f"₹{val / 100000:.2f} L (₹{val:,.0f})"
    else:
        return f"₹{val:,.2f}"

def resolve_sector_filter(query_sectors: List[str]) -> List[str]:
    """
    Expands compound sector strings like 'Railways + Powerline' or macro terms like 'energy'
    to underlying canonical sectors.
    """
    if not query_sectors:
        return []
    resolved: set = set()
    for raw_item in query_sectors:
        if not raw_item:
            continue
        # Split on +, ,, &, and, /
        parts = re.split(r"[,+&/]|(?:\band\b)", str(raw_item), flags=re.IGNORECASE)
        for p in parts:
            s_clean = p.strip().lower()
            if not s_clean:
                continue
            if s_clean in SECTOR_TAXONOMY_GROUPS:
                resolved.update(SECTOR_TAXONOMY_GROUPS[s_clean])
            elif s_clean in CANONICAL_SECTORS:
                resolved.add(CANONICAL_SECTORS[s_clean])
            else:
                # Match partials
                matched = False
                for k, canon in CANONICAL_SECTORS.items():
                    if k in s_clean or s_clean in k:
                        resolved.add(canon)
                        matched = True
                        break
                if not matched:
                    resolved.add(p.strip().title())
    return sorted(list(resolved))

def parse_quantity(value: Any) -> Tuple[Optional[float], Optional[str], bool]:
    """
    Parses unit-embedded strings like '5360 HA', '105 Towers', '45days', '1'.
    Returns (numeric_value, unit, is_valid).
    """
    if value is None:
        return None, None, True
        
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ["nan", "none", "null", ""]:
        return None, None, True
        
    # Match patterns like: "5360 HA", "456.090 HA", "105 Towers", "45days", "1,400"
    match = re.match(r"^([\d,.]+)\s*([a-zA-Z/%]*)$", val_str)
    if match:
        num_part = match.group(1).replace(",", "")
        unit_part = match.group(2).strip() if match.group(2) else None
        try:
            num = float(num_part)
            return num, unit_part, True
        except ValueError:
            return None, val_str, False
            
    # Try extracting first number and rest as unit
    num_match = re.search(r"([\d,.]+)", val_str)
    if num_match:
        try:
            num = float(num_match.group(1).replace(",", ""))
            unit = val_str.replace(num_match.group(1), "").strip() or None
            return num, unit, True
        except ValueError:
            pass
            
    return None, val_str, False

def reconcile_work_order_status(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reconciles 5 overlapping status columns in Work Orders with documented hierarchical authority:
    Collection status > Billing Status > WO Status (billed) > Invoice Status > Execution Status.
    
    Returns structured dict with authoritative status, category, and audit trail.
    """
    def clean(val):
        if val is None:
            return ""
        s = str(val).strip()
        return "" if s.lower() in ["nan", "none", "null", ""] else s

    collection = clean(row.get("Collection status"))
    billing = clean(row.get("Billing Status"))
    wo_billed = clean(row.get("WO Status (billed)"))
    invoice = clean(row.get("Invoice Status"))
    execution = clean(row.get("Execution Status"))

    authoritative_source = "None"
    reconciled_status = "Unknown"
    status_category = "Active Execution"

    # Hierarchy Rule 1: Collection Status
    if collection:
        authoritative_source = "Collection status"
        reconciled_status = collection
        status_category = "Completed & Collected" if "collect" in collection.lower() or "received" in collection.lower() else "Collection Pending"
    # Hierarchy Rule 2: Billing Status
    elif billing:
        authoritative_source = "Billing Status"
        reconciled_status = billing
        if "update required" in billing.lower():
            status_category = "Attention Required"
        elif "not billable" in billing.lower():
            status_category = "Non-Billable"
        elif "stuck" in billing.lower():
            status_category = "Stuck / Blocked"
        elif "partially" in billing.lower():
            status_category = "Partially Billed"
        elif "billed" in billing.lower():
            status_category = "Fully Billed"
        else:
            status_category = "Billing In Progress"
    # Hierarchy Rule 3: Invoice Status
    elif invoice:
        authoritative_source = "Invoice Status"
        reconciled_status = invoice
        if "fully billed" in invoice.lower():
            status_category = "Fully Billed"
        elif "partially billed" in invoice.lower():
            status_category = "Partially Billed"
        elif "not billed" in invoice.lower():
            status_category = "Unbilled / Pending Invoice"
        elif "stuck" in invoice.lower():
            status_category = "Stuck / Blocked"
        else:
            status_category = "Invoicing Active"
    # Hierarchy Rule 4: WO Status (billed)
    elif wo_billed:
        authoritative_source = "WO Status (billed)"
        reconciled_status = f"WO {wo_billed}"
        status_category = "Closed / Inactive" if "close" in wo_billed.lower() else "Open WO"
    # Hierarchy Rule 5: Execution Status
    elif execution:
        authoritative_source = "Execution Status"
        reconciled_status = execution
        norm_exec = normalize_status(execution, "work_order")
        if norm_exec == "Completed":
            status_category = "Execution Done (Pending Invoicing)"
        elif norm_exec == "Ongoing":
            status_category = "Active Execution"
        elif norm_exec == "Not Started":
            status_category = "Not Started"
        elif norm_exec == "Paused / Stuck":
            status_category = "Stuck / Blocked"
        else:
            status_category = "Active Execution"

    return {
        "reconciled_status": reconciled_status,
        "status_category": status_category,
        "authoritative_source": authoritative_source,
        "raw_statuses": {
            "collection_status": collection or None,
            "billing_status": billing or None,
            "invoice_status": invoice or None,
            "wo_status_billed": wo_billed or None,
            "execution_status": execution or None,
        }
    }

def compute_data_quality_report(deals: List[Dict[str, Any]], work_orders: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes field completeness percentages, missing rates, and explicit executive caveats.
    """
    deals_total = len(deals)
    wo_total = len(work_orders)
    
    # Deals analysis
    deals_col_completeness = {}
    deals_caveats = []
    
    if deals_total > 0:
        key_deals_cols = [
            ("Deal Name", "deal_name"),
            ("Sector/service", "sector"),
            ("Deal Status", "status"),
            ("Deal Stage", "stage"),
            ("Masked Deal value", "deal_value"),
            ("Closure Probability", "closure_probability"),
            ("Close Date (A)", "actual_close_date"),
            ("Tentative Close Date", "tentative_close_date"),
            ("Owner code", "owner_code"),
            ("Created Date", "created_date"),
        ]
        
        for col_name, field_key in key_deals_cols:
            present_count = sum(1 for d in deals if d.get(col_name) is not None and str(d.get(col_name)).strip().lower() not in ["", "nan", "none", "null"])
            pct = round((present_count / deals_total) * 100, 1)
            deals_col_completeness[field_key] = {
                "column": col_name,
                "present_count": present_count,
                "total_count": deals_total,
                "completeness_pct": pct,
                "missing_pct": round(100 - pct, 1)
            }
            
        # Specific business caveats
        prob_comp = deals_col_completeness.get("closure_probability", {}).get("completeness_pct", 0)
        if prob_comp < 30:
            deals_caveats.append(
                f"⚠️ Data Resilience Notice: Closure Probability is unpopulated in {deals_col_completeness['closure_probability']['missing_pct']}% of deals ({deals_total - deals_col_completeness['closure_probability']['present_count']}/{deals_total} rows). Pipeline weighted value estimates are directional."
            )
            
        close_date_comp = deals_col_completeness.get("actual_close_date", {}).get("completeness_pct", 0)
        if close_date_comp < 15:
            deals_caveats.append(
                f"ℹ️ Actual Close Date is unrecorded for {deals_col_completeness['actual_close_date']['missing_pct']}% of deals. Projections utilize Tentative Close Dates."
            )
            
        val_comp = deals_col_completeness.get("deal_value", {}).get("completeness_pct", 0)
        if val_comp < 60:
            deals_caveats.append(
                f"⚠️ Deal Value is missing in {deals_col_completeness['deal_value']['missing_pct']}% of deal records. Deal count metrics are more reliable than aggregate values."
            )

    # Work orders analysis
    wo_col_completeness = {}
    wo_caveats = []
    
    if wo_total > 0:
        key_wo_cols = [
            ("Deal name masked", "deal_name"),
            ("Customer Name Code", "customer_code"),
            ("Sector", "sector"),
            ("Execution Status", "execution_status"),
            ("Invoice Status", "invoice_status"),
            ("WO Status (billed)", "wo_status_billed"),
            ("Billing Status", "billing_status"),
            ("Amount in Rupees (Excl of GST) (Masked)", "total_amount_excl_gst"),
            ("Billed Value in Rupees (Excl of GST.) (Masked)", "billed_amount"),
            ("Collected Amount in Rupees (Incl of GST.) (Masked)", "collected_amount"),
            ("Amount Receivable (Masked)", "amount_receivable"),
            ("Quantities as per PO", "quantities_po"),
            ("Data Delivery Date", "data_delivery_date"),
        ]
        
        for col_name, field_key in key_wo_cols:
            present_count = sum(1 for w in work_orders if w.get(col_name) is not None and str(w.get(col_name)).strip().lower() not in ["", "nan", "none", "null"])
            pct = round((present_count / wo_total) * 100, 1)
            wo_col_completeness[field_key] = {
                "column": col_name,
                "present_count": present_count,
                "total_count": wo_total,
                "completeness_pct": pct,
                "missing_pct": round(100 - pct, 1)
            }
            
        coll_comp = wo_col_completeness.get("collected_amount", {}).get("completeness_pct", 0)
        if coll_comp < 50:
            wo_caveats.append(
                f"⚠️ Collection details are missing in {wo_col_completeness['collected_amount']['missing_pct']}% of Work Orders. Cash flow metrics reflect partial reporting."
            )
            
        deliv_comp = wo_col_completeness.get("data_delivery_date", {}).get("completeness_pct", 0)
        if deliv_comp < 40:
            wo_caveats.append(
                f"ℹ️ Data Delivery Date is unpopulated for {wo_col_completeness['data_delivery_date']['missing_pct']}% of Work Orders."
            )

    # Calculate overall board completeness scores
    deals_overall = round(sum(c["completeness_pct"] for c in deals_col_completeness.values()) / max(len(deals_col_completeness), 1), 1) if deals_col_completeness else 0.0
    wo_overall = round(sum(c["completeness_pct"] for c in wo_col_completeness.values()) / max(len(wo_col_completeness), 1), 1) if wo_col_completeness else 0.0

    return {
        "deals_board": {
            "total_records": deals_total,
            "overall_completeness_pct": deals_overall,
            "columns": deals_col_completeness,
            "caveats": deals_caveats
        },
        "work_orders_board": {
            "total_records": wo_total,
            "overall_completeness_pct": wo_overall,
            "columns": wo_col_completeness,
            "caveats": wo_caveats
        },
        "summary_banner": f"Board completeness: Deals {deals_overall}% · Work Orders {wo_overall}%"
    }
