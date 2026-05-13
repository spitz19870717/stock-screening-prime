# -*- coding: utf-8 -*-
"""
分析結果をiPad対応のHTMLレポートに変換する
"""

import json
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

RATING_CONFIG = {
    "◎": {"label": "◎ 優良",   "class": "badge-excellent"},
    "○": {"label": "○ 良好",   "class": "badge-good"},
    "△": {"label": "△ 要注意", "class": "badge-caution"},
}


def _fmt_currency(value):
    if value is None:
        return "不明"
    return f"{int(value):,}円"


def _fmt_market_cap(value):
    if not value:
        return "不明"
    if value >= 1e12:
        return f"{value/1e12:.1f}兆円"
    return f"{value/1e8:.0f}億円"


def _metric_html(label, value, unit="", highlight_class=""):
    cls = f"metric {highlight_class}".strip()
    return f"""
        <div class="{cls}">
          <div class="metric-value">{value}<span class="metric-unit">{unit}</span></div>
          <div class="metric-label">{label}</div>
        </div>"""


def _yield_class(val):
    if val >= 4.0:
        return "metric-green"
    if val >= 3.0:
        return "metric-blue"
    return ""


def _per_class(val):
    if val is None:
        return ""
    if val <= 12:
        return "metric-green"
    if val <= 20:
        return "metric-blue"
    return "metric-red"


def _roe_class(val):
    if val is None:
        return ""
    if val >= 15:
        return "metric-green"
    if val >= 10:
        return "metric-blue"
    return "metric-red"


def _pbr_class(val):
    if val is None:
        return ""
    if val <= 1.0:
        return "metric-green"
    if val <= 1.5:
        return "metric-blue"
    return ""


def _equity_color(val):
    if val is None:
        return "inherit"
    if val >= 50:
        return "#1a7a3c"
    if val >= 30:
        return "#0055a5"
    return "#9a2020"


def _glossary_html():
    finance_items = [
        ("配当利回り",   "株価に対する年間配当の割合。高いほど配当収入が多い。3%以上が魅力的な水準。"),
        ("PER",         "株価 ÷ 1株利益。低いほど割安。20倍以下が目安で、12倍以下はさらに割安（緑色）。"),
        ("ROE",         "自己資金をどれだけ効率よく使って利益を上げているか。10%以上が優良企業の目安（青色）、15%以上が特に優秀（緑色）。"),
        ("PBR",         "株価 ÷ 1株純資産。1倍以下は「会社を解散しても損がない」割安水準の目安（緑色）。"),
        ("配当性向",     "利益のうち何%を配当に回しているか。30〜60%が安定的。80%超は将来の減配リスクあり。"),
        ("自己資本比率", "総資産に占める自己資金の割合。40%以上が安全な水準。低いほど借金への依存度が高い。"),
        ("時価総額",     "会社全体の価値（株価 × 発行株数）。大きいほど財務の安定性が高い傾向がある。"),
    ]
    chart_items = [
        ("ローソク足",           "緑色（陽線）＝その月の終値が始値より高い（上昇）。赤色（陰線）＝終値が始値より低い（下落）。縦線が高値・安値の範囲を示す。"),
        ("移動平均線（MA）",     "過去N期間の終値の平均を結んだ線。株価の大まかなトレンドを把握するために使う。オレンジ＝6ヶ月、青＝12ヶ月。"),
        ("ゴールデンクロス",     "短期線（オレンジ）が長期線（青）を下から上に突き抜けた時。上昇トレンドへの転換サインとされる。"),
        ("デッドクロス",         "短期線（オレンジ）が長期線（青）を上から下に突き抜けた時。下落トレンドへの転換サインとされる。"),
        ("↑ 上昇トレンドマーク", "直近の株価が6ヶ月MAを上回り、かつ6ヶ月MAが12ヶ月MAを上回っている銘柄に表示。買いを検討しやすいタイミングの目安。"),
    ]

    def rows_html(items):
        return "".join(
            f'<div class="gl-row"><span class="gl-term">{n}</span>'
            f'<span class="gl-desc">{d}</span></div>'
            for n, d in items
        )

    return (
        '<details class="glossary">'
        '<summary>📖 指標・チャートの見方（タップで開く）</summary>'
        '<div class="gl-body">'
        '<div class="gl-section-title">📊 財務指標</div>'
        + rows_html(finance_items) +
        '<div class="gl-section-title" style="margin-top:12px">📈 チャートの見方</div>'
        + rows_html(chart_items) +
        '</div></details>'
    )


def _card_html(stock, index):
    rating   = stock.get("rating", "○")
    rc       = RATING_CONFIG.get(rating, RATING_CONFIG["○"])
    comment  = stock.get("comment", "").replace("\n", "<br>")
    purchase = _fmt_currency(stock.get("min_purchase"))
    mktcap   = _fmt_market_cap(stock.get("market_cap"))

    per_val = stock.get("per")
    roe_val = stock.get("roe")
    pbr_val = stock.get("pbr")
    eq_val  = stock.get("equity_ratio")

    per_disp = f"{per_val}" if per_val else "不明"
    roe_disp = f"{roe_val}" if roe_val else "不明"
    pbr_disp = f"{pbr_val}" if pbr_val else "不明"
    eq_disp  = f"{eq_val}%" if eq_val is not None else "不明"

    payout      = stock.get("payout")
    payout_disp = f"{payout}%" if payout else "不明"

    yutai = stock.get("yutai", "要確認")

    # 上昇トレンド判定（終値 > 6ヶ月MA かつ 6ヶ月MA > 12ヶ月MA）
    hist_ohlc_all = stock.get("hist_ohlc", [])
    is_trending_up = False
    if len(hist_ohlc_all) >= 12:
        closes = [o["c"] for o in hist_ohlc_all]
        ma6  = sum(closes[-6:])  / 6
        ma12 = sum(closes[-12:]) / 12
        is_trending_up = closes[-1] > ma6 and ma6 > ma12

    # ローソク足チャート（3年月足）
    hist_dates  = stock.get("hist_dates",  [])
    hist_ohlc   = stock.get("hist_ohlc",   [])
    hist_prices = stock.get("hist_prices", [])
    valid_prices = [p for p in hist_prices if p is not None and p > 0]

    if hist_dates and len(hist_ohlc) >= 3:
        is_up       = valid_prices[-1] >= valid_prices[0] if len(valid_prices) >= 2 else True
        trend_color = "#1a7a3c" if is_up else "#c0392b"
        change_pct  = round((valid_prices[-1] / valid_prices[0] - 1) * 100, 1) if len(valid_prices) >= 2 else 0
        sign        = "+" if change_pct >= 0 else ""
        chart_block = f"""
    <div class="chart-section">
      <div class="chart-label">直近3年の株価チャート（月足）
        <span class="chart-change" style="color:{trend_color}">{sign}{change_pct}%</span>
      </div>
      <div class="chart-wrapper" id="chart-{index}"></div>
    </div>"""
    else:
        chart_block = ""

    price_disp   = f"{int(stock['price']):,}円" if stock.get('price') else "不明"
    trend_badge  = '<span class="badge-trending">↑ 上昇トレンド</span>' if is_trending_up else ''

    return f"""
  <article class="card {'card-trending' if is_trending_up else ''}" id="stock-{index}">
    <div class="card-header">
      <div class="card-title-block">
        <span class="stock-code">{stock['code']}</span>
        <div class="stock-name-row">
          <h2 class="stock-name">{stock['name']}</h2>
          <span class="stock-price-hero">{price_disp}</span>
        </div>
        <span class="stock-sector">{stock['sector']}</span>
      </div>
      <div class="badge-col">
        {trend_badge}
        <span class="badge {rc['class']}">{rc['label']}</span>
      </div>
    </div>

    <div class="metrics">
      {_metric_html("配当利回り", stock['div_yield'], "%", _yield_class(stock['div_yield']))}
      {_metric_html("PER",  per_disp, "倍", _per_class(per_val))}
      {_metric_html("ROE",  roe_disp, "%",  _roe_class(roe_val))}
      {_metric_html("PBR",  pbr_disp, "倍", _pbr_class(pbr_val))}
    </div>

    <div class="sub-metrics">
      <span>株価: <strong>{_fmt_currency(stock.get('price'))}</strong></span>
      <span>100株購入額: <strong>{purchase}</strong></span>
      <span>配当性向: <strong>{payout_disp}</strong></span>
      <span>自己資本比率: <strong style="color:{_equity_color(eq_val)}">{eq_disp}</strong></span>
      <span>時価総額: <strong>{mktcap}</strong></span>
      <span>株主優待: <strong>{yutai}</strong></span>
    </div>
{chart_block}
    <div class="ai-comment">
      <div class="ai-label">📊 分析コメント</div>
      <p>{comment}</p>
    </div>
  </article>"""


def _chart_scripts(stocks):
    inits = []
    for i, stock in enumerate(stocks):
        dates = stock.get("hist_dates", [])
        ohlc  = stock.get("hist_ohlc",  [])
        if not dates or len(ohlc) < 3:
            continue
        data_js = json.dumps([
            {"x": d, "y": [o["o"], o["h"], o["l"], o["c"]]}
            for d, o in zip(dates, ohlc)
        ])
        inits.append(f"  initChart('chart-{i}', {data_js});")

    if not inits:
        return ""

    return (
        '<script src="https://cdn.jsdelivr.net/npm/apexcharts@3.46.0/dist/apexcharts.min.js"></script>\n'
        "<script>\n"
        "function calcMA(data, period) {\n"
        "  return data.map(function(d, i) {\n"
        "    var count = Math.min(i + 1, period);\n"
        "    var sum = 0;\n"
        "    for (var j = i - count + 1; j <= i; j++) sum += data[j].y[3];\n"
        "    return { x: d.x, y: Math.round(sum / count) };\n"
        "  });\n"
        "}\n"
        "function initChart(id, data) {\n"
        "  var el = document.getElementById(id);\n"
        "  if (!el) return;\n"
        "  new ApexCharts(el, {\n"
        "    chart: { type: 'candlestick', height: 240,\n"
        "      toolbar: { show: false }, animations: { enabled: false },\n"
        "      zoom: { enabled: false } },\n"
        "    series: [\n"
        "      { name: 'ローソク足', type: 'candlestick', data: data },\n"
        "      { name: '6ヶ月MA',   type: 'line',         data: calcMA(data, 6) },\n"
        "      { name: '12ヶ月MA',  type: 'line',         data: calcMA(data, 12) }\n"
        "    ],\n"
        "    colors: ['transparent', '#e67e22', '#2980b9'],\n"
        "    stroke: { width: [1, 1.5, 1.5], curve: 'smooth' },\n"
        "    plotOptions: { candlestick: {\n"
        "      colors: { upward: '#1a7a3c', downward: '#c0392b' },\n"
        "      wick: { useFillColor: true }\n"
        "    }},\n"
        "    legend: { show: true, fontSize: '10px',\n"
        "      markers: { width: 10, height: 3, radius: 0 } },\n"
        "    xaxis: { type: 'category', tickAmount: 10,\n"
        "      labels: { rotate: -45, style: { fontSize: '9px' } } },\n"
        "    yaxis: { labels: { style: { fontSize: '9px' },\n"
        "      formatter: function(v) { return Math.round(v).toLocaleString() + '円'; } } },\n"
        "    grid: { borderColor: '#e5e7eb' },\n"
        "    tooltip: { shared: false, custom: function(opt) {\n"
        "      if (opt.seriesIndex !== 0) return '';\n"
        "      var d = opt.w.config.series[0].data[opt.dataPointIndex];\n"
        "      return '<div style=\"padding:8px;font-size:11px;line-height:1.8\">'\n"
        "        + '<b>' + d.x + '</b><br>'\n"
        "        + '始値: ' + d.y[0].toLocaleString() + '円<br>'\n"
        "        + '高値: ' + d.y[1].toLocaleString() + '円<br>'\n"
        "        + '安値: ' + d.y[2].toLocaleString() + '円<br>'\n"
        "        + '終値: ' + d.y[3].toLocaleString() + '円</div>';\n"
        "    }}\n"
        "  }).render();\n"
        "}\n"
        "document.addEventListener('DOMContentLoaded', function() {\n"
        + "\n".join(inits) + "\n"
        "});\n"
        "</script>"
    )


CSS = """
:root {
  --primary: #1a3a5c;
  --primary-light: #2c5282;
  --green: #1a7a3c;
  --green-bg: #e8f5ee;
  --blue: #0055a5;
  --blue-bg: #e6f0ff;
  --red: #9a2020;
  --red-bg: #fdecea;
  --yellow: #9a6000;
  --yellow-bg: #fff8e6;
  --gray: #6b7280;
  --card-bg: #ffffff;
  --page-bg: #f0f4f8;
  --text: #1f2937;
  --border: #e5e7eb;
  --radius: 14px;
  --shadow: 0 2px 12px rgba(0,0,0,0.08);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;
  background: var(--page-bg);
  color: var(--text);
  font-size: 16px;
  line-height: 1.6;
  -webkit-text-size-adjust: 100%;
}

header {
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  color: #fff;
  padding: 28px 20px 24px;
}
header h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 6px; }
.header-meta { font-size: 0.85rem; opacity: 0.85; }

.container { max-width: 1100px; margin: 0 auto; padding: 0 16px; }

.summary-section {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 18px 20px;
  margin: 20px 0 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.summary-section h2 { font-size: 0.9rem; color: var(--gray); width: 100%; margin-bottom: 4px; }
.condition-tag {
  background: var(--blue-bg);
  color: var(--blue);
  border-radius: 20px;
  padding: 5px 14px;
  font-size: 0.85rem;
  font-weight: 600;
}

/* ===== 指標の見方（グロッサリー） ===== */
.glossary {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin: 8px 0;
  border: 1px solid var(--border);
  overflow: hidden;
}
.glossary summary {
  padding: 14px 20px;
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--primary);
  cursor: pointer;
  user-select: none;
  list-style: none;
}
.glossary summary::-webkit-details-marker { display: none; }
.glossary summary::after {
  content: " ▼";
  font-size: 0.75rem;
  color: var(--gray);
}
.glossary[open] summary::after { content: " ▲"; }
.gl-body {
  padding: 0 20px 16px;
  border-top: 1px solid var(--border);
}
.gl-row {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid var(--page-bg);
  font-size: 0.85rem;
}
.gl-row:last-child { border-bottom: none; }
.gl-term {
  font-weight: 700;
  color: var(--primary);
  padding-top: 1px;
}
.gl-desc { color: var(--text); line-height: 1.55; }
.gl-section-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: var(--gray);
  padding: 8px 0 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 4px;
}
@media (max-width: 480px) {
  .gl-row { grid-template-columns: 1fr; gap: 2px; }
}

.result-count {
  font-size: 0.9rem;
  color: var(--gray);
  margin: 12px 0 16px;
  padding: 0 4px;
}

.card-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  margin-bottom: 32px;
}
@media (min-width: 768px) {
  .card-grid { grid-template-columns: repeat(2, 1fr); }
}

.card {
  background: var(--card-bg);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 20px;
  border: 1px solid var(--border);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.card-title-block { flex: 1; min-width: 0; }
.stock-code {
  font-size: 0.75rem;
  color: var(--gray);
  font-weight: 600;
  letter-spacing: 0.05em;
}
.stock-name-row {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 10px;
  margin: 2px 0 4px;
}
.stock-name {
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.3;
}
.stock-price-hero {
  font-size: 1.45rem;
  font-weight: 800;
  color: var(--primary);
  letter-spacing: -0.02em;
  white-space: nowrap;
}
.stock-sector {
  display: inline-block;
  font-size: 0.75rem;
  color: var(--gray);
  background: var(--page-bg);
  border-radius: 4px;
  padding: 2px 8px;
}

.badge-col {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  flex-shrink: 0;
}
.badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 700;
  white-space: nowrap;
}
.badge-excellent { background: var(--green-bg);  color: var(--green);  }
.badge-good      { background: var(--blue-bg);   color: var(--blue);   }
.badge-caution   { background: var(--yellow-bg); color: var(--yellow); }
.badge-trending {
  padding: 5px 10px;
  border-radius: 20px;
  font-size: 0.78rem;
  font-weight: 700;
  white-space: nowrap;
  background: #fff3cd;
  color: #856404;
  border: 1px solid #ffc107;
}
.card-trending {
  border: 2px solid #ffc107;
  box-shadow: 0 2px 16px rgba(255,193,7,0.25);
}

.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
@media (max-width: 480px) {
  .metrics { grid-template-columns: repeat(2, 1fr); }
}

.metric {
  background: var(--page-bg);
  border-radius: 10px;
  padding: 10px 8px;
  text-align: center;
}
.metric-value {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--primary);
}
.metric-unit { font-size: 0.7rem; font-weight: 400; }
.metric-label { font-size: 0.72rem; color: var(--gray); margin-top: 2px; }

.metric-green { background: var(--green-bg); }
.metric-green .metric-value { color: var(--green); }
.metric-blue  { background: var(--blue-bg); }
.metric-blue  .metric-value { color: var(--blue); }
.metric-red   { background: var(--red-bg); }
.metric-red   .metric-value { color: var(--red); }

.sub-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  font-size: 0.82rem;
  color: var(--gray);
  margin-bottom: 14px;
  padding: 10px 12px;
  background: var(--page-bg);
  border-radius: 8px;
}

/* ===== グラフ ===== */
.chart-section { margin-bottom: 14px; }
.chart-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--gray);
  margin-bottom: 6px;
}
.chart-change {
  font-size: 0.82rem;
  font-weight: 700;
  margin-left: 6px;
}
.chart-wrapper {
  width: 100%;
  min-height: 220px;
}

.ai-comment {
  background: #f5f7ff;
  border-left: 4px solid #4a6fa5;
  border-radius: 0 8px 8px 0;
  padding: 12px 14px;
}
.ai-label {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--primary);
  margin-bottom: 6px;
  letter-spacing: 0.04em;
}
.ai-comment p { font-size: 0.9rem; line-height: 1.65; }

.no-results {
  text-align: center;
  padding: 60px 20px;
  color: var(--gray);
  font-size: 1rem;
}

footer {
  background: #fff;
  border-top: 1px solid var(--border);
  padding: 24px 20px;
  font-size: 0.82rem;
  color: var(--gray);
  line-height: 1.7;
}
.footer-disclaimer { margin-bottom: 8px; }
"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="株式レポート">
  <title>東証プライム 日次スクリーニングレポート</title>
  <style>{css}</style>
</head>
<body>

<header>
  <div class="container">
    <h1>📊 東証プライム 日次スクリーニングレポート</h1>
    <p class="header-meta">最終更新: {updated_at} ／ 対象: 東証プライム（{total_scanned}銘柄）</p>
  </div>
</header>

<main class="container">

  <div class="summary-section">
    <h2>スクリーニング条件</h2>
    <span class="condition-tag">配当利回り 2%以上</span>
    <span class="condition-tag">PER 20倍以下</span>
    <span class="condition-tag">ROE 10%以上</span>
    <span class="condition-tag">株価安い順 全件表示</span>
  </div>

  {glossary}

  <p class="result-count">{result_count}</p>

  {body}

</main>

<footer>
  <div class="container">
    <p class="footer-disclaimer">
      ⚠️ このレポートは情報提供を目的としており、特定の銘柄への投資を推奨するものではありません。
      投資の最終判断はご自身の責任で行ってください。株式投資には元本割れのリスクがあります。
    </p>
    <p>株主優待情報は変更・廃止される場合があります。最新情報は各社のIRページでご確認ください。</p>
    <p>次回更新予定: {next_update} ／ データ取得元: Yahoo Finance（yfinance）</p>
  </div>
</footer>

{chart_scripts}
</body>
</html>"""


def generate(stocks, total_scanned=225):
    now = datetime.now(JST)
    updated_at  = now.strftime("%Y年%m月%d日 %H:%M JST")
    tomorrow    = now + timedelta(days=1)
    next_update = tomorrow.strftime("%Y年%m月%d日 9:10")

    glossary = _glossary_html()

    if not stocks:
        body = '<div class="no-results">今日は条件に合う銘柄がありませんでした。<br>明日のレポートをお待ちください。</div>'
        result_count  = "0件（条件一致なし）"
        chart_scripts = ""
    else:
        cards = "\n".join(_card_html(s, i) for i, s in enumerate(stocks))
        body  = f'<div class="card-grid">\n{cards}\n</div>'
        result_count  = f"{len(stocks)}件の銘柄が条件を満たしました（株価安い順）"
        chart_scripts = _chart_scripts(stocks)

    return HTML_TEMPLATE.format(
        css=CSS,
        updated_at=updated_at,
        total_scanned=total_scanned,
        result_count=result_count,
        body=body,
        glossary=glossary,
        next_update=next_update,
        chart_scripts=chart_scripts,
    )


def save(html, path="docs/index.html"):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTMLを保存しました: {path}")
