import threading


def run_in_thread(target, daemon=True):
    thread = threading.Thread(target=target, daemon=daemon)
    thread.start()
    return thread
