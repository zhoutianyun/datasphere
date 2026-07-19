"""
MCP Server for 三机对抗 (Three Agent Card Room)
Exposes the game API as MCP tools for AI agents.
"""
import json
import urllib.request
import urllib.error

GAME_SERVER_URL = "http://localhost:8000"

def _api_post(path: str, data: dict) -> dict:
    """Call the game server HTTP API."""
    url = f"{GAME_SERVER_URL}{path}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def _api_get(path: str) -> dict:
    """Call the game server HTTP GET API."""
    url = f"{GAME_SERVER_URL}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("三机对抗卡牌游戏")

@mcp.tool()
def create_ai_game(name: str = "Agent") -> str:
    """创建一局人机对战游戏。返回房间号和玩家ID。"""
    result = _api_post("/api/create_ai_game", {"name": name})
    if result.get("ok"):
        return json.dumps({
            "room_code": result["room_code"],
            "player_id": result["player_id"],
            "message": f"游戏创建成功！房间号: {result['room_code']}"
        }, ensure_ascii=False)
    return json.dumps({"error": result.get("error", "创建失败")}, ensure_ascii=False)

@mcp.tool()
def get_game_state(room_code: str, player_id: str) -> str:
    """获取当前游戏状态，包括手牌、分数、线索、钥匙等。"""
    result = _api_get(f"/api/state?room={room_code}&player={player_id}")
    if result.get("ok"):
        room = result["room"]
        players_info = []
        for p in room["players"]:
            info = {
                "name": p["name"],
                "score": p["score"],
                "clues": p["clues"],
                "keys": p["keys"],
                "shield": p["shield"],
                "hand_count": p["hand_count"],
            }
            if not p.get("is_ai"):
                info["hand"] = p.get("hand", [])
            players_info.append(info)
        return json.dumps({
            "status": room["status"],
            "current_player_id": room["current_player_id"],
            "players": players_info,
            "log": room["log"],
            "deck_size": room["shared_deck_size"],
            "turn": room["turn_number"],
            "winner": room.get("winner_name", "")
        }, ensure_ascii=False)
    return json.dumps({"error": result.get("error", "获取失败")}, ensure_ascii=False)

@mcp.tool()
def play_card(room_code: str, player_id: str, hand_index: int) -> str:
    """出牌。hand_index是手牌中的位置(0开始)。"""
    result = _api_post("/api/play_card", {
        "room_code": room_code,
        "player_id": player_id,
        "hand_index": hand_index
    })
    if result.get("ok"):
        return json.dumps({"success": True, "message": "出牌成功"}, ensure_ascii=False)
    return json.dumps({"error": result.get("error", "出牌失败")}, ensure_ascii=False)

@mcp.tool()
def skip_turn(room_code: str, player_id: str) -> str:
    """跳过当前回合。"""
    result = _api_post("/api/skip_turn", {
        "room_code": room_code,
        "player_id": player_id
    })
    if result.get("ok"):
        return json.dumps({"success": True, "message": "跳过成功"}, ensure_ascii=False)
    return json.dumps({"error": result.get("error", "跳过失败")}, ensure_ascii=False)

if __name__ == "__main__":
    mcp.run(transport="stdio")
