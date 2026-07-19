#!/usr/bin/env python3
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass


BASE_URL = "http://127.0.0.1:8000"
POLL_INTERVAL = 0.15
MAX_STEPS = 200


@dataclass
class BotIdentity:
    name: str
    player_id: str


def api_get(path: str) -> dict:
    req = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_post(path: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def create_room(name: str) -> tuple[str, str]:
    result = api_post("/api/create_room", {"name": name})
    return result["room_code"], result["player_id"]


def join_room(room_code: str, name: str) -> str:
    result = api_post("/api/join_room", {"room_code": room_code, "name": name})
    return result["player_id"]


def get_state(room_code: str, player_id: str) -> dict:
    query = urllib.parse.urlencode({"room": room_code, "player": player_id})
    return api_get(f"/api/state?{query}")["room"]


def play_card(room_code: str, player_id: str, hand_index: int) -> None:
    api_post(
        "/api/play_card",
        {"room_code": room_code, "player_id": player_id, "hand_index": hand_index},
    )


def resolve_choice(room_code: str, player_id: str, target_id: str) -> None:
    api_post(
        "/api/resolve_choice",
        {"room_code": room_code, "player_id": player_id, "target_id": target_id},
    )


def resource_pressure(player: dict) -> int:
    return int(player["clues"]) * 2 + int(player["keys"]) * 3 + int(player["shield"])


def can_open_now(player: dict) -> bool:
    return int(player["clues"]) >= 2 and int(player["keys"]) >= 1


def threat_score(player: dict) -> int:
    score = int(player["score"]) * 100
    if can_open_now(player):
        score += 60
    score += resource_pressure(player)
    return score


def best_opponent_targets(room: dict, me_id: str, metric: str) -> list[dict]:
    opponents = [p for p in room["players"] if p["id"] != me_id]
    max_value = max(int(p[metric]) for p in opponents)
    if max_value <= 0:
        return []
    return [p for p in opponents if int(p[metric]) == max_value]


def resolve_target(room: dict, choice_type: str, options: list[dict]) -> dict:
    option_ids = {option["id"] for option in options}
    candidates = [p for p in room["players"] if p["id"] in option_ids]
    if choice_type == "winner":
        return max(candidates, key=lambda p: (int(p["score"]), resource_pressure(p)))
    if choice_type == "steal_key":
        return max(candidates, key=threat_score)
    return max(candidates, key=threat_score)


def score_card(card: str, me: dict, room: dict) -> float:
    my_score = int(me["score"])
    my_clues = int(me["clues"])
    my_keys = int(me["keys"])
    my_shield = int(me.get("shield", 0))
    turns_left = int(room["turns_left"])
    opponents = [p for p in room["players"] if p["id"] != me["id"]]
    leading_threat = max((threat_score(p) for p in opponents), default=0)
    someone_can_open = any(can_open_now(p) for p in opponents)

    if card == "open":
        if can_open_now(me):
            return 1000 + my_score * 100
        return -80

    if card == "wild":
        if my_clues >= 1 and my_keys >= 1:
            return 930 + my_score * 100
        if my_clues < 2:
            return 330 if turns_left > 2 else 260
        if my_keys < 1:
            return 350 if turns_left > 2 else 280
        return 210

    if card == "steal_key":
        targets = best_opponent_targets(room, me["id"], "keys")
        if not targets:
            return -40
        target = max(targets, key=threat_score)
        base = 420 if can_open_now(target) else 280
        if int(target.get("shield", 0)) > 0:
            base -= 90
        return base + threat_score(target) / 10

    if card == "disrupt":
        targets = best_opponent_targets(room, me["id"], "clues")
        if not targets:
            return -35
        target = max(targets, key=threat_score)
        base = 410 if can_open_now(target) or someone_can_open else 240
        if int(target.get("shield", 0)) > 0:
            base -= 85
        return base + threat_score(target) / 12

    if card == "shield":
        if my_shield > 0:
            return 70
        if someone_can_open or leading_threat >= 70:
            return 300
        return 180

    if card == "double_investigate":
        if my_clues < 2:
            return 360
        if my_keys < 1:
            return 220
        return 150

    if card == "investigate":
        if my_clues < 2:
            return 260
        if my_keys < 1:
            return 130
        return 90

    if card == "key":
        if my_keys < 1:
            return 320
        if my_clues >= 2:
            return 250
        return 140

    return 0


def choose_card_index(room: dict, viewer_state: dict) -> int:
    me = next(p for p in viewer_state["players"] if p["id"] == room["current_player_id"])
    hand = list(me["hand"])
    scored = [(idx, card, score_card(card, me, room)) for idx, card in enumerate(hand)]
    scored.sort(key=lambda item: item[2], reverse=True)
    return scored[0][0]


def autoplay_game(room_code: str, bots: list[BotIdentity]) -> dict:
    host = bots[0]
    history: list[str] = []

    for _ in range(MAX_STEPS):
        room = get_state(room_code, host.player_id)

        if room["status"] == "finished":
            history.append(f"结束：{room['log']}")
            return {
                "room_code": room_code,
                "winner": room["winner_name"],
                "status": room["status"],
                "turns_left": room["turns_left"],
                "history": history,
                "players": room["players"],
                "log": room["log"],
            }

        if room["pending_choice"]:
            chooser = host.player_id
            target = resolve_target(
                room, room["pending_choice"]["type"], room["pending_choice"]["options"]
            )
            resolve_choice(room_code, chooser, target["id"])
            history.append(
                f"裁决：{room['pending_choice']['type']} -> {target['name']}"
            )
            time.sleep(POLL_INTERVAL)
            continue

        current_id = room["current_player_id"]
        current_bot = next(bot for bot in bots if bot.player_id == current_id)
        viewer_state = get_state(room_code, current_bot.player_id)
        hand_owner = next(
            p for p in viewer_state["players"] if p["id"] == current_bot.player_id
        )
        card_index = choose_card_index(room, viewer_state)
        card_name = hand_owner["hand"][card_index]
        play_card(room_code, current_bot.player_id, card_index)
        history.append(f"出牌：{current_bot.name} -> {card_name}")
        time.sleep(POLL_INTERVAL)

    raise RuntimeError("自动对局超过最大步数，疑似卡住了。")


def main() -> int:
    room_code, host_id = create_room("策略A")
    bot_b = join_room(room_code, "策略B")
    bot_c = join_room(room_code, "策略C")
    bots = [
        BotIdentity("策略A", host_id),
        BotIdentity("策略B", bot_b),
        BotIdentity("策略C", bot_c),
    ]
    result = autoplay_game(room_code, bots)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
