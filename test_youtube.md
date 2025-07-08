---
marp: true
theme: default
paginate: true
---

# YouTube 임베딩 테스트

이 슬라이드는 YouTube 링크 임베딩을 테스트합니다.

---

## 테스트 1: YouTube 링크들

다음은 AI 관련 영상입니다:

https://www.youtube.com/watch?v=abc123def456

이것은 일반 텍스트 사이에 있는 링크입니다 https://youtu.be/xyz789ghi012 이렇게요.

---

## 테스트 2: 일반 링크들

일반 웹사이트 링크들도 자동으로 변환됩니다:

- https://www.google.com
- www.github.com
- https://openai.com/chatgpt

[마크다운 링크](https://www.example.com)도 지원됩니다.

---

## 테스트 3: 코드 블록

```python
# YouTube API 예제
import requests

url = "https://www.youtube.com/watch?v=test123"
response = requests.get(url)
```

코드 블록 안의 URL은 변환되지 않습니다.