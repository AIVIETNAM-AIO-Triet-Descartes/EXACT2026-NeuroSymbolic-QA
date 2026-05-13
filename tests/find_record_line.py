"""
Tìm số dòng (line number) của record thứ idx trong file JSON.
Dùng để nhảy nhanh trong VS Code bằng Ctrl+G.

Cách dùng:
    python tests/find_record_line.py data/train/Logic_Based_Educational_Queries.json 34
    python tests/find_record_line.py data/train/Logic_Based_Educational_Queries.json 34 57 146
"""

import json
import sys
from pathlib import Path


def find_record_lines(filepath: str, indices: list[int]) -> dict[int, int]:
    """Tìm line number (1-indexed) của từng record theo index trong mảng JSON."""
    with open(filepath, encoding="utf-8") as f:
        raw = f.read()

    # Parse JSON để lấy data
    data = json.loads(raw)
    records = data if isinstance(data, list) else data.get("data", [])

    # Duyệt từng dòng để tìm vị trí bắt đầu của mỗi record
    lines = raw.splitlines()
    record_idx = -1       # index record hiện tại
    in_top_array = False  # đã vào mảng chính chưa
    brace_depth = 0       # đếm {} lồng nhau
    result = {}
    target_set = set(indices)

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not in_top_array:
            if stripped == "[" or stripped.startswith("["):
                in_top_array = True
            continue

        # Phát hiện bắt đầu record mới (mở { ở top-level của mảng)
        if brace_depth == 0 and "{" in stripped:
            record_idx += 1
            if record_idx in target_set:
                result[record_idx] = line_num
                if len(result) == len(target_set):
                    break  # Đã tìm đủ

        brace_depth += stripped.count("{") - stripped.count("}")

    return result


def main():
    if len(sys.argv) < 3:
        print("Cách dùng: python find_record_line.py <file.json> <idx1> [idx2] ...")
        print("Ví dụ:     python find_record_line.py data/train/Logic_Based_Educational_Queries.json 34 57 146")
        sys.exit(1)

    filepath = sys.argv[1]
    if not Path(filepath).exists():
        print(f"File không tồn tại: {filepath}")
        sys.exit(1)

    indices = [int(x) for x in sys.argv[2:]]
    result = find_record_lines(filepath, indices)

    print(f"\nFile: {filepath}")
    print(f"{'Record Index':<16} {'Line Number':<12} {'VS Code Jump'}")
    print("-" * 50)
    for idx in sorted(indices):
        if idx in result:
            line = result[idx]
            print(f"  idx={idx:<10} → line {line:<8} (Ctrl+G → {line})")
        else:
            print(f"  idx={idx:<10} → KHÔNG TÌM THẤY")


if __name__ == "__main__":
    main()
