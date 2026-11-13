from config.env import env_bool

from .base import *  # noqa: F403

DEBUG = env_bool("DJANGO_DEBUG", default=False)
