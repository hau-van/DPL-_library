import asyncio
import sys
import os
from dotenv import load_dotenv
import psycopg

# Load env
load_dotenv()

async def update_schema_and_promote(student_id):
    # Get DB URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ Không tìm thấy DATABASE_URL trong file .env")
        return

    # Remove SQLAlchemy async driver prefix for direct psycopg connection
    if db_url.startswith("postgresql+psycopg_async://"):
        db_url = db_url.replace("postgresql+psycopg_async://", "postgresql://")
    elif db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        # Connect directly to Postgres
        conn = await psycopg.AsyncConnection.connect(db_url)
        
        print("--- 1. Cập nhật cấu trúc Database ---")
        async with conn.cursor() as cur:
            # Add role column if not exists
            await cur.execute(
                "ALTER TABLE students ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'STUDENT';"
            )
        print("✅ Đã đảm bảo cột 'role' tồn tại trong bảng 'students'.")

        print(f"--- 2. Nâng cấp quyền cho {student_id} ---")
        async with conn.cursor() as cur:
            # Update student role
            await cur.execute(
                "UPDATE students SET role = 'ADMIN' WHERE student_id = %s",
                (student_id,),
            )
            updated = cur.rowcount
        
        await conn.commit()

        if updated == 1:
            print(f"✅ Đã nâng cấp {student_id} lên thành ADMIN thành công!")
            print("Bây giờ bạn có thể dùng khuôn mặt của người này để vào giao diện Admin.")
        else:
            print(f"❌ Không tìm thấy sinh viên với ID: {student_id}")

        await conn.close()
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Sử dụng: .\\.venv\\Scripts\\python update_admin.py <student_id>")
    else:
        # Load env vars first
        asyncio.run(update_schema_and_promote(sys.argv[1]))
