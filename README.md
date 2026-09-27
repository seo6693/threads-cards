# threads-cards

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
- 매일 08~22시, 2시간마다 프로젝트별로 1개씩 (계정당 하루 8개)
- 순서는 `RUNBOOK.md` 참고
- 토큰은 저장소 Secrets(`THREADS_TOKEN_NUTRI`, `THREADS_TOKEN_LIVING`)에만 있어요
- 토큰 확인(게시 없음): `checks/request` 파일을 바꿔서 push하면 `checks/result.json`에 결과가 기록돼요
