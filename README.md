# threads-cards

**운영판: https://seo6693.github.io/threads-cards/** (폰·PC 어디서든, 5분마다 자동 새로고침)

쿠팡파트너스 상품을 Threads 계정에 자동으로 올리는 저장소예요.
**프로젝트 하나 = Threads 계정 하나**라서 폴더만 보면 어느 계정 글인지 바로 알 수 있어요.

| 프로젝트 | 계정 | 폴더 |
|---|---|---|
| 영양제 | @kkul394 | `projects/nutri/` |
| 생활용품 | @bagdodo6 | `projects/living/` |

각 프로젝트 폴더:
- `config.json` — 검색 키워드, 상품 선정 기준, 문구 규칙, 카드 색
- `queue/` — 게시 대기 (여기에 올라오면 GitHub Actions가 바로 게시)
- `done/` — 게시 완료 기록 (게시물 주소 포함)
- `failed/` — 실패 기록 (이유 포함)
- `cards/` — 게시물별 카드 이미지
- `state.json` — 다음에 검색할 키워드 순번

다른 폴더에 잘못 들어간 글은 게시되지 않고 `failed/`로 가요.

## 자동 게시
- 계정당 하루 3개 (아침·점심·저녁), 준비 후 4~42분 사이 무작위 시각에 게시
- 글 형식 5가지를 돌려 쓰고, 최근 글과 비슷한 문장·구조는 자동으로 거부해요 (`scripts/formats.json`)
- 순서는 `RUNBOOK.md` 참고
- 토큰은 저장소 Secrets(`THREADS_TOKEN_NUTRI`, `THREADS_TOKEN_LIVING`)에만 있어요
- 토큰 확인(게시 없음): `checks/request` 파일을 바꿔서 push하면 `checks/result.json`에 결과가 기록돼요

## 토큰 자동 갱신
- 매주 수요일 12:17(KST)에 두 계정 토큰을 갱신하고 새 토큰을 Secrets에 다시 저장해요 (`.github/workflows/token-refresh.yml`)
- 필요한 것: Secrets에 `SECRETS_PAT` (이 저장소 "Secrets: Read and write" 권한만 있는 GitHub 접근 키)
- 만료일 기록: `checks/token_status.json` (토큰 값은 저장하지 않아요)
- 실패하면 저장소에 이슈가 열리고 GitHub가 이메일로 알려줘요
- 즉시 점검: `checks/refresh-request`에 `dry-run`이라고 써서 push
