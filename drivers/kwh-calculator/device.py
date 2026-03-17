"""전기요금 계산기 디바이스"""
import asyncio
import datetime

from homey.device import Device
from lib.kwh2won_api import kwh2won_api as Kwh2WonApi


class KwhCalculatorDevice(Device):
    """전기요금을 계산하는 가상 센서 디바이스"""

    async def on_init(self):
        self.log("전기요금 계산기 디바이스 초기화")

        # kWh 입력 리스너 등록
        self.register_capability_listener("meter_kwh_input", self._on_kwh_input)

        # 1시간마다 예상 사용량 갱신
        self._refresh_task = asyncio.ensure_future(self._periodic_refresh())

        # 저장된 사용량으로 초기 계산
        saved_kwh = self.get_setting("energyKwh") or 0
        if saved_kwh and float(saved_kwh) > 0:
            await self._calculate(float(saved_kwh))

    async def _on_kwh_input(self, value: float, **kwargs):
        """사용자가 kWh를 변경했을 때"""
        await self.set_settings({"energyKwh": value})
        await self._calculate(value)

    async def _calculate(self, kwh: float):
        try:
            settings = self.get_settings()
            # 앱에서 최신 요금 데이터 가져오기
            app = self.homey.app
            rates = await app.get_rates()

            pressure = settings.get("pressure", "low")
            check_day = int(settings.get("checkDay", 1))
            bigfam = int(settings.get("bigfamDcCfg", 0))
            welfare = int(settings.get("welfareDcCfg", 0))
            now = datetime.datetime.now()

            # 요금 계산
            api = Kwh2WonApi(
                pressure=pressure,
                checkDay=check_day,
                today=now,
                bigfamDcCfg=bigfam,
                welfareDcCfg=welfare,
                rates=rates,
            )
            result = api.kwh2won(float(kwh))

            # 예상 사용량 계산
            forecast = api.energy_forecast(float(kwh))

            # 예상 요금 계산
            forecast_api = Kwh2WonApi(
                pressure=pressure,
                checkDay=check_day,
                today=now,
                bigfamDcCfg=bigfam,
                welfareDcCfg=welfare,
                rates=rates,
            )
            forecast_result = forecast_api.kwh2won(forecast["forecast"])

            # Capability 값 업데이트
            await self.set_capability_value("meter_kwh_input", float(kwh))
            await self.set_capability_value("meter_bill_total", result["total"])
            await self.set_capability_value("meter_bill_basic", result["basicWon"])
            await self.set_capability_value("meter_bill_kwh", result["kwhWon"])
            await self.set_capability_value("meter_bill_climate", result["climateWon"])
            await self.set_capability_value("meter_bill_fuel", result["fuelWon"])
            await self.set_capability_value("meter_bill_vat", result["vat"])
            await self.set_capability_value("meter_bill_fund", result["baseFund"])

            discount = (
                result["bigfamDc"]
                + result["welfareDc"]
                + result["elecBasicDc"]
                + result["elecBasic200Dc"]
                + result["weakDc"]
            )
            await self.set_capability_value("meter_bill_discount", discount)
            await self.set_capability_value("meter_forecast_kwh", forecast["forecast"])
            await self.set_capability_value("meter_forecast_won", forecast_result["total"])
            await self.set_capability_value(
                "meter_check_info",
                f"{result['checkMonth']}월 {result['useDays']}/{result['monthDays']}일",
            )

            self.log(
                f"계산 완료: {kwh}kWh → {result['total']}원 "
                f"(예상: {forecast['forecast']}kWh → {forecast_result['total']}원)"
            )

            # Flow 트리거
            trigger = self.homey.flow.get_trigger_card("bill_calculated")
            await trigger.trigger(
                self,
                {
                    "total": result["total"],
                    "kwh": float(kwh),
                    "forecast_kwh": forecast["forecast"],
                    "forecast_won": forecast_result["total"],
                },
            )

        except Exception as e:
            self.error(f"전기요금 계산 오류: {e}")

    async def on_settings(self, old_settings, new_settings, changed_keys):
        self.log(f"설정 변경: {changed_keys}")
        kwh = new_settings.get("energyKwh") or old_settings.get("energyKwh") or 0
        if kwh and float(kwh) > 0:
            # 약간의 딜레이 후 재계산
            await asyncio.sleep(0.5)
            await self._calculate(float(kwh))
        return None

    async def _periodic_refresh(self):
        """1시간마다 예상 사용량/요금 갱신"""
        while True:
            await asyncio.sleep(3600)  # 1시간
            try:
                kwh = self.get_setting("energyKwh") or 0
                if kwh and float(kwh) > 0:
                    await self._calculate(float(kwh))
            except Exception as e:
                self.error(f"주기적 갱신 실패: {e}")

    async def on_deleted(self):
        if hasattr(self, "_refresh_task") and self._refresh_task:
            self._refresh_task.cancel()
        self.log("디바이스 삭제됨")


homey_export = KwhCalculatorDevice
