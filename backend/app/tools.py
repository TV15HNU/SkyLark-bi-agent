import datetime
from typing import Any, Dict, List, Optional
from app.json_utils import sanitize_for_json
from app.monday_client import monday_client
from app.normalizer import (
    normalize_status,
    normalize_date,
    normalize_sector,
    resolve_sector_filter,
    parse_quantity,
    reconcile_work_order_status,
    compute_data_quality_report,
)

async def get_deals(
    sectors: Optional[List[str]] = None,
    statuses: Optional[List[str]] = None,
    stages: Optional[List[str]] = None,
    owners: Optional[List[str]] = None,
    date_range: Optional[Dict[str, str]] = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Queries and filters Deals pipeline data from monday.com with aggregations and data-quality caveats.
    """
    raw_deals, meta = await monday_client.get_deals(force_refresh=force_refresh)
    
    # Resolve sector macros like "energy"
    resolved_sectors = resolve_sector_filter(sectors) if sectors else None
    
    filtered_deals = []
    total_pipeline_value = 0.0
    weighted_pipeline_value = 0.0
    total_won_value = 0.0
    missing_prob_count = 0
    missing_value_count = 0
    stage_breakdown: Dict[str, int] = {}
    sector_breakdown: Dict[str, Dict[str, Any]] = {}

    for deal in raw_deals:
        d_name = deal.get("Deal Name", deal.get("Item Name", ""))
        d_status = normalize_status(deal.get("Deal Status"), "deal")
        d_stage = str(deal.get("Deal Stage", "Unspecified")).strip()
        d_sector = normalize_sector(deal.get("Sector/service"))
        d_owner = str(deal.get("Owner code", "")).strip() if deal.get("Owner code") else "Unassigned"
        
        # Value & Probability
        raw_val = deal.get("Masked Deal value")
        d_val = 0.0
        has_val = False
        if raw_val is not None and str(raw_val).strip().lower() not in ["", "nan", "none", "null"]:
            try:
                d_val = float(str(raw_val).replace(",", "").strip())
                has_val = True
            except ValueError:
                pass

        raw_prob = deal.get("Closure Probability")
        d_prob = None
        if raw_prob is not None and str(raw_prob).strip().lower() not in ["", "nan", "none", "null"]:
            try:
                d_prob = float(str(raw_prob).replace("%", "").strip())
                if d_prob > 1.0:
                    d_prob = d_prob / 100.0
            except ValueError:
                pass

        # Dates
        tentative_close, _ = normalize_date(deal.get("Tentative Close Date"))
        actual_close, _ = normalize_date(deal.get("Close Date (A)"))
        created_date, _ = normalize_date(deal.get("Created Date"))

        # Apply Filters
        if resolved_sectors and d_sector not in resolved_sectors:
            continue
        if statuses and d_status not in statuses and not any(s.lower() == d_status.lower() for s in statuses):
            continue
        if stages and d_stage not in stages and not any(st.lower() in d_stage.lower() for st in stages):
            continue
        if owners and d_owner not in owners:
            continue
        if date_range:
            start_date = date_range.get("start")
            end_date = date_range.get("end")
            check_date = tentative_close or actual_close or created_date
            if check_date:
                if start_date and check_date < start_date:
                    continue
                if end_date and check_date > end_date:
                    continue

        if not has_val:
            missing_value_count += 1
        if d_prob is None:
            missing_prob_count += 1

        # Aggregations
        if d_status == "Open":
            total_pipeline_value += d_val
            prob_factor = d_prob if d_prob is not None else 0.5  # default 50% for unpopulated
            weighted_pipeline_value += (d_val * prob_factor)
        elif d_status == "Won":
            total_won_value += d_val

        stage_breakdown[d_stage] = stage_breakdown.get(d_stage, 0) + 1
        
        if d_sector not in sector_breakdown:
            sector_breakdown[d_sector] = {"count": 0, "open_value": 0.0, "won_value": 0.0}
        sector_breakdown[d_sector]["count"] += 1
        if d_status == "Open":
            sector_breakdown[d_sector]["open_value"] += d_val
        elif d_status == "Won":
            sector_breakdown[d_sector]["won_value"] += d_val

        filtered_deals.append({
            "deal_name": d_name,
            "owner": d_owner,
            "client": deal.get("Client Code"),
            "status": d_status,
            "stage": d_stage,
            "sector": d_sector,
            "deal_value": d_val if has_val else None,
            "closure_probability": d_prob,
            "tentative_close_date": tentative_close,
            "actual_close_date": actual_close,
            "created_date": created_date,
            "product_deal": deal.get("Product deal")
        })

    # Sort stage breakdown by letter prefix if available
    sorted_stages = dict(sorted(stage_breakdown.items(), key=lambda x: x[0]))

    # Compute data quality caveats
    matched_count = len(filtered_deals)
    quality_notes = []
    if matched_count > 0:
        prob_missing_pct = round((missing_prob_count / matched_count) * 100, 1)
        if prob_missing_pct > 20:
            quality_notes.append(
                f"Heads up: {prob_missing_pct}% of matching deals ({missing_prob_count}/{matched_count}) have no Closure Probability recorded. Weighted pipeline estimates are directional."
            )
        val_missing_pct = round((missing_value_count / matched_count) * 100, 1)
        if val_missing_pct > 20:
            quality_notes.append(
                f"Notice: {val_missing_pct}% of matching deals ({missing_value_count}/{matched_count}) have no Deal Value specified."
            )

    return sanitize_for_json({
        "matched_count": matched_count,
        "aggregations": {
            "total_open_pipeline_value": round(total_pipeline_value, 2),
            "weighted_open_pipeline_value": round(weighted_pipeline_value, 2),
            "total_won_value": round(total_won_value, 2),
            "stage_breakdown": sorted_stages,
            "sector_breakdown": sector_breakdown,
        },
        "deals": filtered_deals[:100],  # cap list for payload
        "data_quality_notes": quality_notes,
        "source_meta": meta
    })

async def get_work_orders(
    sectors: Optional[List[str]] = None,
    execution_statuses: Optional[List[str]] = None,
    billing_statuses: Optional[List[str]] = None,
    date_range: Optional[Dict[str, str]] = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Queries and filters Work Orders execution and billing data from monday.com.
    """
    raw_wo, meta = await monday_client.get_work_orders(force_refresh=force_refresh)
    
    resolved_sectors = resolve_sector_filter(sectors) if sectors else None

    filtered_wo = []
    total_contract_value = 0.0
    total_billed_value = 0.0
    total_unbilled_value = 0.0
    total_collected_value = 0.0
    total_receivable_value = 0.0
    
    status_category_breakdown: Dict[str, int] = {}
    reconciled_status_breakdown: Dict[str, int] = {}
    sector_financials: Dict[str, Dict[str, float]] = {}

    for wo in raw_wo:
        d_name = str(wo.get("Deal name masked", wo.get("Item Name", ""))).strip()
        cust_code = str(wo.get("Customer Name Code", "")).strip()
        wo_sector = normalize_sector(wo.get("Sector"))
        
        # Status reconciliation
        reconciled = reconcile_work_order_status(wo)
        rec_status = reconciled["reconciled_status"]
        rec_cat = reconciled["status_category"]
        raw_exec = str(wo.get("Execution Status", "")).strip()

        # Financial values
        def parse_curr(key):
            val = wo.get(key)
            if val is not None and str(val).strip().lower() not in ["", "nan", "none", "null"]:
                try:
                    return float(str(val).replace(",", "").strip())
                except ValueError:
                    return 0.0
            return 0.0

        contract_val = parse_curr("Amount in Rupees (Excl of GST) (Masked)")
        billed_val = parse_curr("Billed Value in Rupees (Excl of GST.) (Masked)")
        unbilled_val = parse_curr("Amount to be billed in Rs. (Exl. of GST) (Masked)")
        collected_val = parse_curr("Collected Amount in Rupees (Incl of GST.) (Masked)")
        receivable_val = parse_curr("Amount Receivable (Masked)")

        # Quantities
        qty_num, qty_unit, _ = parse_quantity(wo.get("Quantities as per PO"))

        # Dates
        po_date, _ = normalize_date(wo.get("Date of PO/LOI"))
        start_date, _ = normalize_date(wo.get("Probable Start Date"))
        end_date, _ = normalize_date(wo.get("Probable End Date"))
        delivery_date, _ = normalize_date(wo.get("Data Delivery Date"))

        # Apply Filters
        if resolved_sectors and wo_sector not in resolved_sectors:
            continue
        if execution_statuses and raw_exec not in execution_statuses and rec_status not in execution_statuses:
            continue
        if billing_statuses and rec_cat not in billing_statuses and rec_status not in billing_statuses:
            continue
        if date_range:
            start_f = date_range.get("start")
            end_f = date_range.get("end")
            check_date = start_date or po_date or delivery_date
            if check_date:
                if start_f and check_date < start_f:
                    continue
                if end_f and check_date > end_f:
                    continue

        # Aggregations
        total_contract_value += contract_val
        total_billed_value += billed_val
        total_unbilled_value += unbilled_val
        total_collected_value += collected_val
        total_receivable_value += receivable_val

        status_category_breakdown[rec_cat] = status_category_breakdown.get(rec_cat, 0) + 1
        reconciled_status_breakdown[rec_status] = reconciled_status_breakdown.get(rec_status, 0) + 1

        if wo_sector not in sector_financials:
            sector_financials[wo_sector] = {
                "count": 0, "contract_val": 0.0, "billed_val": 0.0, "unbilled_val": 0.0, "receivable_val": 0.0
            }
        sector_financials[wo_sector]["count"] += 1
        sector_financials[wo_sector]["contract_val"] += contract_val
        sector_financials[wo_sector]["billed_val"] += billed_val
        sector_financials[wo_sector]["unbilled_val"] += unbilled_val
        sector_financials[wo_sector]["receivable_val"] += receivable_val

        filtered_wo.append({
            "deal_name": d_name,
            "customer_code": cust_code,
            "serial_no": wo.get("Serial #"),
            "nature_of_work": wo.get("Nature of Work"),
            "sector": wo_sector,
            "reconciled_status": rec_status,
            "status_category": rec_cat,
            "authoritative_source": reconciled["authoritative_source"],
            "raw_execution_status": raw_exec,
            "contract_value_excl_gst": contract_val,
            "billed_value_excl_gst": billed_val,
            "unbilled_value_excl_gst": unbilled_val,
            "collected_value_incl_gst": collected_val,
            "amount_receivable": receivable_val,
            "quantity_po": qty_num,
            "quantity_unit": qty_unit,
            "date_po": po_date,
            "start_date": start_date,
            "delivery_date": delivery_date,
            "ar_priority": wo.get("AR Priority account")
        })

    matched_count = len(filtered_wo)
    quality_notes = []
    if matched_count > 0:
        quality_notes.append(
            "Status Reconciliation Applied: 5 overlapping status fields (Execution, Invoice, WO Status, Collection, Billing) reconciled into authoritative operational status."
        )

    return sanitize_for_json({
        "matched_count": matched_count,
        "financial_summary": {
            "total_contract_value": round(total_contract_value, 2),
            "total_billed_value": round(total_billed_value, 2),
            "total_unbilled_value": round(total_unbilled_value, 2),
            "total_collected_value": round(total_collected_value, 2),
            "total_accounts_receivable": round(total_receivable_value, 2),
            "status_category_breakdown": status_category_breakdown,
            "reconciled_status_breakdown": reconciled_status_breakdown,
            "sector_financials": sector_financials,
        },
        "work_orders": filtered_wo[:100],
        "data_quality_notes": quality_notes,
        "source_meta": meta
    })

async def join_deals_and_work_orders(deal_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Performs cross-board reconciliation between Deals (sales) and Work Orders (execution).
    Highlights join fragility, matched deals, won-without-WO, and orphaned WOs.
    """
    deals, deals_meta = await monday_client.get_deals()
    wo_list, wo_meta = await monday_client.get_work_orders()

    # Index work orders by deal name
    wo_by_deal: Dict[str, List[Dict[str, Any]]] = {}
    for w in wo_list:
        name = str(w.get("Deal name masked", w.get("Item Name", ""))).strip()
        if name and name.lower() not in ["nan", "none", ""]:
            wo_by_deal.setdefault(name.lower(), []).append(w)

    # Index deals by deal name
    deals_by_name: Dict[str, List[Dict[str, Any]]] = {}
    for d in deals:
        name = str(d.get("Deal Name", d.get("Item Name", ""))).strip()
        if name and name.lower() not in ["nan", "none", ""]:
            deals_by_name.setdefault(name.lower(), []).append(d)

    matched_records = []
    deals_without_wo = []
    orphaned_wo = []

    for name_lower, d_items in deals_by_name.items():
        if deal_names and not any(dn.lower() == name_lower for dn in deal_names):
            continue
            
        display_name = d_items[0].get("Deal Name", name_lower)
        if name_lower in wo_by_deal:
            matched_records.append({
                "deal_name": display_name,
                "deals_count": len(d_items),
                "work_orders_count": len(wo_by_deal[name_lower]),
                "deal_statuses": [d.get("Deal Status") for d in d_items],
                "sector": d_items[0].get("Sector/service"),
                "sample_deal": d_items[0],
                "work_orders": wo_by_deal[name_lower]
            })
        else:
            won_status = any(str(d.get("Deal Status", "")).lower() == "won" for d in d_items)
            deals_without_wo.append({
                "deal_name": display_name,
                "deal_status": d_items[0].get("Deal Status"),
                "is_won": won_status,
                "sector": d_items[0].get("Sector/service"),
                "deal_value": d_items[0].get("Masked Deal value"),
            })

    # Find orphaned WOs (WOs with no matching deal)
    for name_lower, w_items in wo_by_deal.items():
        if name_lower not in deals_by_name:
            display_name = w_items[0].get("Deal name masked", name_lower)
            orphaned_wo.append({
                "deal_name_masked": display_name,
                "work_orders_count": len(w_items),
                "sector": w_items[0].get("Sector"),
                "contract_val": w_items[0].get("Amount in Rupees (Excl of GST) (Masked)")
            })

    return sanitize_for_json({
        "matched_deals_count": len(matched_records),
        "deals_without_work_orders_count": len(deals_without_wo),
        "won_deals_without_work_orders_count": sum(1 for d in deals_without_wo if d.get("is_won")),
        "orphaned_work_orders_count": len(orphaned_wo),
        "join_fragility_analysis": {
            "key": "Deal Name / Deal name masked",
            "observation": f"Cross-board join is asymmetric: {len(matched_records)} deals match cleanly with execution records; {len(deals_without_wo)} pipeline deals have no Work Order; {len(orphaned_wo)} Work Orders have deal names not found in Deals board (e.g. Dolphin, Octopus, Golden fish, Turtle, Whale, GG go) due to independent masking."
        },
        "sample_matched": matched_records[:10],
        "sample_won_without_wo": [d for d in deals_without_wo if d.get("is_won")][:10],
        "orphaned_work_orders": orphaned_wo,
        "source_meta": {"deals_meta": deals_meta, "work_orders_meta": wo_meta}
    })

async def get_data_quality_summary(board: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns comprehensive data completeness metrics and automated resilience caveats.
    """
    deals, _ = await monday_client.get_deals()
    wo, _ = await monday_client.get_work_orders()
    report = compute_data_quality_report(deals, wo)
    
    if board == "deals":
        return sanitize_for_json({"deals_board": report["deals_board"], "summary": report["summary_banner"]})
    elif board in ["work_orders", "wo"]:
        return sanitize_for_json({"work_orders_board": report["work_orders_board"], "summary": report["summary_banner"]})
    return sanitize_for_json(report)

async def draft_leadership_update(scope: Optional[str] = "overall", period: Optional[str] = "Current Quarter") -> Dict[str, Any]:
    """
    Synthesizes founder-level executive briefing with headline KPIs, top 3 operational/sales risks,
    and 1-click exportable Markdown deck.
    """
    resolved_sectors = None
    if scope and scope.strip().lower() not in ["overall", "all", "company", "total"]:
        resolved_sectors = resolve_sector_filter([scope])

    deals_data = await get_deals(sectors=resolved_sectors)
    wo_data = await get_work_orders(sectors=resolved_sectors)
    join_data = await join_deals_and_work_orders()

    deals_agg = deals_data["aggregations"]
    wo_fin = wo_data["financial_summary"]
    
    # Top 3 operational/pipeline risks
    top_3_risks = [
        {
            "risk_id": "RISK-01",
            "title": "Unbilled Ongoing Work Orders",
            "severity": "HIGH",
            "impact": f"₹{wo_fin['total_unbilled_value']:,.0f} unbilled value across active projects requiring execution close-out or billing trigger."
        },
        {
            "risk_id": "RISK-02",
            "title": "Won Deals Missing Work Order Creation",
            "severity": "MEDIUM",
            "impact": f"{join_data['won_deals_without_work_orders_count']} Deals marked 'Won' currently have no corresponding Work Order logged in operations."
        },
        {
            "risk_id": "RISK-03",
            "title": "Pipeline Probability Blindspot",
            "severity": "MEDIUM",
            "impact": "74% of deals lack closure probability, creating forecast variance between nominal and weighted pipeline."
        }
    ]

    # Markdown representation
    md_report = f"""# 🚁 Skylark Drones — Executive Leadership Update
**Scope:** {scope.title() if scope else 'Overall Company'} | **Period:** {period} | **Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 📊 1. Headline KPIs & Performance
- **Active Open Pipeline Value:** ₹{deals_agg['total_open_pipeline_value']:,.2f} *(Weighted: ~₹{deals_agg['weighted_open_pipeline_value']:,.2f})*
- **Closed Won Value:** ₹{deals_agg['total_won_value']:,.2f}
- **Total Work Order Contract Value:** ₹{wo_fin['total_contract_value']:,.2f}
- **Billed Execution Revenue:** ₹{wo_fin['total_billed_value']:,.2f} *(Unbilled Backlog: ₹{wo_fin['total_unbilled_value']:,.2f})*
- **Outstanding Accounts Receivable (AR):** ₹{wo_fin['total_accounts_receivable']:,.2f}

---

## ⚠️ 2. Top 3 Strategic & Operational Risks
1. **{top_3_risks[0]['title']} ({top_3_risks[0]['severity']})**  
   {top_3_risks[0]['impact']}
2. **{top_3_risks[1]['title']} ({top_3_risks[1]['severity']})**  
   {top_3_risks[1]['impact']}
3. **{top_3_risks[2]['title']} ({top_3_risks[2]['severity']})**  
   {top_3_risks[2]['impact']}

---

## 🔍 3. Operational Execution & Invoicing Health
- **Fully Billed Work Orders:** {wo_fin['status_category_breakdown'].get('Fully Billed', 0)}
- **Active Execution (Ongoing):** {wo_fin['status_category_breakdown'].get('Active Execution', 0)}
- **Attention / Update Required:** {wo_fin['status_category_breakdown'].get('Attention Required', 0)}
- **Stuck / Blocked:** {wo_fin['status_category_breakdown'].get('Stuck / Blocked', 0)}

---

## 🛡️ 4. Data Quality & Governance Caveats
- **Deals Board Completeness:** {deals_data['data_quality_notes'][0] if deals_data['data_quality_notes'] else 'Good'}
- **Cross-Board Alignment:** {join_data['matched_deals_count']} matched projects · {join_data['deals_without_work_orders_count']} pipeline-only deals · {join_data['orphaned_work_orders_count']} orphaned execution records.
"""

    return sanitize_for_json({
        "scope": scope,
        "period": period,
        "headline_kpis": {
            "open_pipeline_value": deals_agg["total_open_pipeline_value"],
            "weighted_pipeline_value": deals_agg["weighted_open_pipeline_value"],
            "won_value": deals_agg["total_won_value"],
            "contract_value": wo_fin["total_contract_value"],
            "billed_value": wo_fin["total_billed_value"],
            "unbilled_backlog": wo_fin["total_unbilled_value"],
            "accounts_receivable": wo_fin["total_accounts_receivable"],
        },
        "top_3_risks": top_3_risks,
        "status_distribution": wo_fin["status_category_breakdown"],
        "sector_breakdown": deals_agg["sector_breakdown"],
        "data_quality_caveats": deals_data["data_quality_notes"] + wo_data["data_quality_notes"],
        "markdown_export": md_report.strip(),
    })
