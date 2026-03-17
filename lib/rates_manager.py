"""
요금 데이터 관리자 (RatesManager)

GitHub 원본 저장소에서 rates.json을 가져오고,
Homey Settings에 캐시하여 오프라인 시에도 동작합니다.

데이터 흐름:
  GitHub (dugurs/kwh_to_won) → Homey Settings 캐시 → kwh2won_api
"""
import json
import logging
import asyncio
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

_LOGGER = logging.getLogger(__name__)

RATES_URL = (
    "https://raw.githubusercontent.com/dugurs/kwh_to_won/"
    "main/custom_components/kwh_to_won/rates.json"
)
SETTINGS_KEY_RATES = "cached_rates"
SETTINGS_KEY_UPDATED = "rates_updated_at"
SETTINGS_KEY_ETAG = "rates_etag"
CACHE_TTL_SEC = 24 * 60 * 60       # 24시간
MIN_FETCH_INTERVAL_SEC = 60 * 60    # 1시간 (throttle)
FETCH_TIMEOUT_SEC = 15

FALLBACK_PATH = Path(__file__).parent / "rates_fallback.json"

REQUIRED_KEYS = {"PRICE_BASE", "PRICE_KWH", "PRICE_ADJUSTMENT", "BASE_FUND", "PRICE_ELECBASIC", "PRICE_DC"}


class RatesManager:
    """요금 데이터를 GitHub에서 가져오고 캐시하는 관리자."""

    def __init__(self, homey=None, log_fn=None):
        self._homey = homey          # Homey 인스턴스 (settings 접근)
        self._log = log_fn or _LOGGER.info
        self._rates = None
        self._last_fetch_ts = 0.0
        self._refresh_task = None

    # ── Public API ──────────────────────────────────

    async def get_rates(self, force_refresh=False):
        """요금 데이터를 반환합니다. (메모리 → GitHub → 캐시 → fallback)"""
        if self._rates and not force_refresh:
            return self._rates

        # GitHub에서 fetch 시도
        try:
            rates = await asyncio.get_event_loop().run_in_executor(
                None, self._fetch_from_github
            )
            if rates:
                self._rates = rates
                self._save_to_cache(rates)
                self._log("[RatesManager] GitHub에서 최신 요금 데이터 로드 완료.")
                return rates
        except Exception as e:
            self._log(f"[RatesManager] GitHub fetch 실패: {e}")

        # 로컬 캐시
        cached = self._load_from_cache()
        if cached:
            self._rates = cached
            self._log("[RatesManager] 로컬 캐시에서 요금 데이터 로드.")
            return cached

        # 번들 fallback
        fb = self._load_fallback()
        if fb:
            self._rates = fb
            self._log("[RatesManager] 번들 fallback에서 요금 데이터 로드.")
            return fb

        raise RuntimeError("요금 데이터를 가져올 수 없습니다.")

    def start_auto_refresh(self, interval_sec=CACHE_TTL_SEC):
        """비동기 주기적 갱신 시작."""
        self.stop_auto_refresh()
        self._refresh_task = asyncio.ensure_future(self._refresh_loop(interval_sec))

    def stop_auto_refresh(self):
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            self._refresh_task = None

    def get_status(self):
        updated = None
        if self._homey:
            updated = self._homey.settings.get(SETTINGS_KEY_UPDATED)
        return {
            "has_data": self._rates is not None,
            "updated_at": updated,
        }

    # ── Private ─────────────────────────────────────

    async def _refresh_loop(self, interval_sec):
        while True:
            await asyncio.sleep(interval_sec)
            try:
                await self.get_rates(force_refresh=True)
            except Exception as e:
                self._log(f"[RatesManager] 자동 갱신 실패: {e}")

    def _fetch_from_github(self):
        """동기 HTTP GET으로 rates.json 가져오기 (ETag 지원)."""
        import time
        now = time.time()
        if now - self._last_fetch_ts < MIN_FETCH_INTERVAL_SEC:
            return None
        self._last_fetch_ts = now

        headers = {"User-Agent": "Homey-Kwh2Won-Python/1.0"}

        # ETag 조건부 요청
        if self._homey:
            etag = self._homey.settings.get(SETTINGS_KEY_ETAG)
            if etag:
                headers["If-None-Match"] = etag

        req = Request(RATES_URL, headers=headers)
        try:
            resp = urlopen(req, timeout=FETCH_TIMEOUT_SEC)
        except HTTPError as e:
            if e.code == 304:
                self._log("[RatesManager] 304 Not Modified (캐시가 최신)")
                if self._homey:
                    import datetime
                    self._homey.settings.set(SETTINGS_KEY_UPDATED, datetime.datetime.now().isoformat())
                return self._rates or self._load_from_cache()
            raise
        except URLError as e:
            raise ConnectionError(str(e.reason)) from e

        body = resp.read().decode("utf-8")
        data = json.loads(body)
        if not REQUIRED_KEYS.issubset(data.keys()):
            raise ValueError("유효하지 않은 rates.json 형식")

        # ETag 저장
        if self._homey:
            etag = resp.headers.get("ETag")
            if etag:
                self._homey.settings.set(SETTINGS_KEY_ETAG, etag)

        return data

    def _save_to_cache(self, rates):
        if not self._homey:
            return
        try:
            import datetime
            self._homey.settings.set(SETTINGS_KEY_RATES, json.dumps(rates))
            self._homey.settings.set(SETTINGS_KEY_UPDATED, datetime.datetime.now().isoformat())
        except Exception as e:
            self._log(f"[RatesManager] 캐시 저장 실패: {e}")

    def _load_from_cache(self):
        if not self._homey:
            return None
        try:
            raw = self._homey.settings.get(SETTINGS_KEY_RATES)
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return None

    def _load_fallback(self):
        try:
            with open(FALLBACK_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
