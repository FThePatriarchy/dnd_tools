"""The local web app: API functions, input checks, the job runner and the HTTP server."""
import json
import threading
import time
import urllib.request

import pytest

from engine.app import api
from engine.app.jobs import Jobs


def test_meta_lists_what_the_page_needs():
    m = api.meta()
    assert m["preset_levels"][0] == 1 and "undead" in m["themes"] and len(m["monsters"]) >= 154
    names = [b["name"] for b in m["builds"] if b["class"] == "bard"]
    assert names.index("bard_1") < names.index("bard_3") < names.index("bard_17")  # numeric level order


def test_fight_and_day_return_json_ready_results():
    r = api.fight({"party": {"preset": {"level": 5}}, "monsters": [{"name": "ogre", "count": 2}], "runs": 10})
    assert r["runs"] == 10 and r["budget"]["band"] == "Low" and len(r["characters"]) == 4
    json.dumps(r)
    d = api.day({"party": {"builds": ["fighter_5", "cleric_5"]}, "runs": 10,
                 "steps": [{"encounter": [{"name": "ogre"}]}, {"rest": "short"}, {"encounter": [{"name": "goblin_warrior", "count": 3}]}]})
    assert [s.get("rest") for s in d["steps"]] == [None, "short", None] and d["day_xp"] == 450 + 150
    json.dumps(d)


def test_requests_are_checked():
    with pytest.raises(ValueError, match="unknown monster"): api.fight({"monsters": [{"name": "orc"}]})
    with pytest.raises(ValueError, match="add at least one monster"): api.fight({"monsters": []})
    with pytest.raises(ValueError, match="presets exist"): api.fight({"party": {"preset": {"level": 4}}, "monsters": [{"name": "ogre"}]})
    with pytest.raises(ValueError, match="unknown build"): api.fight({"party": {"builds": ["../etc"]}, "monsters": [{"name": "ogre"}]})
    with pytest.raises(ValueError, match="strategy"): api.fight({"strategy": "berserk", "monsters": [{"name": "ogre"}]})


def test_suggest_and_build_sheet():
    r = api.suggest({"level": 5, "difficulty": "high", "template": "boss_minions", "themes": ["undead"], "count": 2})
    assert r["suggestions"] and all(m["name"] for s in r["suggestions"] for m in s["monsters"])
    sheet = api.build_sheet({"name": "fighter_5"})
    assert sheet["attacks"][0]["damage"] == "2d6+4 slashing"


def test_jobs_run_in_the_background_and_report_errors():
    def ok(req, log): log("working"); return {"x": req["x"]}
    def bad(req, log): raise ValueError("nope")
    jobs = Jobs({"ok": ok, "bad": bad})
    a, b = jobs.start("ok", {"x": 3}), jobs.start("bad", {})
    for _ in range(100):
        if a.status != "running" and b.status != "running": break
        time.sleep(.02)
    assert a.view()["result"] == {"x": 3} and a.view()["log"][0]["message"] == "working"
    assert b.status == "failed" and b.error == "nope"
    with pytest.raises(ValueError): jobs.start("nope", {})


def test_http_server_serves_page_meta_and_jobs():
    from http.server import ThreadingHTTPServer
    from engine.app.server import Handler
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert b"Combat Simulator" in urllib.request.urlopen(base + "/").read()
        assert json.loads(urllib.request.urlopen(base + "/api/meta").read())["preset_levels"]
        post = lambda path, body: urllib.request.urlopen(urllib.request.Request(base + path, json.dumps(body).encode(), {"Content-Type": "application/json"}))
        job = json.loads(post("/api/jobs/fight", {"monsters": [{"name": "ogre"}], "runs": 10}).read())
        for _ in range(300):
            view = json.loads(urllib.request.urlopen(f"{base}/api/jobs/{job['id']}").read())
            if view["status"] != "running": break
            time.sleep(.1)
        assert view["status"] == "done" and view["result"]["runs"] == 10
        with pytest.raises(urllib.error.HTTPError) as err: post("/api/suggest", {"difficulty": "deadly"})
        assert err.value.code == 400
    finally:
        server.shutdown(); server.server_close()


def test_no_resources_floor_and_presets():
    from engine.encounters import run_encounter
    party = ["fighter_5", "cleric_5", "rogue_5", "wizard_5"]
    full = run_encounter(party, ["troll x2"], 60, 1)
    floor = run_encounter(party, ["troll x2"], 60, 1, resources="none")
    assert floor["slots_spent"] == 0 and full["slots_spent"] > 0
    assert floor["defeat"] > full["defeat"] + .1
    with pytest.raises(ValueError): run_encounter(party, ["ogre"], 5, 1, resources="some")
    from engine.day_presets import PRESETS, make_day
    for name in PRESETS:
        day, labels = make_day(name, 5)
        assert len(day["steps"]) == len(PRESETS[name]["slots"]) == len(labels)
    day, labels = make_day("typical", 5, fight=["troll x2"])
    assert day["steps"][-1] == {"encounter": ["troll x2"]}
    assert make_day("typical", 5, seed=1)[1] != make_day("typical", 5, seed=2)[1]
    with pytest.raises(ValueError): make_day("typical", 5, fight=["ogre"], slot=2)  # a rest, not a fight
    with pytest.raises(ValueError): make_day("typical", 5, scale=10)


def test_preset_day_api():
    r = api.preset_day({"party": {"preset": {"level": 5}}, "day_preset": "short", "days": 2, "day_seed": 3})
    assert len(r["days"]) == 2 and r["days"][0]["steps"][1] == {"rest": "short"}
    assert all(m["count"] >= 1 for d in r["days"] for s in d["steps"] if "encounter" in s for m in s["encounter"])
    assert "typical" in api.meta()["day_presets"]


def test_character_builder_preview_save_load_delete(monkeypatch, tmp_path):
    from engine import builder
    monkeypatch.setattr(builder, "USER_BUILDS", tmp_path / "builds")
    recipe = {"class": "fighter", "level": 4, "choices": {"species": "orc", "origin_feat": "lucky",
                                                          "asis": {"4": {"feat": "great_weapon_master", "ability": "str"}}}}
    p = api.preview_build({"recipe": recipe})
    assert p["ok"] and p["sheet"]["name"] == "Fighter 4 (Champion), Orc" and p["sheet"]["abilities"]["str"] == 18
    bad = api.preview_build({"recipe": {"class": "wizard", "level": 5, "choices": {"cantrips": ["Fire Bolt"]}}})
    assert not bad["ok"] and "cantrip" in bad["error"]
    with pytest.raises(ValueError, match="preset"): api.save_build({"name": "fighter_5", "recipe": recipe})
    with pytest.raises(ValueError, match="lowercase"): api.save_build({"name": "Thorin", "recipe": recipe})
    api.save_build({"name": "thorin_4", "recipe": recipe})
    assert {"name": "thorin_4", "class": "fighter", "level": 4, "profile": "mine"} in api.user_builds()
    assert api.load_user_build({"name": "thorin_4"})["recipe"]["choices"]["species"] == "orc"
    from engine.builder import load_character
    assert load_character("thorin_4")["name"] == "Fighter 4 (Champion), Orc"      # loads by name like a preset
    r = api.fight({"party": {"builds": ["thorin_4", "cleric_5"]}, "monsters": [{"name": "ogre"}], "runs": 10})
    assert r["party"][0] == "thorin_4"
    api.delete_build({"name": "thorin_4"})
    assert api.user_builds() == []


def test_builder_options_cover_any_level():
    o = api.builder_options({"class": "wizard", "level": 6})                       # no preset exists at 6
    assert o["start"]["level"] == 6 and o["counts"]["cantrips"] > 0 and "Fireball" in [n for _, n in o["spells"]]
    assert api.preview_build({"recipe": o["start"]})["ok"]
