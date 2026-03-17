"""한국 전기요금 계산기 Homey App (Python SDK)"""
from homey.app import App
from lib.rates_manager import RatesManager
from lib.kwh2won_api import kwh2won_api as Kwh2WonApi


class Kwh2WonApp(App):
    """한국전력 가정용 전기요금 계산기"""

    async def on_init(self):
        self.log("한국 전기요금 계산기 앱 시작...")

        # ── 요금 데이터 로더 초기화 ──
        self.rates_manager = RatesManager(
            homey=self.homey,
            log_fn=self.log,
        )

        # 최초 로드
        try:
            await self.rates_manager.get_rates()
            self.log("요금 데이터 로드 완료.")
        except Exception as e:
            self.error(f"요금 데이터 초기 로드 실패: {e}")

        # 24시간마다 자동 갱신
        self.rates_manager.start_auto_refresh()

        # ── Flow 카드 등록 ──
        self._register_flow_cards()

        self.log("한국 전기요금 계산기 앱 준비 완료.")

    async def get_rates(self, force_refresh=False):
        """디바이스에서 호출하여 rates를 가져갑니다."""
        return await self.rates_manager.get_rates(force_refresh)

    def _register_flow_cards(self):
        # Action: 전기요금 계산
        calculate_action = self.homey.flow.get_action_card("calculate_bill")
        calculate_action.register_run_listener(self._on_calculate_action)

        # Condition: 요금 초과 여부
        bill_exceeds = self.homey.flow.get_condition_card("bill_exceeds")
        bill_exceeds.register_run_listener(self._on_bill_exceeds)

    async def _on_calculate_action(self, args, state):
        rates = await self.get_rates()
        api = Kwh2WonApi(
            pressure=args.get("pressure", "low"),
            checkDay=int(args.get("checkDay", 1)),
            bigfamDcCfg=int(args.get("bigfamDc", 0)),
            welfareDcCfg=int(args.get("welfareDc", 0)),
            rates=rates,
        )
        result = api.kwh2won(float(args.get("kwh", 0)))

        # Trigger flow card
        trigger = self.homey.flow.get_trigger_card("bill_calculated")
        await trigger.trigger({
            "total": result["total"],
            "kwh": float(args.get("kwh", 0)),
        })
        return True

    async def _on_bill_exceeds(self, args, state):
        return state.get("total", 0) >= args.get("threshold", 0)

    async def on_uninit(self):
        if hasattr(self, "rates_manager"):
            self.rates_manager.stop_auto_refresh()


homey_export = Kwh2WonApp
