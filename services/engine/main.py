from quantsail_engine.main import main as engine_main


def main() -> int:
    return engine_main()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
