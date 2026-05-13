# -*- coding: utf-8 -*-
"""
東証プライム市場全銘柄のスクリーニング
条件: 配当利回り2%以上、PER20倍以下、ROE10%以上
"""

import yfinance as yf
import warnings
import io
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
warnings.filterwarnings('ignore')

# 日経225銘柄の日本語名マッピング（既知銘柄のみ・他はyfinanceの名称を使用）
JP_NAMES = {
    "1332": "ニッスイ", "1333": "マルハニチロ", "1605": "INPEX",
    "1721": "コムシスホールディングス", "1801": "大成建設", "1802": "大林組",
    "1803": "清水建設", "1808": "長谷工コーポレーション", "1812": "鹿島建設",
    "1925": "大和ハウス工業", "1928": "積水ハウス", "1963": "日揮ホールディングス",
    "2002": "日清製粉グループ本社", "2269": "明治ホールディングス", "2282": "日本ハム",
    "2413": "エムスリー", "2432": "ディー・エヌ・エー", "2501": "サッポロホールディングス",
    "2502": "アサヒグループホールディングス", "2503": "キリンホールディングス",
    "2531": "宝ホールディングス", "2768": "双日", "2801": "キッコーマン",
    "2802": "味の素", "2871": "ニチレイ", "2914": "日本たばこ産業（JT）",
    "3086": "J.フロントリテイリング", "3099": "三越伊勢丹ホールディングス",
    "3101": "東洋紡", "3105": "日清紡ホールディングス", "3289": "東急不動産ホールディングス",
    "3382": "セブン＆アイ・ホールディングス", "3402": "東レ", "3405": "クラレ",
    "3407": "旭化成", "3436": "SUMCO", "3659": "ネクソン",
    "3861": "王子ホールディングス", "3863": "日本製紙",
    "4004": "レゾナック・ホールディングス", "4005": "住友化学", "4021": "日産化学",
    "4042": "東ソー", "4043": "トクヤマ", "4061": "デンカ", "4063": "信越化学工業",
    "4151": "協和キリン", "4183": "三井化学", "4188": "三菱ケミカルグループ",
    "4208": "UBE", "4307": "野村総合研究所", "4324": "電通グループ", "4452": "花王",
    "4502": "武田薬品工業", "4503": "アステラス製薬", "4506": "住友ファーマ",
    "4507": "塩野義製薬", "4519": "中外製薬", "4523": "エーザイ", "4543": "テルモ",
    "4568": "第一三共", "4578": "大塚ホールディングス", "4631": "DIC",
    "4661": "オリエンタルランド", "4689": "LINEヤフー", "4704": "トレンドマイクロ",
    "4751": "サイバーエージェント", "4755": "楽天グループ",
    "4901": "富士フイルムホールディングス", "4902": "コニカミノルタ", "4911": "資生堂",
    "5019": "出光興産", "5020": "ENEOSホールディングス",
    "5101": "横浜ゴム", "5108": "ブリヂストン", "5201": "AGC",
    "5214": "日本電気硝子", "5232": "住友大阪セメント", "5233": "太平洋セメント",
    "5301": "東海カーボン", "5332": "TOTO", "5333": "日本ガイシ", "5334": "日本特殊陶業",
    "5401": "日本製鉄", "5406": "神戸製鋼所", "5411": "JFEホールディングス",
    "5631": "日本製鋼所", "5706": "三井金属鉱業", "5707": "東邦亜鉛",
    "5711": "三菱マテリアル", "5713": "住友金属鉱山", "5714": "DOWAホールディングス",
    "5715": "古河電気工業", "5801": "住友電気工業", "5802": "フジクラ", "5803": "古河電工",
    "6098": "リクルートホールディングス", "6103": "オークマ", "6113": "アマダホールディングス",
    "6178": "日本郵政", "6273": "SMC", "6301": "コマツ（小松製作所）",
    "6302": "住友重機械工業", "6305": "日立建機", "6326": "クボタ", "6361": "荏原製作所",
    "6367": "ダイキン工業", "6471": "日本精工", "6472": "NTNコーポレーション",
    "6473": "ジェイテクト", "6501": "日立製作所", "6503": "三菱電機", "6504": "富士電機",
    "6506": "安川電機", "6526": "ソシオネクスト", "6594": "ニデック", "6645": "オムロン",
    "6702": "富士通", "6703": "沖電気工業", "6724": "セイコーエプソン",
    "6752": "パナソニックホールディングス", "6753": "シャープ", "6758": "ソニーグループ",
    "6762": "TDK", "6770": "アルプスアルパイン", "6841": "横河電機",
    "6857": "アドバンテスト", "6902": "デンソー", "6952": "カシオ計算機",
    "6954": "ファナック", "6971": "京セラ", "6976": "太陽誘電", "6981": "村田製作所",
    "7003": "三井E&Sホールディングス", "7004": "日立造船", "7011": "三菱重工業",
    "7012": "川崎重工業", "7013": "IHI", "7201": "日産自動車", "7202": "いすゞ自動車",
    "7203": "トヨタ自動車", "7205": "日野自動車", "7211": "三菱自動車工業",
    "7261": "マツダ", "7267": "本田技研工業（ホンダ）", "7269": "スズキ",
    "7270": "SUBARU", "7272": "ヤマハ発動機", "7731": "ニコン", "7733": "オリンパス",
    "7735": "SCREENホールディングス", "7751": "キヤノン", "7752": "リコー",
    "7762": "シチズン時計", "7832": "バンダイナムコホールディングス", "7951": "ヤマハ",
    "7974": "任天堂", "8001": "伊藤忠商事", "8002": "丸紅", "8003": "豊田通商",
    "8015": "豊田通商", "8031": "三井物産", "8035": "東京エレクトロン",
    "8053": "住友商事", "8058": "三菱商事", "8233": "高島屋", "8252": "丸井グループ",
    "8267": "イオン", "8303": "新生銀行", "8304": "あおぞら銀行",
    "8306": "三菱UFJフィナンシャル・グループ", "8308": "りそなホールディングス",
    "8309": "三井住友トラスト・ホールディングス", "8316": "三井住友フィナンシャルグループ",
    "8331": "千葉銀行", "8354": "ふくおかフィナンシャルグループ", "8355": "静岡銀行",
    "8411": "みずほフィナンシャルグループ", "8473": "SBIホールディングス",
    "8591": "オリックス", "8601": "大和証券グループ本社", "8604": "野村ホールディングス",
    "8630": "SOMPOホールディングス", "8697": "日本取引所グループ",
    "8750": "第一生命ホールディングス", "8766": "東京海上ホールディングス",
    "8795": "T&Dホールディングス", "9001": "東武鉄道", "9005": "東京急行電鉄（東急）",
    "9007": "小田急電鉄", "9008": "京王電鉄", "9009": "京成電鉄",
    "9020": "東日本旅客鉄道（JR東日本）", "9021": "西日本旅客鉄道（JR西日本）",
    "9022": "東海旅客鉄道（JR東海）", "9062": "日本通運", "9064": "ヤマトホールディングス",
    "9101": "日本郵船", "9104": "商船三井", "9107": "川崎汽船",
    "9202": "ANAホールディングス", "9301": "三菱倉庫",
    "9432": "NTT（日本電信電話）", "9433": "KDDI", "9434": "ソフトバンク",
    "9501": "東京電力ホールディングス", "9502": "中部電力", "9503": "関西電力",
    "9531": "東京ガス", "9532": "大阪ガス", "9602": "東宝", "9613": "NTTデータグループ",
    "9681": "東京ドーム", "9735": "セコム", "9766": "コナミグループ",
    "9983": "ファーストリテイリング", "9984": "ソフトバンクグループ",
}

SECTOR_JP = {
    "Communication Services": "通信・メディア",
    "Consumer Cyclical":      "一般消費財",
    "Consumer Defensive":     "生活必需品",
    "Energy":                 "エネルギー",
    "Financial Services":     "金融",
    "Healthcare":             "医薬・医療",
    "Industrials":            "産業・機械",
    "Basic Materials":        "素材・化学",
    "Real Estate":            "不動産",
    "Technology":             "テクノロジー",
    "Utilities":              "公共事業",
}

# 株主優待マッピング（主要銘柄のみ・他は「要確認」）
YUTAI = {
    "1928": "QUOカード500円相当（100株以上）",
    "2002": "自社製品詰め合わせ（500株以上）",
    "2269": "自社製品セット（1,000株以上）",
    "2282": "自社製品詰め合わせ・3,000円相当（100株以上）",
    "2501": "自社製品ビール等（1,000株以上）",
    "2502": "自社製品詰め合わせ（100株以上）",
    "2503": "自社製品詰め合わせ（100株以上）",
    "2531": "自社製品（お酒等）（1,000株以上）",
    "2801": "自社製品詰め合わせ（100株以上）",
    "2802": "自社製品詰め合わせ（100株以上）",
    "2871": "自社製品詰め合わせ・1,500円相当（100株以上）",
    "2914": "自社グループ食品詰め合わせ（100株以上）",
    "3086": "買物優待カード・10%割引（100株以上）",
    "3099": "買物優待カード・10%割引（100株以上）",
    "3289": "自社施設・ホテル優待券（100株以上）",
    "4661": "ディズニー1デーパスポート1枚（100株以上）",
    "4911": "自社製品詰め合わせ・2,000円相当（100株以上）",
    "8233": "買物優待カード・10%割引（100株以上）",
    "8252": "買物優待・5〜10%還元（100株以上）",
    "8267": "オーナーズカード・3〜7%還元（100株以上）",
    "8591": "なし（2024年3月廃止）",
    "9001": "全線乗車証（100株以上・半期毎）",
    "9005": "乗車証・グループ施設優待（100株以上）",
    "9007": "全線乗車証・施設優待（100株以上）",
    "9008": "全線乗車証（100株以上・半期毎）",
    "9009": "全線乗車証（100株以上・半期毎）",
    "9020": "新幹線・特急40%割引券（100株以上）",
    "9021": "鉄道50%割引乗車券（100株以上）",
    "9022": "新幹線10%割引券（100株以上）",
    "9202": "国内線50%割引券（100株以上・年2枚）",
    "9432": "dポイント（100株以上・保有年数で増量）",
    "9433": "Pontaポイント等2,000〜3,000円相当（100株・1年以上保有）",
    "9434": "PayPayポイント1,000pt（100株・1年以上保有・年2回）",
    "9602": "映画招待券2枚（100株以上）",
    "9766": "スポーツクラブ1ヶ月無料体験等（100株以上）",
}

# スクリーニング条件
MIN_YIELD = 2.0
MAX_PER   = 20.0
MIN_ROE   = 10.0


def get_prime_codes():
    """JPXから東証プライム市場の銘柄コードリストを取得する"""
    import requests
    import pandas as pd

    url = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"
    try:
        print("JPXから銘柄リストを取得中...")
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        resp.raise_for_status()

        try:
            df = pd.read_excel(io.BytesIO(resp.content), engine="xlrd")
        except Exception:
            df = pd.read_excel(io.BytesIO(resp.content), engine="openpyxl")

        for col in df.columns:
            if "市場" in str(col):
                prime = df[df[col].astype(str).str.contains("プライム", na=False)]
                code_col = df.columns[0]
                raw_codes = prime[code_col].dropna()
                codes = []
                for c in raw_codes:
                    try:
                        codes.append(f"{int(float(str(c))):04d}.T")
                    except (ValueError, TypeError):
                        pass
                print(f"東証プライム: {len(codes)}銘柄取得")
                return codes

        print("警告: 市場区分列が見つかりませんでした")
    except Exception as e:
        print(f"JPX銘柄リスト取得エラー: {e}")

    return []


def _calc_yield(info, price):
    rate = info.get("dividendRate") or info.get("trailingAnnualDividendRate")
    if rate and rate > 0 and price and price > 0:
        val = round(rate / price * 100, 2)
        if 0.1 <= val <= 20.0:
            return val
    raw = info.get("dividendYield")
    if not raw or raw <= 0:
        return None
    pct = round(raw if raw > 1 else raw * 100, 2)
    if pct > 20.0:
        return None
    return pct


def _screen_one(code):
    """1銘柄をスクリーニングし、条件を満たせばdictを返す"""
    time.sleep(0.5)  # レート制限対策
    try:
        info = yf.Ticker(code).info
        if not info or len(info) < 5:
            return None
        price = (info.get("currentPrice")
                 or info.get("regularMarketPrice")
                 or info.get("previousClose"))
        if not price or price <= 0:
            return None

        div_yield = _calc_yield(info, price)
        if not div_yield or div_yield < MIN_YIELD:
            return None

        per_raw = info.get("trailingPE") or info.get("forwardPE")
        per = round(per_raw, 1) if per_raw and 0 < per_raw < 300 else None
        if not per or per > MAX_PER:
            return None

        roe_raw = info.get("returnOnEquity")
        roe = round(roe_raw * 100, 1) if roe_raw else None
        if not roe or roe < MIN_ROE:
            return None

        payout_raw = info.get("payoutRatio")
        sector_en  = info.get("sector") or ""
        code_short = code.replace(".T", "")
        jp_name = JP_NAMES.get(code_short)
        en_name = info.get("longName") or info.get("shortName") or code_short

        return {
            "code":         code_short,
            "name":         jp_name or en_name,
            "sector":       SECTOR_JP.get(sector_en, sector_en or "その他"),
            "price":        round(price, 0),
            "min_purchase": int(price * 100),
            "div_yield":    div_yield,
            "per":          per,
            "roe":          roe,
            "pbr":          round(float(info.get("priceToBook")), 2) if info.get("priceToBook") else None,
            "payout":       round(payout_raw * 100, 1) if payout_raw else None,
            "market_cap":   info.get("marketCap"),
            "yutai":        YUTAI.get(code_short, "要確認"),
        }
    except Exception:
        return None


def _fetch_extra(stock):
    """フィルター通過銘柄の追加データ（自己資本比率・株価履歴）を取得"""
    code_full = stock["code"] + ".T"
    try:
        t = yf.Ticker(code_full)

        equity_ratio = None
        try:
            bs = t.balance_sheet
            if not bs.empty:
                eq, assets = None, None
                for label in ["Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity"]:
                    if label in bs.index:
                        eq = float(bs.loc[label].iloc[0])
                        break
                if "Total Assets" in bs.index:
                    assets = float(bs.loc["Total Assets"].iloc[0])
                if eq and assets and assets > 0:
                    equity_ratio = round(eq / assets * 100, 1)
        except Exception:
            pass
        stock["equity_ratio"] = equity_ratio

        hist = t.history(period="3y", interval="1mo")
        if not hist.empty:
            df = hist[["Open", "High", "Low", "Close"]].dropna()
            stock["hist_dates"]  = [d.strftime("%Y/%m") for d in df.index]
            stock["hist_ohlc"]   = [
                {"o": round(float(r.Open),  0),
                 "h": round(float(r.High),  0),
                 "l": round(float(r.Low),   0),
                 "c": round(float(r.Close), 0)}
                for _, r in df.iterrows()
            ]
            stock["hist_prices"] = [d["c"] for d in stock["hist_ohlc"]]
        else:
            stock["hist_dates"]  = []
            stock["hist_ohlc"]   = []
            stock["hist_prices"] = []
    except Exception:
        stock["equity_ratio"] = None
        stock["hist_dates"]   = []
        stock["hist_ohlc"]    = []
        stock["hist_prices"]  = []

    return stock


def run_screening(codes=None, verbose=True):
    """
    東証プライム全銘柄をスキャンし、条件を満たす銘柄を返す。

    Args:
        codes: 銘柄コードリスト（Noneの場合はJPXから自動取得）
    Returns:
        list[dict]: 条件を満たした銘柄データのリスト（株価安い順）
    """
    if codes is None:
        codes = get_prime_codes()
    if not codes:
        print("銘柄リストの取得に失敗しました。")
        return []

    total = len(codes)
    if verbose:
        print(f"東証プライム全{total}銘柄をスキャン中（順次処理）...")

    results = []

    for i, code in enumerate(codes):
        if verbose and (i + 1) % 100 == 0:
            print(f"  進捗: {i+1}/{total}")
        result = _screen_one(code)
        if result:
            results.append(result)

    results.sort(key=lambda x: x["price"])

    if verbose:
        print(f"追加データ取得中（{len(results)}銘柄）...")

    for stock in results:
        _fetch_extra(stock)

    if verbose:
        print(f"スキャン完了。条件一致: {len(results)}件（全件表示）")

    return results
