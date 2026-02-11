# 사용 시나리오

## 1. 초기 설정

```
/smart-briefing:setup
```

GA4 MCP 서버 연결 상태를 확인하고, `.mcp.json` 설정을 안내합니다.

---

## 2. 데이터 조회 (자연어)

GA 관련 질문을 하면 자동으로 데이터를 조회하고 분석합니다.

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

```
/smart-briefing:reports
```

---

## 4. 일일 브리핑 생성

```
/smart-briefing:briefing
```

활성 섹션의 GA4 데이터를 종합 수집하여 분석합니다:
- 핵심 요약 (2~3문장)
- 주요 지표 테이블 + 시각화 차트
- 이상 탐지 (전주 대비 변화)
- 인사이트 및 액션 아이템

결과는 터미널에 표시되고 `briefings/YYYY-MM-DD.md`에 저장됩니다.

---

## 5. 브리핑 개인화

브리핑 내용을 자연어로 맞춤 설정할 수 있습니다.

```
"캠페인 위주로 브리핑해줘"
"사용자 행동패턴 중심으로 바꿔줘"
"이벤트 섹션 추가해줘"
"이상 탐지 임계값 30%로 높여줘"
```

프리셋으로 빠르게 변경:

```
/smart-briefing:customize preset behavior    # 사용자 행동패턴
/smart-briefing:customize preset traffic     # 트래픽/유입
/smart-briefing:customize preset campaign    # 캠페인 성과
/smart-briefing:customize preset content     # 콘텐츠 성과
/smart-briefing:customize preset default     # 기본
```

현재 설정 확인:

```
/smart-briefing:customize
```

---

## 6. 자동 브리핑 스케줄

매일 정해진 시간에 자동으로 브리핑을 생성합니다 (macOS).

```
"매일 아침 9시에 브리핑 보내줘"
```

또는:

```
/smart-briefing:schedule install 09:00
```

설정 시 Slack webhook URL 입력을 안내하며, 등록하면 매일 자동 실행 후 Slack으로 알림을 받을 수 있습니다.

---

## 7. 리포트별 개별 스케줄

저장된 리포트마다 별도 스케줄을 설정할 수 있습니다.

```
"모바일분석 리포트를 매주 월요일 9시에 실행해줘"
```

또는:

```
/smart-briefing:schedule 모바일분석
→ 빈도 선택 (매일/매주) → 요일 선택 → 시간 입력 → 자동 등록
```

---

## 8. 스케줄 관리

### 상태 확인

```
/smart-briefing:schedule status
```

출력 예시:

```
ACTIVE: 매일 09:00
SLACK: 활성화됨
REPORTS:
  모바일분석 | weekly | 월 09:00
  트래픽분석 | daily | 18:00
```

### 스케줄 해제

```
/smart-briefing:schedule uninstall                    # 일일 브리핑 해제
/smart-briefing:schedule uninstall-report 모바일분석    # 리포트 스케줄 해제
```

### 리포트 수동 실행

```
/smart-briefing:schedule run 모바일분석
```

---

## 9. Slack 알림 설정

자동 브리핑/리포트 실행 후 Slack으로 요약을 받을 수 있습니다.

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
