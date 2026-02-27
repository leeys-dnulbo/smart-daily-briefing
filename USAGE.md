# 사용 시나리오

## 1. 초기 설정

### Claude Code

```
/smart-briefing:setup
```

GA4 MCP 서버 연결 상태를 확인하고, `.mcp.json` 설정을 안내합니다.

### OpenClaw

[docs/openclaw-setup.md](docs/openclaw-setup.md)를 참고하여 설정합니다:
1. `~/.openclaw/openclaw.json`에 스킬 디렉토리와 MCP 서버 추가
2. OpenClaw 재시작

### Cowork (Claude Desktop)

[docs/cowork-setup.md](docs/cowork-setup.md)를 참고하여 설정합니다:
1. 호스트 측 Claude Desktop에서 MCP 서버 등록
2. Cowork에서 프로젝트 열기 (CLAUDE.md가 자동 로드됩니다)

### 환경 진단 (헬스체크)

설정 후 환경 상태를 점검합니다:

```
/smart-briefing:setup healthcheck              # 전체 진단 (12개 항목)
/smart-briefing:setup healthcheck --json       # JSON 형식 출력
/smart-briefing:setup healthcheck --check config,slack  # 특정 항목만
```

점검 항목: config.json, Python, matplotlib, weasyprint, Slack/Telegram/Discord 연결, sidecar, 폰트, 필수 스크립트, config 버전, 네트워크 프록시

---

## 2. 데이터 조회 (자연어)

GA 관련 질문을 하면 자동으로 데이터를 조회하고 분석합니다.
Claude Code, OpenClaw, Cowork 모두 동일하게 동작합니다.

```
"이번 주 세션 수 보여줘"
"모바일 이탈률이 어떻게 돼?"
"트래픽 소스별 성과 비교해줘"
"어제 캠페인 성과 요약해줘"
```

---

## 3. 리포트 저장

데이터 조회 후 결과를 리포트로 저장할 수 있습니다.

```
"이 분석을 리포트로 저장해줘"
→ 리포트명 확인 → reports/{name}.json 저장
```

### 리포트 목록 확인

**Claude Code:**
```
/smart-briefing:reports
```

**OpenClaw / Cowork:**
```
"저장된 리포트 목록 보여줘"
```

---

## 4. 일일 브리핑

**Claude Code:**
```
/smart-briefing:briefing
/smart-briefing:briefing 2026-02-20    # 특정 날짜 지정
```

**OpenClaw / Cowork:**
```
"브리핑 생성해줘"
"오늘 GA4 리포트 만들어줘"
```

활성 섹션의 GA4 데이터를 종합 수집하여 분석합니다:
- 핵심 요약 (2~3문장)
- 주요 지표 테이블 + 시각화 차트
- 이상 탐지 (전주 대비 변화)
- 인사이트 및 액션 아이템

결과는 `briefings/YYYY-MM-DD.md`에 저장됩니다.

---

## 5. 주간 브리핑

**Claude Code:**
```
/smart-briefing:briefing weekly              # 직전 완결 주 브리핑
/smart-briefing:briefing weekly 2026-02-16   # 특정 주 (월요일 날짜)
```

**OpenClaw / Cowork:**
```
"주간 브리핑 생성해줘"
```

일일 sidecar 데이터를 집계하여 주간 트렌드를 분석합니다:
- 주간 지표 추이 (월~일 일별 테이블 + 차트)
- 전주 대비 변화
- 주간 이상 탐지 요약
- 다음 주 관찰 포인트

결과는 `briefings/weekly-{시작일}.md`에 저장됩니다.
sidecar가 4일 이상 있으면 sidecar 기반, 부족하면 GA4 직접 조회로 자동 전환합니다.

---

## 6. 브리핑 비교

**Claude Code:**
```
/smart-briefing:briefing compare                         # 어제 vs 그제
/smart-briefing:briefing compare 2026-02-20 2026-02-26   # 특정 날짜 비교
```

**OpenClaw / Cowork:**
```
"어제랑 그제 브리핑 비교해줘"
```

두 날짜의 sidecar JSON을 비교하여 지표 변화, 트렌드, 이상 항목을 분석합니다.

---

## 7. 브리핑 히스토리

**Claude Code:**
```
/smart-briefing:briefing list
```

**OpenClaw / Cowork:**
```
"최근 브리핑 목록 보여줘"
```

최근 14일간 생성된 브리핑 파일(일일/주간/PDF/sidecar)을 목록으로 표시합니다.

---

## 8. 브리핑 개인화

브리핑 내용을 자연어로 맞춤 설정할 수 있습니다 (전 플랫폼 공통).

```
"캠페인 위주로 브리핑해줘"
"사용자 행동패턴 중심으로 바꿔줘"
"이벤트 섹션 추가해줘"
"이상 탐지 임계값 30%로 높여줘"
```

프리셋으로 빠르게 변경:

**Claude Code:**
```
/smart-briefing:customize preset behavior    # 사용자 행동패턴
/smart-briefing:customize preset traffic     # 트래픽/유입
/smart-briefing:customize preset campaign    # 캠페인 성과
/smart-briefing:customize preset content     # 콘텐츠 성과
/smart-briefing:customize preset default     # 기본
```

**OpenClaw / Cowork:**
```
"행동패턴 프리셋으로 바꿔줘"
"캠페인 프리셋 적용해줘"
```

현재 설정 확인:

**Claude Code:** `/smart-briefing:customize`
**OpenClaw / Cowork:** "브리핑 설정 보여줘"

---

## 9. PDF 내보내기

마크다운 브리핑을 차트 이미지가 포함된 PDF로 변환합니다.

### 사전 요구사항

```bash
pip install weasyprint markdown
```

### 사용 방법

**Claude Code:**
```
/smart-briefing:briefing export latest        # 최신 브리핑을 PDF로
/smart-briefing:briefing export 2026-02-15    # 특정 날짜 지정
```

**자연어 (전 플랫폼):**
```
"이 브리핑 PDF로 만들어줘"
"오늘 브리핑 PDF로 내보내줘"
```

> `/smart-briefing:export`는 deprecated입니다. `/smart-briefing:briefing export`를 사용하세요.
>
> **Cowork**: weasyprint이 미설치일 수 있습니다. `pip install weasyprint markdown`으로 설치하세요. 마크다운 브리핑은 항상 생성됩니다.

### 자동 PDF 생성

브리핑 생성 시 PDF도 자동으로 함께 생성됩니다 (기본값).
비활성화하려면 `config.json`에서 설정합니다:

```json
{
  "export": {
    "auto_pdf": false
  }
}
```

---

## 10. 이상 탐지 알림

브리핑 생성 시 이상 항목이 감지되면 활성 채널로 즉시 알림을 전송합니다.

- 쿨다운: 동일 지표 반복 알림 방지 (기본 4시간)
- 일일 한도: 하루 최대 알림 수 (기본 10건)
- 심각도 필터: warning 이상만 전송 (기본값)

### 설정

```json
{
  "notifications": {
    "anomaly_alerts": {
      "enabled": true,
      "cooldown_hours": 4,
      "max_alerts_per_day": 10,
      "min_severity": "warning"
    }
  }
}
```

### 이력 확인

```
/smart-briefing:notification history
```

---

## 11. 알림 채널 설정 및 관리

Slack, Telegram, Discord로 브리핑/이상 탐지 알림을 받을 수 있습니다.

### 채널 설정

**Slack:**
```
"Slack webhook 등록해줘"
→ Webhook URL 입력 → 테스트 → 완료
```

**Telegram:**
```
/smart-briefing:notification setup telegram
→ Bot Token + Chat ID 입력 → 완료
```

**Discord:**
```
/smart-briefing:notification setup discord
→ Webhook URL 입력 → 완료
```

### 알림 관리 커맨드

```
/smart-briefing:notification status         # 채널 연결 상태 + 큐 현황
/smart-briefing:notification test            # 모든 활성 채널에 테스트 전송
/smart-briefing:notification test slack      # 특정 채널만 테스트
/smart-briefing:notification flush           # 실패로 큐에 쌓인 메시지 재전송
/smart-briefing:notification history         # 이상 탐지 알림 발송/억제 이력
/smart-briefing:notification setup {채널}    # 채널별 설정 안내
```

---

## 12. 자동 스케줄

매일/매주 정해진 시간에 자동으로 브리핑을 생성합니다.

> **Cowork**: `/schedule` 명령 또는 사이드바 "Scheduled"에서 반복 작업을 설정할 수 있습니다. 단, 컴퓨터가 깨어있고 Claude Desktop 앱이 열려있을 때만 실행됩니다.

### 일일 브리핑 스케줄

**Claude Code (macOS):**
```
/smart-briefing:schedule install 09:00
/smart-briefing:schedule uninstall           # 해제
```

**OpenClaw:**
```bash
openclaw cron add --name "GA4-daily-briefing" \
  --cron "0 9 * * *" --tz "Asia/Seoul" \
  --session isolated \
  --message "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘."
```

**Cowork:**
Cowork 태스크에서 `/schedule`을 입력하거나, 사이드바 "Scheduled" > "+ New task"로 생성합니다:
- 프롬프트: "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘"
- 주기: Daily

> 참고: 컴퓨터가 깨어있고 Claude Desktop 앱이 열려있을 때만 실행됩니다.

### 주간 브리핑 스케줄

**Claude Code (macOS):**
```
/smart-briefing:schedule install-weekly 09:00        # 매주 월요일
/smart-briefing:schedule install-weekly 09:00 금     # 매주 금요일
/smart-briefing:schedule uninstall-weekly             # 해제
```

### 리포트별 개별 스케줄

```
/smart-briefing:schedule 모바일분석
→ 빈도(매일/매주) → 요일 → 시간 → 자동 등록

/smart-briefing:schedule uninstall-report 모바일분석   # 해제
/smart-briefing:schedule run 모바일분석               # 즉시 실행
```

### 스케줄 상태 확인

```
/smart-briefing:schedule status
/smart-briefing:schedule list
```

### OpenClaw 채널 전송 연동

스케줄 실행 결과를 Slack 등으로 전송할 수 있습니다:

```bash
openclaw cron add --name "GA4-daily-briefing" \
  --cron "0 9 * * *" --tz "Asia/Seoul" \
  --session isolated \
  --announce --channel slack --to "webhook:${SLACK_WEBHOOK_URL}" \
  --message "GA4 일일 브리핑을 생성해줘."
```

---

## 13. v1.x에서 업그레이드

v1.x config.json을 v2.0으로 자동 마이그레이션합니다.
기존 설정(Slack webhook 등)은 보존되고, Telegram/Discord 섹션이 추가됩니다.

```bash
python3 scripts/migrate-config.py             # 마이그레이션 실행 (자동 백업)
python3 scripts/migrate-config.py --dry-run   # 변경 사항 미리보기
```

---

## 14. 테스트 실행

```bash
pip install pytest
python3 -m pytest tests/ -v
```

358개 테스트: 알림 시스템(Slack/Telegram/Discord), 이상 탐지, 헬스체크, 설정 마이그레이션, sidecar 스키마, 유틸리티, AST 코드 검증

---

## 커맨드 요약

| 커맨드 | 설명 |
|--------|------|
| `/smart-briefing:briefing` | 일일/주간 브리핑, 비교, 히스토리, PDF 내보내기 |
| `/smart-briefing:customize` | 브리핑 개인화 설정 |
| `/smart-briefing:notification` | 알림 채널 관리 (test/status/flush/history/setup) |
| `/smart-briefing:reports` | 저장된 리포트 목록 |
| `/smart-briefing:schedule` | 자동 스케줄 관리 (일일/주간/리포트별) |
| `/smart-briefing:setup` | 초기 설정 + 환경 진단 (healthcheck) |

> Cowork에서는 슬래시 명령 대신 자연어로 동일한 기능을 사용합니다.
> 예: `/smart-briefing:briefing` → "브리핑 생성해줘"

---

## 플랫폼별 기능 비교

| 기능 | Claude Code | OpenClaw | Cowork |
|------|:-----------:|:--------:|:------:|
| 데이터 조회 (자연어) | O | O | O |
| 일일 브리핑 | O | O | O |
| 주간 브리핑 | O | O | O |
| 브리핑 비교 | O | O | O |
| 브리핑 히스토리 | O | O | O |
| 리포트 저장/실행 | O | O | O |
| 브리핑 개인화 | O | O | O |
| 차트 생성 | O | O | △ (Python 필요) |
| PDF 내보내기 | O | O | △ (weasyprint 필요) |
| 자동 스케줄 | O (launchd/systemd) | O (cron) | O (/schedule, 앱 실행 중) |
| 이상 탐지 알림 | O (자동) | O (자동) | △ (프록시 필요) |
| 알림 채널 (Slack 등) | O | O | △ (프록시 필요) |
| 환경 진단 (헬스체크) | O | O | O |
| 코드 검증 훅 | O (자동) | - | X (자기 준수) |

O = 완전 지원, △ = 제한적 지원, X = 미지원
