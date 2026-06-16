import re
import logging

logger = logging.getLogger(__name__)


def validate_editor_math(editor_text: str) -> str:
    """
    Parses the Editor's raw text breakdown, checks if the declared effect durations
    fit inside the declared phase durations, and generates a validation report.
    """
    logger.info("Running Math Validation on Editor Directives...")

    report = "=== TIMESTAMP MATH VALIDATION REPORT ===\n"
    errors_found = False

    # Simple regex parsing to find Phase durations and Effect durations
    # Assumes formatting like:
    # - Phase 1 (Setup): 15.0 - 20.0 (Duration: 5.0)
    # Effects: [{'effect_name': 'vhs', 'relative_start_time': 0.0, 'duration': 5.0}]

    phases = editor_text.split("- Phase")

    for idx, phase_block in enumerate(phases[1:]):
        try:
            # Extract Phase Duration
            dur_match = re.search(r"Duration:\s*([0-9.]+)", phase_block)
            if not dur_match:
                continue

            phase_dur = float(dur_match.group(1))

            # Extract effects
            eff_match = re.search(r"Effects:\s*\[(.*?)\]", phase_block)
            if eff_match:
                eff_str = eff_match.group(1)
                # Find all duration values inside the effect dicts
                eff_durs = re.findall(r"'duration':\s*([0-9.]+)", eff_str)
                eff_starts = re.findall(r"'relative_start_time':\s*([0-9.]+)", eff_str)

                for start, dur in zip(eff_starts, eff_durs):
                    s = float(start)
                    d = float(dur)
                    if s + d > phase_dur + 0.1:  # 0.1s tolerance
                        report += f"[WARNING] Phase {idx + 1}: Effect starting at {s}s for {d}s exceeds Phase Duration of {phase_dur}s.\n"
                        errors_found = True

            # Extract punch-ins
            punch_match = re.search(r"Punch-ins:\s*\[(.*?)\]", phase_block)
            if punch_match:
                punches = re.findall(r"([0-9.]+)", punch_match.group(1))
                for p in punches:
                    pf = float(p)
                    if pf > phase_dur:
                        report += f"[WARNING] Phase {idx + 1}: Punch-in at {pf}s exceeds Phase Duration of {phase_dur}s.\n"
                        errors_found = True

        except Exception as e:
            logger.warning(f"Math parser failed on phase {idx + 1}: {e}")

    if not errors_found:
        report += "SUCCESS: All effect timestamps and durations fit perfectly within their respective phases.\n"
    else:
        report += "ACTION REQUIRED: Please adjust the timestamps to fit within the Phase boundaries.\n"

    return report
