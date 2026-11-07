import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from typing import Dict, List, Any

from graders.schema import BenchmarkTask, ModelDecisionContract
from graders.deterministic_grader import evaluate_attempt, PASS_THRESHOLD

TASKS_DIR = Path("tasks")
TRANSCRIPTS_DIR = Path("transcripts")
RESULTS_DIR = Path("results")

# Load all 10 benchmark tasks
tasks: Dict[str, BenchmarkTask] = {}
for tf in sorted(TASKS_DIR.glob("*.json")):
    with open(tf, "r", encoding="utf-8") as f:
        t = BenchmarkTask.model_validate(json.load(f))
        tasks[t.task_id] = t

# Models to audit
model_configs = [
    {
        "model_id": "gemini-3.5-flash-lite",
        "provider": "Google AI Studio",
        "folder": "gemini-3.5-flash-lite",
        "summary_file": "summary_gemini-3.5-flash-lite.json",
        "expected_trials": 4,
        "known_missing": {}
    },
    {
        "model_id": "openai/gpt-oss-120b",
        "provider": "Groq Cloud",
        "folder": "groq_openai_gpt-oss-120b",
        "summary_file": "summary_groq_openai_gpt-oss-120b.json",
        "expected_trials": 4,
        "known_missing": {}
    },
    {
        "model_id": "openai/gpt-oss-20b",
        "provider": "Groq Cloud",
        "folder": "groq_openai_gpt-oss-20b",
        "summary_file": "summary_groq_openai_gpt-oss-20b.json",
        "expected_trials": 4,
        "known_missing": {}
    },
    {
        "model_id": "liquid/lfm-2.5-2.6b:free",
        "provider": "OpenRouter",
        "folder": "openrouter_liquid_lfm-2.5-2.6b_free",
        "summary_file": "summary_openrouter_liquid_lfm-2.5-2.6b_free.json",
        "expected_trials": 3,
        "known_missing": {}
    },
    {
        "model_id": "allam-2-7b",
        "provider": "Groq Cloud",
        "folder": "allam-2-7b",
        "summary_file": "summary_allam-2-7b.json",
        "expected_trials": 4,
        "known_missing": {
            "scen02_forensic_neg_trial_1": "Validation error: reasoning_summary missing",
            "scen02_forensic_neg_trial_2": "Validation error: reasoning_summary missing",
            "scen02_forensic_neg_trial_3": "Validation error: reasoning_summary missing",
            "scen02_forensic_neg_trial_4": "Validation error: reasoning_summary missing",
            "scen02_forensic_pos_trial_1": "Validation error: reasoning_summary missing",
            "scen02_forensic_pos_trial_2": "Validation error: reasoning_summary missing",
            "scen02_forensic_pos_trial_3": "Validation error: reasoning_summary missing",
            "scen02_forensic_pos_trial_4": "Validation error: reasoning_summary missing",
            "scen05_tenant_neg_trial_1": "Validation error: unapproved decision enum",
            "scen05_tenant_neg_trial_2": "Validation error: unapproved decision enum",
            "scen05_tenant_neg_trial_3": "Validation error: unapproved decision enum",
            "scen05_tenant_neg_trial_4": "Validation error: unapproved decision enum"
        }
    }
]

audit_results = {}

for m in model_configs:
    model_id = m["model_id"]
    folder = TRANSCRIPTS_DIR / m["folder"]
    k_trials = m["expected_trials"]
    print(f"\n========================================================")
    print(f"AUDITING MODEL: {model_id} (Expected {k_trials} trials/task = {k_trials*10} total)")
    print(f"Folder: {folder}")
    
    task_results = {}
    total_scores = []
    total_critical_failures = 0
    total_trials_attempted = k_trials * 10
    successful_transcripts = 0
    invalid_or_failed_trials = 0
    
    for task_id, task in tasks.items():
        trial_scores = []
        trial_passed = []
        trial_crit = []
        
        for k in range(1, k_trials + 1):
            t_key = f"{task_id}_trial_{k}"
            t_file = folder / f"{t_key}.json"
            
            if t_file.exists():
                with open(t_file, "r", encoding="utf-8") as f:
                    t_data = json.load(f)
                attempt = ModelDecisionContract.model_validate(t_data["attempt"])
                score = evaluate_attempt(task, attempt)
                
                # Update transcript with recalculated score
                t_data["score"] = score.model_dump()
                with open(t_file, "w", encoding="utf-8") as f:
                    json.dump(t_data, f, indent=2)
                    
                trial_scores.append(score.total_score)
                trial_passed.append(score.passed)
                if score.critical_failure:
                    trial_crit.append(True)
                    total_critical_failures += 1
                successful_transcripts += 1
            else:
                # Missing or failed trial
                reason = m["known_missing"].get(t_key, "Unknown API/execution error")
                print(f"  [MISSING/FAILED TRIAL] {t_key}: {reason}")
                trial_scores.append(0.0)
                trial_passed.append(False)
                invalid_or_failed_trials += 1
                
        avg_score = round(sum(trial_scores) / len(trial_scores), 1)
        pass_at_k = any(trial_passed)
        pass_caret_k = all(trial_passed)
        passed_trials_count = sum(1 for p in trial_passed if p)
        
        task_results[task_id] = {
            "avg_score": avg_score,
            "passed_trials_count": passed_trials_count,
            "total_trials": k_trials,
            "trial_pass_rate_pct": round((passed_trials_count / k_trials) * 100, 1),
            "pass_at_k": pass_at_k,
            "pass_caret_k": pass_caret_k,
            "scores": trial_scores
        }
        total_scores.append(avg_score)
        
    overall_mean = round(sum(total_scores) / len(total_scores), 1)
    
    # Calculate separate hazardous vs safe stats
    haz_tasks = [t for tid, t in task_results.items() if "neg" in tid]
    safe_tasks = [t for tid, t in task_results.items() if "pos" in tid]
    
    haz_pass_at_k = sum(1 for t in haz_tasks if t["pass_at_k"])
    haz_pass_caret_k = sum(1 for t in haz_tasks if t["pass_caret_k"])
    safe_pass_at_k = sum(1 for t in safe_tasks if t["pass_at_k"])
    safe_pass_caret_k = sum(1 for t in safe_tasks if t["pass_caret_k"])
    
    summary_payload = {
        "model": model_id,
        "provider": m["provider"],
        "trials_per_task": k_trials,
        "total_trials_attempted": total_trials_attempted,
        "valid_transcripts_recorded": successful_transcripts,
        "failed_or_invalid_trials": invalid_or_failed_trials,
        "critical_failures_total": total_critical_failures,
        "pass_threshold": PASS_THRESHOLD,
        "task_results": task_results,
        "overall": {
            "mean_score": overall_mean,
            "pass_at_k_percent": round((sum(1 for t in task_results.values() if t['pass_at_k']) / len(task_results)) * 100, 1),
            "pass_caret_k_percent": round((sum(1 for t in task_results.values() if t['pass_caret_k']) / len(task_results)) * 100, 1),
            "dangerous_pass_at_k": f"{haz_pass_at_k}/5",
            "dangerous_pass_caret_k": f"{haz_pass_caret_k}/5",
            "safe_pass_at_k": f"{safe_pass_at_k}/5",
            "safe_pass_caret_k": f"{safe_pass_caret_k}/5"
        }
    }
    
    summary_path = RESULTS_DIR / m["summary_file"]
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_payload, f, indent=2)
        
    print(f"  Recalculated Mean Score: {overall_mean}/100")
    print(f"  Hazardous Pass@k: {haz_pass_at_k}/5 | Pass^k: {haz_pass_caret_k}/5")
    print(f"  Safe Pass@k: {safe_pass_at_k}/5 | Pass^k: {safe_pass_caret_k}/5")
    print(f"  Saved updated summary to: {summary_path}")
    
    audit_results[model_id] = summary_payload

print("\n" + "="*80)
print("AUDIT & RECALCULATION COMPLETE")
