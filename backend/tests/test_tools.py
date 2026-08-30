import pytest
import asyncio
from app.tools import (
    get_deals,
    get_work_orders,
    join_deals_and_work_orders,
    get_data_quality_summary,
    draft_leadership_update,
)

@pytest.mark.asyncio
async def test_get_deals_basic():
    res = await get_deals()
    assert res["matched_count"] > 0
    assert "aggregations" in res
    assert res["aggregations"]["total_open_pipeline_value"] >= 0
    assert "data_quality_notes" in res
    assert len(res["data_quality_notes"]) > 0

@pytest.mark.asyncio
async def test_get_deals_sector_filter():
    # Test energy macro filter
    res = await get_deals(sectors=["energy"])
    assert res["matched_count"] > 0
    for d in res["deals"]:
        assert d["sector"] in ["Mining", "Renewables", "Powerline"]

@pytest.mark.asyncio
async def test_get_work_orders_basic():
    res = await get_work_orders()
    assert res["matched_count"] > 0
    assert "financial_summary" in res
    assert res["financial_summary"]["total_contract_value"] > 0
    assert "status_category_breakdown" in res["financial_summary"]

@pytest.mark.asyncio
async def test_join_deals_and_work_orders():
    res = await join_deals_and_work_orders()
    assert res["matched_deals_count"] > 0
    assert res["deals_without_work_orders_count"] > 0
    assert res["orphaned_work_orders_count"] > 0
    assert "join_fragility_analysis" in res

@pytest.mark.asyncio
async def test_get_data_quality_summary():
    res = await get_data_quality_summary()
    assert "deals_board" in res
    assert "work_orders_board" in res
    assert "summary_banner" in res

@pytest.mark.asyncio
async def test_draft_leadership_update():
    res = await draft_leadership_update(scope="overall", period="Q3 2026")
    assert "headline_kpis" in res
    assert len(res["top_3_risks"]) == 3
    assert "markdown_export" in res
    assert "Skylark Drones" in res["markdown_export"]
