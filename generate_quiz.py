"""
generate_quiz.py
─────────────────────────────────────
GitHub Actions가 매일 오전 6시에 실행하는 스크립트.
최신 경제 뉴스를 기반으로 퀴즈 5개를 생성하고
quiz_today.json 파일로 저장합니다.

로컬 테스트:
  export ANTHROPIC_API_KEY="sk-..."
  python generate_quiz.py
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
1. 입문 (lv-easy)    — "얼마?" "누가?" 단순 사실 확인
2. 초급 (lv-mid)     — "왜?" 원인 묻기
3. 중급 (lv-hard)    — 결과·영향 묻기
4. 고급 (lv-expert)  — 경제 메커니즘 묻기
5. 최고급 (lv-master) — 여러 개념 연결 추론

[질문 규칙]
- 15자 이내, 짧고 임팩트 있게
- 4지선다, 정답 1개
- 오답 3개는 그럴듯하게

[한 줄 해설 (exp)]
- 2문장 이내, 핵심 키워드 1개만 <strong> 강조
- 생활 비유 1개 포함, "~해요" 말투

[전문가 해설 (expert_detail)] 모든 문제 필수
경제학 박사가 이론과 실제를 함께 설명:
- <span class="expert-label">🎓 박사의 한마디</span> 로 시작
- <p> 태그 2~3개 문단
- 문단1: 경제학 이론명 + 쉬운 풀이 (전문용어 뒤 괄호로 설명)
- 문단2: 실제 사례 또는 역사적 선례
- 마지막: <p class="takeaway"> 핵심 한 줄 정리
- <strong>으로 핵심 개념 강조
- "~해요" "~거든요" "~이에요" 말투, 200~300자 내외

[출력] JSON만, 다른 텍스트 없이:
{{
  "date": "{today}",
  "quizzes": [
    {{
      "levelClass": "lv-easy",
      "source": "{today_display} · 출처명",
      "q": "질문 (15자 이내)",
      "opts": ["보기1", "보기2", "보기3", "보기4"],
      "ans": 0,
      "exp": "한 줄 해설 HTML",
      "expert_detail": "전문가 해설 HTML"
    }}
  ]
}}
"""

def generate():
    client = anthropic.Anthropic()
    print(f"🤖 [{today}] 퀴즈 생성 시작...")
    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": PROMPT}]
    )
    raw = msg.content[0].text
    match = re.search(r'\{[\s\S]*\}', raw)
    if not match:
        raise ValueError("JSON 파싱 실패. 응답:\n" + raw[:500])
    data = json.loads(match.group())
    assert len(data['quizzes']) == 5, f"퀴즈 5개 필요. 실제: {len(data['quizzes'])}개"
    for q in data['quizzes']:
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

if __name__ == '__main__':
    if not os.environ.get('ANTHROPIC_API_KEY'):
        raise EnvironmentError("ANTHROPIC_API_KEY 없음\n터미널: export ANTHROPIC_API_KEY='sk-...'")
    save(generate())
    print("\n🎉 완료!")
