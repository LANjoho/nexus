def seconds_to_mmss(seconds):
    if seconds is None:
        return "-"
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}m {secs:02d}s"