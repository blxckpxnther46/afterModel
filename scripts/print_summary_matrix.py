import json

models = [
    ('gemini-3.5-flash-lite', 'Google AI Studio', 'Frontier Multimodal', 4, 'results/summary_gemini-3.5-flash-lite.json'),
    ('openai/gpt-oss-120b', 'Groq Cloud', '120B Open Weights', 4, 'results/summary_groq_openai_gpt-oss-120b.json'),
    ('openai/gpt-oss-20b', 'Groq Cloud', '20B Dense Reasoning', 4, 'results/summary_groq_openai_gpt-oss-20b.json'),
    ('liquid/lfm-2.5-2.6b:free', 'OpenRouter', '2.6B Edge Architecture', 3, 'results/summary_openrouter_liquid_lfm-2.5-2.6b_free.json'),
    ('allam-2-7b', 'Groq Cloud', '7B Baseline Model', 4, 'results/summary_allam-2-7b.json'),
]

print("| Model Identifier | Provider / Platform | Model Scale & Class | Trials per Task | Total Live Trials | Hazardous Tasks Passed (Mean >=70) | Safe Tasks Passed (Mean >=70) | Overall Tasks Passed (Mean >=70) | High-Reliability Passed (All Trials >=70) | Final Benchmark Score (Overall Mean / 100) |")
print("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

for name, prov, cls, trials, path in models:
    d = json.load(open(path, "r", encoding="utf-8"))
    o = d['overall']
    neg_passed = sum(1 for t, v in d['task_results'].items() if 'neg' in t and v['avg_score'] >= 70.0)
    pos_passed = sum(1 for t, v in d['task_results'].items() if 'pos' in t and v['avg_score'] >= 70.0)
    tot_passed = neg_passed + pos_passed
    high_rel = sum(1 for t, v in d['task_results'].items() if v['pass_caret_k'])
    tot_att = d["total_trials_attempted"]
    mean_s = o["mean_score"]
    print(f"| **`{name}`** | {prov} | {cls} | **{trials} trials** | **{tot_att} trials** | **{neg_passed} / 5** | **{pos_passed} / 5** | **{tot_passed} / 10** | **{high_rel} / 10** | **{mean_s:.1f} / 100** |")
