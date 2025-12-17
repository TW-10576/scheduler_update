#!/usr/bin/env python3
"""
Local development runner for Shift Scheduler Backend
Run this with: python run.py
"""

import sys
import subprocess

def main():
    """Run the FastAPI application locally"""
    print("=" * 70)
    print("🚀 Starting Shift Scheduler Backend (Development Mode)")
    print("=" * 70)
    print("\n✅ Configuration:")
    print("   - Database: PostgreSQL at localhost:5432")
    print("   - Server: http://localhost:8000")
    print("   - API Docs: http://localhost:8000/docs")
    print("   - ReDoc: http://localhost:8000/redoc")
    print("\n⏳ Make sure PostgreSQL is running:")
    print("   - Run: docker compose up -d")
    print("   - In another terminal")
    print("\n" + "=" * 70 + "\n")

    try:
        # Run uvicorn with reload for development
        import os
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        subprocess.run(
            [
                sys.executable, "-m", "uvicorn",
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ],
            cwd=backend_dir
        )
    except KeyboardInterrupt:
        print("\n\n🛑 Backend stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
