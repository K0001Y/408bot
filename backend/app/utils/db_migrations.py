"""
数据库迁移模块

简易版本化迁移系统：
- 维护 schema_version 表追踪已应用的迁移版本
- 每次启动时自动执行未应用的迁移
- 支持 WAL 模式提升并发写入性能
"""

import aiosqlite

from app.utils.logging import get_logger

logger = get_logger("db_migrations")


# 迁移定义：(版本号, 描述, SQL 语句列表)
MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (
        1,
        "创建 mistakes 表",
        [
            """
            CREATE TABLE IF NOT EXISTS mistakes (
                mistake_id TEXT PRIMARY KEY,
                subject_code TEXT NOT NULL,
                page INTEGER NOT NULL,
                chapter TEXT NOT NULL,
                question_number INTEGER NOT NULL,
                question_text TEXT DEFAULT '',
                answer_text TEXT DEFAULT '',
                explanation TEXT DEFAULT '',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ],
    ),
    (
        2,
        "添加 updated_at 列",
        [
            """
            ALTER TABLE mistakes ADD COLUMN updated_at TIMESTAMP DEFAULT NULL
            """,
        ],
    ),
]


async def run_migrations(db_path: str) -> None:
    """
    执行数据库迁移。

    Args:
        db_path: SQLite 数据库文件路径
    """
    async with aiosqlite.connect(db_path) as db:
        # 启用 WAL 模式（提升并发写入性能）
        await db.execute("PRAGMA journal_mode=WAL")

        # 创建迁移版本追踪表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

        # 查询已应用的最大版本
        async with db.execute("SELECT MAX(version) FROM schema_version") as cursor:
            row = await cursor.fetchone()
            current_version = row[0] if row[0] is not None else 0

        logger.info("当前数据库版本: %d, 共有 %d 个迁移", current_version, len(MIGRATIONS))

        # 逐个执行未应用的迁移
        applied = 0
        for version, description, sqls in MIGRATIONS:
            if version <= current_version:
                continue

            logger.info("执行迁移 V%d: %s", version, description)
            try:
                for sql in sqls:
                    await db.execute(sql)

                # 记录已应用
                await db.execute(
                    "INSERT INTO schema_version (version, description) VALUES (?, ?)",
                    (version, description),
                )
                await db.commit()
                applied += 1
                logger.info("迁移 V%d 执行成功", version)

            except Exception as e:
                # ALTER TABLE ADD COLUMN 在列已存在时会报错，安全跳过
                error_msg = str(e).lower()
                if "duplicate column" in error_msg or "already exists" in error_msg:
                    logger.info("迁移 V%d 跳过（结构已存在）", version)
                    await db.execute(
                        "INSERT OR REPLACE INTO schema_version (version, description) VALUES (?, ?)",
                        (version, description),
                    )
                    await db.commit()
                else:
                    logger.error("迁移 V%d 失败: %s", version, str(e), exc_info=True)
                    raise

        if applied > 0:
            logger.info("数据库迁移完成, 新应用 %d 个迁移, 当前版本: V%d", applied, version)
        else:
            logger.info("数据库已是最新版本 V%d", current_version)
