# -*- coding: utf-8 -*-
"""
メイン実行スクリプト
screening → コメント生成 → HTML生成 → docs/index.html に保存
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from screening   import run_screening, get_prime_codes
from ai_analysis import analyze_all
from generate_html import generate, save


def main():
    print("=" * 50)
    print("  東証プライム 日次スクリーニング＆レポート生成")
    print("=" * 50)

    codes = get_prime_codes()
    print(f"取得した銘柄数: {len(codes)}社")

    stocks = run_screening(codes=codes, verbose=True)

    if not stocks:
        print("条件に合う銘柄がありませんでした。HTMLは「0件」として生成します。")

    stocks = analyze_all(stocks, verbose=True)

    html = generate(stocks, total_scanned=len(codes))
    save(html, path="docs/index.html")

    print("\n完了！docs/index.html を確認してください。")


if __name__ == "__main__":
    main()
