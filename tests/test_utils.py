import os
import sys
import pytest
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import api.utilities.utils as utils


@pytest.mark.asyncio
async def test_rsn():
    assert await utils.is_valid_rsn("Ferrariic") == True
    assert await utils.is_valid_rsn("$$$$$$") == False


@pytest.mark.asyncio
async def test_verify_ID():
    assert await utils.verify_ID("3484373727") == True
    assert await utils.verify_ID("abehehdheff09309393") == False


@pytest.mark.asyncio
async def test_clean_notes():
    assert await utils.clean_text("hello") == "hello"
    assert await utils.clean_text("""<a href="www.google.com">google</a>""") == "google"
    assert await utils.clean_text(" hello ") == "hello"
    assert await utils.clean_text("wtf") == "****"


@pytest.mark.asyncio
async def test_sha256():
    assert (
        utils.sha256(string="hello")
        == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )
    assert (
        utils.sha256(string="goodbye")
        == "82e35a63ceba37e9646434c5dd412ea577147f1e4a41ccde1614253187e3dbf9"
    )


@pytest.mark.asyncio
async def test_verify_user_agent():
    assert await utils.verify_user_agent(user_agent="RuneLite") == True
    assert await utils.verify_user_agent(user_agent="RuneLite-38ff4h") == True
    assert await utils.verify_user_agent(user_agent="OpenOSRS") == False
    assert await utils.verify_user_agent(user_agent="BlueLite") == False


@pytest.mark.asyncio
async def test_verify_plugin_version():
    assert await utils.verify_plugin_version(plugin_version="v2.0.0-alpha") == True
    assert await utils.verify_plugin_version(plugin_version="v1.0.0-alpha") == False


@pytest.mark.asyncio
async def test_is_valid_rsn():
    assert await utils.is_valid_rsn(login="Ferrariic") == True
    assert await utils.is_valid_rsn(login="Ferrariic$") == False
    assert await utils.is_valid_rsn(login="Ferrariiiiiiiiiiiiiiiiiiic") == False
    assert await utils.is_valid_rsn(login="@") == False


@pytest.mark.asyncio
async def test_validate_discord():
    assert await utils.validate_discord(discord="@Ferrariic#0001") == False
    assert await utils.validate_discord(discord="Ferrariic#0001") == False
    assert await utils.validate_discord(discord="@Ferrariic0001") == False
    assert await utils.validate_discord(discord="@Ferrariic") == False
    assert await utils.validate_discord(discord="Ferrariic0001") == False
    assert await utils.validate_discord(discord="178965680266149888") == False


@pytest.mark.asyncio
async def test_verify_token_construction():
    assert (
        await utils.verify_token_construction(token="y5BAz6OiYaZO-8YpQf_OLUWT6Q3WK-6K")
        == True
    )
    assert (
        await utils.verify_token_construction(token="yrBdz6kilaZh8YpQf_zLUmT6Q3WK-6Kz")
        == True
    )
    assert (
        await utils.verify_token_construction(token="yrBdz6kilaZh8YpQf_zLUmT6Q3WK-6K")
        == False
    )
    assert (
        await utils.verify_token_construction(token="yrBdz6k$laZh8YpQf_zLUmT6Q3WK-6K")
        == False
    )
    assert (
        await utils.verify_token_construction(token="yrBdz6k$laZh8YpQf_3WK-6K") == False
    )


@pytest.mark.asyncio
async def test_verify_discord_id():
    assert await utils.verify_discord_id(discord_id="NULL") == True
    assert await utils.verify_discord_id(discord_id="178965680266149888") == True
    assert await utils.verify_discord_id(discord_id="17896568$$$$266149888") == False
    assert await utils.verify_discord_id(discord_id="Ferrariic#0001") == False
    assert await utils.verify_discord_id(discord_id="@Ferrariic#0001") == False


@pytest.mark.asyncio
async def test_sanitize():
    assert await utils.sanitize(string=" ") == None
    assert await utils.sanitize(string=" r") == "R"
    assert await utils.sanitize(string="r") == "R"


@pytest.mark.asyncio
async def test_match_ID_pairing():
    for i in range(0, 1000):
        valid = re.fullmatch("^[a-z]{2,7}-[a-z]{2,7}-[a-z]{2,7}", utils.matchID())
        assert valid != None
