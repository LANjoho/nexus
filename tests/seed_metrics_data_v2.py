"""Compatibility wrapper around the canonical fake-data seeder."""

from tests.seed_metrics_data import SeedConfig, seed_fake_metrics


if __name__ == "__main__":
    summary = seed_fake_metrics(
        SeedConfig(
            db_path="clinic.db",
            room_count=8,
            days_back=7,
            cycles_per_room=5,
            stuck_rooms=1,
            reset=True,
            seed=24,
        )
    )
    
    print("Database seeded successfully.")
    for key, value in summary.items():
        print(f"  - {key}: {value}")