import asyncio
from sqlalchemy import select, desc
from app.database import async_session_maker
from app.models.audit_log import AuditLog
from app.models.student import Student
from app.models.face_embedding import FaceEmbedding
from sqlalchemy import func

async def check():
    async with async_session_maker() as session:
        # Check total students
        stu_count = await session.execute(select(func.count(Student.student_id)))
        print(f"Total students: {stu_count.scalar()}")
        
        # Check total embeddings
        emb_count = await session.execute(select(func.count(FaceEmbedding.id)))
        print(f"Total face embeddings: {emb_count.scalar()}")

        # Get latest audit logs
        stmt = select(AuditLog).order_by(desc(AuditLog.timestamp)).limit(10)
        logs = await session.execute(stmt)
        print("\n--- Latest 10 Audit Logs ---")
        for log in logs.scalars():
            print(f"[{log.timestamp}] {log.event_type} | Student: {log.student_id} | Sim: {log.similarity_score} | Live: {log.liveness_score} | Details: {log.details}")

asyncio.run(check())
