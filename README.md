# 🌡️ 광주광역시 북구 도심 열환경 및 다차원 기후 취약성 분석
(Urban Heat Environment and Climate Vulnerability Analysis in Buk-gu, Gwangju)

본 레포지토리는 구글 어스 엔진(Google Earth Engine, GEE) 기반의 다중위성 데이터와 통계청 미시 공간 데이터를 융합하여, 도심 열섬 현상(UHI)의 공간적 패턴을 분석하고 기후위기 적응 정책의 우선순위(투트랙 타겟팅)를 도출하기 위한 분석 코드 및 마스터 데이터를 제공합니다.

## 📂 파일 설명 (Files)
* `MAXLST추출`: GEE 기반 하절기 최고 지표면온도(Max LST) 산출 스크립트
* `Mean LST+NDBI`: GEE 기반 상대 지표면온도(RLST) 및 건물 밀도(NDBI) 산출 스크립트
* `SAVI+DEM`: GEE 기반 토양조정 식생지수(SAVI) 및 해발고도(DEM) 산출 스크립트
* `Bukgu_100m_Master_Data.csv`: 공간 통계(Zonal Statistics) 및 다차원 중첩 분석이 완료된 100m 격자 및 집계구 단위 마스터 데이터

## 📊 데이터 명세서 (Data Dictionary)
마스터 데이터(`Bukgu_100m_Master_Data`)의 주요 변수 설명입니다.

| 변수명 (Column) | 설명 (Description) | 기후 취약성 지표 |
| :--- | :--- | :--- |
| `TOT_OA_CD` | 통계청 집계구 코드 (13자리) | - |
| `ADM_CD` | 행정동 코드 | - |
| `Abs_mean` | 2025년 하절기 평균 절대 표면온도 (℃) | 노출도 (Track 1) |
| `dRL_mean` | 2020-2025년 상대 지표면온도 변화량 (ΔRLST) | 노출도 (Track 2) |
| `dNB_mean` | 2020-2025년 건물 밀도 변화량 (ΔNDBI) | 노출도 (Track 2) |
| `Elderly_Ratio` | 집계구 단위 고령 인구 비율 (%) | 민감도 (Track 1) |
| `Old_housing_Ratio` | 집계구 단위 30년 이상 노후 주택 비율 (%) | 적응 능력 (Track 2) |
| `Track1_Score` | 단기 인명 구호형(Track 1) 타겟팅 Z-score 합산 점수 | - |
| `Track2_Score` | 중장기 공간 개조형(Track 2) 타겟팅 Z-score 합산 점수 | - |

> *참고: Track 1 = `Z_Abs_mean` + `Z_Elderly_Ratio` / Track 2 = `Z_dRL_mean` + `Z_dNB_mean` + `Z_Old_housing_Ratio`*

## 📎 데이터 출처 및 인용 (Data Sources)
본 연구의 데이터는 다음의 공공 API 및 오픈 데이터를 가공하여 구축되었습니다.
* **위성 영상 (Satellite Imagery):** Google Earth Engine Data Catalog (Landsat 8/9, Sentinel-2, SRTM DEM 등)
* **인구 및 주택 공간 통계:** 통계청 통계지리정보서비스(SGIS) 2024년 기준 집계구 데이터
* **행정구역 경계:** 국토교통부 국가공간정보포털 및 SGIS 제공 Shapefile

## 📜 라이선스 (License)
본 레포지토리의 코드 및 가공 데이터는 학술적 목적으로 자유롭게 활용하실 수 있습니다. 단, 원천 데이터(인구 및 주택 통계)의 저작권 및 활용 규정은 [통계청 SGIS](https://sgis.kostat.go.kr/)의 정책을 따릅니다.
