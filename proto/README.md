# Protocol Buffer Definitions (`socialfeed.v1`)

Proto3 contracts for internal service-to-service communication, defining the
migration path from the current REST/JSON APIs to gRPC (issue #20).

## Layout

| File | Service | RPCs |
|------|---------|------|
| `common.proto` | shared | `ContentType`, `EngagementType` enums |
| `feed_service.proto` | feed-service | `FeedService.GetFeed`, `FeedService.InvalidateFeed` |
| `ranking_engine.proto` | ranking-engine | `RankingService.ScoreCandidates`, `RankingService.ScoreCandidatesStream` (bidi) |
| `user_profile.proto` | user-profile | `UserProfileService.GetProfile` / `GetSocialGraph` / `GetFollowing` / `Follow` |
| `content_ingestion.proto` | content-ingestion | `ContentIngestionService.PublishPost`, `StreamEngagements` (client-streaming) |

Every message mirrors an existing Pydantic model so REST and gRPC payloads
stay semantically identical during the migration:

- `RankedPost`, `FeedResponse` → `services/feed-service/src/models/feed.py`
- `FeedRequest` → `PaginationCursor` in `services/shared/src/models/base.py`
- `ScoreRequest`/`ScoreResponse` → `ScoringRequest`/`ScoringResponse` in `services/ranking-engine/src/main.py`
- `UserProfile`, `SocialGraph` → `services/user-profile/src/main.py`
- `PostEvent`, `EngagementEvent` → `services/shared/src/models/base.py`
- `ContentType`, `EngagementType` → `services/shared/src/models/base.py`

## Conventions

- **Package**: `socialfeed.v1`. Breaking changes require a new `socialfeed.v2`
  package; `v1` messages only ever gain new fields (never renumber or reuse
  field numbers).
- **UUIDs**: encoded as canonical lowercase hyphenated strings
  (`"8f14e45f-ceea-467f-a0e6-8f14e45fceea"`). Protobuf has no native UUID
  type; strings keep payloads debuggable and map 1:1 to the Pydantic `UUID`
  fields.
- **Timestamps**: `google.protobuf.Timestamp` (UTC) everywhere a model uses
  `datetime`.
- **Cursors**: opaque strings; clients must never parse them.
- **Optionality**: proto3 defaults (empty string / 0) represent "unset" for
  fields that are `Optional` in the Pydantic models (e.g. `media_url`,
  `dwell_time_ms`).

## Generating Python stubs

With grpcio-tools (no extra tooling needed):

```bash
pip install grpcio-tools
./scripts/gen_protos.sh            # writes to gen/python (gitignored)
```

Or with [buf](https://buf.build) (also runs lint and breaking-change checks):

```bash
buf lint
buf generate                       # uses buf.gen.yaml, writes to gen/python
```

Generated stubs are **not** committed; regenerate them in each service's
build (Dockerfile step or CI job).

## Migration path: REST → gRPC

The rollout is incremental, one edge at a time, highest-QPS edges first:

1. **Contracts (this PR)** — protos land, stubs are generated, no runtime
   changes. REST remains the only transport.
2. **Dual-serve** — each service adds a `grpc.aio` server alongside FastAPI
   on a separate port (e.g. 50051), registering the servicer generated from
   these protos. Both transports share the existing handler/service layer,
   so behavior is identical. Standard gRPC health checking
   (`grpc.health.v1`) backs k8s readiness probes.
3. **Client cutover per edge** — callers switch behind a config flag
   (`TRANSPORT=grpc|rest`), in dependency order:
   - feed-service → ranking-engine (`ScoreCandidates`): hottest internal
     edge; batch scoring benefits most from protobuf encoding and HTTP/2
     multiplexing.
   - feed-service → user-profile (`GetFollowing`): hot path for candidate
     generation.
   - producers → content-ingestion (`StreamEngagements`): long-lived
     client streams replace per-event JSON posts in front of Kafka.
4. **REST retirement** — once an edge runs 100% gRPC, the internal REST
   route is removed. The api-gateway keeps its public REST surface and
   becomes a REST-to-gRPC translation layer.

Error mapping during dual-serve: `404` → `NOT_FOUND`, `400` →
`INVALID_ARGUMENT`, `429` → `RESOURCE_EXHAUSTED`, `5xx` → `UNAVAILABLE` /
`INTERNAL`.

## Compatibility rules

- Never change a field number or type; add new fields with new numbers.
- Never remove enum values; deprecate with `[deprecated = true]`.
- New RPCs may be added freely; removing one requires a `v2` package.
- `buf breaking --against '.git#branch=main'` enforces this in CI once buf
  is adopted.
