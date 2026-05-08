from AOA.gui.main_window import App
from AOA.utils.logging_utils import configure_logging


def main():
    configure_logging()
    App().mainloop()


if __name__ == "__main__":
    main()
