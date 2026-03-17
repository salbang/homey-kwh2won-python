"""
kwh2won_api 테스트
원본 Home Assistant 테스트 케이스와 동일한 결과를 검증합니다.
rates는 로컬 fallback 파일에서 로드합니다.
"""
import sys
import os
import json
import datetime

# lib를 import path에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.kwh2won_api import kwh2won_api as Kwh2WonApi

# rates fallback 로드
rates_path = os.path.join(os.path.dirname(__file__), "..", "lib", "rates_fallback.json")
with open(rates_path, "r", encoding="utf-8") as f:
    RATES = json.load(f)

passed = 0
failed = 0


def assert_equal(test_name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ✅ {test_name}: {actual} === {expected}")
        passed += 1
    else:
        print(f"  ❌ {test_name}: {actual} !== {expected} (diff: {actual - expected})")
        failed += 1


# Test 1: 저압, 할인 없음, 350kWh
print("\nTest 1: 저압, 할인 없음, 350kWh (2025.10.14, 검침일 15)")
api = Kwh2WonApi(pressure="low", checkDay=15, today=datetime.datetime(2025, 10, 14), rates=RATES)
result = api.kwh2won(350)
assert_equal("total", result["total"], 70640)

# Test 2: 고압, 하계, 500kWh
print("\nTest 2: 고압, 하계, 500kWh (2025.8.31, 검침일 1)")
api = Kwh2WonApi(pressure="high", checkDay=1, today=datetime.datetime(2025, 8, 31), rates=RATES)
result = api.kwh2won(500)
assert_equal("total", result["total"], 93280)

# Test 3: 대가족 할인, 450kWh
print("\nTest 3: 저압, 대가족 할인, 450kWh (2025.11.19, 검침일 20)")
api = Kwh2WonApi(pressure="low", checkDay=20, today=datetime.datetime(2025, 11, 19), bigfamDcCfg=1, rates=RATES)
result = api.kwh2won(450)
assert_equal("total", result["total"], 90020)

# Test 4: 복지 할인, 180kWh
print("\nTest 4: 저압, 복지 할인(장애인), 180kWh (2025.9.30, 검침일 1)")
api = Kwh2WonApi(pressure="low", checkDay=1, today=datetime.datetime(2025, 9, 30), welfareDcCfg=1, rates=RATES)
result = api.kwh2won(180)
assert_equal("total", result["total"], 5660)

# Test 5: 중복 할인, 550kWh
print("\nTest 5: 저압, 중복 할인 (대가족+기초생활), 550kWh (2025.10.9, 검침일 10)")
api = Kwh2WonApi(pressure="low", checkDay=10, today=datetime.datetime(2025, 10, 9), bigfamDcCfg=1, welfareDcCfg=4, rates=RATES)
result = api.kwh2won(550)
assert_equal("total", result["total"], 114960)

# Test 6: 동계, 고압, 1200kWh
print("\nTest 6: 고압, 동계, 1200kWh (2026.1.31, 검침일 1)")
api = Kwh2WonApi(pressure="high", checkDay=1, today=datetime.datetime(2026, 1, 31), rates=RATES)
result = api.kwh2won(1200)
assert_equal("total", result["total"], 388020)

# Summary
print(f"\n{'=' * 50}")
print(f"결과: {passed} passed, {failed} failed (total {passed + failed})")
print(f"{'=' * 50}")

sys.exit(1 if failed > 0 else 0)
