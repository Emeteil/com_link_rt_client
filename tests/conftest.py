import pytest

from core.commands.base import BaseCommand


@pytest.fixture(autouse=True)
def reset_command_singletons():
    BaseCommand._instances.clear()
    yield
    BaseCommand._instances.clear()
