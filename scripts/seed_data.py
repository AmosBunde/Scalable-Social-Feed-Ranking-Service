#!/usr/bin/env python3
"""Seed sample data for local development."""
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

NUM_USERS = 50
NUM_POSTS = 500
NUM_ENGAGEMENTS = 2000

CONTENT_TYPES = ["text", "image", "video", "link"]
ENGAGEMENT_TYPES = ["like", "comment", "share", "follow", "dwell"]

def generate_users(n):
    users = []
    for i in range(n):
        users.append({
            "id": str(uuid.uuid4()),
            "username": f"user_{i:04d}",
            "display_name": f"User {i}",
            "bio": f"Bio for user {i}",
            "follower_count": random.randint(0, 10000),
            "following_count": random.randint(0, 500),
        })
    return users

def generate_posts(users, n):
    posts = []
    now = datetime.now(timezone.utc)
    for _ in range(n):
        author = random.choice(users)
        age_hours = random.uniform(0.1, 168)
        posts.append({
            "id": str(uuid.uuid4()),
            "author_id": author["id"],
            "content_type": random.choice(CONTENT_TYPES),
            "text_content": f"Sample post content {random.randint(1, 10000)}",
            "like_count": random.randint(0, 500),
            "comment_count": random.randint(0, 100),
            "share_count": random.randint(0, 50),
            "is_trending": random.random() < 0.05,
            "created_at": (now - timedelta(hours=age_hours)).isoformat(),
        })
    return posts

def generate_follows(users, avg_following=20):
    follows = []
    for user in users:
        n_following = min(random.randint(5, avg_following * 2), len(users) - 1)
        targets = random.sample([u for u in users if u["id"] != user["id"]], n_following)
        for target in targets:
            follows.append({
                "follower_id": user["id"],
                "followee_id": target["id"],
            })
    return follows

def generate_engagements(users, posts, n):
    events = []
    now = datetime.now(timezone.utc)
    for _ in range(n):
        user = random.choice(users)
        post = random.choice(posts)
        events.append({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "post_id": post["id"],
            "engagement_type": random.choice(ENGAGEMENT_TYPES),
            "value": 1.0,
            "dwell_time_ms": random.randint(500, 30000) if random.random() < 0.3 else None,
            "created_at": (now - timedelta(hours=random.uniform(0, 72))).isoformat(),
        })
    return events


if __name__ == "__main__":
    print("Generating seed data...")
    users = generate_users(NUM_USERS)
    posts = generate_posts(users, NUM_POSTS)
    follows = generate_follows(users)
    engagements = generate_engagements(users, posts, NUM_ENGAGEMENTS)

    data = {
        "users": users,
        "posts": posts,
        "follows": follows,
        "engagements": engagements,
    }

    with open("scripts/seed-data.json", "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Generated: {len(users)} users, {len(posts)} posts, "
          f"{len(follows)} follows, {len(engagements)} engagements")
    print("Saved to scripts/seed-data.json")
