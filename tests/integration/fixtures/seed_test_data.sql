-- Deterministic seed data for the integration test suite (Issue #16).
-- Fixed UUIDs and fixed timestamps so every test run sees identical data.
-- Loaded into the isolated postgres-test container after scripts/init-db.sql.

-- Users (fixed UUIDs)
INSERT INTO users (id, username, display_name, bio, follower_count, following_count, created_at, updated_at) VALUES
    ('00000000-0000-0000-0000-000000000001', 'test_viewer',  'Test Viewer',  'The user whose feed we assert on', 10, 3, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'),
    ('00000000-0000-0000-0000-000000000002', 'author_alpha', 'Author Alpha', 'High-affinity followed author',    500, 5, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'),
    ('00000000-0000-0000-0000-000000000003', 'author_beta',  'Author Beta',  'Followed author',                  200, 8, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z'),
    ('00000000-0000-0000-0000-000000000004', 'author_gamma', 'Author Gamma', 'Trending, not followed',           9000, 1, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');

-- Social graph (viewer follows alpha and beta)
INSERT INTO follows (follower_id, followee_id, created_at) VALUES
    ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', '2026-01-02T00:00:00Z'),
    ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000003', '2026-01-02T00:00:00Z');

-- Posts (fixed UUIDs, fixed timestamps, deterministic engagement counters)
INSERT INTO posts (id, author_id, content_type, text_content, media_url, hashtags, like_count, comment_count, share_count, is_trending, created_at, updated_at) VALUES
    ('aaaaaaaa-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', 'image', 'Fresh high-engagement post from Alpha with a long enough caption to score on quality.', 'https://cdn.test/alpha1.jpg', '{ranking,feeds}', 500, 100, 50, FALSE, '2026-01-10T11:00:00Z', '2026-01-10T11:00:00Z'),
    ('aaaaaaaa-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000002', 'text',  'Second post from Alpha.',                                                              NULL,                          '{feeds}',        40,  10,  2,  FALSE, '2026-01-10T09:00:00Z', '2026-01-10T09:00:00Z'),
    ('bbbbbbbb-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000003', 'video', 'Beta ships a video walkthrough of the ranking pipeline internals.',                    'https://cdn.test/beta1.mp4',  '{video}',        120, 30,  12, FALSE, '2026-01-10T06:00:00Z', '2026-01-10T06:00:00Z'),
    ('bbbbbbbb-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000003', 'text',  'Old low-engagement post from Beta.',                                                   NULL,                          '{}',             1,   0,   0,  FALSE, '2026-01-08T12:00:00Z', '2026-01-08T12:00:00Z'),
    ('cccccccc-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000004', 'image', 'Trending post from Gamma sweeping the network right now.',                             'https://cdn.test/gamma1.jpg', '{trending}',     3000, 800, 400, TRUE, '2026-01-10T10:00:00Z', '2026-01-10T10:00:00Z');

-- Engagement events (fixed UUIDs, fixed timestamps)
INSERT INTO engagement_events (id, user_id, post_id, engagement_type, value, dwell_time_ms, created_at) VALUES
    ('eeeeeeee-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'like',    1.0, 4500, '2026-01-10T11:05:00Z'),
    ('eeeeeeee-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'aaaaaaaa-0000-0000-0000-000000000001', 'comment', 1.0, 9000, '2026-01-10T11:06:00Z'),
    ('eeeeeeee-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001', 'bbbbbbbb-0000-0000-0000-000000000001', 'like',    1.0, 3000, '2026-01-10T11:07:00Z'),
    ('eeeeeeee-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000003', 'cccccccc-0000-0000-0000-000000000001', 'share',   1.0, NULL, '2026-01-10T11:08:00Z');

-- Viewer preferences: prefers video slightly over image
INSERT INTO user_preferences (user_id, content_weights, muted_authors, language, updated_at) VALUES
    ('00000000-0000-0000-0000-000000000001', '{"text": 0.8, "image": 1.0, "video": 1.2, "link": 0.5}', '{}', 'en', '2026-01-01T00:00:00Z');

REFRESH MATERIALIZED VIEW post_engagement_agg;
