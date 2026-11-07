import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table

from graders.schema import BenchmarkTask, ModelDecisionContract
from graders.deterministic_grader import evaluate_attempt, EvaluationScore
from graders.model_clients import MockReplayClient, GeminiClient, GroqClient

import sys
# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

console = Console()

def load_tasks(tasks_dir: Path = Path("tasks")) -> List[BenchmarkTask]:
    tasks = []
    for tf in sorted(tasks_dir.glob("*.json")):
        with open(tf, "r", encoding="utf-8") as f:
            tasks.append(BenchmarkTask.model_validate(json.load(f)))
    return tasks

def run_verification_mode(tasks: List[BenchmarkTask]) -> int:
    """
    Offline verification of graders against reference solutions and mutations.
    Judges can run this with 0 API keys.
    """
    console.print("\n[bold cyan]=== RUNNING DETERMINISTIC GRADER VERIFICATION (OFFLINE) ===[/bold cyan]\n")
    ref_dir = Path("reference")
    table = Table(title="Reference Solution Verification (Target: 100% Pass)")
    table.add_column("Task ID", style="bold")
    table.add_column("Type")
    table.add_column("Expected Decision")
    table.add_column("Score", justify="right")
    table.add_column("Status")

    all_passed = True
    for t in tasks:
        ref_file = ref_dir / f"{t.task_id}.json"
        with open(ref_file, "r", encoding="utf-8") as f:
            ref_decision = ModelDecisionContract.model_validate(json.load(f))
        score = evaluate_attempt(t, ref_decision)
        status_str = "[bold green]PASS[/bold green]" if score.passed else "[bold red]FAIL[/bold red]"
        if not score.passed:
            all_passed = False
        table.add_row(
            t.task_id,
            "Positive Control" if t.is_positive_control else "Negative Hazard",
            t.ground_truth.required_action,
            f"{score.total_score:.1f}/100",
            status_str
        )
    console.print(table)
    
    if all_passed:
        console.print("\n[bold green]✓ All reference solutions passed deterministic grading with 0 false fails.[/bold green]\n")
        return 0
    else:
        console.print("\n[bold red]✗ Some reference solutions failed grader checks.[/bold red]\n")
        return 1

def run_evaluation(model_name: str, trials: int = 1, mode: str = "live") -> None:
    tasks = load_tasks()
    console.print(f"\n[bold magenta]=== EXECUTING AFTERMODEL BENCHMARK ===[/bold magenta]")
    console.print(f"[yellow]Target Model:[/yellow] {model_name} | [yellow]Trials per task:[/yellow] {trials} | [yellow]Mode:[/yellow] {mode}\n")

    client = None
    if mode == "replay" or model_name == "mock":
        client = MockReplayClient()
    elif "gemini" in model_name:
        client = GeminiClient(model_name=model_name)
    elif "groq" in model_name or "llama" in model_name:
        clean_name = model_name.replace("groq/", "")
        client = GroqClient(model_name=clean_name)
    else:
        raise ValueError(f"Unsupported model provider for {model_name}")

    results_dir = Path("results")
    transcripts_dir = Path("transcripts") / model_name.replace("/", "_")
    results_dir.mkdir(exist_ok=True)
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    task_scores: Dict[str, List[EvaluationScore]] = {t.task_id: [] for t in tasks}

    for task in tasks:
        console.print(f"[bold]Running {task.task_id}[/bold] ({task.title})...")
        for k in range(trials):
            try:
                if isinstance(client, MockReplayClient):
                    attempt = client.generate_decision(task.user_prompt, task.context_files, task_id=task.task_id)
                else:
                    attempt = client.generate_decision(task.user_prompt, task.context_files, task_id=task.task_id)

                score = evaluate_attempt(task, attempt)
                task_scores[task.task_id].append(score)

                # Save transcript
                transcript_file = transcripts_dir / f"{task.task_id}_trial_{k+1}.json"
                with open(transcript_file, "w", encoding="utf-8") as f:
                    json.dump({
                        "task_id": task.task_id,
                        "trial": k + 1,
                        "prompt": task.user_prompt,
                        "attempt": attempt.model_dump(),
                        "score": score.model_dump()
                    }, f, indent=2)

            except Exception as e:
                console.print(f"  [red]Trial {k+1} encountered error: {e}[/red]")
                fail_score = EvaluationScore(
                    passed=False,
                    total_score=0.0,
                    action_score=0.0,
                    risk_score=0.0,
                    prereq_score=0.0,
                    actionable_score=0.0,
                    critical_failure=True,
                    critical_failure_reasons=[f"Exception during trial: {e}"]
                )
                task_scores[task.task_id].append(fail_score)

    # Compute Summary Metrics
    summary_table = Table(title=f"Benchmark Results: {model_name}")
    summary_table.add_column("Task ID", style="bold")
    summary_table.add_column("Type")
    summary_table.add_column("Avg Score", justify="right")
    summary_table.add_column(f"pass@{trials}", justify="center")
    summary_table.add_column(f"pass^{trials}", justify="center")

    total_avg_score = 0.0
    pass_at_k_count = 0
    pass_caret_k_count = 0

    metrics_payload = {
        "model": model_name,
        "trials_per_task": trials,
        "task_results": {}
    }

    for task in tasks:
        scores = task_scores[task.task_id]
        avg_score = sum(s.total_score for s in scores) / len(scores)
        pass_at_k = any(s.passed for s in scores)
        pass_caret_k = all(s.passed for s in scores)

        total_avg_score += avg_score
        if pass_at_k:
            pass_at_k_count += 1
        if pass_caret_k:
            pass_caret_k_count += 1

        metrics_payload["task_results"][task.task_id] = {
            "avg_score": round(avg_score, 1),
            "pass_at_k": pass_at_k,
            "pass_caret_k": pass_caret_k,
            "scores": [s.total_score for s in scores]
        }

        summary_table.add_row(
            task.task_id,
            "Positive Control" if task.is_positive_control else "Negative Hazard",
            f"{avg_score:.1f}",
            "[green]✓[/green]" if pass_at_k else "[red]✗[/red]",
            "[green]✓[/green]" if pass_caret_k else "[red]✗[/red]"
        )

    overall_mean = total_avg_score / len(tasks)
    overall_pass_at_k = (pass_at_k_count / len(tasks)) * 100
    overall_pass_caret_k = (pass_caret_k_count / len(tasks)) * 100

    metrics_payload["overall"] = {
        "mean_score": round(overall_mean, 1),
        "pass_at_k_percent": round(overall_pass_at_k, 1),
        "pass_caret_k_percent": round(overall_pass_caret_k, 1)
    }

    console.print(summary_table)
    console.print(f"\n[bold]Overall Mean Score:[/bold] {overall_mean:.1f}/100")
    console.print(f"[bold]pass@{trials}:[/bold] {overall_pass_at_k:.1f}% | [bold]pass^{trials}:[/bold] {overall_pass_caret_k:.1f}%\n")

    summary_file = results_dir / f"summary_{model_name.replace('/', '_')}.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, indent=2)
    console.print(f"[green]Saved summary metrics to {summary_file}[/green]\n")

def main():
    parser = argparse.ArgumentParser(description="afterModel Benchmark Runner")
    parser.add_argument("--mode", choices=["live", "replay", "verify"], default="verify",
                        help="Execution mode: verify (offline reference check), replay (mock transcripts), live (API)")
    parser.add_argument("--model", type=str, default="mock",
                        help="Model to test (e.g., gemini-2.5-flash, groq/llama-3.3-70b-versatile, mock)")
    parser.add_argument("--trials", type=int, default=3,
                        help="Number of trials per task")
    args = parser.parse_args()

    if args.mode == "verify":
        tasks = load_tasks()
        sys.exit(run_verification_mode(tasks))
    else:
        run_evaluation(model_name=args.model, trials=args.trials, mode=args.mode)

if __name__ == "__main__":
    main()
