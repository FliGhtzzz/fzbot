"""Regression checks run with isolated JSON files and mocked external services."""
import asyncio
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import data_paths
import duel
import http_client
import linkcf
import main
import storage
import views


def problem(contest=1):
    return {"contestId": contest, "index": "A", "name": "Example", "rating": 800,
            "url": f"https://codeforces.com/problemset/problem/{contest}/A"}


def duel_info():
    return {"duel_id": "original", "start_time": 100, "end_time": 200,
            "challenger_dc": "c", "opponent_dc": "o", "challenger_cf": "c_cf",
            "opponent_cf": "o_cf", "challenger_id": "11", "opponent_id": "22",
            "guild_id": 99, "update_channel_id": 123, "update_message_id": 456,
            "problems": [problem()], "num_problems": 1}


class IsolatedData:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fzbot-tests-")
        self.paths = patch.object(data_paths, "DATA_DIR", Path(self.temp.name))
        self.paths.start()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.paths.stop)


class RuntimeTests(IsolatedData, unittest.TestCase):
    def test_unlink_keeps_other_accounts(self):
        linkcf._save_link_data({"one": {"linked": True}, "two": {"linked": True}})
        self.assertIn("successfully", linkcf.unlink("one"))
        self.assertEqual(linkcf._load_link_data(), {"two": {"linked": True}})

    def test_corrupt_json_is_not_silently_erased(self):
        path = Path(data_paths.data_path("link.json"))
        path.write_text("{bad")
        with self.assertRaises(ValueError):
            linkcf._load_link_data()
        self.assertEqual(path.read_text(), "{bad")

    def test_force_check_does_not_finish_early(self):
        with patch.object(duel.time, "time", return_value=180), patch.object(duel, "_check_solved_problems", return_value={}):
            self.assertEqual(duel.check_duel_result(duel_info(), force_check=True)["status"], "active")

    def test_deadline_finishes_duel(self):
        with patch.object(duel.time, "time", return_value=200), patch.object(duel, "_check_solved_problems", return_value={}):
            self.assertEqual(duel.check_duel_result(duel_info())["status"], "completed")

    def test_submissions_use_window_and_full_problem_id(self):
        submissions = [{"verdict": "OK", "creationTimeSeconds": when,
                        "problem": {"contestId": contest, "index": "A"}}
                       for contest, when in [(1, 90), (1, 110), (1, 120), (2, 115), (2, 210)]]
        response = Mock()
        response.json.return_value = {"status": "OK", "result": submissions}
        with patch.object(duel, "http_get", return_value=response):
            self.assertEqual(duel._check_solved_problems("c", [problem(1), problem(2)], 100, 200),
                             {"1:A": 110, "2:A": 115})

    def test_api_failure_does_not_award_false_tie(self):
        with patch.object(duel, "http_get", side_effect=TimeoutError("mock timeout")):
            self.assertEqual(duel.check_duel_result(duel_info())["status"], "retry")

    def test_finalization_preserves_new_entries_and_runs_once(self):
        info = duel_info()
        duel._save_duel({"pending": {"new-pending": {}}, "active": {"old": info, "new": {"start_time": 999}}, "history": []})
        result = duel._build_tie_result(info, {}, {}, "time up")
        self.assertTrue(duel.finalize_duel("old", info, result))
        self.assertFalse(duel.finalize_duel("old", info, result))
        state = duel._load_duel()
        self.assertIn("new", state["active"])
        self.assertIn("new-pending", state["pending"])
        self.assertEqual(len(state["history"]), 1)
        self.assertEqual(duel.get_user_stats("c")["ties"], 1)

    def test_stale_result_does_not_finalize_replacement(self):
        info = duel_info()
        newer = dict(info, duel_id="replacement")
        duel._save_duel({"pending": {}, "active": {"same-key": newer}, "history": []})
        self.assertFalse(duel.finalize_duel("same-key", info, {"winner": None}))
        self.assertEqual(duel._load_duel()["active"]["same-key"]["duel_id"], "replacement")

    def test_expiry_keeps_unexpired_pending(self):
        duel._save_duel({"pending": {"expired": {"expires_at": 1}, "new": {"expires_at": 100}}, "active": {}, "history": []})
        self.assertEqual(duel.expire_pending(now=50), [("expired", {"expires_at": 1})])
        self.assertIn("new", duel._load_duel()["pending"])

    def test_accept_preserves_guild_and_participant_ids(self):
        info = dict(duel_info(), expires_at=300, duration_minutes=5)
        duel._save_duel({"pending": {"challenge": info}, "active": {}, "history": []})
        with patch.object(duel.time, "time", return_value=150):
            active = duel.accept_pending("challenge", 99, 123, 456)
        self.assertEqual(active["opponent_id"], "22")
        self.assertEqual(active["guild_id"], 99)
        self.assertEqual(active["end_time"], 450)
        self.assertIsNone(duel.accept_pending("challenge", 99, 123, 456))

    def test_http_default_timeout_and_status_check(self):
        response = Mock()
        with patch.object(http_client.requests, "get", return_value=response) as get:
            self.assertIs(http_client.http_get("https://example.com"), response)
        get.assert_called_once_with("https://example.com", timeout=(5, 15))
        response.raise_for_status.assert_called_once()


class AsyncRuntimeTests(IsolatedData, unittest.IsolatedAsyncioTestCase):
    async def test_unlink_does_not_replace_running_event_loop(self):
        loop = asyncio.get_running_loop()
        linkcf.unlink("missing")
        self.assertIs(asyncio.get_running_loop(), loop)

    async def test_search_acknowledges_then_uses_worker_thread(self):
        response = SimpleNamespace(defer=AsyncMock())
        interaction = SimpleNamespace(response=response, followup=SimpleNamespace(send=AsyncMock()), user=object())
        original_thread = threading.get_ident()
        def build(*args):
            self.assertTrue(response.defer.await_count)
            self.assertNotEqual(threading.get_ident(), original_thread)
            return "embed"
        with patch.object(main.auto_role, "build_rating_embed", side_effect=build):
            await main.searchcf.callback(interaction, "example")
        interaction.followup.send.assert_awaited_once_with(embed="embed")

    async def test_new_duel_created_during_notification_survives(self):
        info = duel_info()
        duel._save_duel({"pending": {}, "active": {"old": info}, "history": []})
        async def fetch(message_id):
            state = duel._load_duel()
            state["active"]["new"] = {"start_time": 999}
            duel._save_duel(state)
            return SimpleNamespace(edit=AsyncMock())
        channel = SimpleNamespace(fetch_message=fetch)
        guild = SimpleNamespace(get_channel=Mock(return_value=channel))
        bot = SimpleNamespace(get_guild=Mock(return_value=guild))
        result = duel._build_tie_result(info, {}, {}, "time up")
        with patch.object(main, "bot", bot), patch.object(duel, "check_duel_result", return_value=result), patch.object(main, "duel_participant", new=AsyncMock(return_value=None)):
            await main.check_and_finalize_duels()
        self.assertIn("new", duel._load_duel()["active"])
        bot.get_guild.assert_called_with(99)

    async def test_participants_resolve_by_id(self):
        user = object()
        bot = SimpleNamespace(get_user=Mock(return_value=user))
        with patch.object(main, "bot", bot):
            self.assertIs(await main.duel_participant(duel_info(), "opponent"), user)
        bot.get_user.assert_called_once_with(22)

    async def test_restore_persistent_menu_and_skip_duplicate_registration(self):
        storage.write_json("role_selects.json", {"menus": {"456": {"guild_id": 99, "channel_id": 123, "roles": {"7": "Role"}}}})
        message = SimpleNamespace(edit=AsyncMock())
        channel = SimpleNamespace(fetch_message=AsyncMock(return_value=message))
        guild = SimpleNamespace(id=99, get_channel=Mock(return_value=channel))
        bot = SimpleNamespace(get_guild=Mock(return_value=guild), add_view=Mock())
        await views.restore_role_menus(bot)
        view = bot.add_view.call_args.args[0]
        self.assertTrue(view.is_persistent())
        self.assertEqual(view.children[0].custom_id, "fzbot:roles:open")
        bot.add_view.assert_called_once_with(view, message_id=456)
        await views.restore_role_menus(bot)
        self.assertEqual(bot.add_view.call_count, 1)

    async def test_public_menu_opens_private_member_selection(self):
        role = SimpleNamespace(id=7, name="Role")
        member = SimpleNamespace(roles=[role])
        guild = SimpleNamespace(id=99, get_role=Mock(return_value=role))
        interaction = SimpleNamespace(guild=guild, user=member, response=SimpleNamespace(send_message=AsyncMock()))
        view = views.PersistentRoleMenu(guild, [7])
        await view.open_roles.callback(interaction)
        arguments = interaction.response.send_message.call_args.kwargs
        self.assertTrue(arguments["ephemeral"])
        private = arguments["view"]
        self.assertTrue(private.children[0].options[0].default)
        self.assertEqual(private.timeout, 180)


if __name__ == "__main__":
    unittest.main()
