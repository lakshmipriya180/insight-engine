"""Generate a realistic synthetic feedback dataset (deterministic, seed=42).

Builds ~600 records across 6 planted themes + noise, so the clustering
pipeline has genuine structure to discover.
"""
import csv
import random
from pathlib import Path

random.seed(42)

OUT = Path(__file__).resolve().parent.parent / "data" / "sample_feedback.csv"

THEMES = {
    "sync_bugs": {
        "templates": [
            "The mobile app keeps losing my data when I sync between devices. {tail}",
            "Sync failed again and I lost my notes from yesterday. {tail}",
            "Calendar sync is broken since the last update, events just disappear. {tail}",
            "My tasks vanish after syncing, this is the third time. {tail}",
            "Sync conflict destroyed my shopping list, no way to recover it. {tail}",
        ],
        "tails": ["Please fix this!", "This is unacceptable.", "Losing trust fast.",
                  "I might cancel my subscription.", "Really frustrating."],
        "rating_range": (1, 2), "weight": 110, "sources": ["ticket", "review"],
    },
    "pricing_confusion": {
        "templates": [
            "I don't understand what the premium plan actually includes. {tail}",
            "Got charged twice this month and can't find where to see my invoices. {tail}",
            "The difference between the family plan and duo plan is confusing. {tail}",
            "Why did my price go up without any notice? {tail}",
            "The billing page is impossible to navigate, I just want a refund. {tail}",
        ],
        "tails": ["Please clarify.", "Support hasn't replied.", "Make pricing simpler.",
                  "Very confusing.", "Not happy about this."],
        "rating_range": (1, 3), "weight": 90, "sources": ["ticket", "survey"],
    },
    "onboarding_love": {
        "templates": [
            "The setup wizard was so easy, I had everything running in five minutes. {tail}",
            "Love how the onboarding walks you through creating your first project. {tail}",
            "Getting started was seamless, the tutorial is excellent. {tail}",
            "Signed up yesterday and I'm already fully set up. Great first experience. {tail}",
            "The welcome checklist made setup intuitive even for my partner. {tail}",
        ],
        "tails": ["Great job!", "Keep it up.", "Impressed so far.", "Well done team.",
                  "Best onboarding I've seen."],
        "rating_range": (4, 5), "weight": 100, "sources": ["review", "survey"],
    },
    "notifications_noise": {
        "templates": [
            "Way too many notifications, I get pinged for every tiny update. {tail}",
            "The reminder emails are relentless, let me control the frequency. {tail}",
            "Push notifications are annoying and there's no granular mute option. {tail}",
            "I want notifications for mentions only, not everything. {tail}",
            "Daily digest would be better than constant alerts. {tail}",
        ],
        "tails": ["Please add settings for this.", "It's overwhelming.", "Considering turning them all off.",
                  "Needs work.", "Otherwise good product."],
        "rating_range": (2, 4), "weight": 85, "sources": ["review", "survey", "ticket"],
    },
    "search_feature_request": {
        "templates": [
            "Search can't find items in archived projects, please add that. {tail}",
            "Would love filters in search — by date, by person, by tag. {tail}",
            "Search is too basic, no fuzzy matching so typos return nothing. {tail}",
            "Please add global search across all workspaces. {tail}",
            "Search results ordering makes no sense, newest should come first. {tail}",
        ],
        "tails": ["Would make it perfect.", "Happy to beta test.", "This is my top request.",
                  "Otherwise loving it.", "Hope this is on the roadmap."],
        "rating_range": (3, 4), "weight": 95, "sources": ["survey", "review"],
    },
    "performance_praise": {
        "templates": [
            "The app is noticeably faster after the update, great work. {tail}",
            "Loads instantly even with hundreds of tasks, very impressed. {tail}",
            "Smooth and reliable on my old phone, well optimized. {tail}",
            "Fast, clean, and it just works. {tail}",
            "Performance is excellent compared to the competitors I tried. {tail}",
        ],
        "tails": ["Keep it up!", "Five stars.", "Recommending to friends.", "Solid app.",
                  "No complaints."],
        "rating_range": (4, 5), "weight": 80, "sources": ["review"],
    },
}

NOISE = [
    "Just downloaded the app, will report back.",
    "How do I contact support?",
    "Is there a student discount?",
    "The logo colors look different on Android.",
    "Does this integrate with my smart fridge?",
    "First!",
    "Using this for my book club.",
    "What time zone does the server use?",
]


def main() -> None:
    rows: list[dict] = []
    for spec in THEMES.values():
        for _ in range(spec["weight"]):
            template = random.choice(spec["templates"])
            tail = random.choice(spec["tails"])
            rows.append({
                "source": random.choice(spec["sources"]),
                "text": template.format(tail=tail),
                "rating": random.randint(*spec["rating_range"]),
            })
    for _ in range(40):  # noise records
        rows.append({
            "source": random.choice(["review", "survey", "ticket"]),
            "text": random.choice(NOISE),
            "rating": random.choice([None, random.randint(2, 5)]),
        })

    random.shuffle(rows)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["source", "text", "rating"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} records to {OUT}")


if __name__ == "__main__":
    main()
