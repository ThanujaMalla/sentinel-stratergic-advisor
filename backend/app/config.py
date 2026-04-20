from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    APP_NAME: str = 'Sentinel Strategic Advisor API'

    MONGODB_URI: str="mongodb+srv://thanu582:Thanu%402004@healthcareai.ivdrwbz.mongodb.net/"
    MONGODB_DB: str="News"
    MONGODB_COLLECTION: str="PoliticalNews"
    MONGODB_PROFILE_COLLECTION: str = 'Profiles'

    NEWS_API_KEY: str = ''
    NYC_OPEN_DATA_APP_TOKEN: str = ''
    NYC_OPEN_DATA_BASE_URL: str = 'https://data.cityofnewyork.us'
    YOUTUBE_API_KEY: str = 'AIzaSyA2SYSsQvT3wCjq_iBKE8TiGJDQXnfQq80'
    TWITTER_BEARER: str = ''
    FACTIVA_API_KEY: str = ''
    LEXISNEXIS_API_KEY: str = ''
    GEMINI_API_KEY: str = ''

    model_config = SettingsConfigDict(env_file=str(BASE_DIR / '.env'), extra='ignore')


settings = Settings()
