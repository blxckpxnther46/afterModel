import json

models = [
    ('gemini-3.5-flash-lite', 'Google AI Studio', 'Frontier Multimodal', 4, 'results/summary_gemini-3.5-flash-lite.json'),
    ('liquid/lfm-2.5-2.6b:free', 'OpenRouter', '2.6B Edge Architecture', 3, 'results/summary_openrouter_liquid_lfm-2.5-2.6b_free.json'),
    ('openai/gpt-oss-20b', 'Groq Cloud', '20B Dense Reasoning', 4, 'results/summary_groq_openai_gpt-oss-20b.json'),
    ('openai/gpt-oss-120b', 'Groq Cloud', '120B Open Weights', 4, 'results/summary_groq_openai_gpt-oss-120b.json'),
    ('allam-2-7b', 'Groq Cloud', '7B Baseline Model', 4, 'results/summary_allam-2-7b.json'),
]

headers = [
    'Model Identifier', 'Provider / Platform', 'Model Scale & Class', 'Trials / Task',
    'Total Live Trials', 'Hazardous (Mean $\\ge 70$)', 'Safe (Mean $\\ge 70$)',
    'Overall (Mean $\\ge 70$)', 'High Reliability ($pass^k$)', '**Benchmark Score**'
]
alignments = [':---', ':---', ':---:', ':---:', ':---:', ':---:', ':---:', ':---:', ':---:', ':---:']

rows = []
for name, prov, cls, trials, path in models:
    d = json.load(open(path, "r", encoding="utf-8"))
    o = d['overall']
    haz_mean = sum(1 for t, v in d['task_results'].items() if 'neg' in t and v['avg_score'] >= 70.0)
    haz_at_k = sum(1 for t, v in d['task_results'].items() if 'neg' in t and v['pass_at_k'])
    safe_mean = sum(1 for t, v in d['task_results'].items() if 'pos' in t and v['avg_score'] >= 70.0)
    safe_at_k = sum(1 for t, v in d['task_results'].items() if 'pos' in t and v['pass_at_k'])
    tot_mean = haz_mean + safe_mean
    tot_at_k = haz_at_k + safe_at_k
    high_rel = sum(1 for t, v in d['task_results'].items() if v['pass_caret_k'])
    tot_att = d["total_trials_attempted"]
    valid = d.get("valid_transcripts_recorded", tot_att)
    failed = d.get("failed_or_invalid_trials", 0)
    mean_s = o["mean_score"]
    
    if 'gemini' in name and failed > 0:
        trial_str = f"**{tot_att}** ({valid} valid, {failed} timeout)"
    elif failed > 0:
        trial_str = f"**{tot_att}** ({valid} valid, {failed} schema err)"
    else:
        trial_str = f"**{tot_att}** ({valid} valid, 0 err)"
        
    rows.append([
        f"**`{name}`**",
        prov,
        cls,
        f"**{trials} trials**",
        trial_str,
        f"**{haz_mean} / 5** ({haz_at_k}/5 pass@k)",
        f"**{safe_mean} / 5** ({safe_at_k}/5 pass@k)",
        f"**{tot_mean} / 10** ({tot_at_k}/10 pass@k)",
        f"**{high_rel} / 10** ({high_rel*10:.1f}%)",
        f"**{mean_s:.1f} / 100**"
    ])

cols = len(headers)
widths = [len(h) for h in headers]
for row in rows:
    for i, cell in enumerate(row):
        widths[i] = max(widths[i], len(cell))

def pad(text, width, align):
    if align == ':---':
        return text.ljust(width)
    elif align == ':---:':
        return text.center(width)
    elif align == '---:':
        return text.rjust(width)
    return text.ljust(width)

print('| ' + ' | '.join(pad(headers[i], widths[i], alignments[i]) for i in range(cols)) + ' |')
sep_cells = []
for i, align in enumerate(alignments):
    w = max(3, widths[i])
    if align == ':---':
        sep_cells.append(':' + '-' * (w - 1))
    elif align == ':---:':
        sep_cells.append(':' + '-' * (w - 2) + ':')
    elif align == '---:':
        sep_cells.append('-' * (w - 1) + ':')
print('| ' + ' | '.join(sep_cells) + ' |')
for row in rows:
    print('| ' + ' | '.join(pad(row[i], widths[i], alignments[i]) for i in range(cols)) + ' |')
