"""Rough cost model: does per-step model switching pay off once prompt caching is considered?

Prices are USD per million tokens (Anthropic first-party API, 2026-09 snapshot).
cache_write = 5-minute TTL write (1.25x base input).
"""

PRICES = {
    #          input  output  cache_write  cache_read
    "fable":  (10.0, 50.0, 12.50, 0.25),
    "opus":   (4.0,  20.0,  5.00, 0.20),
    "sonnet": (2.0,  10.0,  2.50, 0.20),
    "haiku":  (1.0,   5.0,  1.25, 0.10),
}
M = 1_000_000


def turn_cost(model, context, new_in, out, warm=True):
    """One agent-loop request: read `context` from cache, write `new_in` fresh tokens, emit `out`."""
    _, o, w, r = PRICES[model]
    if warm:
        return (context * r + new_in * w + out * o) / M
    # cold: the whole prefix must be re-written for this model
    return ((context + new_in) * w + out * o) / M


def main_loop_switch(base, cheap, context, steps, new_in=4_000, out=1_500):
    """Cost of running `steps` turns on `cheap` inside the main conversation and then switching back,
    versus staying on `base` the whole time."""
    stay = sum(turn_cost(base, context + i * (new_in + out), new_in, out) for i in range(steps + 1))
    sw = turn_cost(cheap, context, new_in, out, warm=False)
    sw += sum(turn_cost(cheap, context + i * (new_in + out), new_in, out) for i in range(1, steps))
    back_ctx = context + steps * (new_in + out)
    # back on base: everything added while on `cheap` is uncached for `base`
    _, o, w, r = PRICES[base]
    sw += (context * r + (steps * (new_in + out) + new_in) * w + out * o) / M
    return stay, sw


def subagent_vs_inline(main, sub, reads, read_tokens, remaining_main_turns,
                       sub_overhead=15_000, summary=1_500, out=800):
    """File search / log reading: do it inline on the main model, or delegate to a subagent.

    Inline: each tool result is written to the main cache and then re-read on every later main turn.
    Subagent: pays its own cold start (system prompt + tools), reads in its own context,
    and only `summary` tokens come back into the main context.
    """
    _, mo, mw, mr = PRICES[main]
    inline_tokens = reads * read_tokens
    inline = (inline_tokens * mw + reads * out * mo) / M
    inline += remaining_main_turns * inline_tokens * mr / M  # bloat re-read on every later turn

    _, so, sw, sr = PRICES[sub]
    sub_cost = sub_overhead * sw / M
    ctx = sub_overhead
    for _ in range(reads):
        sub_cost += (ctx * sr + read_tokens * sw + out * so) / M
        ctx += read_tokens + out
    sub_cost += (summary * mw + summary * mo) / M  # main writes the delegation prompt + reads the summary
    sub_cost += remaining_main_turns * summary * mr / M
    return inline, sub_cost


if __name__ == "__main__":
    print("== A. Switching the MAIN loop model mid-conversation (Opus 5.5 -> cheaper -> back) ==")
    for cheap in ("sonnet", "haiku"):
        for ctx in (30_000, 100_000, 300_000):
            if cheap == "haiku" and ctx > 200_000:
                continue  # Haiku 4.5 context window is 200k
            for steps in (1, 3, 10):
                stay, sw = main_loop_switch("opus", cheap, ctx, steps)
                print(f"  {cheap:6s} ctx={ctx//1000:>3}k steps={steps:>2}: stay=${stay:.3f}  switch=${sw:.3f}  "
                      f"{'SAVES' if sw < stay else 'COSTS MORE'} ({(sw/stay-1)*100:+.0f}%)")

    print("\n== B. File search: inline on Opus 5.5 vs delegated subagent ==")
    for sub in ("haiku", "sonnet", "opus"):
        for reads, rt in ((3, 2_000), (10, 5_000), (20, 8_000)):
            inline, s = subagent_vs_inline("opus", sub, reads, rt, remaining_main_turns=30)
            print(f"  sub={sub:6s} reads={reads:>2}x{rt//1000}k: inline=${inline:.3f}  subagent=${s:.3f}  "
                  f"({(s/inline-1)*100:+.0f}%)")

    print("\n== C. Jev routing call ==")
    print(f"  2,000-token routing request: ${2_000 * 0.042 / M:.6f}")
