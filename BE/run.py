"""
Start the server without --reload to avoid Python 3.14 multiprocessing/logging crash.
Usage: python run.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
