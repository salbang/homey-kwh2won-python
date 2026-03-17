# 한국 전기요금 계산기 for Homey (Python SDK)

한국전력(KEPCO) 가정용 전기요금을 자동으로 계산하는 Homey 앱입니다.

Home Assistant용 [kwh_to_won](https://github.com/dugurs/kwh_to_won) (by dugurs)을 Homey Python SDK로 포팅한 버전입니다.

> **Python SDK 사용**: 원본 계산 엔진(`kwh2won_api.py`)을 거의 그대로 사용하여 높은 호환성을 유지합니다.

## 주요 기능

- **전기요금 계산**: kWh 사용량 → 한전 요금체계에 따른 청구금액 자동 계산
- **누진요금 적용**: 가정용 저압/고압, 계절별(하계/동계/기타) 누진 단계 자동 반영
- **할인 지원**: 대가족 할인, 복지 할인 (유공자/장애인/기초생활/차상위계층)
- **예상 사용량/요금**: 현재까지의 사용량을 기반으로 월말 예상 사용량과 요금 계산
- **Homey Flow 연동**: Flow 카드를 통한 자동화
- **Homey Insights**: 사용량/요금 추이 그래프 자동 기록

## 요금 정보 자동 업데이트

요금 단가는 앱에 내장되지 않고, **GitHub 원본 저장소에서 실시간으로** 가져옵니다.

```
원본 저장소 (dugurs/kwh_to_won)
  └─ rates.json 업데이트
        ↓ (HTTPS fetch)
Homey 앱 (24시간마다 자동 갱신)
  └─ Homey Settings에 캐시 저장
        ↓
요금 계산 엔진 (kwh2won_api.py)
```

- **자동 갱신**: 24시간마다 GitHub에서 최신 `rates.json`을 확인
- **ETag 지원**: HTTP 304 Not Modified를 활용해 불필요한 다운로드 방지
- **오프라인 대응**: 네트워크 장애 시 로컬 캐시 → 번들 fallback 순으로 사용
- **앱 업데이트 불필요**: 한전 요금 변경 시 원본 저장소만 업데이트되면 자동 반영

## 설치

```bash
homey app run    # 개발 모드
homey app install  # 설치
```

## 설정

디바이스 추가 후 설정에서 다음 항목을 구성합니다:

| 항목 | 설명 |
|------|------|
| 전압 구분 | 가정용 저압 / 가정용 고압 |
| 검침일 | 1일 ~ 26일, 말일 |
| 대가족 할인 | 해당없음 / 5인이상,3자녀 / 생명유지장치 |
| 복지 할인 | 해당없음 / 유공자,장애인 / 사회복지시설 / 기초생활 / 차상위 |
| 월간 사용량 | kWh 단위로 직접 입력 또는 Flow로 연동 |

## 표시되는 정보 (Capabilities)

| Capability | 설명 |
|------------|------|
| 전기 사용량 | 입력된 월간 kWh |
| 청구금액 | 최종 청구 금액 (원) |
| 기본요금 | 누진 단계별 기본요금 |
| 전력량요금 | 사용량에 따른 전력량 요금 |
| 기후환경요금 | 기후환경 부과금 |
| 연료비조정액 | 연료비 조정 금액 |
| 부가가치세 | VAT 10% |
| 전력산업기반기금 | 전력 기금 |
| 할인액 | 적용된 총 할인 금액 |
| 예상 사용량 | 월말까지 예상 kWh |
| 예상 요금 | 예상 청구 금액 |
| 검침 정보 | 현재 검침 기간 정보 |

## Flow 카드

### 트리거 (When)
- **전기요금이 계산됨**: 요금 계산 완료 시 (토큰: 청구금액, 사용량, 예상사용량, 예상요금)

### 조건 (And)
- **요금이 기준을 초과**: 요금이 지정 금액을 초과하는지 확인

### 액션 (Then)
- **전기요금 계산**: 지정된 kWh와 설정으로 요금 계산 실행

## 프로젝트 구조

```
app.py                        ← Homey App (Python SDK)
drivers/kwh-calculator/
  ├─ driver.py                ← 드라이버 (페어링)
  └─ device.py                ← 가상 센서 디바이스
lib/
  ├─ kwh2won_api.py           ← 원본 계산 엔진 (dugurs)
  ├─ rates_manager.py         ← GitHub rates.json 로더
  └─ rates_fallback.json      ← 오프라인 fallback 데이터
.homeycompose/
  ├─ app.json                 ← 앱 매니페스트
  ├─ capabilities/            ← 12개 커스텀 capability
  └─ flow/                    ← Flow 카드 정의
```

## 원본 프로젝트

- 원본: [dugurs/kwh_to_won](https://github.com/dugurs/kwh_to_won) (Home Assistant)
- 한전 전기요금 계산기: [KEPCO 공식](https://online.kepco.co.kr/PRM033D00)
- 한전 전기요금표: [KEPCO 요금표](https://online.kepco.co.kr/PRM004D00)
