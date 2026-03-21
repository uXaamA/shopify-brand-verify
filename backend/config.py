
# Central configuration module that loads and validates all environment variables using Pydantic.
# Ensures secure, structured access to sensitive settings like API keys, database URL, and app secrets.


from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SHOPIFY_API_KEY: str
    SHOPIFY_API_SECRET: str
    SHOPIFY_APP_URL: str
    DATABASE_URL: str
    SECRET_KEY: str
    APP_ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()