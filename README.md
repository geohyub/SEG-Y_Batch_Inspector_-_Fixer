# SEG-Y Batch Inspector & Fixer

SEG-Y 파일 헤더를 검증하고 편집하는 종합 툴킷입니다. CLI와 GUI 인터페이스를 모두 제공합니다.

## 주요 기능

- **EBCDIC 헤더 편집** — 라인 단위 편집, 템플릿 적용
- **Binary 헤더 편집** — 40+ 표준 필드 수정, 커스텀 바이트 오프셋 지원
- **Trace 헤더 배치 편집** — 고정값 설정, 수식 변환, 필드 복사, CSV 임포트
- **파일 검증** — 구조 검증, 좌표 이상치 탐지, 좌표 범위 체크
- **리포팅** — Excel 검증 보고서, CSV 변경 이력
- **Dry Run** — 실제 수정 전 미리보기

## 설치

### 기본 (CLI 전용)

```bash
pip install .
```

### GUI 포함

```bash
pip install ".[gui]"
```

### 개발 환경

```bash
pip install ".[all]"
```

## 빠른 시작

### GUI 실행

```bash
# Python 모듈 실행
python -m segy_toolbox gui

# 또는 설치 후
segy-toolbox gui

# Windows
run_gui.bat
```

### CLI 사용

```bash
# 단일 파일 검증
segy-toolbox validate path/to/file.segy

# 폴더 내 전체 검증 + Excel 리포트
segy-toolbox validate path/to/folder/ -o report.xlsx

# EBCDIC 헤더 보기
segy-toolbox ebcdic path/to/file.segy --show

# YAML 설정으로 편집 (Dry Run)
segy-toolbox edit path/to/file.segy -c config.yaml --dry-run

# YAML 설정으로 편집 (실제 적용)
segy-toolbox edit path/to/file.segy -c config.yaml -o ./output
```

## YAML 설정 예시

```yaml
output_mode: "separate_folder"
output_dir: "./output"
dry_run: false

validations:
  check_file_structure: true
  check_coordinate_range: false
  coordinate_bounds:
    x_min: 0
    x_max: 1000000

edits:
  # EBCDIC 헤더 라인 편집
  - type: "ebcdic"
    mode: "lines"
    lines:
      0: "C01 NEW HEADER LINE 1"
      1: "C02 UPDATED BY SEGY-TOOLBOX"

  # Binary 헤더 편집
  - type: "binary_header"
    fields:
      - name: "sample_interval"
        value: 2000
      - name: "format_code"
        value: 1

  # Trace 헤더 수식 편집
  - type: "trace_header"
    condition: "trace_sequence_line > 100"
    fields:
      - name: "source_x"
        expression: "source_x * 100"
      - name: "coordinate_scalar"
        value: -100

  # Trace 헤더 필드 복사
  - type: "trace_header"
    fields:
      - name: "cdp_x"
        copy_from: "source_x"

  # CSV에서 Trace 헤더 가져오기
  - type: "trace_header"
    fields:
      - name: "inline"
        csv_file: "headers.csv"
        csv_column: "inline"
```

## 수식 문법

Trace 헤더 편집에서 사용 가능한 수식:

| 요소 | 예시 |
|------|------|
| 산술 연산 | `source_x * 100 + 500000` |
| 비교 연산 | `trace_sequence_line > 100` |
| 논리 연산 | `source_x > 0 and source_y > 0` |
| 함수 | `abs(source_x)`, `int()`, `round()`, `min()`, `max()`, `float()` |
| 변수 | 모든 trace 헤더 필드명 + `trace_index` |

## 프로젝트 구조

```
segy_toolbox/
├── __init__.py          # 패키지 메타데이터
├── __main__.py          # 진입점 (CLI/GUI)
├── cli.py               # Click 기반 CLI
├── config.py            # YAML 설정 로더
├── models.py            # 데이터 모델 (dataclass)
├── logging.py           # 로깅 설정
├── core/
│   ├── engine.py        # 파이프라인 오케스트레이터
│   ├── validator.py     # 파일 검증 엔진
│   ├── expression.py    # 안전한 수식 평가기
│   ├── binary_editor.py # Binary 헤더 편집기
│   ├── ebcdic_editor.py # EBCDIC 헤더 편집기
│   └── trace_editor.py  # Trace 헤더 배치 편집기
├── gui/
│   ├── app.py           # 메인 윈도우 (PySide6)
│   ├── theme.qss        # 다크 테마 (Catppuccin Mocha)
│   ├── workers.py       # 백그라운드 스레드 워커
│   ├── i18n.py          # 다국어 지원
│   └── panels/          # UI 패널 위젯
├── io/
│   ├── reader.py        # SEG-Y 파일 리더
│   ├── writer.py        # SEG-Y 파일 라이터
│   └── ebcdic.py        # EBCDIC 코덱 유틸리티
└── reporting/
    ├── changelog.py     # CSV 변경 이력
    └── excel_report.py  # Excel 검증 보고서
```

## 개발

### 테스트 실행

```bash
pytest
pytest --cov=segy_toolbox
```

### 린트

```bash
ruff check segy_toolbox/
```

## 라이선스

MIT License

## 작성자

Geoview
