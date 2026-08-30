import os
import time
import logging
import httpx
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
from app.config import settings
from app.normalizer import drop_embedded_header_rows

logger = logging.getLogger("monday_client")
logging.basicConfig(level=logging.INFO)

class MondayAPIError(Exception):
    """Custom exception raised when Monday.com API returns errors or fails."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details

class CacheEntry:
    def __init__(self, data: List[Dict[str, Any]], source: str, ttl_seconds: int = 120):
        self.data = data
        self.source = source  # 'monday_api' or 'local_fallback'
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds

    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds

    @property
    def age_seconds(self) -> int:
        return int(time.time() - self.created_at)

class MondayClient:
    def __init__(self):
        self.api_url = settings.MONDAY_API_URL
        self.api_token = settings.MONDAY_API_TOKEN
        self.deals_board_id = settings.DEALS_BOARD_ID
        self.work_orders_board_id = settings.WORK_ORDERS_BOARD_ID
        self.cache_ttl = settings.CACHE_TTL_SECONDS
        self._cache: Dict[str, CacheEntry] = {}

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": self.api_token,
            "Content-Type": "application/json",
            "API-Version": "2024-01",
        }

    async def test_connection(self) -> Dict[str, Any]:
        """
        Tests the Monday.com API token and board accessibility.
        """
        if not self.api_token:
            return {
                "status": "unconfigured",
                "message": "MONDAY_API_TOKEN is not set. Operating in local resilient dataset mode.",
                "connected": False,
                "boards": {
                    "deals_board_id": self.deals_board_id or "local_deals_fallback",
                    "work_orders_board_id": self.work_orders_board_id or "local_wo_fallback"
                }
            }

        query = """
        query {
            me {
                id
                name
                email
            }
        }
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    self.api_url,
                    json={"query": query},
                    headers=self._get_headers()
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "errors" in data:
                        return {
                            "status": "error",
                            "connected": False,
                            "message": f"Monday API Error: {data['errors'][0].get('message', 'Unknown')}",
                            "details": data["errors"]
                        }
                    user_info = data.get("data", {}).get("me", {})
                    return {
                        "status": "connected",
                        "connected": True,
                        "user": user_info,
                        "message": f"Connected to monday.com as {user_info.get('name', 'User')}"
                    }
                else:
                    return {
                        "status": "error",
                        "connected": False,
                        "status_code": resp.status_code,
                        "message": f"HTTP {resp.status_code}: {resp.text}"
                    }
        except Exception as e:
            return {
                "status": "error",
                "connected": False,
                "message": f"Failed to connect to monday.com: {str(e)}"
            }

    async def fetch_board_items_api(self, board_id: str) -> List[Dict[str, Any]]:
        """
        Fetches all items from a monday.com board using GraphQL items_page cursor pagination.
        Flattens column_values into dicts.
        """
        if not self.api_token or not board_id:
            raise MondayAPIError("Monday API Token or Board ID is missing")

        all_items: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        has_more = True

        async with httpx.AsyncClient(timeout=20.0) as client:
            while has_more:
                if cursor:
                    query = """
                    query ($cursor: String!) {
                        next_items_page (cursor: $cursor, limit: 100) {
                            cursor
                            items {
                                id
                                name
                                column_values {
                                    id
                                    text
                                    value
                                    column {
                                        title
                                    }
                                }
                            }
                        }
                    }
                    """
                    variables = {"cursor": cursor}
                else:
                    query = """
                    query ($boardId: [ID!]) {
                        boards (ids: $boardId) {
                            name
                            items_page (limit: 100) {
                                cursor
                                items {
                                    id
                                    name
                                    column_values {
                                        id
                                        text
                                        value
                                        column {
                                            title
                                        }
                                    }
                                }
                            }
                        }
                    }
                    """
                    variables = {"boardId": [board_id]}

                try:
                    resp = await client.post(
                        self.api_url,
                        json={"query": query, "variables": variables},
                        headers=self._get_headers()
                    )
                except Exception as ex:
                    raise MondayAPIError(f"Network error querying monday.com: {str(ex)}")

                if resp.status_code != 200:
                    raise MondayAPIError(f"Monday API returned HTTP {resp.status_code}: {resp.text}", status_code=resp.status_code)

                body = resp.json()
                if "errors" in body:
                    raise MondayAPIError(f"GraphQL Errors: {body['errors'][0].get('message')}", details=body["errors"])

                if cursor:
                    page_data = body.get("data", {}).get("next_items_page", {})
                else:
                    boards = body.get("data", {}).get("boards", [])
                    if not boards:
                        raise MondayAPIError(f"Board ID {board_id} not found in monday.com")
                    page_data = boards[0].get("items_page", {})

                items = page_data.get("items", [])
                for item in items:
                    flattened = {"id": item.get("id"), "Item Name": item.get("name")}
                    for col in item.get("column_values", []):
                        col_title = col.get("column", {}).get("title") or col.get("id")
                        flattened[col_title] = col.get("text")
                    all_items.append(flattened)

                cursor = page_data.get("cursor")
                if not cursor or len(items) == 0:
                    has_more = False

        return all_items

    def load_local_fallback_data(self, board_type: str) -> List[Dict[str, Any]]:
        """
        Loads the clean dataset from local CSV/Excel files as a zero-setup fallback.
        """
        csv_filename = "deals_for_monday_import.csv" if board_type == "deals" else "work_orders_for_monday_import.csv"
        csv_path = settings.DATA_DIR / csv_filename
        
        if not csv_path.exists():
            # Fallback to reading raw excel
            if board_type == "deals":
                excel_path = settings.BASE_DIR.parent / "Deal funnel Data.xlsx"
                df = pd.read_excel(excel_path)
            else:
                excel_path = settings.BASE_DIR.parent / "Work_Order_Tracker Data.xlsx"
                df = pd.read_excel(excel_path, header=1)
        else:
            df = pd.read_csv(csv_path)

        # Replace NaN with None
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")
        from app.json_utils import sanitize_for_json
        return sanitize_for_json(records)

    async def get_deals(self, force_refresh: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Retrieves Deals items from Monday.com API with TTL caching and local fallback.
        Returns (items, metadata).
        """
        cache_key = f"deals_{self.deals_board_id or 'default'}"
        
        # Check cache
        if not force_refresh and cache_key in self._cache and not self._cache[cache_key].is_expired():
            entry = self._cache[cache_key]
            return entry.data, {
                "source": entry.source,
                "cached": True,
                "age_seconds": entry.age_seconds,
                "ttl_seconds": entry.ttl_seconds,
            }

        items: List[Dict[str, Any]] = []
        source = "monday_api"

        if self.api_token and self.deals_board_id:
            try:
                items = await self.fetch_board_items_api(self.deals_board_id)
                logger.info(f"Successfully fetched {len(items)} deals from monday.com API")
            except Exception as e:
                logger.warning(f"Monday.com API fetch failed: {e}. Gracefully falling back to cached/local data.")
                items = self.load_local_fallback_data("deals")
                source = "local_fallback"
        else:
            items = self.load_local_fallback_data("deals")
            source = "local_fallback"

        # Apply normalizer drop embedded headers
        cleaned_items, dropped_count, notes = drop_embedded_header_rows(items)

        # Store in cache
        self._cache[cache_key] = CacheEntry(cleaned_items, source, self.cache_ttl)

        return cleaned_items, {
            "source": source,
            "cached": False,
            "age_seconds": 0,
            "ttl_seconds": self.cache_ttl,
            "dropped_header_rows": dropped_count,
            "normalization_notes": notes
        }

    async def get_work_orders(self, force_refresh: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Retrieves Work Orders items from Monday.com API with TTL caching and local fallback.
        Returns (items, metadata).
        """
        cache_key = f"work_orders_{self.work_orders_board_id or 'default'}"
        
        # Check cache
        if not force_refresh and cache_key in self._cache and not self._cache[cache_key].is_expired():
            entry = self._cache[cache_key]
            return entry.data, {
                "source": entry.source,
                "cached": True,
                "age_seconds": entry.age_seconds,
                "ttl_seconds": entry.ttl_seconds,
            }

        items: List[Dict[str, Any]] = []
        source = "monday_api"

        if self.api_token and self.work_orders_board_id:
            try:
                items = await self.fetch_board_items_api(self.work_orders_board_id)
                logger.info(f"Successfully fetched {len(items)} work orders from monday.com API")
            except Exception as e:
                logger.warning(f"Monday.com API fetch failed: {e}. Gracefully falling back to cached/local data.")
                items = self.load_local_fallback_data("work_orders")
                source = "local_fallback"
        else:
            items = self.load_local_fallback_data("work_orders")
            source = "local_fallback"

        cleaned_items, dropped_count, notes = drop_embedded_header_rows(items)

        self._cache[cache_key] = CacheEntry(cleaned_items, source, self.cache_ttl)

        return cleaned_items, {
            "source": source,
            "cached": False,
            "age_seconds": 0,
            "ttl_seconds": self.cache_ttl,
            "dropped_header_rows": dropped_count,
            "normalization_notes": notes
        }

    def clear_cache(self):
        self._cache.clear()

monday_client = MondayClient()
