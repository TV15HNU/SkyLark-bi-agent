import pytest
from app.normalizer import (
    drop_embedded_header_rows,
    normalize_status,
    normalize_date,
    normalize_sector,
    resolve_sector_filter,
    parse_quantity,
    reconcile_work_order_status,
    compute_data_quality_report,
)

def test_drop_embedded_header_rows():
    sample_data = [
        {"Deal Name": "Naruto", "Deal Status": "Won", "Sector/service": "Mining"},
        {"Deal Name": "Deal Name", "Deal Status": "Deal Status", "Sector/service": "Sector/service"},
        {"Deal Name": "Sasuke", "Deal Status": "Open", "Sector/service": "Renewables"},
        {"Deal Name": "Header", "Deal Status": "Deal Status", "Sector/service": "Mining"},
    ]
    cleaned, dropped, notes = drop_embedded_header_rows(sample_data)
    assert dropped == 2
    assert len(cleaned) == 2
    assert cleaned[0]["Deal Name"] == "Naruto"
    assert cleaned[1]["Deal Name"] == "Sasuke"
    assert "Filtered 2 duplicate embedded header rows" in notes[0]

def test_normalize_status():
    assert normalize_status("open", "deal") == "Open"
    assert normalize_status("WON", "deal") == "Won"
    assert normalize_status("Closed Lost", "deal") == "Dead"
    assert normalize_status("On Hold", "deal") == "On Hold"
    assert normalize_status(None, "deal") == "Unknown"
    assert normalize_status("", "deal") == "Unknown"

    # Work order execution statuses
    assert normalize_status("Executed until current month", "work_order") == "Ongoing"
    assert normalize_status("Completed", "work_order") == "Completed"
    assert normalize_status("Pause / struck", "work_order") == "Paused / Stuck"
    assert normalize_status("Details pending from Client", "work_order") == "Pending Client Details"

def test_normalize_date():
    iso, valid = normalize_date("2025-12-26 00:00:00")
    assert iso == "2025-12-26"
    assert valid is True

    iso2, valid2 = normalize_date("14/10/2025")
    assert valid2 is True

    iso3, valid3 = normalize_date(None)
    assert iso3 is None
    assert valid3 is True

    iso4, valid4 = normalize_date("invalid-date-string-xyz")
    assert iso4 is None
    assert valid4 is False

def test_normalize_sector():
    assert normalize_sector("renewables") == "Renewables"
    assert normalize_sector("  MINING  ") == "Mining"
    assert normalize_sector("solar") == "Renewables"
    assert normalize_sector("powerline") == "Powerline"
    assert normalize_sector(None) == "Unclassified"
    assert normalize_sector("") == "Unclassified"

def test_resolve_sector_filter():
    energy_sectors = resolve_sector_filter(["energy"])
    assert "Mining" in energy_sectors
    assert "Renewables" in energy_sectors
    assert "Powerline" in energy_sectors

    single_sector = resolve_sector_filter(["railways"])
    assert single_sector == ["Railways"]

def test_parse_quantity():
    # Unit embedded strings
    num, unit, valid = parse_quantity("5360 HA")
    assert num == 5360.0
    assert unit == "HA"
    assert valid is True

    num2, unit2, valid2 = parse_quantity("105 Towers")
    assert num2 == 105.0
    assert unit2 == "Towers"
    assert valid2 is True

    num3, unit3, valid3 = parse_quantity("45days")
    assert num3 == 45.0
    assert unit3 == "days"
    assert valid3 is True

    num4, unit4, valid4 = parse_quantity("1")
    assert num4 == 1.0
    assert unit4 is None
    assert valid4 is True

    num5, unit5, valid5 = parse_quantity(None)
    assert num5 is None
    assert unit5 is None
    assert valid5 is True

def test_reconcile_work_order_status():
    # Priority test: Collection status overrides execution status
    row1 = {
        "Collection status": "Payment Received",
        "Billing Status": "Update Required",
        "Invoice Status": "Fully Billed",
        "WO Status (billed)": "Closed",
        "Execution Status": "Ongoing"
    }
    rec1 = reconcile_work_order_status(row1)
    assert rec1["authoritative_source"] == "Collection status"
    assert rec1["reconciled_status"] == "Payment Received"
    assert rec1["status_category"] == "Completed & Collected"

    # Fallback to Billing Status
    row2 = {
        "Collection status": None,
        "Billing Status": "Update Required",
        "Invoice Status": "Partially Billed",
        "WO Status (billed)": "Open",
        "Execution Status": "Ongoing"
    }
    rec2 = reconcile_work_order_status(row2)
    assert rec2["authoritative_source"] == "Billing Status"
    assert rec2["reconciled_status"] == "Update Required"
    assert rec2["status_category"] == "Attention Required"

    # Fallback to Execution Status
    row3 = {
        "Collection status": None,
        "Billing Status": None,
        "Invoice Status": None,
        "WO Status (billed)": None,
        "Execution Status": "Ongoing"
    }
    rec3 = reconcile_work_order_status(row3)
    assert rec3["authoritative_source"] == "Execution Status"
    assert rec3["reconciled_status"] == "Ongoing"
    assert rec3["status_category"] == "Active Execution"

def test_compute_data_quality_report():
    sample_deals = [
        {"Deal Name": "D1", "Deal Status": "Won", "Closure Probability": 0.8, "Masked Deal value": 500000, "Sector/service": "Mining"},
        {"Deal Name": "D2", "Deal Status": "Open", "Closure Probability": None, "Masked Deal value": None, "Sector/service": "Renewables"},
        {"Deal Name": "D3", "Deal Status": "Open", "Closure Probability": None, "Masked Deal value": 300000, "Sector/service": None},
    ]
    sample_wo = [
        {"Deal name masked": "D1", "Sector": "Mining", "Execution Status": "Completed", "Collected Amount in Rupees (Incl of GST.) (Masked)": None},
        {"Deal name masked": "D2", "Sector": "Renewables", "Execution Status": "Ongoing", "Collected Amount in Rupees (Incl of GST.) (Masked)": 200000},
    ]
    report = compute_data_quality_report(sample_deals, sample_wo)
    assert "deals_board" in report
    assert "work_orders_board" in report
    assert report["deals_board"]["total_records"] == 3
    assert report["work_orders_board"]["total_records"] == 2
    # Check that caveats are generated
    assert len(report["deals_board"]["caveats"]) > 0
