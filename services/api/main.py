import uvicorn

from app.main import app


def main(run_server: bool = True) -> int:
    """Run the API server or exit successfully for CLI usage."""
    if run_server:
        uvicorn.run(app, host="127.0.0.1", port=8000)  # pragma: no cover

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
