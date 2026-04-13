-- Social Feed Ranking Service: Database Schema
-- PostgreSQL 16

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    bio TEXT,
    avatar_url TEXT,
    follower_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);

-- Posts table
CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    author_id UUID NOT NULL REFERENCES users(id),
    content_type VARCHAR(16) NOT NULL DEFAULT 'text',
    text_content TEXT,
    media_url TEXT,
    hashtags TEXT[] DEFAULT '{}',
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    is_trending BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_posts_author ON posts(author_id);
CREATE INDEX idx_posts_created ON posts(created_at DESC);
CREATE INDEX idx_posts_trending ON posts(is_trending) WHERE is_trending = TRUE;

-- Social graph (follows)
CREATE TABLE IF NOT EXISTS follows (
    follower_id UUID NOT NULL REFERENCES users(id),
    followee_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (follower_id, followee_id)
);

CREATE INDEX idx_follows_follower ON follows(follower_id);
CREATE INDEX idx_follows_followee ON follows(followee_id);

-- Engagement events (append-only)
CREATE TABLE IF NOT EXISTS engagement_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    post_id UUID NOT NULL REFERENCES posts(id),
    engagement_type VARCHAR(16) NOT NULL,
    value FLOAT DEFAULT 1.0,
    dwell_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_engagement_post ON engagement_events(post_id, created_at DESC);
CREATE INDEX idx_engagement_user ON engagement_events(user_id, created_at DESC);
CREATE INDEX idx_engagement_type ON engagement_events(engagement_type);

-- Materialized view: engagement aggregates (refreshed periodically)
CREATE MATERIALIZED VIEW IF NOT EXISTS post_engagement_agg AS
SELECT
    post_id,
    COUNT(*) FILTER (WHERE engagement_type = 'like') AS like_count_total,
    COUNT(*) FILTER (WHERE engagement_type = 'comment') AS comment_count_total,
    COUNT(*) FILTER (WHERE engagement_type = 'share') AS share_count_total,
    COUNT(*) FILTER (WHERE engagement_type = 'like' AND created_at > NOW() - INTERVAL '1 hour') AS like_count_1h,
    COUNT(*) FILTER (WHERE engagement_type = 'like' AND created_at > NOW() - INTERVAL '24 hours') AS like_count_24h,
    AVG(dwell_time_ms) FILTER (WHERE dwell_time_ms IS NOT NULL) AS avg_dwell_ms
FROM engagement_events
GROUP BY post_id;

CREATE UNIQUE INDEX idx_post_engagement_agg ON post_engagement_agg(post_id);

-- User preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    content_weights JSONB DEFAULT '{"text": 1.0, "image": 1.2, "video": 1.1, "link": 0.8}',
    muted_authors UUID[] DEFAULT '{}',
    language VARCHAR(8) DEFAULT 'en',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
