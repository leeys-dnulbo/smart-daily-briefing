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

---

## 2. 데이터 조회 (자연어)

GA 관련 질문을 하면 자동으로 데이터를 조회하고 분석합니다.
Claude Code와 OpenClaw 모두 동일하게 동작합니다.

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

**OpenClaw:**
```
"저장된 리포트 목록 보여줘"
```

---

## 4. 일일 브리핑 생성

**Claude Code:**
```
/smart-briefing:briefing
```

**OpenClaw:**
```
"브리핑 생성해줘"
"오늘 GA4 리포트 만들어줘"
```

활성 섹션의 GA4 데이터를 종합 수집하여 분석합니다:
- 핵심 요약 (2~3문장)
- 주요 지표 테이블 + 시각화 차트
- 이상 탐지 (전주 대비 변화)
- 인사이트 및 액션 아이템

결과는 터미널에 표시되고 `briefings/YYYY-MM-DD.md`에 저장됩니다.

---

## 5. 브리핑 개인화

브리핑 내용을 자연어로 맞춤 설정할 수 있습니다 (Claude Code + OpenClaw 공통).

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

**OpenClaw:**
```
"행동패턴 프리셋으로 바꿔줘"
"캠페인 프리셋 적용해줘"
```

현재 설정 확인:

**Claude Code:** `/smart-briefing:customize`
**OpenClaw:** "브리핑 설정 보여줘"

---

## 6. 자동 브리핑 스케줄

매일 정해진 시간에 자동으로 브리핑을 생성합니다.

### Claude Code (macOS launchd)

```
"매일 아침 9시에 브리핑 보내줘"
```

또는:

```
/smart-briefing:schedule install 09:00
```

설정 시 Slack webhook URL 입력을 안내하며, 등록하면 매일 자동 실행 후 Slack으로 알림을 받을 수 있습니다.

### OpenClaw (내장 cron)

```
"매일 아침 9시에 브리핑 보내줘"
```

또는 직접 cron 설정:

```bash
openclaw cron add --name "GA4-daily-briefing" \
  --cron "0 9 * * *" --tz "Asia/Seoul" \
  --session isolated \
  --message "GA4 일일 브리핑을 생성하고 briefings/ 폴더에 저장해줘. config.json 설정에 따라 활성 섹션의 데이터를 수집하고 분석해."
```

OpenClaw cron 장점:
- 크로스 플랫폼 (macOS/Linux/Windows)
- 자동 재시도 (exponential backoff)
- 채널 전송 연동 가능

---

## 7. 리포트별 개별 스케줄

저장된 리포트마다 별도 스케줄을 설정할 수 있습니다.

```
"모바일분석 리포트를 매주 월요일 9시에 실행해줘"
```

### Claude Code

```
/smart-briefing:schedule 모바일분석
→ 빈도 선택 (매일/매주) → 요일 선택 → 시간 입력 → 자동 등록
```

### OpenClaw

```bash
openclaw cron add --name "GA4-report-mobile-analysis" \
  --cron "0 9 * * 1" --tz "Asia/Seoul" \
  --session isolated \
  --message "reports/mobile-analysis.json 리포트를 실행해줘. query 정보를 읽고 get_ga4_data로 데이터를 조회한 뒤 결과를 분석해서 보여줘."
```

> 리포트 파일명은 kebab-case로 저장됩니다 (예: "모바일분석" → `mobile-analysis.json`).

---

## 8. 스케줄 관리

### Claude Code

**상태 확인:**
```
/smart-briefing:schedule status
```

**스케줄 해제:**
```
/smart-briefing:schedule uninstall                    # 일일 브리핑 해제
/smart-briefing:schedule uninstall-report 모바일분석    # 리포트 스케줄 해제
```

**리포트 수동 실행:**
```
/smart-briefing:schedule run 모바일분석
```

### OpenClaw

**상태 확인:**
```bash
openclaw cron list
```

**스케줄 해제:**
```bash
openclaw cron remove "GA4-daily-briefing"
openclaw cron remove "GA4-report-mobile-analysis"
```

---

## 9. Slack 알림 설정

자동 브리핑/리포트 실행 후 Slack으로 요약을 받을 수 있습니다 (Claude Code + OpenClaw 공통).

```
"Slack webhook 등록해줘"
→ Webhook URL 입력 → 테스트 메시지 전송 → 설정 완료
```

Slack Incoming Webhook URL 생성:
1. https://api.slack.com/messaging/webhooks 접속
2. Slack App 생성 → Incoming Webhooks 활성화
3. 채널 선택 후 Webhook URL 복사

알림 on/off:

```
"Slack 알림 꺼줘"
"Slack 알림 켜줘"
```

---

## 10. PDF 내보내기

마크다운 브리핑을 차트 이미지가 포함된 PDF로 변환합니다 (Claude Code + OpenClaw 공통).

### 사전 요구사항

```bash
pip install weasyprint markdown
```

### 사용 방법

**Claude Code:**
```
/smart-briefing:export latest        # 최신 브리핑을 PDF로
/smart-briefing:export 2026-02-15    # 특정 날짜 지정
```

**자연어 (Claude Code + OpenClaw):**
```
"이 브리핑 PDF로 만들어줘"
"오늘 브리핑 PDF로 내보내줘"
"어제 브리핑 PDF로 변환해줘"
```

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

### 출력 파일

- 마크다운: `briefings/YYYY-MM-DD.md`
- PDF: `briefings/YYYY-MM-DD.pdf`

파일명은 항상 `YYYY-MM-DD` 형식입니다.

---

## 11. OpenClaw 채널 전송

OpenClaw에서 Slack으로 브리핑 결과를 전송할 수 있습니다.

```bash
openclaw cron add --name "GA4-daily-briefing" \
  --cron "0 9 * * *" --tz "Asia/Seoul" \
  --session isolated \
  --announce --channel slack --to "webhook:${SLACK_WEBHOOK_URL}" \
  --message "GA4 일일 브리핑을 생성해줘."
```

> Telegram, Discord 채널은 v2.0.0에서 지원 예정입니다.

---

## 12. 테스트 실행

v1.10.0부터 pytest 기반 테스트가 포함됩니다.

```bash
pip install pytest
python3 -m pytest tests/ -v
```

pytest 기반 테스트 스위트: utils.py 유틸리티 + AST 코드 검증기
