from datetime import datetime

def now_str() -> str:
    """Returns the current time string in the format YYYY-MM-DD HH:MM:SS."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log(msg: str):
    print(f"[{now_str()}] {msg}")

def log_error(msg: str) -> None:
    print(f"[{now_str()}] [ERROR] {msg}")

if __name__ == '__main__':
    log("This is a log message.")
    log_error("Slot not found")