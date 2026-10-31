#!/usr/bin/env python3
"""compare_arms.py - compara brazos de clasificación de postura (3 clases).

Brazos: lexicon (MASSIVE _score_text), llm (API compatible con OpenAI),
von (von.decide, local), jev (OpenRouter decisions API), mock (solo para probar
el código; produce probabilidades aleatorias y NO debe usarse en la prueba real).

Dependencias: solo biblioteca estándar. Opcionales según el brazo: openai, von.
Todas las respuestas se guardan en cache/ para no repetir llamadas.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
import zlib
from datetime import datetime
from pathlib import Path

LABELS = ["a_favor", "neutral", "en_contra"]

DESCR_ES = {
    "a_favor": "El autor expresa apoyo o una postura favorable hacia el tema objetivo.",
    "neutral": "El autor no toma postura clara, o el texto no trata el tema objetivo.",
    "en_contra": "El autor expresa rechazo o una postura contraria al tema objetivo.",
}


def instructions_for(target: str) -> str:
    return f"¿Cuál es la postura del autor del texto hacia el tema: {target}?"


# ----------------------------------------------------------------- brazos
class Arm:
    name = "base"

    def predict(self, text: str, target: str, run: int) -> dict:
        raise NotImplementedError


class LexiconArm(Arm):
    """Usa score_text de massive.core.sentiment (sentimiento -> clase).

    Lightweight keyword-based sentiment scoring using the bundled
    sentiment module (massive/core/sentiment.py).
    """

    name = "lexicon"

    def __init__(self, repo: str | None, threshold: float):
        if repo:
            sys.path.insert(0, repo)
        from massive.core.sentiment import score_text  # noqa: WPS433

        self._score = score_text
        self.t = threshold

    def predict(self, text, target, run):
        t0 = time.perf_counter()
        s = self._score(text)
        label = "a_favor" if s > self.t else "en_contra" if s < -self.t else "neutral"
        return {
            "label": label,
            "probs": None,
            "latency_s": time.perf_counter() - t0,
            "input_tokens": None,
            "meta": {"score": s},
        }


class VonArm(Arm):
    """von.decide(state, choices, instructions) según el README de Von."""

    name = "von"

    def __init__(self):
        import von  # noqa: WPS433

        self.von = von

    def predict(self, text, target, run):
        t0 = time.perf_counter()
        r = self.von.decide(
            state=text, choices=dict(DESCR_ES), instructions=instructions_for(target)
        )
        return {
            "label": r.choice,
            "probs": dict(r.probabilities),
            "latency_s": time.perf_counter() - t0,
            "input_tokens": None,
            "meta": {"confidence": getattr(r, "confidence", None)},
        }


class JevArm(Arm):
    """POST https://openrouter.ai/api/alpha/decisions (ruta alpha: puede cambiar)."""

    name = "jev"

    def __init__(self, model: str, min_interval: float):
        self.key = os.environ.get("OPENROUTER_API_KEY")
        if not self.key:
            raise RuntimeError("Falta OPENROUTER_API_KEY")
        self.model, self.min_interval, self._last = model, min_interval, 0.0

    def predict(self, text, target, run):
        body = {
            "model": self.model,
            "state": text,
            "questions": {
                "stance": {
                    "type": "choice",
                    "instructions": instructions_for(target),
                    "criteria": dict(DESCR_ES),
                }
            },
        }
        req = urllib.request.Request(
            "https://openrouter.ai/api/alpha/decisions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        for attempt in range(4):
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            t0 = time.perf_counter()
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                ans = data["answers"]["stance"]
                return {
                    "label": ans["choice"],
                    "probs": ans["probabilities"],
                    "latency_s": time.perf_counter() - t0,
                    "input_tokens": data.get("usage", {}).get("input_tokens"),
                    "meta": {"model": data.get("model"), "confidence": ans.get("confidence")},
                }
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 500, 502, 503) and attempt < 3:
                    time.sleep(2**attempt)
                    continue
                raise
        raise RuntimeError("Jev: reintentos agotados")


class LLMArm(Arm):
    """LLM generalista vía API compatible con OpenAI; pide probabilidades en JSON."""

    name = "llm"

    def __init__(self):
        from openai import OpenAI  # noqa: WPS433

        self.model = os.environ["LLM_MODEL"]
        self.client = OpenAI(
            api_key=os.environ["LLM_API_KEY"], base_url=os.environ.get("LLM_BASE_URL") or None
        )

    def predict(self, text, target, run):
        system = (
            "Clasifica la postura del autor hacia el tema objetivo. Responde SOLO un JSON: "
            '{"probabilities": {"a_favor": p1, "neutral": p2, "en_contra": p3}} '
            "con probabilidades que sumen 1.\n"
            + "\n".join(f"- {k}: {v}" for k, v in DESCR_ES.items())
        )
        user = f"Tema objetivo: {target}\nTexto: {text}"
        t0 = time.perf_counter()
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            max_tokens=120,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        raw = resp.choices[0].message.content or ""
        probs = parse_probs(raw)
        usage = getattr(resp, "usage", None)
        return {
            "label": max(probs, key=probs.get) if probs else None,
            "probs": probs,
            "latency_s": time.perf_counter() - t0,
            "input_tokens": getattr(usage, "prompt_tokens", None),
            "meta": {"raw": raw[:200], "model": self.model},
        }


class MockArm(Arm):
    """Solo para probar el código: probabilidades aleatorias reproducibles."""

    name = "mock"

    def predict(self, text, target, run):
        rng = random.Random(zlib.crc32(f"{text}|{run}".encode()))
        w = [rng.random() + 0.05 for _ in LABELS]
        probs = {k: v / sum(w) for k, v in zip(LABELS, w, strict=True)}
        return {
            "label": max(probs, key=probs.get),
            "probs": probs,
            "latency_s": 0.001,
            "input_tokens": None,
            "meta": {},
        }


def parse_probs(raw: str) -> dict | None:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        p = obj.get("probabilities", obj)
        probs = {k: float(p[k]) for k in LABELS}
        tot = sum(probs.values())
        return {k: v / tot for k, v in probs.items()} if tot > 0 else None
    except (ValueError, KeyError, TypeError):
        return None


# --------------------------------------------------------------- métricas
def macro_f1(y_true, y_pred):
    f1s = []
    for c in LABELS:
        tp = sum(t == c and p == c for t, p in zip(y_true, y_pred, strict=True))
        fp = sum(t != c and p == c for t, p in zip(y_true, y_pred, strict=True))
        fn = sum(t == c and p != c for t, p in zip(y_true, y_pred, strict=True))
        pr = tp / (tp + fp) if tp + fp else 0.0
        rc = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * pr * rc / (pr + rc) if pr + rc else 0.0)
    return sum(f1s) / len(f1s)


def ece(confs, correct, bins=10):
    n, total = len(confs), 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, c in enumerate(confs) if (c > lo or b == 0) and c <= hi]
        if idx:
            acc = sum(correct[i] for i in idx) / len(idx)
            conf = sum(confs[i] for i in idx) / len(idx)
            total += len(idx) / n * abs(acc - conf)
    return total


def brier(probs_list, y_true):
    return sum(
        sum((p.get(k, 0.0) - (1.0 if k == y else 0.0)) ** 2 for k in LABELS)
        for p, y in zip(probs_list, y_true, strict=True)
    ) / len(y_true)


def paired_boot(a, b, n_boot=2000, seed=42):
    rng, n, diffs = random.Random(seed), len(a), []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(a[i] - b[i] for i in idx) / n)
    diffs.sort()
    return (
        sum(a[i] - b[i] for i in range(n)) / n,
        diffs[int(0.025 * n_boot)],
        diffs[int(0.975 * n_boot)],
    )


# ------------------------------------------------------------------ cache
class Cache:
    def __init__(self, path: Path):
        self.path, self.d = path, {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                self.d[(rec["id"], rec["run"])] = rec

    def get(self, i, run):
        return self.d.get((i, run))

    def put(self, i, run, res):
        rec = {"id": i, "run": run, **res}
        self.d[(i, run)] = rec
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run_arm(arm: Arm, rows, target_default, cache: Cache, repeat_n, repeat_k):
    for run in range(repeat_k):
        subset = rows if run == 0 else rows[:repeat_n]
        for r in subset:
            if cache.get(r["id"], run):
                continue
            try:
                res = arm.predict(r["text"], r.get("target") or target_default, run)
            except Exception as exc:  # error del brazo: se registra y cuenta como inválido
                res = {
                    "label": None,
                    "probs": None,
                    "latency_s": None,
                    "input_tokens": None,
                    "meta": {"error": str(exc)[:200]},
                }
            if res["label"] not in LABELS:
                res["label"] = None
            cache.put(r["id"], run, res)


def summarize(name, rows, cache, repeat_n, repeat_k, price, flip_ref=None):
    y = [r["label"] for r in rows]
    recs = [cache.get(r["id"], 0) for r in rows]
    pred = [rc["label"] if rc else None for rc in recs]
    correct = [int(p == t) for p, t in zip(pred, y, strict=True)]
    out = {
        "n": len(rows),
        "invalid_rate": sum(p is None for p in pred) / len(rows),
        "accuracy": sum(correct) / len(rows),
        "macro_f1": macro_f1(y, pred),
        "by_lang": {},
    }
    for lang in sorted({r["lang"] for r in rows}):
        idx = [i for i, r in enumerate(rows) if r["lang"] == lang]
        out["by_lang"][lang] = {"n": len(idx), "accuracy": sum(correct[i] for i in idx) / len(idx)}
    have = [i for i, rc in enumerate(recs) if rc and rc["probs"] and rc["label"]]
    if have and len(have) >= 0.5 * len(rows):
        out["ece"] = ece([recs[i]["probs"][pred[i]] for i in have], [correct[i] for i in have])
        out["brier"] = brier([recs[i]["probs"] for i in have], [y[i] for i in have])
    lat = [rc["latency_s"] for rc in recs if rc and rc["latency_s"] is not None]
    if lat:
        s = sorted(lat)
        out["latency_median_s"] = statistics.median(s)
        out["latency_p95_s"] = s[min(len(s) - 1, int(0.95 * len(s)))]
    toks = [rc["input_tokens"] for rc in recs if rc and rc["input_tokens"]]
    est = len(toks) < len(rows)
    tok_per_item = (
        (sum(toks) / len(toks)) if toks else sum(len(r["text"]) for r in rows) / len(rows) / 4
    )
    out["cost_per_1k_usd"] = tok_per_item * 1000 * price.get(name, 0.0) / 1e6
    out["cost_is_estimate"] = est
    if repeat_k > 1:
        sub = rows[:repeat_n]
        flips = 0
        for r in sub:
            labs = {(cache.get(r["id"], k) or {}).get("label") for k in range(repeat_k)}
            flips += len(labs) > 1
        out["flip_rate"] = flips / max(1, len(sub))
    out["_correct"] = correct
    return out


def verdict(name, res, base, lex, args):
    lines = []
    if lex is not None and name != "lexicon":
        ok = True
        for scope in ["global"] + sorted(res["by_lang"]):
            idx = (
                list(range(res["n"]))
                if scope == "global"
                else [i for i, r in enumerate(args._rows) if r["lang"] == scope]
            )
            d, lo, hi = paired_boot(
                [res["_correct"][i] for i in idx], [lex["_correct"][i] for i in idx]
            )
            lines.append(f"  R0 vs léxico [{scope}]: dif={d:+.3f} IC95%=[{lo:+.3f},{hi:+.3f}]")
            ok &= lo > 0
        lines.append(f"  R0 (supera al léxico en todo): {'CUMPLE' if ok else 'NO CUMPLE'}")
    if base is not None and name in ("von", "jev"):
        ok1 = True
        for scope in ["global"] + sorted(res["by_lang"]):
            idx = (
                list(range(res["n"]))
                if scope == "global"
                else [i for i, r in enumerate(args._rows) if r["lang"] == scope]
            )
            d, lo, hi = paired_boot(
                [res["_correct"][i] for i in idx], [base["_correct"][i] for i in idx]
            )
            lines.append(f"  R1 vs LLM [{scope}]: dif={d:+.3f} IC95%=[{lo:+.3f},{hi:+.3f}]")
            ok1 &= lo > -args.margin
        adv = []
        if "ece" in res and "ece" in base and base["ece"] - res["ece"] >= args.min_ece_gain:
            adv.append("ECE")
        if (
            "flip_rate" in res
            and "flip_rate" in base
            and base["flip_rate"] - res["flip_rate"] >= args.min_flip_gain
        ):
            adv.append("estabilidad")
        if (
            res.get("latency_median_s")
            and base.get("latency_median_s")
            and base["latency_median_s"] / res["latency_median_s"] >= args.min_ratio
        ):
            adv.append("latencia")
        if (
            res["cost_per_1k_usd"] > 0
            and base["cost_per_1k_usd"] / res["cost_per_1k_usd"] >= args.min_ratio
        ):
            adv.append("costo")
        elif res["cost_per_1k_usd"] == 0 and base["cost_per_1k_usd"] > 0:
            adv.append("costo (sin costo por llamada)")
        lines.append(
            f"  R1 (no inferior al LLM, margen {args.margin}): {'CUMPLE' if ok1 else 'NO CUMPLE'}"
        )
        lines.append(f"  R2 (ventajas sobre el LLM): {', '.join(adv) if adv else 'ninguna'}")
        lines.append("  R3 (licencias/privacidad): verificar manualmente")
    return lines


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--data", required=True)
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--arms", default="lexicon,llm,von,jev")
    ap.add_argument(
        "--target", default="", help="tema objetivo por defecto (si el CSV no trae columna target)"
    )
    ap.add_argument("--repo", default=None, help="ruta al repo MASSIVE (para el brazo lexicon)")
    ap.add_argument("--lex-threshold", type=float, default=0.2)
    ap.add_argument("--jev-model", default="typesafe/jev-1.13")
    ap.add_argument("--jev-min-interval", type=float, default=0.06, help="segundos entre llamadas")
    ap.add_argument("--repeat-n", type=int, default=100)
    ap.add_argument("--repeat-k", type=int, default=1)
    ap.add_argument(
        "--price",
        default="jev=0.042,llm=0,von=0,lexicon=0,mock=0",
        help="USD por millón de tokens de entrada, ej. llm=0.25 (verifica precios vigentes)",
    )
    ap.add_argument("--margin", type=float, default=0.05)
    ap.add_argument("--min-ece-gain", type=float, default=0.02)
    ap.add_argument("--min-flip-gain", type=float, default=0.02)
    ap.add_argument("--min-ratio", type=float, default=5.0)
    ap.add_argument("--cache-dir", default="cache")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    with open(args.data, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("label") or "").strip()]
    for r in rows:
        r["label"] = r["label"].strip()
        r["lang"] = (r.get("lang") or "?").strip()
    bad = [r["id"] for r in rows if r["label"] not in LABELS]
    if bad:
        sys.exit(f"Etiquetas fuera de {LABELS}: {bad[:5]}")
    if args.split != "all":
        rows = [r for r in rows if (r.get("split") or "").strip() == args.split]
    if not rows:
        sys.exit("No hay filas con etiqueta en esa partición.")
    args._rows = rows
    price = {k: float(v) for k, v in (kv.split("=") for kv in args.price.split(",") if kv)}

    factories = {
        "lexicon": lambda: LexiconArm(args.repo, args.lex_threshold),
        "llm": LLMArm,
        "von": VonArm,
        "mock": MockArm,
        "jev": lambda: JevArm(args.jev_model, args.jev_min_interval),
    }
    Path(args.cache_dir).mkdir(exist_ok=True)
    results, skipped = {}, {}
    for name in [a.strip() for a in args.arms.split(",") if a.strip()]:
        try:
            arm = factories[name]()
        except Exception as exc:
            skipped[name] = str(exc)
            continue
        cache = Cache(Path(args.cache_dir) / f"{name}.jsonl")
        run_arm(arm, rows, args.target, cache, args.repeat_n, args.repeat_k)
        results[name] = summarize(name, rows, cache, args.repeat_n, args.repeat_k, price)

    print(f"\nn={len(rows)} partición={args.split}; brazos omitidos: {skipped or 'ninguno'}\n")
    hdr = f"{'brazo':9}{'acc':>7}{'F1m':>7}{'inval':>7}{'ECE':>7}{'Brier':>7}{'flip':>7}{'lat_med':>9}{'USD/1k':>10}"
    print(hdr)

    def fmt(r: dict, k: str, fmt_str: str) -> str:
        return fmt_str % r[k] if k in r else "-"

    for name, r in results.items():
        print(
            f"{name:9}{r['accuracy']:7.3f}{r['macro_f1']:7.3f}{r['invalid_rate']:7.3f}"
            f"{fmt(r, 'ece', '%7.3f'):>7}{fmt(r, 'brier', '%7.3f'):>7}{fmt(r, 'flip_rate', '%7.3f'):>7}"
            f"{fmt(r, 'latency_median_s', '%9.3f'):>9}{r['cost_per_1k_usd']:10.4f}{'*' if r['cost_is_estimate'] else ''}"
        )
        for lang, d in r["by_lang"].items():
            print(f"{'':9}  {lang}: acc={d['accuracy']:.3f} (n={d['n']})")
    print("(* costo estimado por caracteres/4)\n")
    for name, r in results.items():
        vl = verdict(name, r, results.get("llm"), results.get("lexicon"), args)
        if vl:
            print(f"[{name}]")
            print("\n".join(vl))
    out = args.out or f"results_{datetime.now():%Y%m%d_%H%M%S}.json"
    for r in results.values():
        r.pop("_correct", None)
    Path(out).write_text(
        json.dumps(
            {
                "args": {k: v for k, v in vars(args).items() if k != "_rows"},
                "skipped": skipped,
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nGuardado en {out}")


if __name__ == "__main__":
    main()
