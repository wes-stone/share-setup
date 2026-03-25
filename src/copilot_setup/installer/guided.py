"""Guided interactive setup steps (auth flows, first-time config, etc.)."""

from __future__ import annotations

import subprocess

from copilot_setup.installer.tui import (
    console,
    prompt_continue,
    prompt_yes_no,
    show_error,
    show_guidance,
    show_info,
    show_success,
    show_warning,
)
from copilot_setup.models import SetupStep, StepType


def _run_command(command: str, interactive: bool = False) -> tuple[bool, str]:
    """Run a shell command, optionally in interactive mode."""
    try:
        if interactive:
            result = subprocess.run(command, shell=True, timeout=300)
            return result.returncode == 0, ""
        else:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=300
            )
            return result.returncode == 0, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except (FileNotFoundError, OSError) as exc:
        return False, str(exc)


def _verify_step(step: SetupStep) -> bool:
    """Verify that a step completed successfully."""
    if not step.verify_command:
        return True
    success, _ = _run_command(step.verify_command)
    return success


def handle_auto_step(step: SetupStep) -> bool:
    """Execute a fully automated step."""
    # Pre-verify: skip if already done
    if step.verify_command and _verify_step(step):
        show_success(f"{step.description} — already done")
        return True

    show_info(f"{step.description}...")
    if not step.command:
        show_success(f"{step.description} — done")
        return True

    success, error = _run_command(step.command)
    if success and _verify_step(step):
        show_success(f"{step.description} — done!")
        return True

    show_error(f"{step.description} — failed")
    if error:
        console.print(f"     [muted]{error[:200]}[/]")
    if step.error_help:
        show_info(step.error_help)
    return False


def handle_guided_step(step: SetupStep) -> bool:
    """Walk the user through an interactive step."""
    # Pre-verify: skip if already completed from a previous run
    if step.verify_command and _verify_step(step):
        show_success(f"{step.description} — already done from a previous session")
        return True

    if step.guidance:
        show_guidance(step.guidance)

    if step.command:
        if not prompt_continue("Press Enter to begin..."):
            return False

        show_info("Running — follow any prompts that appear...\n")
        success, error = _run_command(step.command, interactive=True)

        if not success:
            show_warning("The command finished with an issue.")
            if step.error_help:
                show_info(step.error_help)
    else:
        prompt_continue("Follow the instructions above, then press Enter when done...")

    # Verify regardless of command outcome — the user may have fixed it
    if _verify_step(step):
        show_success(f"{step.description} — verified!")
        return True

    show_warning(f"Could not verify that '{step.description}' completed.")
    if step.error_help:
        show_info(step.error_help)

    # Offer a real retry: re-run the command or just re-check
    while True:
        if step.command:
            choice = prompt_yes_no("Would you like to try again?", default=True)
        else:
            choice = prompt_yes_no("Re-check now?", default=True)

        if not choice:
            return False

        if step.command:
            show_info("Running again — follow any prompts that appear...\n")
            _run_command(step.command, interactive=True)

        if _verify_step(step):
            show_success(f"{step.description} — verified!")
            return True

        show_warning("Still not verified.")


def handle_info_step(step: SetupStep) -> bool:
    """Display informational content — no action needed."""
    if step.guidance:
        show_guidance(step.guidance)
    else:
        show_info(step.description)
    return True


def handle_setup_steps(
    steps: list[SetupStep],
) -> tuple[list[str], list[str], list[str]]:
    """
    Run all setup steps in order.
    Returns (succeeded, skipped, failed) lists of descriptions.
    """
    succeeded: list[str] = []
    skipped: list[str] = []
    failed: list[str] = []

    handlers = {
        StepType.AUTO: handle_auto_step,
        StepType.GUIDED: handle_guided_step,
        StepType.INFO: handle_info_step,
    }

    for step in steps:
        handler = handlers.get(step.step_type, handle_auto_step)
        try:
            if handler(step):
                succeeded.append(step.description)
            else:
                failed.append(step.description)
        except KeyboardInterrupt:
            skipped.append(step.description)
            show_warning(f"Skipped: {step.description}")

    return succeeded, skipped, failed
