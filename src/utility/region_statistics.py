from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import stats as scipy_stats

from src.utility.formulas import get_algorithm_list, lookup_formula
from src.utility.spectral import (
    create_spectral_color_lut, evaluate_formula_values, normalize_formula_values,
)


def validate_polygon(points: list[tuple[float, float]]) -> np.ndarray:
    """Accept a finite normalized polygon with nonzero signed area."""
    polygon = np.asarray(points, dtype=np.float64)
    if polygon.ndim != 2 or polygon.shape[1] != 2 or not 3 <= len(polygon) <= 100:
        raise ValueError("框選區域須包含 3 至 100 個頂點")
    if not np.isfinite(polygon).all() or (polygon < 0).any() or (polygon > 1).any():
        raise ValueError("框選座標須介於 0 與 1 之間")
    x, y = polygon.T
    area = abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    if area <= 1e-12:
        raise ValueError("框選區域面積必須大於零")
    return polygon


def _polygon_mask(polygon: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    """Even-odd fill sampled at pixel centers, including concave polygons."""
    left, top, right, bottom = box
    x = np.arange(left, right)[None, :] + 0.5
    y = np.arange(top, bottom)[:, None] + 0.5
    inside = np.zeros((bottom - top, right - left), dtype=bool)
    for (x1, y1), (x2, y2) in zip(polygon, np.roll(polygon, -1, axis=0)):
        if y1 == y2:
            continue
        inside ^= ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1)
    return inside


def _pixel_batches(image: Image.Image, polygon: np.ndarray):
    """Read bounded strips of original pixels; fully transparent pixels are excluded."""
    polygon = polygon * np.array(image.size)
    left, top = np.floor(polygon.min(axis=0)).astype(int)
    right, bottom = np.ceil(polygon.max(axis=0)).astype(int)
    rows = max(1, 262144 // max(1, right - left))
    for start in range(top, bottom, rows):
        box = (left, start, right, min(start + rows, bottom))
        with image.crop(box) as crop, crop.convert("RGBA") as rgba:
            pixels = np.asarray(rgba)
            mask = _polygon_mask(polygon, box) & (pixels[:, :, 3] > 0)
            yield pixels[:, :, :3][mask]


def _accumulate_algorithm(pixels: np.ndarray, algorithm: dict, lut: np.ndarray, totals: dict) -> None:
    """累計未截斷的純 RGB 指數值，以及套用紅→黃→綠假色階（LUT，B 固定為 0）後的輸出 RGB 總和。"""
    expr, hrange = lookup_formula(algorithm["id"])
    values = evaluate_formula_values(pixels, expr)
    finite = np.isfinite(values)
    totals["sum"] += float(values[finite].sum(dtype=np.float64))
    totals["count"] += int(finite.sum())
    colors = lut[normalize_formula_values(values, hrange)]
    totals["rgb"] += colors.sum(axis=(0, 1), dtype=np.float64)


def _mean_rgb(total: np.ndarray, count: int) -> list[float] | None:
    return (total / count).round(2).tolist() if count else None


def _collect_statistics(image: Image.Image, polygon: np.ndarray) -> dict:
    algorithms = get_algorithm_list()
    totals = {a["id"]: {"sum": 0.0, "count": 0, "rgb": np.zeros(3)} for a in algorithms}
    rgb_sum, count = np.zeros(3), 0
    lut = create_spectral_color_lut()
    for batch in _pixel_batches(image, polygon):
        if len(batch) == 0:
            continue
        count += len(batch)
        rgb_sum += batch.sum(axis=0, dtype=np.float64)
        normalized = batch.astype(np.float32).reshape(-1, 1, 3) / 255.0
        for algorithm in algorithms:
            _accumulate_algorithm(normalized, algorithm, lut, totals[algorithm["id"]])
    return _format_statistics(count, rgb_sum, totals)


def _format_statistics(count: int, rgb_sum: np.ndarray, totals: dict) -> dict:
    """輸出統計結果：頂層 rgb_mean 為原始輸入影像 RGB 平均；各演算法 rgb_mean 為紅→黃→綠著色輸出 RGB 平均（B 恆為 0.00）。"""
    return {
        "pixel_count": count,
        "rgb_mean": _mean_rgb(rgb_sum, count),
        "algorithms": [
            {
                "id": key,
                "index_mean": value["sum"] / value["count"] if value["count"] else None,
                "valid_pixel_count": value["count"],
                "rgb_mean": _mean_rgb(value["rgb"], count),
            }
            for key, value in totals.items()
        ],
    }


def calculate_region_statistics(path: Path, points: list[tuple[float, float]]) -> dict:
    """Orchestrate validation, source loading, and region statistics without saving plots."""
    polygon = validate_polygon(points)
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(path) as image:
        return _collect_statistics(image, polygon)


def _group_label_for_plot(plot: dict[str, Any]) -> tuple[str, str, bool]:
    """Derive stable (group_key, display_label, is_control) for plot aggregation."""
    is_control = bool(plot.get("is_control", False))
    if is_control:
        return ("CK", "對照組 (CK)", True)
    treatment = str(plot.get("treatment") or "").strip()
    dose = str(plot.get("dose") or "").strip()
    parts = [p for p in (treatment, dose) if p]
    label = " ".join(parts) if parts else "未分類處理組"
    return (f"{treatment}::{dose}", label, False)


def _average_plot_entries(entries: list[dict[str, Any]], algo_ids: list[str]) -> dict[str, Any]:
    """計算多個小區的等權平均與描述統計（均值、標準差、變異係數、四分位數）。"""
    total_pixels = sum(int(e.get("pixel_count") or 0) for e in entries)
    valid_rgbs = [e["rgb_mean"] for e in entries if e.get("rgb_mean")]
    rgb_mean = (
        [round(sum(r[i] for r in valid_rgbs) / len(valid_rgbs), 2) for i in range(3)]
        if valid_rgbs
        else None
    )

    algorithms: list[dict[str, Any]] = []
    for algo_id in algo_ids:
        means: list[float] = []
        valid_pixel_total = 0
        algo_rgbs: list[list[float]] = []
        for entry in entries:
            row = next((a for a in entry.get("algorithms", []) if a["id"] == algo_id), None)
            if not row:
                continue
            valid_pixel_total += int(row.get("valid_pixel_count") or 0)
            if row.get("index_mean") is not None:
                means.append(float(row["index_mean"]))
            if row.get("rgb_mean"):
                algo_rgbs.append(row["rgb_mean"])

        if means:
            arr = np.asarray(means, dtype=np.float64)
            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr, ddof=1)) if len(arr) >= 2 else None
            cv_pct = (
                round(abs(std_val / mean_val) * 100.0, 2)
                if std_val is not None and abs(mean_val) > 1e-6
                else None
            )
            q1, median, q3 = (float(v) for v in np.percentile(arr, [25, 50, 75]))
            min_val = float(np.min(arr))
            max_val = float(np.max(arr))
        else:
            mean_val = None
            std_val = None
            cv_pct = None
            q1 = None
            median = None
            q3 = None
            min_val = None
            max_val = None

        algorithms.append(
            {
                "id": algo_id,
                "index_mean": mean_val,
                "index_std": std_val,
                "index_cv_pct": cv_pct,
                "index_min": min_val,
                "index_q1": q1,
                "index_median": median,
                "index_q3": q3,
                "index_max": max_val,
                "replicate_count": len(means),
                "tukey_group": None,
                "outlier_plot_numbers": [],
                "valid_pixel_count": valid_pixel_total,
                "rgb_mean": (
                    [round(sum(r[i] for r in algo_rgbs) / len(algo_rgbs), 2) for i in range(3)]
                    if algo_rgbs
                    else None
                ),
            }
        )

    return {
        "plot_count": len(entries),
        "pixel_count": total_pixels,
        "rgb_mean": rgb_mean,
        "algorithms": algorithms,
    }


def _find_maximal_cliques(adj: list[set[int]]) -> list[set[int]]:
    """使用 Bron-Kerbosch 演算法找出無顯著差異圖中的所有最大團（供顯著性字母標記使用）。"""
    cliques: list[set[int]] = []

    def _bron_kerbosch(r: set[int], p: set[int], x: set[int]) -> None:
        if not p and not x:
            cliques.append(set(r))
            return
        pivot = next(iter(p | x))
        for v in list(p - adj[pivot]):
            _bron_kerbosch(r | {v}, p & adj[v], x & adj[v])
            p.remove(v)
            x.add(v)

    _bron_kerbosch(set(), set(range(len(adj))), set())
    return cliques


def _index_to_letter(idx: int) -> str:
    """將團序號轉為農藝顯著性字母（a..z，超過 26 組則遞增為 a1..z1）。"""
    base = chr(ord("a") + (idx % 26))
    cycle = idx // 26
    return base if cycle == 0 else f"{base}{cycle}"


def _assign_compact_letters(group_keys_sorted: list[str], non_sig_adj: list[set[int]]) -> dict[str, str]:
    """依據已按均值降冪排序之組別與無顯著差異鄰接表，產出 Compact Letter Display (a/b/ab)。"""
    cliques = _find_maximal_cliques(non_sig_adj)
    cliques.sort(key=lambda c: (min(c), -len(c), sorted(c)))
    letters_by_idx: list[list[str]] = [[] for _ in group_keys_sorted]
    for clique_idx, clique in enumerate(cliques):
        letter = _index_to_letter(clique_idx)
        for member in clique:
            letters_by_idx[member].append(letter)
    return {
        key: "".join(letters_by_idx[i]) or "a"
        for i, key in enumerate(group_keys_sorted)
    }


def _extract_group_algo_samples(
    ordered_groups: list[dict[str, Any]], algo_id: str
) -> list[dict[str, Any]]:
    """從分組後的各小區結果中擷取指定演算法的非空均值樣本清單。"""
    samples: list[dict[str, Any]] = []
    for g in ordered_groups:
        values: list[float] = []
        plot_pairs: list[tuple[int, float]] = []
        for entry in g["entries"]:
            row = next((a for a in entry.get("algorithms", []) if a["id"] == algo_id), None)
            if row and row.get("index_mean") is not None:
                val = float(row["index_mean"])
                values.append(val)
                plot_pairs.append((int(entry["plot_number"]), val))
        samples.append(
            {
                "key": g["key"],
                "label": g["label"],
                "is_control": g["is_control"],
                "values": values,
                "plot_pairs": plot_pairs,
            }
        )
    return samples


def _compute_anova_and_tukey(
    ordered_groups: list[dict[str, Any]], algo_id: str, alpha: float = 0.05
) -> dict[str, Any]:
    """針對指定光譜指標執行單因子 ANOVA 與 Tukey HSD 事後多重比較，並產出顯著性字母標記。"""
    group_samples = _extract_group_algo_samples(ordered_groups, algo_id)
    non_empty = [g for g in group_samples if g["values"]]
    if len(non_empty) < 2:
        return {
            "formula_id": algo_id,
            "status": "insufficient_groups",
            "message": "處理組數不足（至少需 2 個具數值之組別），已略過顯著性檢定",
            "alpha": alpha,
            "anova_f": None,
            "anova_p": None,
            "significant": False,
            "group_letters": {},
            "pairwise": [],
        }

    testable = [g for g in non_empty if len(g["values"]) >= 2]
    if len(testable) < 2:
        return {
            "formula_id": algo_id,
            "status": "insufficient_replicates",
            "message": "重複數不足（至少需 2 組且每組至少 2 重複），已略過顯著性檢定",
            "alpha": alpha,
            "anova_f": None,
            "anova_p": None,
            "significant": False,
            "group_letters": {},
            "pairwise": [],
        }

    # 按組均值由高至低排序，使最高均值組對應字母 a
    testable.sort(key=lambda g: float(np.mean(g["values"])), reverse=True)
    arrays = [np.asarray(g["values"], dtype=np.float64) for g in testable]
    means = [float(np.mean(arr)) for arr in arrays]
    within_vars = [float(np.var(arr, ddof=1)) for arr in arrays]

    # 處理組內變異皆為 0 的退化情境
    if all(v <= 1e-18 for v in within_vars):
        if max(means) - min(means) <= 1e-12:
            return {
                "formula_id": algo_id,
                "status": "zero_variance",
                "message": "各組數值完全相同（變異為 0），無統計差異",
                "alpha": alpha,
                "anova_f": 0.0,
                "anova_p": 1.0,
                "significant": False,
                "group_letters": {g["key"]: "a" for g in testable},
                "pairwise": [],
            }
        # 組內無變異但組間均值不同：依均值相等關係建立鄰接表
        n_groups = len(testable)
        adj: list[set[int]] = [set() for _ in range(n_groups)]
        pairwise_zero: list[dict[str, Any]] = []
        for i in range(n_groups):
            for j in range(i + 1, n_groups):
                same = abs(means[i] - means[j]) <= 1e-12
                if same:
                    adj[i].add(j)
                    adj[j].add(i)
                pairwise_zero.append(
                    {
                        "group_a": testable[i]["key"],
                        "group_b": testable[j]["key"],
                        "label_a": testable[i]["label"],
                        "label_b": testable[j]["label"],
                        "mean_diff": round(means[i] - means[j], 4),
                        "p_value": 1.0 if same else 0.0,
                        "significant": not same,
                    }
                )
        letters = _assign_compact_letters([g["key"] for g in testable], adj)
        return {
            "formula_id": algo_id,
            "status": "ok",
            "message": "組內變異為 0 且組間均值不同，達顯著差異 (p < 0.001)",
            "alpha": alpha,
            "anova_f": None,
            "anova_p": 0.0,
            "significant": True,
            "group_letters": letters,
            "pairwise": pairwise_zero,
        }

    f_stat, p_val = scipy_stats.f_oneway(*arrays)
    anova_f = round(float(f_stat), 4) if np.isfinite(f_stat) else None
    anova_p = float(p_val) if np.isfinite(p_val) else None
    is_anova_sig = bool(anova_p is not None and anova_p < alpha)

    tukey_res = scipy_stats.tukey_hsd(*arrays)
    n_groups = len(testable)
    non_sig_adj: list[set[int]] = [set() for _ in range(n_groups)]
    pairwise: list[dict[str, Any]] = []

    for i in range(n_groups):
        for j in range(i + 1, n_groups):
            pair_p = float(tukey_res.pvalue[i, j])
            if not np.isfinite(pair_p):
                pair_p = 1.0
            pair_sig = bool(is_anova_sig and pair_p < alpha)
            if not pair_sig:
                non_sig_adj[i].add(j)
                non_sig_adj[j].add(i)
            pairwise.append(
                {
                    "group_a": testable[i]["key"],
                    "group_b": testable[j]["key"],
                    "label_a": testable[i]["label"],
                    "label_b": testable[j]["label"],
                    "mean_diff": round(means[i] - means[j], 4),
                    "p_value": round(pair_p, 4),
                    "significant": pair_sig,
                }
            )

    if is_anova_sig:
        group_letters = _assign_compact_letters([g["key"] for g in testable], non_sig_adj)
        p_desc = "< 0.001" if (anova_p is not None and anova_p < 0.001) else f"= {anova_p:.4f}"
        msg = f"單因子 ANOVA 達顯著差異 (F={anova_f}, p {p_desc})，已依 Tukey HSD 標記分群字母"
    else:
        group_letters = {g["key"]: "a" for g in testable}
        p_desc = f"= {anova_p:.4f}" if anova_p is not None else "無法計算"
        msg = f"單因子 ANOVA 未達顯著差異 (F={anova_f}, p {p_desc})，各組皆標記為 a"

    return {
        "formula_id": algo_id,
        "status": "ok",
        "message": msg,
        "alpha": alpha,
        "anova_f": anova_f,
        "anova_p": round(anova_p, 6) if anova_p is not None else None,
        "significant": is_anova_sig,
        "group_letters": group_letters,
        "pairwise": pairwise,
    }


def _detect_group_outliers(
    ordered_groups: list[dict[str, Any]], algo_id: str, cv_threshold_pct: float = 15.0
) -> list[dict[str, Any]]:
    """依重複數自適應偵測同組異常小區（只標記供複查，絕不自動剔除）。

    - n >= 4：以 1.5 × IQR 判定離群小區。
    - n == 3：當組內變異係數 CV% > 15% 時，標記偏離組中位數最遠者為需複查小區。
    """
    outliers: list[dict[str, Any]] = []
    group_samples = _extract_group_algo_samples(ordered_groups, algo_id)

    for g in group_samples:
        pairs = g["plot_pairs"]
        n = len(pairs)
        if n < 3:
            continue

        vals = np.asarray([v for _, v in pairs], dtype=np.float64)
        mean_val = float(np.mean(vals))
        std_val = float(np.std(vals, ddof=1))
        cv_pct = round(abs(std_val / mean_val) * 100.0, 2) if abs(mean_val) > 1e-6 else None
        q1, median, q3 = (float(x) for x in np.percentile(vals, [25, 50, 75]))

        if n >= 4:
            iqr = q3 - q1
            if iqr <= 1e-9:
                continue
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            for plot_num, val in pairs:
                if val < lower or val > upper:
                    direction = "high" if val > upper else "low"
                    outliers.append(
                        {
                            "plot_number": plot_num,
                            "group_key": g["key"],
                            "group_label": g["label"],
                            "is_control": g["is_control"],
                            "formula_id": algo_id,
                            "value": round(val, 4),
                            "group_mean": round(mean_val, 4),
                            "group_median": round(median, 4),
                            "group_cv_pct": cv_pct,
                            "method": "iqr_1.5",
                            "direction": direction,
                            "reason": f"數值 {val:.4f} 超出 1.5×IQR 範圍 [{lower:.4f}, {upper:.4f}]，建議複查影像",
                        }
                    )
        elif n == 3 and cv_pct is not None and cv_pct > cv_threshold_pct:
            # 3 重複且組內變異過大時，標記偏離中位數最遠之單一小區
            furthest_plot, furthest_val = max(pairs, key=lambda item: abs(item[1] - median))
            if abs(furthest_val - median) > 1e-9:
                direction = "high" if furthest_val > median else "low"
                outliers.append(
                    {
                        "plot_number": furthest_plot,
                        "group_key": g["key"],
                        "group_label": g["label"],
                        "is_control": g["is_control"],
                        "formula_id": algo_id,
                        "value": round(furthest_val, 4),
                        "group_mean": round(mean_val, 4),
                        "group_median": round(median, 4),
                        "group_cv_pct": cv_pct,
                        "method": "cv_15_n3",
                        "direction": direction,
                        "reason": (
                            f"3 重複組內變異係數 CV={cv_pct:.1f}% (>{cv_threshold_pct:.0f}%)，"
                            f"此小區 ({furthest_val:.4f}) 偏離組中位數 ({median:.4f}) 最遠，建議複查影像"
                        ),
                    }
                )

    return outliers


def calculate_plots_statistics(path: Path, plots: list[dict[str, Any]]) -> dict[str, Any]:
    """單次讀取正射圖完成所有小區 RGB 與光譜統計，並計算 CK 基準、處理組彙整、ANOVA/Tukey 檢定與離群小區。"""
    algo_ids = [a["id"] for a in get_algorithm_list()]
    plot_results: list[dict[str, Any]] = []

    Image.MAX_IMAGE_PIXELS = None
    with Image.open(path) as image:
        for plot in plots:
            raw_coords = plot.get("coords", "")
            try:
                pts = json.loads(raw_coords) if isinstance(raw_coords, str) else raw_coords
                polygon = validate_polygon([(float(p[0]), float(p[1])) for p in pts])
                stats = _collect_statistics(image, polygon)
            except Exception:
                stats = {
                    "pixel_count": 0,
                    "rgb_mean": None,
                    "algorithms": [
                        {"id": aid, "index_mean": None, "valid_pixel_count": 0, "rgb_mean": None}
                        for aid in algo_ids
                    ],
                }

            plot_results.append(
                {
                    "plot_number": int(plot.get("plot_number", 0)),
                    "is_control": bool(plot.get("is_control", False)),
                    "treatment": str(plot.get("treatment") or ""),
                    "dose": str(plot.get("dose") or ""),
                    **stats,
                }
            )

    control_entries = [p for p in plot_results if p["is_control"]]
    control_baseline = (
        _average_plot_entries(control_entries, algo_ids) if control_entries else None
    )

    groups_bucket: dict[str, dict[str, Any]] = {}
    for entry in plot_results:
        gkey, glabel, is_ctrl = _group_label_for_plot(entry)
        if gkey not in groups_bucket:
            groups_bucket[gkey] = {
                "key": gkey,
                "label": glabel,
                "is_control": is_ctrl,
                "entries": [],
            }
        groups_bucket[gkey]["entries"].append(entry)

    ordered_groups = sorted(
        groups_bucket.values(),
        key=lambda g: (not g["is_control"], g["label"]),
    )

    statistical_tests = {
        aid: _compute_anova_and_tukey(ordered_groups, aid) for aid in algo_ids
    }
    outliers = {
        aid: _detect_group_outliers(ordered_groups, aid) for aid in algo_ids
    }

    treatment_groups: list[dict[str, Any]] = []
    for g in ordered_groups:
        avg_data = _average_plot_entries(g["entries"], algo_ids)
        for algo_row in avg_data["algorithms"]:
            aid = algo_row["id"]
            algo_row["tukey_group"] = statistical_tests[aid]["group_letters"].get(g["key"])
            algo_row["outlier_plot_numbers"] = [
                o["plot_number"] for o in outliers[aid] if o["group_key"] == g["key"]
            ]
        treatment_groups.append(
            {
                "key": g["key"],
                "label": g["label"],
                "is_control": g["is_control"],
                "plot_numbers": [e["plot_number"] for e in g["entries"]],
                **avg_data,
            }
        )

    field_summary = _average_plot_entries(plot_results, algo_ids)

    return {
        "plots": plot_results,
        "control_baseline": control_baseline,
        "treatment_groups": treatment_groups,
        "field_summary": field_summary,
        "statistical_tests": statistical_tests,
        "outliers": outliers,
    }
