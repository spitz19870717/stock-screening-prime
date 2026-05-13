# -*- coding: utf-8 -*-
"""
銘柄データの数値からルールベースでコメント・評価を生成する（API不要）
"""


def _rating(div_yield, per, roe):
    """配当利回り・PER・ROEから総合評価を判定する"""
    score = 0
    if div_yield >= 3.5:
        score += 2
    elif div_yield >= 2.5:
        score += 1

    if per <= 12:
        score += 2
    elif per <= 16:
        score += 1

    if roe >= 18:
        score += 2
    elif roe >= 13:
        score += 1

    if score >= 5:
        return "◎"
    elif score >= 3:
        return "○"
    else:
        return "△"


def _strength(div_yield, per, roe):
    """最も強みとなる指標を1文で返す"""
    if div_yield >= 4.0:
        return f"配当利回り{div_yield}%と高水準で、インカムゲインが期待できます。"
    if roe >= 18:
        return f"ROE{roe}%と高く、資本を効率よく活用できている企業です。"
    if per <= 12:
        return f"PER{per}倍と割安水準にあり、下値リスクが限定的です。"
    if div_yield >= 3.0:
        return f"配当利回り{div_yield}%で、安定した配当収入が見込めます。"
    if roe >= 13:
        return f"ROE{roe}%と高く、収益性の高いビジネスモデルを持ちます。"
    return f"配当利回り{div_yield}%・PER{per}倍・ROE{roe}%でバランスの取れた指標です。"


def _caution(per, roe, sector):
    """注意すべき点を1文で返す"""
    sector_risks = {
        "金融": "金利変動や景気後退の影響を受けやすい点に注意。",
        "銀行": "金利政策や不良債権リスクに注意が必要です。",
        "保険": "自然災害や金利変動が業績に影響する場合があります。",
        "不動産": "金利上昇局面では不動産価値や借入コストに影響が出る可能性。",
        "エネルギー": "原油・資源価格の変動が収益に直結します。",
        "素材": "原材料価格と為替の影響を受けやすい業種です。",
        "情報技術": "技術革新のスピードが速く、競合環境の変化に注意。",
        "通信": "設備投資負担が大きく、競争激化による料金引き下げ圧力があります。",
        "運輸": "燃料費や人件費の上昇が収益を圧迫するリスクがあります。",
        "小売": "消費動向や競合の影響を受けやすい業種です。",
    }
    for key, msg in sector_risks.items():
        if key in sector:
            return msg

    if per >= 18:
        return f"PER{per}倍とやや割高感があり、業績悪化時の株価下落に注意。"
    if roe < 12:
        return f"ROE{roe}%はやや低めで、資本効率の改善が今後の課題です。"
    return "市場全体の調整局面では下落する可能性があり、長期保有が前提です。"


def _make_comment(stock):
    div_yield = stock["div_yield"]
    per       = stock["per"]
    roe       = stock["roe"]
    sector    = stock.get("sector", "")

    strength = _strength(div_yield, per, roe)
    caution  = _caution(per, roe, sector)
    rating   = _rating(div_yield, per, roe)

    comment = f"{strength} 一方、{caution} 【総合評価：{rating}】"
    return comment, rating


def analyze_all(stocks, verbose=True):
    """
    スクリーニング結果の全銘柄にルールベースのコメント・評価を付与する。

    Args:
        stocks (list[dict]): screening.py の戻り値

    Returns:
        list[dict]: 各銘柄に "comment" と "rating" を追加したリスト
    """
    if verbose:
        print(f"コメント生成中（{len(stocks)}銘柄）...")

    for stock in stocks:
        comment, rating = _make_comment(stock)
        stock["comment"] = comment
        stock["rating"]  = rating

    if verbose:
        print("コメント生成完了")

    return stocks
