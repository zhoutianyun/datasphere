#!/usr/bin/env python3



from __future__ import annotations







import json



import os



import random



import secrets



import threading



from http import HTTPStatus



from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer



from pathlib import Path



from urllib.parse import parse_qs, urlparse











HOST = os.getenv("HOST", "0.0.0.0")



PORT = int(os.getenv("PORT", "8000"))



MAX_TURNS = 0



MAX_SCORE = 5



ROOM_SIZE = 3







CARD_DEFS = {



    "investigate": {



        "name": "调查牌",



        "rank": "A",



        "suit": "♠",



        "desc": "获得 1 条线索。",



        "foot": "资源牌",



    },



    "key": {



        "name": "钥匙牌",



        "rank": "K",



        "suit": "♦",



        "desc": "获得 1 把钥匙。",



        "foot": "资源牌",



    },



    "disrupt": {



        "name": "干扰牌",



        "rank": "J",



        "suit": "♣",



        "desc": "让线索领先的对手失去 1 条线索。",



        "foot": "对抗牌",



    },



    "open": {



        "name": "开箱牌",



        "rank": "Q",



        "suit": "♥",



        "desc": "需要 2 条线索和 1 把钥匙，成功后得 1 分。",



        "foot": "得分牌",



    },



    "double_investigate": {



        "name": "深度调查",



        "rank": "10",



        "suit": "♠",



        "desc": "直接获得 2 条线索。",



        "foot": "强化资源牌",



    },



    "steal_key": {



        "name": "顺手牵钥",



        "rank": "9",



        "suit": "♦",



        "desc": "从钥匙最多的对手那里夺走 1 把钥匙；若并列则问人决定。",



        "foot": "抢夺牌",



    },



    "shield": {



        "name": "防护牌",



        "rank": "8",



        "suit": "♣",



        "desc": "获得 1 层护盾。下一次被干扰或被抢钥匙时优先抵消。",



        "foot": "防守牌",



    },



    "wild": {



        "name": "万用牌",



        "rank": "JOKER",



        "suit": "★",



        "desc": "会自动按当前局势变成最有用的效果。",



        "foot": "高随机牌",



    },



    "trade": {



        "name": "交易牌",



        "rank": "9",



        "suit": "♣",



        "desc": "消耗 2 线索换 1 钥匙；或消耗 1 钥匙换 2 线索。",



        "foot": "灵活牌",



    },



    "recycle": {



        "name": "回收牌",



        "rank": "8",



        "suit": "♠",



        "desc": "从牌库摸 1 张牌（跳过弃牌堆）。",



        "foot": "战术牌",



    },



    "freeze": {



        "name": "冻结牌",



        "rank": "7",



        "suit": "♦",



        "desc": "跳过下一名玩家的回合。",



        "foot": "节奏牌",



    },



    "shield_break": {



        "name": "护盾击碎",



        "rank": "6",



        "suit": "♥",



        "desc": "目标对手失去 1 层护盾；若无护盾则失去 1 条线索。",



        "foot": "破解牌",



    },



    "sabotage": {



        "name": "暗算牌",



        "rank": "5",



        "suit": "♠",



        "desc": "手牌最多的对手随机弃 1 张手牌。",



        "foot": "破坏牌",



    },



    "inspiration": {



        "name": "灵感牌",



        "rank": "4",



        "suit": "♦",



        "desc": "获得 2 条线索和 1 把钥匙。",



        "foot": "爆发牌",



    },



    "fog": {



        "name": "迷雾牌",



        "rank": "3",



        "suit": "♣",



        "desc": "所有对手失去 1 条线索。",



        "foot": "群体牌",



    },



    "double_draw": {



        "name": "连抽牌",



        "rank": "2",



        "suit": "♥",



        "desc": "连续摸 2 张牌。",



        "foot": "过牌牌",



    },



}







DECK_POOL = [



    "investigate",



    "investigate",



    "investigate",



    "investigate",



    "key",



    "key",



    "key",



    "disrupt",



    "disrupt",



    "open",



    "open",



    "open",



    "open",



    "open",



    "double_investigate",



    "double_investigate",



    "steal_key",



    "steal_key",



    "shield",



    "shield",



    "wild",



    "wild",



    "trade",



    "trade",



    "recycle",



    "recycle",



    "freeze",



    "freeze",



    "shield_break",



    "shield_break",



    "sabotage",



    "sabotage",



    "inspiration",



    "inspiration",



    "fog",



    "fog",



    "double_draw",



    "double_draw",



    "double_draw",



    "double_draw",



]



DECK_SIZE = 47



HAND_SIZE = 4







ROOMS: dict[str, dict] = {}



LOCK = threading.Lock()











HTML = """<!DOCTYPE html>



<html lang="zh-CN">



<head>



  <meta charset="UTF-8">



  <meta name="viewport" content="width=device-width, initial-scale=1.0">



  <title>三机对抗 - 联机房间版</title>



  <style>



    :root {



      --bg: #0f1116;



      --table: #154734;



      --panel: rgba(16, 20, 26, 0.94);



      --line: #32424d;



      --text: #f4efe5;



      --muted: #c8c0b2;



      --gold: #e0b15a;



      --red: #d97468;



      --green: #82c78f;



      --blue: #81b7e7;



    }



    * { box-sizing: border-box; }



    body {



      margin: 0;



      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;



      color: var(--text);



      background:



        radial-gradient(circle at top, rgba(224,177,90,0.16), transparent 25%),



        linear-gradient(180deg, #143828, var(--bg));



      min-height: 100vh;



      padding: 24px;



    }



    .app {



      max-width: 1280px;



      margin: 0 auto;



      display: grid;



      grid-template-columns: 320px 1fr;



      gap: 20px;



    }



    .shell {



      background: var(--panel);



      border: 1px solid var(--line);



      border-radius: 22px;



      overflow: hidden;



      box-shadow: 0 18px 50px rgba(0,0,0,0.35);



    }



    .side {



      padding: 24px;



      align-self: start;



      position: sticky;



      top: 24px;



    }



    h1,h2,h3,p { margin-top: 0; }



    .tag {



      display: inline-block;



      padding: 6px 12px;



      border-radius: 999px;



      background: rgba(224,177,90,0.14);



      color: var(--gold);



      font-size: 13px;



      margin-bottom: 16px;



    }



    .desc {



      color: var(--muted);



      line-height: 1.6;



      margin-bottom: 18px;



    }



    .mini {



      padding: 12px 14px;



      border-radius: 14px;



      background: rgba(255,255,255,0.03);



      border: 1px solid rgba(255,255,255,0.05);



      margin-bottom: 12px;



    }



    .mini strong {



      display: block;



      margin-bottom: 6px;



      color: var(--gold);



    }



    .main-top {



      padding: 22px 24px;



      border-bottom: 1px solid var(--line);



      background: linear-gradient(135deg, rgba(224,177,90,0.12), rgba(129,183,231,0.08));



    }



    .main-top p {



      color: var(--muted);



      line-height: 1.6;



      margin-bottom: 0;



    }



    .section {



      padding: 20px;



    }



    .hidden { display: none; }



    .row {



      display: flex;



      gap: 10px;



      flex-wrap: wrap;



      margin-bottom: 12px;



    }



    input {



      flex: 1;



      min-width: 180px;



      border-radius: 12px;



      border: 1px solid var(--line);



      background: rgba(255,255,255,0.04);



      color: var(--text);



      padding: 12px 14px;



      font-size: 14px;



    }



    button {



      border: 0;



      border-radius: 12px;



      padding: 10px 14px;



      cursor: pointer;



      font-size: 14px;



      font-weight: 700;



      color: #171a20;



      background: #f4efe5;



    }



    button.primary {



      background: linear-gradient(135deg, var(--gold), var(--blue));



    }



    button:disabled {



      opacity: 0.45;



      cursor: not-allowed;



    }



    .status {



      color: var(--muted);



      margin-bottom: 12px;



      white-space: pre-line;



    }



    .table {



      display: grid;



      gap: 18px;



      padding: 20px;



      min-height: 720px;



      grid-template-columns: repeat(2, minmax(0, 1fr));



      grid-template-areas:



        "top-left top-right"



        "center center"



        "bottom bottom";



      background:



        radial-gradient(circle at center, rgba(255,255,255,0.08), transparent 26%),



        linear-gradient(180deg, rgba(255,255,255,0.04), transparent 30%),



        var(--table);



    }



    .player {



      border: 1px solid rgba(255,255,255,0.1);



      border-radius: 20px;



      padding: 16px;



      background: rgba(16,20,26,0.26);



    }



    .player.opponent {



      min-height: 240px;



    }



    .player.me {



      background: rgba(16,20,26,0.42);



      border-color: rgba(224,177,90,0.35);



    }



    .player.top-left { grid-area: top-left; }



    .player.top-right { grid-area: top-right; }



    .player.bottom { grid-area: bottom; }



    .center-stage {



      grid-area: center;



      border: 1px solid rgba(255,255,255,0.1);



      border-radius: 24px;



      padding: 18px;



      background: rgba(7, 11, 16, 0.32);



      display: grid;



      grid-template-columns: repeat(3, minmax(0, 1fr));



      gap: 16px;



      align-items: start;



    }



    .center-slot {



      min-height: 170px;



      border-radius: 18px;



      padding: 14px;



      border: 1px dashed rgba(255,255,255,0.15);



      background: rgba(255,255,255,0.03);



    }



    .center-slot strong {



      display: block;



      margin-bottom: 10px;



      color: var(--gold);



      font-size: 14px;



    }



    .player-head {



      display: flex;



      justify-content: space-between;



      gap: 12px;



      margin-bottom: 10px;



      align-items: baseline;



    }



    .player-head span {



      color: var(--muted);



      font-size: 14px;



    }



    .stats {



      display: flex;



      gap: 10px;



      flex-wrap: wrap;



      margin-bottom: 14px;



    }



    .badge {



      padding: 6px 10px;



      border-radius: 999px;



      background: rgba(255,255,255,0.06);



      font-size: 13px;



    }



    .hand {



      display: flex;



      gap: 14px;



      flex-wrap: wrap;



    }



    .opponent-hand {



      display: flex;



      gap: 8px;



      flex-wrap: wrap;



      min-height: 94px;



      align-items: flex-start;



    }



    .back-card {



      width: 52px;



      height: 74px;



      border-radius: 12px;



      border: 1px solid rgba(255,255,255,0.1);



      background:



        linear-gradient(135deg, rgba(224,177,90,0.28), rgba(129,183,231,0.2)),



        repeating-linear-gradient(



          45deg,



          rgba(255,255,255,0.08) 0,



          rgba(255,255,255,0.08) 8px,



          rgba(0,0,0,0.08) 8px,



          rgba(0,0,0,0.08) 16px



        ),



        #17202a;



      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.04);



    }



    .card {



      width: 160px;



      min-height: 210px;



      border-radius: 18px;



      border: 1px solid var(--line);



      background:



        linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02)),



        #181c23;



      color: var(--text);



      text-align: left;



      padding: 14px;



      display: flex;



      flex-direction: column;



      justify-content: space-between;



      cursor: pointer;



    }



    .card:disabled {



      opacity: 0.4;



      cursor: not-allowed;



    }



    .card-top {



      display: flex;



      justify-content: space-between;



      margin-bottom: 10px;



    }



    .rank {



      font-size: 26px;



      font-weight: 800;



      color: var(--gold);



    }



    .suit {



      font-size: 22px;



      color: var(--gold);



    }



    .card-name {



      font-size: 20px;



      font-weight: 800;



      margin-bottom: 8px;



    }



    .card-text {



      font-size: 13px;



      line-height: 1.6;



      color: var(--muted);



      flex: 1;



    }



    .card-foot {



      margin-top: 12px;



      font-size: 12px;



      color: var(--gold);



    }



    .played-card {



      width: 100%;



      max-width: 180px;



      min-height: 120px;



      border-radius: 16px;



      border: 1px solid rgba(224,177,90,0.28);



      background:



        linear-gradient(180deg, rgba(255,255,255,0.08), rgba(255,255,255,0.03)),



        #141920;



      padding: 12px;



      display: flex;



      flex-direction: column;



      justify-content: space-between;



    }



    .played-card.empty { display: none !important;



      border-style: dashed;



      border-color: rgba(255,255,255,0.12);



      color: var(--muted);



      align-items: center;



      justify-content: center;



      text-align: center;



    }



    .played-card .card-name {



      font-size: 16px;



      margin-bottom: 6px;



    }



    .played-card .card-text {



      font-size: 12px;



    }



    .played-row {



      margin-top: 12px;



      display: flex;



      gap: 12px;



      align-items: flex-start;



      flex-wrap: wrap;



    }



    .log-box {



      border: 1px solid var(--line);



      border-radius: 18px;



      padding: 18px;



      background: rgba(0,0,0,0.18);



      min-height: 150px;



      white-space: pre-line;



      line-height: 1.7;



    }



    .target-box {



      margin-top: 16px;



      padding: 14px;



      border-radius: 14px;



      border: 1px dashed var(--gold);



      background: rgba(224,177,90,0.08);



    }



    .winner { color: var(--green); font-weight: 700; }



    .warn { color: var(--gold); font-weight: 700; }



    @media (max-width: 980px) {



      .app { grid-template-columns: 1fr; }



      .side { position: static; }



      .table {



        grid-template-columns: 1fr;



        grid-template-areas:



          "top-left"



          "top-right"



          "center"



          "bottom";



      }



      .center-stage {



        grid-template-columns: 1fr;



      }



    }



  
.victory-overlay {
    display: none; position: fixed; top: 0; left: 0;
    width: 100%; height: 100%;
    background: rgba(0,0,0,0.85);
    z-index: 9999;
    justify-content: center; align-items: center;
    flex-direction: column;
    animation: fadeIn 0.5s ease;
}
.victory-overlay.show { display: flex; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.victory-content {
    text-align: center; color: #f4efe5;
    padding: 30px; position: relative; z-index: 1;
}
.victory-trophy { font-size: 80px; animation: bounce 1s ease infinite; }
@keyframes bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-15px); } }
.victory-title { font-size: 48px; font-weight: 700; color: #ffd700; margin: 10px 0; text-shadow: 0 0 30px rgba(255,215,0,0.5); }
.victory-winner { font-size: 28px; color: #fff; margin: 10px 0 20px; }
.victory-scores { display: flex; justify-content: center; gap: 16px; margin: 20px 0; }
.victory-score-card { background: rgba(255,255,255,0.1); border-radius: 12px; padding: 15px 25px; min-width: 100px; }
.victory-score-card .name { font-size: 14px; color: #c8c0b2; }
.victory-score-card .score { font-size: 36px; font-weight: 700; color: #e0b15a; }
.victory-score-card.winner .score { color: #ffd700; text-shadow: 0 0 10px rgba(255,215,0,0.5); }
.victory-btn { margin-top: 20px; padding: 14px 40px; font-size: 18px; font-weight: 600; background: linear-gradient(135deg, #ffd700, #e0b15a); color: #0f1116; border: none; border-radius: 8px; cursor: pointer; transition: transform 0.2s; }
.victory-btn:hover { transform: scale(1.05); }
#confetti-canvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 10000; }

.victory-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 9999; justify-content: center; align-items: center; flex-direction: column; animation: fadeIn 0.5s ease; }
.victory-overlay.show { display: flex; }

.agent-overlay { visibility: hidden; opacity: 0; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.75); z-index: 9998; justify-content: center; align-items: center; flex-direction: column; transition: opacity 0.15s ease; will-change: opacity; transform: translateZ(0); }
.agent-overlay.show { visibility: visible; opacity: 1; }
.agent-modal { background: #1a1a2e; border: 2px solid #e94560; border-radius: 12px; padding: 24px; max-width: 480px; width: 90%; color: #eee; }
.agent-modal h3 { color: #e94560; margin: 0 0 12px 0; font-size: 18px; }
.agent-modal pre { background: #16213e; padding: 12px; border-radius: 8px; font-size: 13px; overflow-x: auto; margin: 8px 0; }
.agent-modal .url-box { background: #16213e; padding: 8px 12px; border-radius: 6px; font-family: monospace; font-size: 14px; word-break: break-all; border: 1px solid #333; margin: 8px 0; }
.agent-modal .close-btn { background: #e94560; color: #fff; border: none; border-radius: 6px; padding: 8px 20px; cursor: pointer; margin-top: 12px; font-size: 14px; }
.agent-modal .close-btn:hover { background: #c73650; }
.agent-modal p { margin: 6px 0; line-height: 1.5; }
.agent-modal .tip { color: #aaa; font-size: 12px; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.victory-content { text-align: center; color: #f4efe5; padding: 30px; position: relative; z-index: 1; }
.victory-trophy { font-size: 80px; animation: bounce 1s ease infinite; }
@keyframes bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-15px); } }
.victory-title { font-size: 48px; font-weight: 700; color: #ffd700; margin: 10px 0; text-shadow: 0 0 30px rgba(255,215,0,0.5); }
.victory-winner { font-size: 28px; color: #fff; margin: 10px 0 20px; }
.victory-scores { display: flex; justify-content: center; gap: 16px; margin: 20px 0; }
.victory-score-card { background: rgba(255,255,255,0.1); border-radius: 12px; padding: 15px 25px; min-width: 100px; }
.victory-score-card .name { font-size: 14px; color: #c8c0b2; }
.victory-score-card .score { font-size: 36px; font-weight: 700; color: #e0b15a; }
.victory-score-card.winner .score { color: #ffd700; text-shadow: 0 0 10px rgba(255,215,0,0.5); }
.victory-btn { margin-top: 20px; padding: 14px 40px; font-size: 18px; font-weight: 600; background: linear-gradient(135deg, #ffd700, #e0b15a); color: #0f1116; border: none; border-radius: 8px; cursor: pointer; transition: transform 0.2s; }
.victory-btn:hover { transform: scale(1.05); }
#confetti-canvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 10000; }

/* ===== RESPONSIVE LAYOUT: fit in viewport without scrolling ===== */
.player .played-row { display: none !important; }
.player.opponent { min-height: 30px !important; max-height: 60px !important; }
html, body { height: 100%; overflow: hidden !important; margin: 0; padding: 0 !important; }
.app { height: 100vh !important; max-height: 100vh; min-height: 0 !important; overflow: hidden !important; padding: 2px 4px !important; }
main { padding: 0 !important; margin: 0 !important; overflow: hidden; display: flex; flex-direction: column; }
section { padding: 0; margin: 0; }
#gameView:not(.hidden) { display: flex; flex-direction: column; flex: 1; min-height: 0; }
.table, #table { flex: 1; min-height: 0 !important; height: auto !important; gap: 2px !important; padding: 2px 4px !important; overflow: hidden !important; }
.complementary { padding: 1px 6px !important; max-height: 24px; overflow: hidden; font-size: 9px; }
.complementary p { display: none !important; }
.complementary h1 { font-size: 11px !important; margin: 0 !important; }
.complementary strong, .complementary .generic { font-size: 9px !important; }
.player { padding: 3px 6px !important; border-radius: 8px !important; }
.player.opponent { min-height: 40px !important; max-height: 80px; overflow: hidden; }
.player-head { gap: 2px !important; margin-bottom: 1px !important; }
.player-head h3 { font-size: 11px !important; margin: 0; line-height: 1.2; }
.player-head span { font-size: 9px !important; }
.stats { gap: 2px !important; margin-bottom: 1px !important; }
.badge { padding: 1px 4px !important; font-size: 9px !important; border-radius: 4px !important; }
.hand { gap: 3px !important; }
.opponent-hand { min-height: 0 !important; height: 22px; overflow: hidden; }
.back-card { width: 14px !important; height: 20px !important; border-radius: 3px !important; font-size: 6px; }
.center-stage { min-height: 60px !important; padding: 6px 12px !important; border-radius: 12px !important; background: rgba(255,255,255,0.08) !important; max-height: none !important; overflow: visible; } .center-stage .played-card { min-height: 36px !important; max-height: 36px !important; width: 80px !important; display: inline-flex; align-items: center; overflow: hidden; } .center-stage .played-card .card-name { font-size: 10px !important; } .center-stage .played-card .card-text { font-size: 9px !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.played-card { max-width: 100px !important; min-height: 45px !important; padding: 4px 10px !important; border-radius: 8px !important; }
.played-card .card-name { font-size: 9px !important; margin-bottom: 0 !important; }
.played-card .card-name { font-size: 11px !important; margin-bottom: 2px !important; } .played-card .card-text { font-size: 10px !important; display: block !important; }
.played-card .card-foot { font-size: 7px !important; }
.center-slot strong { font-size: 9px !important; }
.card { width: 65px !important; min-height: 80px !important; padding: 3px !important; border-radius: 6px !important; }
.card-top { font-size: 10px !important; }
.card-name { font-size: 8px !important; }
.card-text { font-size: 7px !important; display: none; }
.card-foot { font-size: 8px !important; }
.player.bottom { font-size: 78%; } .player.bottom .card { width: 34px !important; min-height: 34px !important; padding: 1px !important; overflow: hidden !important; } .player.bottom .card-name { font-size: 7px !important; } .player.bottom .card-text { font-size: 7px !important; } .player.bottom .card-top { font-size: 9px !important; } .player.bottom .badge { font-size: 8px !important; padding: 1px 3px !important; } .player.bottom .player-head h3 { font-size: 10px !important; } .player.bottom .card-top, .player.bottom .card-name, .player.bottom .card-text, .player.bottom .card-foot { padding: 1px 2px !important; }
.player.bottom .card-text { display: block; font-size: 8px !important; }
.ghost { margin-top: 1px !important; padding: 1px 4px !important; font-size: 8px !important; }

/* Player hand & cards - playing card style */
.player.bottom .card { width: 55px !important; height: 130px !important; min-height: 0 !important; padding: 3px !important; border-radius: 6px !important; display: flex !important; flex-direction: column !important; align-items: center !important; text-align: center; overflow: hidden !important; }
.player.bottom .card-top { display: flex !important; font-size: 11px !important; padding: 2px 0 !important; gap: 1px; }
.player.bottom .card-top .rank, .player.bottom .card-top .suit { font-size: 11px !important; padding: 0 !important; margin: 0 !important; }
.player.bottom .card-name { display: block !important; font-size: 7px !important; padding: 0 !important; margin: 1px 0 !important; }
.player.bottom .card-text { display: block !important; font-size: 6.5px !important; line-height: 1.1 !important; padding: 0 !important; margin: 1px 2px !important; }
.player.bottom .card-foot { display: block !important; font-size: 6px !important; padding: 0 !important; margin-top: auto !important; opacity: 0.7; }
.player.bottom .hand { min-height: 140px !important; gap: 2px !important; padding: 2px 0 !important; }
.center-stage { min-height: 240px !important; max-height: none !important; overflow-y: auto; }
.center-stage .played-card { min-height: 80px !important; max-height: none !important; width: 110px !important; display: flex !important; flex-direction: column; align-items: center; overflow: visible; padding: 4px 8px !important; }
.center-stage .played-card .card-name { font-size: 10px !important; margin: 2px 0 !important; } .center-stage .played-card .card-text { font-size: 9px !important; white-space: normal !important; line-height: 1.2 !important; display: block !important; } .center-stage .played-card .card-foot { font-size: 8px !important; margin-top: auto !important; opacity: 0.7; }
</style>



</head>



<body>



  <div class="app">



    <aside class="shell side">



      <div class="tag">房间制联机牌局</div>



      <h1>三机对抗</h1>



      <p class="desc">一台电脑开房，另外两台电脑加入。同一局牌桌会实时同步，3 个 Agent 轮流竞争抢分。</p>



      <div class="mini">



        <strong>我的身份</strong>



        <div id="meText">未加入房间</div>



      </div>



      <div class="mini">



        <strong>房间号</strong>



        <div id="roomText">暂无</div>



      </div>



      <div class="mini">



        <strong>当前状态</strong>



        <div id="stateText">等待创建或加入房间</div>



      </div>



      <div class="mini">



        <strong>联机提示</strong>



        <div>其他电脑请打开同一地址并输入房间号加入。</div>



      </div>



    </aside>







    <main class="shell">



      <section class="main-top">



        <h2>联机说明</h2>



        <p>房主先创建房间，其他玩家输入房间号加入。满 3 人后会自动开始。选择"人机对打"可直接与 AI 对手开局。</p>



      </section>







      <section class="section" id="joinView">



        <div class="status" id="joinStatus">先输入你的名字，然后创建房间或加入房间。</div>



        <div class="row">



          <input id="nameInput" placeholder="输入你的名字，例如 Agent 1">



        </div>



        <div class="row">



          <button class="primary" id="createBtn" style="flex:1">创建房间</button>



          <button class="primary" id="aiBtn" style="flex:1">人机对打</button>



        </div>


        <div class="row">


          <button class="primary" id="agentBtn" style="flex:1;background:#e94560">Agent 接入</button>


        </div>



        <div class="row">



          <input id="roomInput" placeholder="输入房间号加入，例如 A1B2C">



          <button id="joinBtn">加入房间</button>



        </div>



      </section>







      <section class="section hidden" id="lobbyView">



        <div class="status" id="lobbyStatus"></div>



        <div class="row">



          <button id="leaveBtn">离开房间</button>



        </div>



      </section>







      <section class="hidden" id="gameView">



        <div class="table" id="table"></div>



        <div class="section">



          <div class="log-box" id="logText"></div>



          <div class="target-box hidden" id="choiceBox">



            <div id="choicePrompt"></div>



            <div class="row" id="choiceButtons"></div>



          </div>



          <div class="row" style="margin-top: 16px;">



            <button id="refreshBtn">立即同步</button>



            <button id="leaveBtn2">离开房间</button>



          </div>



        </div>



      </section>



    </main>



  </div>







  <script>



    const cardDefs = %CARD_DEFS%;



    


    var urlParams = new URLSearchParams(window.location.search);
    var roomFromUrl = urlParams.get('room');
    var playerFromUrl = urlParams.get('player');
    var nameFromUrl = urlParams.get('name');
    if (roomFromUrl) { localStorage.setItem('roomCode', roomFromUrl); }
    if (playerFromUrl) { localStorage.setItem('playerId', playerFromUrl); }
    if (nameFromUrl) { localStorage.setItem('playerName', nameFromUrl); }

const appState = {



      roomCode: localStorage.getItem("roomCode") || "",



      playerId: localStorage.getItem("playerId") || "",



      playerName: localStorage.getItem("playerName") || "",



      pollTimer: null,



      snapshot: null



    };







    const joinView = document.getElementById("joinView");



    const lobbyView = document.getElementById("lobbyView");



    const gameView = document.getElementById("gameView");



    const joinStatus = document.getElementById("joinStatus");



    const lobbyStatus = document.getElementById("lobbyStatus");



    const logText = document.getElementById("logText");







    document.getElementById("nameInput").value = appState.playerName;



    document.getElementById("roomInput").value = appState.roomCode;







    function saveIdentity() {



      localStorage.setItem("roomCode", appState.roomCode);



      localStorage.setItem("playerId", appState.playerId);



      localStorage.setItem("playerName", appState.playerName);



    }







    function clearIdentity() {



      appState.roomCode = "";



      appState.playerId = "";



      appState.snapshot = null;



      localStorage.removeItem("roomCode");



      localStorage.removeItem("playerId");



    }







    async function api(path, method = "GET", body = null) {



      const options = { method, headers: {} };



      if (body) {



        options.headers["Content-Type"] = "application/json";



        options.body = JSON.stringify(body);



      }



      const res = await fetch(path, options);



      const data = await res.json();



      if (!res.ok || !data.ok) {



        throw new Error(data.error || "请求失败");



      }



      return data;



    }







    function setSide(snapshot) {



      document.getElementById("meText").textContent = appState.playerName || "未加入房间";



      document.getElementById("roomText").textContent = appState.roomCode || "暂无";



      if (document.getElementById("turnNum")) {



        document.getElementById("turnNum").textContent = snapshot ? snapshot.turn_number || "0" : "0";



      }



      if (!snapshot) {



        document.getElementById("stateText").textContent = "等待创建或加入房间";



        return;



      }



      const statusMap = {



        waiting: "等待玩家加入",



        playing: "游戏进行中",



        finished: "本局已结束",



        choosing_disrupt: "等待人类决定干扰目标",



        choosing_winner: "等待人类决定并列胜者"



      };



      document.getElementById("stateText").textContent = statusMap[snapshot.status] || snapshot.status;



    }







    function showJoin() {



      joinView.classList.remove("hidden");



      lobbyView.classList.add("hidden");



      gameView.classList.add("hidden");



      setSide(null);



    }







    function showLobby(snapshot) {



      joinView.classList.add("hidden");



      lobbyView.classList.remove("hidden");



      gameView.classList.add("hidden");



      const players = snapshot.players.map((p) => p.name).join("、");



      lobbyStatus.textContent = `房间 ${snapshot.room_code}\



当前玩家：${players}\



${snapshot.players.length}/3 人\



满 3 人后自动开始`;



      setSide(snapshot);



    }







    function renderGame(snapshot) {



      joinView.classList.add("hidden");



      lobbyView.classList.add("hidden");



      gameView.classList.remove("hidden");



      setSide(snapshot);



      const table = document.getElementById("table");



      table.innerHTML = "";







      snapshot.players.forEach((player) => {



        const isMe = player.id === appState.playerId;



        const isCurrent = snapshot.current_player_id === player.id;



        const handHtml = player.hand.map((card, index) => {



          const def = cardDefs[card];



          const disabled = !isMe || !isCurrent || snapshot.status !== "playing";



          return `



            <button class="card" data-index="${index}" ${disabled ? "disabled" : ""}>



              <div>



                <div class="card-top">



                  <span class="rank">${def.rank}</span>



                  <span class="suit">${def.suit}</span>



                </div>



                <div class="card-name">${def.name}</div>



                <div class="card-text">${def.desc}</div>



              </div>



              <div class="card-foot">${def.foot}</div>



            </button>



          `;



        }).join("");







        const hiddenHand = isMe ? handHtml : `<div class="badge">其余玩家看不到对方手牌</div>`;







        const section = document.createElement("section");



        section.className = "player";



        section.innerHTML = `



          <div class="player-head">



            <h3>${player.name}${isMe ? "（你）" : ""}${player.is_ai ? "（AI）" : ""}</h3>



            <span>${isCurrent ? "当前出牌者" : ""}</span>



          </div>



          <div class="stats">



            <div class="badge">分数：${player.score}</div>



            <div class="badge">线索：${player.clues}</div>



            <div class="badge">钥匙：${player.keys}</div>



            <div class="badge">坐位：${player.is_host ? "房主" : (player.is_ai ? "AI" : "玩家")}</div>



          </div>



          ${isMe && isCurrent && snapshot.status === "playing" ? '<button class="ghost" onclick="skipTurn()" style="margin-top:8px;font-size:12px">跳过</button>' : ""}

          <div class="hand">${hiddenHand}</div>



        `;



        table.appendChild(section);



      });







      const mySection = table.querySelectorAll(".player")[snapshot.players.findIndex((p) => p.id === appState.playerId)];



      if (mySection) {



        mySection.querySelectorAll(".card").forEach((button) => {



          button.addEventListener("click", () => playCard(Number(button.dataset.index)));



        });



      }







      const turnName = snapshot.players.find((p) => p.id === snapshot.current_player_id)?.name || "未知";



      const winnerText = snapshot.winner_name ? `\



胜者：${snapshot.winner_name}` : "";



      logText.className = snapshot.status === "finished" ? "winner" : (snapshot.status.startsWith("choosing") ? "warn" : "");



      logText.textContent = `房间：${snapshot.room_code}\



剩余牌库：手牌 4 张 | 牌库 ∞\



当前出牌者：${turnName}\



\



${snapshot.log}${winnerText}`;







      renderChoice(snapshot);
      showVictoryIfFinished(snapshot);



      showVictoryIfFinished(snapshot);
    }







    function renderPublicCard(card) {



      if (!card) {



        return `<div class="played-card empty"></div>`;



      }



      const def = cardDefs[card];



      return `



        <div class="played-card">



          <div>



            <div class="card-top">



              <span class="rank">${def.rank}</span>



              <span class="suit">${def.suit}</span>



            </div>



            <div class="card-name">${def.name}</div>



            <div class="card-text">${def.desc}</div>



          </div>



          <div class="card-foot">${def.foot}</div>



        </div>



      `;



    }







    function renderOpponentBacks(count) {



      return Array.from({ length: count }, () => `<div class="back-card" aria-hidden="true"></div>`).join("");



    }







    function renderGame(snapshot) {



      joinView.classList.add("hidden");



      lobbyView.classList.add("hidden");



      gameView.classList.remove("hidden");



      setSide(snapshot);



      const table = document.getElementById("table");



      table.innerHTML = "";



      const meIndex = snapshot.players.findIndex((p) => p.id === appState.playerId);



      const seatOrder = meIndex === -1



        ? snapshot.players



        : [



            snapshot.players[(meIndex + 1) % snapshot.players.length],



            snapshot.players[(meIndex + 2) % snapshot.players.length],



            snapshot.players[meIndex]



          ];



      const seatClasses = ["top-left", "top-right", "bottom"];







      seatOrder.forEach((player, index) => {



        const isMe = player.id === appState.playerId;



        const isCurrent = snapshot.current_player_id === player.id;



        const handHtml = player.hand.map((card, handIndex) => {



          const def = cardDefs[card];



          const disabled = !isMe || !isCurrent || snapshot.status !== "playing";



          return `



            <button class="card" data-index="${handIndex}" ${disabled ? "disabled" : ""}>



              <div>



                <div class="card-top">



                  <span class="rank">${def.rank}</span>



                  <span class="suit">${def.suit}</span>



                </div>



                <div class="card-name">${def.name}</div>



                <div class="card-text">${def.desc}</div>



              </div>



              <div class="card-foot">${def.foot}</div>



            </button>



          `;



        }).join("");







        const visibleHand = isMe



          ? handHtml



          : `<div class="opponent-hand">${renderOpponentBacks(player.hand_count)}</div>`;







        const section = document.createElement("section");



        section.className = `player ${isMe ? "me" : "opponent"} ${seatClasses[index] || ""}`;



        section.innerHTML = `



          <div class="player-head">



            <h3>${player.name}${isMe ? "（你）" : ""}${player.is_ai ? "（AI）" : ""}</h3>



            <span>${isCurrent ? "当前出牌者" : ""}</span>



          </div>



          <div class="stats">



            <div class="badge">分数：${player.score}</div>



            <div class="badge">线索：${player.clues}</div>



            <div class="badge">钥匙：${player.keys}</div>



            <div class="badge">护盾：${player.shield}</div>



            <div class="badge">手牌：${player.hand_count}</div>



            <div class="badge">坐位：${player.is_host ? "房主" : (player.is_ai ? "AI" : "玩家")}</div>



          </div>



          <div class="played-row">



            ${renderPublicCard(player.last_played)}



          </div>



          ${isMe && isCurrent && snapshot.status === "playing" ? '<button class="ghost" onclick="skipTurn()" style="margin-top:8px;font-size:12px">跳过</button>' : ""}

          <div class="hand">${visibleHand}</div>



        `;



        table.appendChild(section);



      });







      const center = document.createElement("section");



      center.className = "center-stage";



      center.innerHTML = seatOrder.map((player) => `



        <div class="center-slot">



          <strong>${player.name} 的出牌区</strong>



          ${renderPublicCard(player.last_played)}



        </div>



      `).join("");



      table.appendChild(center);







      const mySection = table.querySelector(".player.me");



      if (mySection) {



        mySection.querySelectorAll(".card").forEach((button) => {



          button.addEventListener("click", () => playCard(Number(button.dataset.index)));



        });



      }







      const turnName = snapshot.players.find((p) => p.id === snapshot.current_player_id)?.name || "未知";



      const winnerText = snapshot.winner_name ? `\



胜者：${snapshot.winner_name}` : "";



      logText.className = snapshot.status === "finished" ? "winner" : (snapshot.status.startsWith("choosing") ? "warn" : "");



      logText.textContent = `房间：${snapshot.room_code}\



剩余牌库：手牌 4 张 | 牌库 ∞\



当前出牌者：${turnName}\



\



${snapshot.log}${winnerText}`;







      renderChoice(snapshot);
      showVictoryIfFinished(snapshot);



    }







    function renderChoice(snapshot) {



      const box = document.getElementById("choiceBox");



      const prompt = document.getElementById("choicePrompt");



      const buttons = document.getElementById("choiceButtons");



      buttons.innerHTML = "";







      if (!snapshot.pending_choice) {



        box.classList.add("hidden");



        return;



      }







      box.classList.remove("hidden");



      prompt.textContent = snapshot.pending_choice.prompt;



      snapshot.pending_choice.options.forEach((option) => {



        const button = document.createElement("button");



        button.textContent = option.name;



        button.addEventListener("click", () => resolveChoice(option.id));



        buttons.appendChild(button);



      });



    }







    async function refreshState() {



      if (!appState.roomCode || !appState.playerId) {



        showJoin();



        return;



      }



      try {



        const data = await api(`/api/state?room=${encodeURIComponent(appState.roomCode)}&player=${encodeURIComponent(appState.playerId)}`);



        appState.snapshot = data.room;



        if (data.room.status === "waiting") {



          showLobby(data.room);



        } else {



          renderGame(data.room);



        }



      } catch (error) {



        joinStatus.textContent = error.message;



        clearIdentity();



        showJoin();



      }



    }







    async function createAIGame() {



      try {



        const name = document.getElementById("nameInput").value.trim();



        if (!name) throw new Error("请先输入你的名字");



        appState.playerName = name;



        const data = await api("/api/create_ai_game", "POST", { name });



        appState.roomCode = data.room_code;



        appState.playerId = data.player_id;



        saveIdentity();



        refreshState();



      } catch (error) {



        joinStatus.textContent = error.message;



      }



    }







    async function createRoom() {



      try {



        const name = document.getElementById("nameInput").value.trim();



        if (!name) throw new Error("请先输入你的名字");



        appState.playerName = name;



        const data = await api("/api/create_room", "POST", { name });



        appState.roomCode = data.room_code;



        appState.playerId = data.player_id;



        saveIdentity();



        refreshState();



      } catch (error) {



        joinStatus.textContent = error.message;



      }



    }







    async function joinRoom() {



      try {



        const name = document.getElementById("nameInput").value.trim();



        const roomCode = document.getElementById("roomInput").value.trim().toUpperCase();



        if (!name) throw new Error("请先输入你的名字");



        if (!roomCode) throw new Error("请输入房间号");



        appState.playerName = name;



        const data = await api("/api/join_room", "POST", { name, room_code: roomCode });



        appState.roomCode = roomCode;



        appState.playerId = data.player_id;



        saveIdentity();



        refreshState();



      } catch (error) {



        joinStatus.textContent = error.message;



      }



    }







    async function playCard(handIndex) {



      try {



        await api("/api/play_card", "POST", {



          room_code: appState.roomCode,



          player_id: appState.playerId,



          hand_index: handIndex



        });



        refreshState();



      } catch (error) {



        logText.textContent = error.message;



      }



    }







    async function resolveChoice(targetId) {



      try {



        await api("/api/resolve_choice", "POST", {



          room_code: appState.roomCode,



          player_id: appState.playerId,



          target_id: targetId



        });



        refreshState();



      } catch (error) {



        logText.textContent = error.message;



      }



    }







    async function skipTurn() {
      try {
        await api("/api/skip_turn", "POST", {
          room_code: appState.roomCode,
          player_id: appState.playerId
        });
        refreshState();
      } catch (error) {
        logText.textContent = error.message;
      }
    }

    function leaveRoom() {



      clearIdentity();



      showJoin();


document.getElementById("agentBtn").addEventListener("click", function() {
    var overlay = document.getElementById("agentOverlay");
    if (!overlay) return;
    var urlBox = document.getElementById("agentEndpointUrl");
    if (urlBox) urlBox.textContent = window.location.origin + "/api/agent/info";
    if (appState.pollTimer) clearInterval(appState.pollTimer);
    overlay.classList.add("show");
    var closeBtns = overlay.querySelectorAll(".agent-close-btn");
    for (var ci = 0; ci < closeBtns.length; ci++) {
        closeBtns[ci].addEventListener("click", function() {
            overlay.classList.remove("show");
            if (appState.pollTimer) appState.pollTimer = setInterval(refreshState, 1000);
        });
    }
    overlay.addEventListener("click", function(e) {
        if (e.target === this) {
            overlay.classList.remove("show");
            if (appState.pollTimer) appState.pollTimer = setInterval(refreshState, 1000);
        }
    });
});



    }







    document.getElementById("createBtn").addEventListener("click", createRoom);



    document.getElementById("aiBtn").addEventListener("click", createAIGame);



    document.getElementById("joinBtn").addEventListener("click", joinRoom);



    document.getElementById("refreshBtn").addEventListener("click", refreshState);



    document.getElementById("leaveBtn").addEventListener("click", leaveRoom);



    document.getElementById("leaveBtn2").addEventListener("click", leaveRoom);







    appState.pollTimer = setInterval(refreshState, 1000);



    refreshState();



  
function showVictoryIfFinished(snapshot) {
    if (snapshot.status !== "finished" || !snapshot.winner_name) { return; }
    var overlay = document.getElementById("victoryOverlay");
    if (!overlay || overlay.classList.contains("show")) { return; }
    document.getElementById("victoryWinner").textContent = snapshot.winner_name;
    var container = document.getElementById("victoryScores");
    container.textContent = "";
    for (var i = 0; i < snapshot.players.length; i++) {
        var p = snapshot.players[i];
        var win = (p.name === snapshot.winner_name);
        var card = document.createElement("div");
        card.className = "victory-score-card" + (win ? " winner" : "");
        var nd = document.createElement("div");
        nd.className = "name";
        nd.textContent = p.name;
        var sd = document.createElement("div");
        sd.className = "score";
        sd.textContent = p.score;
        card.appendChild(nd);
        card.appendChild(sd);
        container.appendChild(card);
    }
    overlay.classList.add("show");
    startConfetti();
}
function startConfetti() {
    var c = document.getElementById("confetti-canvas");
    if (!c) { return; }
    var ctx = c.getContext("2d");
    c.width = window.innerWidth;
    c.height = window.innerHeight;
    var colors = ["#ffd700","#e0b15a","#ff6b6b","#82c78f","#81b7e7","#c084fc","#d97468"];
    var pieces = [];
    for (var i = 0; i < 200; i++) {
        pieces.push({
            x: Math.random() * c.width,
            y: Math.random() * c.height - c.height,
            w: Math.random() * 10 + 5,
            h: Math.random() * 6 + 3,
            color: colors[Math.floor(Math.random() * colors.length)],
            speed: Math.random() * 3 + 1,
            rot: Math.random() * 360,
            rotSpd: Math.random() * 10 - 5
        });
    }
    function anim() {
        ctx.clearRect(0, 0, c.width, c.height);
        var alive = false;
        for (var i = 0; i < pieces.length; i++) {
            var p = pieces[i];
            p.y += p.speed;
            p.rot += p.rotSpd;
            if (p.y < c.height + 20) {
                alive = true;
                ctx.save();
                ctx.translate(p.x, p.y);
                ctx.rotate(p.rot * Math.PI / 180);
                ctx.fillStyle = p.color;
                ctx.fillRect(-p.w/2, -p.h/2, p.w, p.h);
                ctx.restore();
            }
        }
        if (alive) { requestAnimationFrame(anim); }
    }
    anim();
}
</script>



<div id="victoryOverlay" class="victory-overlay"><canvas id="confetti-canvas"></canvas><div class="victory-content"><div class="victory-trophy">🏆</div><div class="victory-title">胜利！</div><div class="victory-winner" id="victoryWinner"></div><div class="victory-scores" id="victoryScores"></div><button class="victory-btn" onclick="location.reload()">再来一局</button></div></div>
<div id="victoryOverlay" class="victory-overlay">
<canvas id="confetti-canvas"></canvas>
<div class="victory-content">
<div class="victory-trophy">🏆</div>
<div class="victory-title">胜 利 ！</div>
<div class="victory-winner" id="victoryWinner"></div>
<div class="victory-scores" id="victoryScores"></div>
<button class="victory-btn" onclick="location.reload()">再来一局</button>
</div>
</div>
<div id="agentOverlay" class="agent-overlay">
<div class="agent-modal">
<button class="agent-close-btn" style="float:right;background:none;border:none;color:#e94560;font-size:20px;cursor:pointer">&times;</button>
<h3>🤖 Agent 接入</h3>
<p>AI Agent 可通过以下接口连接游戏：</p>
<div class="url-box" id="agentEndpointUrl">加载中...</div>
<p><strong>接口说明：</strong></p>
<pre>GET  /api/agent/info        - 获取连接信息
GET  /api/agent/state?room=X  - 获取房间状态
POST /api/agent/play          - 执行出牌操作</pre>
<p>使用示例：</p>
<pre>curl -s "/api/agent/info"
curl -s "/api/agent/state?room=ROOM1"</pre>
<p class="tip">💡 用于 AI Agent、MCP 服务端等外部程序接入游戏。</p>
<button class="close-btn agent-close-btn">关闭</button>
</div>
</div>
</body>




</html>



"""











def json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:



    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")



    handler.send_response(status)



    handler.send_header("Content-Type", "application/json; charset=utf-8")



    handler.send_header("Content-Length", str(len(data)))



    handler.end_headers()



    handler.wfile.write(data)











def html_response(handler: BaseHTTPRequestHandler, html: str) -> None:



    data = html.encode("utf-8")



    handler.send_response(HTTPStatus.OK)



    handler.send_header("Content-Type", "text/html; charset=utf-8")



    handler.send_header("Content-Length", str(len(data)))



    handler.end_headers()



    handler.wfile.write(data)











def error(handler: BaseHTTPRequestHandler, message: str, status: int = 400) -> None:



    json_response(handler, status, {"ok": False, "error": message})











def room_code() -> str:



    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"



    while True:



        code = "".join(secrets.choice(alphabet) for _ in range(5))



        if code not in ROOMS:



            return code











def shuffled_deck() -> list[str]:



    deck = list(DECK_POOL)



    random.shuffle(deck)



    return deck[:DECK_SIZE]











def draw_card(room: dict, player: dict) -> None:



    if len(player["hand"]) >= 6:



        return



    dk = "shared_deck"



    dc = "shared_discard"



    if len(room[dk]) < 4 and room[dc]:



        room[dk].extend(room[dc])



        random.shuffle(room[dk])



        room[dc] = []



    if room[dk]:



        player["hand"].append(room[dk].pop(0))











def make_player(name: str, is_host: bool = False) -> dict:



    return {



        "id": secrets.token_hex(8),



        "name": name,



        "is_host": is_host,



        "is_ai": False,



        "score": 0,



        "clues": 0,



        "keys": 0,



        "shield": 0,



        "hand": [],



        "last_played": None,



    }











def reset_players_for_game(room: dict, players: list[dict]) -> None:



    room["shared_deck"] = shuffled_deck()



    room["shared_discard"] = []



    for player in players:



        player["score"] = 0



        player["clues"] = 0



        player["keys"] = 0



        player["shield"] = 0



        player["hand"] = []



        player["last_played"] = None



        for _ in range(HAND_SIZE):



            draw_card(room, player)











def serialize_room(room: dict, viewer_id: str) -> dict:



    players = []



    for player in room["players"]:



        players.append(



            {



                "id": player["id"],



                "name": player["name"],



                "score": player["score"],



                "clues": player["clues"],



                "keys": player["keys"],



                "shield": player["shield"],



                "deck_count": len(room.get("shared_deck", [])),



                "hand_count": len(player["hand"]),



                "hand": list(player["hand"]) if player["id"] == viewer_id else [],



                "last_played": player["last_played"],



                "is_host": player["is_host"],



                "is_ai": player.get("is_ai", False),



            }



        )







    viewer = next((p for p in room["players"] if p["id"] == viewer_id), None)



    pending_choice = None



    if room["pending_choice"]:



        pending_choice = {



            "type": room["pending_choice"]["type"],



            "prompt": room["pending_choice"]["prompt"],



            "options": [



                {"id": option_id, "name": player_name(room, option_id)}



                for option_id in room["pending_choice"]["options"]



            ],



        }







    return {



        "room_code": room["code"],



        "status": room["status"],



        "turns_left": room["turns_left"],



        "max_turns": 0,



        "players": players,



        "current_player_id": room["current_player_id"],



        "log": room["log"],



        "pending_choice": pending_choice,



        "shared_deck_size": len(room.get("shared_deck", [])),



        "turn_number": room.get("turn_number", 0),



        "shared_discard_size": len(room.get("shared_discard", [])),



        "winner_name": player_name(room, room["winner_id"]) if room["winner_id"] else "",



        "is_host": bool(viewer and viewer["is_host"]),



    }











def player_name(room: dict, player_id: str | None) -> str:



    if not player_id:



        return ""



    for player in room["players"]:



        if player["id"] == player_id:



            return player["name"]



    return ""











def current_player(room: dict) -> dict:



    for player in room["players"]:



        if player["id"] == room["current_player_id"]:



            return player



    raise KeyError("current player missing")











def next_player(room: dict) -> None:



    ids = [player["id"] for player in room["players"]]



    idx = ids.index(room["current_player_id"])



    room["current_player_id"] = ids[(idx + 1) % len(ids)]



    if room.get("skip_next"):



        room["skip_next"] = False



        next_player(room)











def absorb_shield(player: dict) -> bool:



    if player["shield"] > 0:



        player["shield"] -= 1



        return True



    return False











def record_played_card(room: dict, player: dict, card: str) -> None:



    player["last_played"] = card



    room["shared_discard"].append(card)











def finish_if_needed(room: dict) -> None:



    if room["status"] == "finished":



        return



    for player in room["players"]:



        if player["score"] >= MAX_SCORE:



            room["status"] = "finished"



            room["winner_id"] = player["id"]



            room["log"] = f"{player['name']} 率先达到 5 分，立即获胜！"



            return



    # No turn limit — game only ends when someone reaches MAX_SCORE











def resource_pressure(player: dict) -> int:



    return int(player["clues"]) * 2 + int(player["keys"]) * 3 + int(player.get("shield", 0))











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











def ai_score_card(card: str, me: dict, room: dict) -> float:



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







    if card == "double_draw":



        return 230







    if card == "sabotage":



        opponents = [p for p in room["players"] if p["id"] != me["id"]]



        max_hand = max((len(p["hand"]) for p in opponents), default=0)



        return 290 if max_hand > 0 else -20







    if card == "inspiration":



        return 420







    if card == "fog":



        opponents = [p for p in room["players"] if p["id"] != me["id"]]



        max_cl = max((p["clues"] for p in opponents), default=0)



        return 330 if max_cl > 0 else -15







    if card == "trade":



        if my_clues >= 2:



            return 310



        if my_keys >= 1:



            return 250



        return -50







    if card == "recycle":



        return 280







    if card == "freeze":



        return 320







    if card == "shield_break":



        opponents = [p for p in room["players"] if p["id"] != me["id"]]



        max_sh = max((p.get("shield", 0) for p in opponents), default=0)



        if max_sh > 0:



            return 400



        max_cl = max((p["clues"] for p in opponents), default=0)



        return 250 if max_cl > 0 else -30







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











def ai_choose_card(room: dict, player: dict) -> int:



    hand = list(player["hand"])



    scored = [(idx, ai_score_card(card, player, room)) for idx, card in enumerate(hand)]



    scored.sort(key=lambda item: item[1], reverse=True)



    return scored[0][0]











def ai_resolve_target(room: dict, choice_type: str) -> str | None:



    pending = room["pending_choice"]



    if not pending or not pending["options"]:



        return None



    option_ids = pending["options"]



    candidates = [p for p in room["players"] if p["id"] in option_ids]



    if not candidates:



        return None



    if choice_type == "winner":



        return max(candidates, key=lambda p: (int(p["score"]), resource_pressure(p)))["id"]



    if choice_type == "shield_break":



        return max(candidates, key=lambda p: (int(p.get("shield", 0)) * 10 + threat_score(p)))["id"]



    return max(candidates, key=threat_score)["id"]











def auto_skip_empty_hand(room: dict) -> bool:



    """If current player has no cards, draw 1 and skip turn."""



    if room["status"] != "playing":



        return False



    cur = next((p for p in room["players"] if p["id"] == room["current_player_id"]), None)



    if cur and len(cur["hand"]) == 0:



        draw_card(room, cur)



        room["log"] = f"{cur['name']} 手牌为空，自动补 1 张牌并跳过回合。"



        next_player(room)



        finish_if_needed(room)



        return True



    return False











def auto_play_ai_turns(code: str) -> None:



    room = ROOMS.get(code)



    if not room or room["status"] not in ("playing", "choosing_disrupt"):



        return



    # Auto-skip AI with empty hand



    auto_skip_empty_hand(room)



    if room["status"] == "finished":



        return







    max_loops = 30



    for _ in range(max_loops):



        if room["status"] not in ("playing", "choosing_disrupt"):



            break



        # Handle AI choices first



        auto_skip_empty_hand(room)



        while room["pending_choice"] and room["status"] == "choosing_disrupt":



            target_id = ai_resolve_target(room, room["pending_choice"]["type"])



            if not target_id:



                break



            # Resolve choice for AI



            pending = room["pending_choice"]



            target = next(p for p in room["players"] if p["id"] == target_id)



            room["status"] = "playing"



            room["pending_choice"] = None



            if pending["type"] == "disrupt":



                if target["clues"] > 0:



                    target["clues"] -= 1



                room["log"] = f"(AI 自动选择) {player_name(room, target_id)} 被干扰失去 1 条线索。"



                next_player(room)



                finish_if_needed(room)



            elif pending["type"] == "steal_key":



                if target["keys"] > 0:



                    target["keys"] -= 1



                room["log"] = f"(AI 自动选择) {player_name(room, target_id)} 被夺走 1 把钥匙。"



                next_player(room)



                finish_if_needed(room)



            elif pending["type"] == "shield_break":



                if target["shield"] > 0:



                    target["shield"] -= 1



                    room["log"] = f"(AI 自动选择) {player_name(room, target_id)} 被击碎 1 层护盾。"



                else:



                    target["clues"] = max(0, target["clues"] - 1)



                    room["log"] = f"(AI 自动选择) {player_name(room, target_id)} 失去 1 条线索。"



                next_player(room)



                finish_if_needed(room)



            else:



                break



            if room["status"] == "finished":



                return







        # Check if current player is AI



        cur = next((p for p in room["players"] if p["id"] == room["current_player_id"]), None)



        if not cur or not cur.get("is_ai"):



            break



        if room["status"] != "playing":



            break







        card_idx = ai_choose_card(room, cur)



        card_name = cur["hand"][card_idx]



        



        # Reuse play_card logic directly



        try:



            # Status is already "playing" for AI auto-play



            # Back up current player for play_card



            old_id = room["current_player_id"]



            play_card(code, cur["id"], card_idx)



            # AI log set by play_card【{card_name}】。"



        except ValueError:



            room["current_player_id"] = old_id



            break



        



        if room["status"] == "finished":



            return











def auto_play_needed(room: dict) -> bool:



    if room["status"] != "playing":



        return False



    cur = next((p for p in room["players"] if p["id"] == room["current_player_id"]), None)



    return bool(cur and cur.get("is_ai"))











def create_ai_game(name: str) -> tuple[str, str]:



    code = room_code()



    human = make_player(name, is_host=True)



    ai_1 = make_player("AI 对手 1")



    ai_1["is_ai"] = True



    ai_2 = make_player("AI 对手 2")



    ai_2["is_ai"] = True



    players = [human, ai_1, ai_2]



    room = {



        "code": code,



        "players": players,



        "status": "playing",



        "turn_number": 0,



        "turns_left": 0,



        "current_player_id": human["id"],



        "log": "人机对战开始。轮到你先出牌。",



        "pending_choice": None,



        "winner_id": None,



    }



    reset_players_for_game(room, players)



    ROOMS[code] = room



    return code, human["id"]







def create_room(name: str) -> tuple[str, str]:



    code = room_code()



    host = make_player(name, is_host=True)



    room = {



        "code": code,



        "players": [host],



        "status": "waiting",



        "turn_number": 0,



        "turns_left": 0,



        "current_player_id": host["id"],



        "log": "房间已创建，等待另外两位玩家加入。",



        "pending_choice": None,



        "winner_id": None,



    }



    ROOMS[code] = room



    return code, host["id"]











def join_room(code: str, name: str) -> str:



    room = ROOMS.get(code)



    if not room:



        raise ValueError("房间不存在")



    if room["status"] != "waiting":



        raise ValueError("房间已经开始，不能再加入")



    if len(room["players"]) >= ROOM_SIZE:



        raise ValueError("房间人数已满")



    player = make_player(name)



    room["players"].append(player)



    if len(room["players"]) == ROOM_SIZE:



        reset_players_for_game(room, room["players"])



        room["status"] = "playing"



        room["turns_left"] = 0



        room["current_player_id"] = room["players"][0]["id"]



        room["winner_id"] = None



        room["pending_choice"] = None



        room["log"] = f"{name} 已加入房间。当前正好 3 人，游戏自动开始。"



    else:



        room["log"] = f"{name} 已加入房间。当前 {len(room['players'])}/3 人。"



    return player["id"]











def start_game(code: str, player_id: str) -> None:



    room = ROOMS.get(code)



    if not room:



        raise ValueError("房间不存在")



    host = next((p for p in room["players"] if p["id"] == player_id), None)



    if not host or not host["is_host"]:



        raise ValueError("只有房主可以开始游戏")



    if len(room["players"]) != ROOM_SIZE:



        raise ValueError("需要 3 位玩家才能开始")



    reset_players_for_game(room, room["players"])



    room["status"] = "playing"



    room["turn_number"] = 0



    room["turns_left"] = 0



    room["current_player_id"] = room["players"][0]["id"]



    room["winner_id"] = None



    room["pending_choice"] = None



    room["log"] = "游戏开始。3 位玩家轮流出牌，先拿到 2 分者获胜。"











def require_room_and_player(code: str, player_id: str) -> tuple[dict, dict]:



    room = ROOMS.get(code)



    if not room:



        raise ValueError("房间不存在")



    player = next((p for p in room["players"] if p["id"] == player_id), None)



    if not player:



        raise ValueError("你不在这个房间里")



    return room, player











def play_card(code: str, player_id: str, hand_index: int) -> None:



    room, player = require_room_and_player(code, player_id)



    if room["status"] != "playing":



        raise ValueError("当前不能出牌")



    if room["pending_choice"]:



        raise ValueError("当前正在等待人类做选择")



    if room["current_player_id"] != player_id:



        raise ValueError("还没轮到你出牌")



    if hand_index < 0 or hand_index >= len(player["hand"]):



        raise ValueError("手牌索引无效")







    card = player["hand"].pop(hand_index)



    record_played_card(room, player, card)



    room["turn_number"] = room.get("turn_number", 0) + 1







    if card == "investigate":



        player["clues"] += 1



        draw_card(room, player)



        room["log"] = f"{player['name']} 打出【调查牌】，获得 1 条线索。"



        next_player(room)



        finish_if_needed(room)



        return







    if card == "double_investigate":



        player["clues"] += 2



        draw_card(room, player)



        room["log"] = f"{player['name']} 打出【深度调查】，直接获得 2 条线索。"



        next_player(room)



        finish_if_needed(room)



        return







    if card == "key":



        player["keys"] += 1



        draw_card(room, player)



        room["log"] = f"{player['name']} 打出【钥匙牌】，获得 1 把钥匙。"



        next_player(room)



        finish_if_needed(room)



        return







    if card == "shield":



        player["shield"] += 1



        draw_card(room, player)



        room["log"] = f"{player['name']} 打出【防护牌】，获得 1 层护盾。"



        next_player(room)



        finish_if_needed(room)



        return







    if card == "open":



        if player["clues"] >= 2 and player["keys"] >= 1:



            player["clues"] -= 2



            player["keys"] -= 1



            player["score"] += 1



            room["log"] = f"{player['name']} 打出【开箱牌】并成功开箱，获得 1 分。"



        else:



            room["log"] = f"{player['name']} 打出【开箱牌】，但资源不足，开箱失败。"



        draw_card(room, player)



        next_player(room)



        finish_if_needed(room)



        return







    if card == "sabotage":



        opponents = [p for p in room["players"] if p["id"] != player_id]



        max_hand = max(len(p["hand"]) for p in opponents)



        targets = [p for p in opponents if len(p["hand"]) == max_hand]



        target = max(targets, key=lambda p: p["score"])



        draw_card(room, player)



        if target["hand"]:



            idx = random.randrange(len(target["hand"]))



            discarded = target["hand"].pop(idx)



            room["shared_discard"].append(discarded)



            room["log"] = f"{player['name']} 打出【暗算牌】，{target['name']} 被随机弃掉 1 张手牌。"



        else:



            room["log"] = f"{player['name']} 打出【暗算牌】，但 {target['name']} 没有手牌。"



        next_player(room)



        finish_if_needed(room)



        return







    if card == "double_draw":



        draw_card(room, player)



        draw_card(room, player)



        room["log"] = f"{player['name']} 打出【连抽牌】，连续摸 2 张牌。"



        next_player(room)



        finish_if_needed(room)



        return







    if card == "inspiration":



        player["clues"] += 2



        player["keys"] += 1



        draw_card(room, player)



        room["log"] = f"{player['name']} 打出【灵感牌】，获得 2 条线索和 1 把钥匙。"



        next_player(room)



        finish_if_needed(room)



        return







    if card == "fog":



        affected = False



        for p in room["players"]:



            if p["id"] != player_id and p["clues"] > 0:



                p["clues"] -= 1



                affected = True



        draw_card(room, player)



        if affected:



            room["log"] = f"{player['name']} 打出【迷雾牌】，所有对手失去 1 条线索。"



        else:



            room["log"] = f"{player['name']} 打出【迷雾牌】，但所有对手都没有线索。"



        next_player(room)



        finish_if_needed(room)



        return







    if card == "trade":



        if player["clues"] >= 2:



            player["clues"] -= 2



            player["keys"] += 1



            room["log"] = f"{player['name']} 打出【交易牌】，消耗 2 条线索换来 1 把钥匙。"



        elif player["keys"] >= 1:



            player["keys"] -= 1



            player["clues"] += 2



            room["log"] = f"{player['name']} 打出【交易牌】，消耗 1 把钥匙换来 2 条线索。"



        else:



            room["log"] = f"{player['name']} 打出【交易牌】，但资源不足以交易，本回合浪费。"



        draw_card(room, player)



        next_player(room)



        finish_if_needed(room)



        return







    if card == "recycle":
        draw_card(room, player)
        room["log"] = f"{player['name']} ʹ�����ջ��ƣ��ӿ���� 1 ���ơ�"
        next_player(room)
        finish_if_needed(room)
        return
    if card == "freeze":



        room["skip_next"] = True



        draw_card(room, player)



        room["log"] = f"{player['name']} 打出【冻结牌】，下一名玩家的回合将被跳过。"



        next_player(room)



        finish_if_needed(room)



        return







    if card == "shield_break":



        opponents = [p for p in room["players"] if p["id"] != player_id]



        max_shield = max(p["shield"] for p in opponents)



        if max_shield > 0:



            targets = [p for p in opponents if p["shield"] == max_shield]



        else:



            max_clues = max(p["clues"] for p in opponents)



            targets = [p for p in opponents if p["clues"] == max_clues] if max_clues > 0 else []



        if not targets:



            draw_card(room, player)



            room["log"] = f"{player['name']} 打出【护盾击碎】，但没有可攻击的目标。"



            next_player(room)



            finish_if_needed(room)



            return



        draw_card(room, player)



        if len(targets) == 1:



            if targets[0]["shield"] > 0:



                targets[0]["shield"] -= 1



                room["log"] = f"{player['name']} 打出【护盾击碎】，{targets[0]['name']} 失去 1 层护盾。"



            else:



                targets[0]["clues"] = max(0, targets[0]["clues"] - 1)



                room["log"] = f"{player['name']} 打出【护盾击碎】，{targets[0]['name']} 失去 1 条线索。"



            next_player(room)



            finish_if_needed(room)



            return



        room["status"] = "choosing_disrupt"



        room["pending_choice"] = {



            "type": "shield_break",



            "prompt": "多名对手的护盾（或线索）并列最高，请选择目标：",



            "options": [p["id"] for p in targets],



            "source_id": player_id,



        }



        room["log"] = f"{player['name']} 打出【护盾击碎】，但目标并列，必须停下来问人。"



        return







    if card == "wild":



        if player["clues"] >= 1 and player["keys"] >= 1:



            player["clues"] -= 1



            player["keys"] -= 1



            player["score"] += 1



            room["log"] = f"{player['name']} 打出【万用牌】，把它变成终结资源，直接完成一次开箱并获得 1 分。"



        elif player["clues"] < 2:



            player["clues"] += 1



            room["log"] = f"{player['name']} 打出【万用牌】，当前最缺线索，因此获得 1 条线索。"



        else:



            player["keys"] += 1



            room["log"] = f"{player['name']} 打出【万用牌】，当前最缺钥匙，因此获得 1 把钥匙。"



        opponents = [p for p in room["players"] if p["id"] != player_id]



        max_clues = max(p["clues"] for p in opponents)



        if max_clues <= 0:



            draw_card(room, player)



            room["log"] = f"{player['name']} 打出【干扰牌】，但没有可削减线索的目标。"



            next_player(room)



            finish_if_needed(room)



            return







        targets = [p for p in opponents if p["clues"] == max_clues]



        draw_card(room, player)



        if len(targets) == 1:



            if absorb_shield(targets[0]):



                room["log"] = f"{player['name']} 打出【干扰牌】，但 {targets[0]['name']} 的护盾抵消了这次影响。"



            else:



                targets[0]["clues"] -= 1



                room["log"] = f"{player['name']} 打出【干扰牌】，{targets[0]['name']} 失去 1 条线索。"



            next_player(room)



            finish_if_needed(room)



            return







        room["status"] = "choosing_disrupt"



        room["pending_choice"] = {



            "type": "disrupt",



            "prompt": "两名对手在线索数上并列第一，请选择被干扰的目标：",



            "options": [p["id"] for p in targets],



            "source_id": player_id,



        }



        room["log"] = f"{player['name']} 打出【干扰牌】，但目标并列，必须停下来问人决定干扰谁。"



        return







    if card == "steal_key":



        opponents = [p for p in room["players"] if p["id"] != player_id]



        max_keys = max(p["keys"] for p in opponents)



        if max_keys <= 0:



            draw_card(room, player)



            room["log"] = f"{player['name']} 打出【顺手牵钥】，但没有对手持有钥匙，本次抢夺落空。"



            next_player(room)



            finish_if_needed(room)



            return







        targets = [p for p in opponents if p["keys"] == max_keys]



        draw_card(room, player)



        if len(targets) == 1:



            if absorb_shield(targets[0]):



                room["log"] = f"{player['name']} 打出【顺手牵钥】，但 {targets[0]['name']} 的护盾抵消了这次抢夺。"



            else:



                targets[0]["keys"] -= 1



                player["keys"] += 1



                room["log"] = f"{player['name']} 打出【顺手牵钥】，从 {targets[0]['name']} 手里夺走了 1 把钥匙。"



            next_player(room)



            finish_if_needed(room)



            return







        room["status"] = "choosing_disrupt"



        room["pending_choice"] = {



            "type": "steal_key",



            "prompt": "两名对手持有的钥匙数并列最多，请选择被抢夺的目标：",



            "options": [p["id"] for p in targets],



            "source_id": player_id,



        }



        room["log"] = f"{player['name']} 打出【顺手牵钥】，但目标并列，必须停下来问人决定抢谁。"



        return











def resolve_choice(code: str, player_id: str, target_id: str) -> None:



    room, _ = require_room_and_player(code, player_id)



    pending = room["pending_choice"]



    if not pending:



        raise ValueError("当前没有待决定的选择")



    if target_id not in pending["options"]:



        raise ValueError("目标不在可选范围内")







    if pending["type"] == "disrupt":



        target = next(p for p in room["players"] if p["id"] == target_id)



        room["status"] = "playing"



        room["pending_choice"] = None



        if absorb_shield(target):



            room["log"] = f"人类指定后，{target['name']} 的护盾抵消了这次干扰。"



        else:



            if target["clues"] > 0:



                target["clues"] -= 1



            room["log"] = f"人类指定后，{target['name']} 失去 1 条线索。"



        next_player(room)



        finish_if_needed(room)



        return







    if pending["type"] == "steal_key":



        source = next(p for p in room["players"] if p["id"] == pending["source_id"])



        target = next(p for p in room["players"] if p["id"] == target_id)



        room["status"] = "playing"



        room["pending_choice"] = None



        if absorb_shield(target):



            room["log"] = f"人类指定后，{target['name']} 的护盾抵消了这次抢夺。"



        else:



            if target["keys"] > 0:



                target["keys"] -= 1



                source["keys"] += 1



            room["log"] = f"人类指定后，{source['name']} 从 {target['name']} 手里夺走了 1 把钥匙。"



        next_player(room)



        finish_if_needed(room)



        return







    # After human resolves a choice, auto-play for AI if needed



    if pending["type"] == "shield_break":



        target = next(p for p in room["players"] if p["id"] == target_id)



        room["status"] = "playing"



        room["pending_choice"] = None



        if target["shield"] > 0:



            target["shield"] -= 1



            room["log"] = f"人类指定后，{target['name']} 被击碎 1 层护盾。"



        else:



            target["clues"] = max(0, target["clues"] - 1)



            room["log"] = f"人类指定后，{target['name']} 被击碎护盾失败，失去 1 条线索。"



        next_player(room)



        finish_if_needed(room)



        return







    if pending["type"] == "winner":



        room["status"] = "finished"



        room["pending_choice"] = None



        room["winner_id"] = target_id



        room["log"] = f"人类指定后，{player_name(room, target_id)} 成为并列决胜胜者。"



        return











class Handler(BaseHTTPRequestHandler):



    def log_message(self, format: str, *args) -> None:



        return







    def do_GET(self) -> None:



        parsed = urlparse(self.path)



        if parsed.path == "/":



            html_response(self, HTML.replace("%CARD_DEFS%", json.dumps(CARD_DEFS, ensure_ascii=False)))



            return



        if parsed.path == "/api/state":


            qs = parse_qs(parsed.query)



            code = (qs.get("room") or [""])[0].upper()



            player_id = (qs.get("player") or [""])[0]



            with LOCK:



                try:



                    room, _ = require_room_and_player(code, player_id)



                    auto_skip_empty_hand(room)



                    payload = {"ok": True, "room": serialize_room(room, player_id)}



                except ValueError as exc:



                    error(self, str(exc), 404)



                    return



            json_response(self, 200, payload)



            return




        if parsed.path == "/api/agent/info":

            data = {"server": "三机对抗卡牌游戏", "version": "1.0", "endpoints": ["/api/agent/info", "/api/agent/state"], "note": "通过 ?room=房间号&player=玩家ID 参数获取游戏状态"}

            json_response(self, 200, data)

            return


        error(self, "未找到页面", 404)







    def do_POST(self) -> None:



        try:



            length = int(self.headers.get("Content-Length", "0"))



            body = self.rfile.read(length) if length else b"{}"



            data = json.loads(body.decode("utf-8"))



        except (ValueError, json.JSONDecodeError):



            error(self, "请求格式错误")



            return










        with LOCK:



            try:



                if self.path == "/api/create_ai_game":



                    name = str(data.get("name", "")).strip()



                    if not name:



                        raise ValueError("请输入名字")



                    code, player_id = create_ai_game(name)



                    auto_play_ai_turns(code)



                    json_response(self, 200, {"ok": True, "room_code": code, "player_id": player_id})



                    return







                if self.path == "/api/create_room":



                    name = str(data.get("name", "")).strip()



                    if not name:



                        raise ValueError("请输入名字")



                    code, player_id = create_room(name)



                    json_response(self, 200, {"ok": True, "room_code": code, "player_id": player_id})



                    return



                if self.path == "/api/join_room":



                    name = str(data.get("name", "")).strip()



                    code = str(data.get("room_code", "")).strip().upper()



                    if not name:



                        raise ValueError("请输入名字")



                    if not code:



                        raise ValueError("请输入房间号")



                    player_id = join_room(code, name)



                    json_response(self, 200, {"ok": True, "player_id": player_id})



                    return







                if self.path == "/api/start_game":



                    start_game(str(data.get("room_code", "")).strip().upper(), str(data.get("player_id", "")).strip())



                    json_response(self, 200, {"ok": True})



                    return







                if self.path == "/api/play_card":



                    code = str(data.get("room_code", "")).strip().upper()



                    play_card(code, str(data.get("player_id", "")).strip(), int(data.get("hand_index", -1)))



                    auto_play_ai_turns(code)



                    json_response(self, 200, {"ok": True})



                    return







                if self.path == "/api/skip_turn":



                    code = str(data.get("room_code", "")).strip().upper()



                    player_id = str(data.get("player_id", "")).strip()



                    room, player = require_room_and_player(code, player_id)



                    if room["status"] != "playing":



                        raise ValueError("当前不能跳过")



                    if room["current_player_id"] != player_id:



                        raise ValueError("还没轮到你")



                    room["log"] = f"{player['name']} 选择跳过回合。"



                    draw_card(room, player)



                    next_player(room)



                    finish_if_needed(room)

                    auto_play_ai_turns(code)



                    json_response(self, 200, {"ok": True})



                    return







                if self.path == "/api/resolve_choice":



                    code = str(data.get("room_code", "")).strip().upper()



                    resolve_choice(code, str(data.get("player_id", "")).strip(), str(data.get("target_id", "")).strip())



                    auto_play_ai_turns(code)



                    json_response(self, 200, {"ok": True})



                    return







                error(self, "未找到接口", 404)



            except ValueError as exc:



                error(self, str(exc))











def main() -> None:



    server = ThreadingHTTPServer((HOST, PORT), Handler)



    print(f"联机牌局服务已启动：http://localhost:{PORT}")



    print("其他电脑请访问：http://房主电脑局域网IP:8000")



    print("按 Ctrl+C 停止服务。")



    try:



        server.serve_forever()



    except KeyboardInterrupt:



        pass



    finally:



        server.server_close()











if __name__ == "__main__":



    main()