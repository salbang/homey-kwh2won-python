"""전기요금 계산기 드라이버"""
from homey.driver import Driver


class KwhCalculatorDriver(Driver):
    """전기요금 계산기 가상 디바이스 드라이버"""

    async def on_init(self):
        self.log("KwhCalculatorDriver 초기화 완료")

    async def on_pair_list_devices(self):
        import time
        return [
            {
                "name": "전기요금 계산기",
                "data": {"id": f"kwh2won_{int(time.time())}"},
                "settings": {
                    "pressure": "low",
                    "checkDay": "1",
                    "bigfamDcCfg": "0",
                    "welfareDcCfg": "0",
                    "energyKwh": 0,
                },
            }
        ]


homey_export = KwhCalculatorDriver
