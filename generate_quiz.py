"""
generate_quiz.py
─────────────────────────────────────
GitHub Actions가 매일 오전 6시에 실행하는 스크립트.
"""

import anthropic
import json
import re
import os
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
today = datetime.now(KST).strftime('%Y-%m-%d')
today_display = datetime.now(KST).strftime('%Y.%m.%d')

PROMPT = f"""
당신은 경제 퀴즈 출제 전문가입니다.
오늘({today_display}) 기준 가장 화제가 된 경제 뉴스 5가지를 직접 선정해서,
각 뉴스마다 퀴즈 1개씩, 총 5개를 만들어주세요.

[뉴스 선정 기준]
- 일반인이 "어, 나도 들어봤는데!" 할 만큼 화제성 있는 것
- 금리·환율·주가·무역·기업 실적 등 생활과 연결된 것
- 숫자/금액이 등장하거나 인과관계가 명확한 것

[난이도 구성] 순서 그대로 1개씩
1. 입문 (lv-easy)    — 단순 사실 확인 (얼마? 누가? 몇 %?)
2. 초급 (lv-mid)     — 원인 묻기 (왜 이런 일이 생겼을까?)
3. 중급 (lv-hard)    — 결과·영향 묻기 (이게 우리 생활에 어떤 영향을?)
4. 고급 (lv-expert)  — 경제 메커니즘 묻기 (어떤 원리로 이런 일이?)
5. 최고급 (lv-master) — 여러 개념 연결 추론 (A가 B가 되면 C는 어떻게 될까?)

[context 필드 — 배경 설명] ★ 가장 중요
- 반드시 3~4문장으로 작성할 것. 절대 1~2문장으로 줄이지 말 것.
- 독자가 해당 뉴스를 전혀 모른다고 가정하고 설명
- 포함할 내용:
  ① 무슨 일이 있었는지 (사건/배경 설명)
  ② 왜 이게 중요한지 (우리 생활과의 연결고리)
  ③ 현재 상황이 어떤지 (배경 맥락)
- ★ 절대 금지: context 안에 정답이나 오답 보기에 해당하는 수치·단어를 직접 언급하지 말 것
  예) 정답이 "13% 상승"이라면 context에서 "13%"를 언급하지 말 것
  예) 정답이 "금리 인상"이라면 context에서 "금리를 올렸다"고 쓰지 말 것
  → 대신 "얼마나 변했는지가 이번 퀴즈의 핵심이에요" 같은 식으로 궁금증 유발
- 예시 (정답이 "0.25%p 인상"인 경우):
  "미국 연방준비제도(연준)가 이번 달 기준금리를 조정했습니다.
   기준금리는 은행들이 서로 돈을 빌릴 때 적용하는 금리예요.
   이 결정이 우리 대출 이자와 환율에도 영향을 줄 수 있어서 전 세계가 주목했어요.
   과연 연준은 어떤 결정을 내렸을까요?"

[q 필드 — 질문]
- 30자 이내로 명확하게
- context를 읽은 사람이 "오, 이거 알 것 같은데?" 하는 느낌으로
- 4지선다, 정답 1개, 오답 3개는 헷갈리게

[opts 필드 — 보기]
- 각 보기는 10~20자 내외로 구체적으로
- 오답도 "그럴 것 같은" 숫자나 이유를 넣어서 그럴듯하게

[exp 필드 — 한 줄 해설]
- 3문장 이내
- 핵심 키워드 1~2개 <strong> 강조
- 정답인 이유 + 생활 속 비유 1개
- "~해요" 말투

[expert_detail 필드 — 전문가 해설] 모든 문제 필수
경제학 박사가 이론과 실제를 함께 알기 쉽게 설명:
- <span class="expert-label">🎓 박사의 한마디</span> 로 시작
- <p> 태그로 정확히 3개 문단 구성
- 문단1: 관련 경제학 이론 이름 소개 + 괄호 안에 쉬운 풀이
  예: "<strong>수요-공급 법칙(Demand-Supply Law)</strong>에 따르면..."
- 문단2: 역사적 실제 사례 1개 (연도, 나라, 구체적 수치 포함)
- 문단3: <p class="takeaway"> 오늘 기사와 연결한 핵심 한 줄 정리
- 전체 350~450자 내외로 충분히 설명
- "~해요" "~거든요" "~이에요" "~답니다" 말투 혼용

[article_url / article_title 필드]
- 반드시 web_search 도구로 실제 기사를 검색해서 존재하는 URL만 사용할 것
- 검색어 예: "연합뉴스 호르무즈 봉쇄 2026" 또는 "한국경제 코스피 폭락 2026"
- 검색 결과에서 실제로 확인된 URL만 article_url에 넣을 것
- 추측하거나 URL을 임의로 만들지 말 것. 확인된 URL이 없으면 article_url을 null로 설정
- 기사 제목도 실제 기사 제목 그대로 article_title에 저장

[출력] JSON만, 다른 텍스트 없이:
{{
  "date": "{today}",
  "quizzes": [
    {{
      "levelClass": "lv-easy",
      "source": "{today_display} · 출처명",
      "context": "3~4문장 배경 설명 (독자가 뉴스를 모른다고 가정)",
      "q": "질문 (30자 이내)",
      "opts": ["보기1", "보기2", "보기3", "보기4"],
      "ans": 0,
      "exp": "한 줄 해설 HTML (3문장 이내)",
      "expert_detail": "전문가 해설 HTML (3문단, 350~450자)",
      "article_title": "관련 기사 제목",
      "article_url": "https://..."
    }}
  ]
}}
"""

def generate():
    client = anthropic.Anthropic()
    print(f"🤖 [{today}] 퀴즈 생성 시작...")
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=6000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": PROMPT}]
    )

    # text 블록만 모으되, 가장 긴 것(=최종 JSON 응답)을 사용
    texts = [b.text for b in msg.content if hasattr(b, 'text') and b.text.strip()]
    if not texts:
        raise ValueError("텍스트 응답 없음. content 타입: " + str([b.type for b in msg.content]))

    # 가장 긴 텍스트 블록이 최종 JSON일 가능성이 높음
    raw = max(texts, key=len)
    print(f"📄 응답 길이: {len(raw)}자")

    # JSON 블록 추출 — 중첩 중괄호까지 정확히 매칭
    start = raw.find('{')
    if start == -1:
        raise ValueError("JSON 시작 { 없음. 응답:\n" + raw[:300])

    depth, end = 0, -1
    for i, ch in enumerate(raw[start:], start):
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i + 1
                break

    if end == -1:
        raise ValueError("JSON 끝 } 없음. 응답:\n" + raw[:300])

    json_str = raw[start:end]

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        # 특수문자·개행 이슈 시 완화 시도
        json_str_clean = json_str.replace('\n', ' ').replace('\r', '')
        data = json.loads(json_str_clean)

    assert len(data['quizzes']) == 5, f"퀴즈 5개 필요. 실제: {len(data['quizzes'])}개"
    for q in data['quizzes']:
        assert 'context' in q and len(q['context']) > 50, f"context 너무 짧음: {q.get('context','')}"
        assert len(q['opts']) == 4 and 0 <= q['ans'] <= 3
    return data

def save(data):
    with open('quiz_today.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    levels = {'lv-easy':'🌱 입문','lv-mid':'🔥 초급','lv-hard':'⚡ 중급',
              'lv-expert':'💎 고급','lv-master':'👑 최고급'}
    print(f"✅ quiz_today.json 저장 완료 — 퀴즈 {len(data['quizzes'])}개")
    for i, q in enumerate(data['quizzes'], 1):
        print(f"  {i}. [{levels.get(q['levelClass'], q['levelClass'])}] {q['q']}")
        print(f"      📝 {q.get('context','')[:40]}...")

if __name__ == '__main__':
    if not os.environ.get('ANTHROPIC_API_KEY'):
        raise EnvironmentError("ANTHROPIC_API_KEY 없음\n터미널: export ANTHROPIC_API_KEY='sk-...'")
    save(generate())
    print("\n🎉 완료!")
