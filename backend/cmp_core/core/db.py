from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

# 1. Підвантажуємо .env.dev у середовище
load_dotenv(".env", override=True)


class Settings(BaseSettings):
    database_url: str  # буде взято з os.environ після load_dotenv()


settings = Settings()  # завантажиться DATABASE_URL

# 2. Ініціалізація SQLAlchemy
engine: AsyncEngine = create_async_engine(
    settings.database_url, echo=False, future=True
)
AsyncSession = async_sessionmaker(engine, expire_on_commit=False)
