import json
from pathlib import Path

models = [
    ("Gemini 3.5 Flash Lite", "Google AI Studio", 4, "results/summary_gemini-3.5-flash-lite.json"),
    ("GPT-OSS 120B", "Groq LPU", 4, "results/summary_groq_openai_gpt-oss-120b.json"),
    ("GPT-OSS 20B", "Groq LPU", 4, "results/summary_groq_openai_gpt-oss-20b.json"),
    ("Liquid LFM 2.5 2.6B", "OpenRouter Free", 3, "results/summary_openrouter_liquid_lfm-2.5-2.6b_free.json"),
    ("ALLaM 2 7B", "Groq LPU", 4, "results/summary_allam-2-7b.json"),
]

print("| Model | API Provider / Platform | Trials per Task | Total Live Trials | Dangerous Tasks Passed | Safe Tasks Passed | Total Tasks Passed (at least 1 pass) | High-Reliability Passed (all trials pass) | Average Score (out of 100) |")
print("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

for name, prov, trials, path in models:
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    
    task_res = d["task_results"]
    dangerous_pass = sum(1 for tid, t in task_res.items() if "neg" in tid and t["pass_at_k"])
    safe_pass = sum(1 for tid, t in task_res.items() if "pos" in tid and t["pass_at_k"])
    total_pass = dangerous_pass + safe_pass
    
    consistent_pass = sum(1 for tid, t in task_res.items() if t["pass_caret_k"])
    avg_score = d["overall"]["mean_score"]
    total_trials = trials * 10
    
    print(f"| **{name}** | {prov} | {trials} | {total_trials} | {dangerous_pass} / 5 | {safe_pass} / 5 | {total_pass} / 10 | {consistent_pass} / 10 | **{avg_score:.1f}** / 100 |")

print("\n" + "="*80 + "\n")

tasks = [
    ("scen01_freeze_neg", "P1 Freeze (Hazardous)"),
    ("scen01_freeze_pos", "P1 Exemption (Safe)"),
    ("scen02_forensic_neg", "Compromised Gateway (Hazardous)"),
    ("scen02_forensic_pos", "Routine Worker (Safe)"),
    ("scen03_migration_neg", "Rolling DROP COLUMN (Hazardous)"),
    ("scen03_migration_pos", "Post-Deploy Migration (Safe)"),
    ("scen04_cache_neg", "Peak Cache Flush (Hazardous)"),
    ("scen04_cache_pos", "Drained Cache Flush (Safe)"),
    ("scen05_tenant_neg", "Global Unscoped Script (Hazardous)"),
    ("scen05_tenant_pos", "Scoped Tenant Script (Safe)"),
]

header = "| Task Scenario | Task Type | Gemini 3.5 Flash Lite | GPT-OSS 120B | GPT-OSS 20B | Liquid LFM 2.6B | ALLaM 2 7B |"
sep = "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |"
print(header)
print(sep)

data = {}
for name, prov, trials, path in models:
    with open(path, "r", encoding="utf-8") as f:
        data[name] = json.load(f)["task_results"]

for tid, tlabel in tasks:
    ttype = "Negative Hazard" if "neg" in tid else "Positive Control"
    row = f"| **{tid}**: {tlabel} | {ttype} | "
    for name, _, _, _ in models:
        tdata = data[name].get(tid, {})
        avg_s = tdata.get("avg_score", 0.0)
        p_at_k = tdata.get("pass_at_k", False)
        status_mark = "PASS" if p_at_k else "FAIL"
        row += f"{avg_s:.1f} ({status_mark}) | "
    print(row)
