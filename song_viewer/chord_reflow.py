"""Paired wrap for chord line + lyric line (monospace columns)."""

from __future__ import annotations

# QTextBlock userState bit flags (default userState is -1 = unset).
# BLOCK_MARKED distinguishes "reflow classified this block" from plain 0.
BLOCK_WRAP_CONT = 1  # continuation inside an already-started pair
BLOCK_IS_CHORD = 2  # this block is the chord row
BLOCK_LEAD = 4  # lyric-only prefix before the first chord of a pair
BLOCK_MARKED = 8  # reflow has written a classification into userState


def pack_state(*, is_chord: bool, wrap_cont: bool = False, lead: bool = False) -> int:
    value = BLOCK_MARKED
    if is_chord:
        value |= BLOCK_IS_CHORD
    if wrap_cont:
        value |= BLOCK_WRAP_CONT
    if lead:
        value |= BLOCK_LEAD
    return value


def state_marked(state: int) -> bool:
    return state >= 0 and bool(state & BLOCK_MARKED)


def state_wrap_cont(state: int) -> bool:
    return state_marked(state) and bool(state & BLOCK_WRAP_CONT)


def state_lead(state: int) -> bool:
    return state_marked(state) and bool(state & BLOCK_LEAD)


def state_is_chord(state: int, fallback: bool) -> bool:
    if not state_marked(state):
        return fallback
    return bool(state & BLOCK_IS_CHORD)


def _pad(a: str, b: str) -> tuple[str, str]:
    n = max(len(a), len(b), 1)
    return a + (" " * (n - len(a))), b + (" " * (n - len(b)))


def _chord_token_end(chord: str, start: int) -> int:
    i = start
    n = len(chord)
    while i < n and chord[i] == " ":
        i += 1
    while i < n and chord[i] != " ":
        i += 1
    return i


def _choose_break(lyric: str, pos: int, limit: int, width: int) -> int:
    """Word-aware break; avoid 1–2 character orphans on the next line."""
    if limit >= width:
        return width
    br = lyric.rfind(" ", pos, limit)
    if br <= pos:
        break_at = limit
    else:
        break_at = br + 1

    rest = width - break_at
    if 0 < rest <= 2:
        # Pull the orphan word onto the next line instead of "снов" / "а"
        prev = lyric.rfind(" ", pos, break_at - 1) if break_at > pos + 1 else -1
        if prev > pos:
            break_at = prev + 1
        else:
            break_at = width
    return break_at


def wrap_chord_lyric(chord: str, lyric: str, cols: int) -> list[tuple[str, str]]:
    """Split a chord/lyric pair into fragments that fit ``cols`` characters each."""
    cols = max(8, int(cols))
    chord_p, lyric_p = _pad(
        chord.replace("\t", " ").rstrip("\n"),
        lyric.replace("\t", " ").rstrip("\n"),
    )
    width = len(lyric_p)
    fragments: list[tuple[str, str, int]] = []  # c, l, slice_width
    pos = 0

    while pos < width:
        limit = min(pos + cols, width)
        break_at = _choose_break(lyric_p, pos, limit, width)

        # Keep whole chord tokens that start inside this window together.
        j = pos
        while j < limit:
            if chord_p[j] != " ":
                token_end = _chord_token_end(chord_p, j)
                if j < break_at < token_end or (j < break_at and token_end > break_at):
                    break_at = max(break_at, token_end)
                elif break_at <= j < limit:
                    break_at = max(break_at, token_end)
                j = token_end
            else:
                j += 1

        if break_at <= pos:
            break_at = min(pos + cols, width)

        c_part = chord_p[pos:break_at]
        l_part = lyric_p[pos:break_at]
        slice_w = break_at - pos
        if c_part.strip() or l_part.strip():
            fragments.append((c_part, l_part, slice_w))
        pos = break_at

    if fragments:
        last_c, last_l, last_w = fragments[-1]
        fragments[-1] = (last_c.rstrip(), last_l.rstrip(), last_w)
    return fragments or [("", "", 0)]


def reflow_line_pairs(
    lines: list[tuple[str, bool, int]],
    cols: int,
) -> list[tuple[str, bool, int]]:
    """
    Reflow (text, is_chord, user_state) lines.
    First unwraps previous wrap fragments, then wraps pairs to ``cols``.
    """
    logical: list[tuple[str, bool]] = []
    i = 0
    n = len(lines)
    while i < n:
        # Lyric-only LEAD fragments belong to the following chord/lyric pair.
        # Track column width so chord absolute positions survive unwrap.
        lead_lyric = ""
        lead_cols = 0
        while i < n and not lines[i][1] and state_lead(lines[i][2]):
            chunk = lines[i][0]
            lead_lyric += chunk
            # Slice width was preserved via trailing spaces where needed; use
            # max(len, stored) — LEAD chunks keep their original slice padding
            # in a trailing marker of spaces when emitted below.
            lead_cols += len(chunk)
            i += 1
        if i >= n:
            if lead_lyric:
                logical.append((lead_lyric.rstrip(), False))
            break

        text, is_chord, _state = lines[i]
        if is_chord and i + 1 < n and not lines[i + 1][1]:
            # Restore columns skipped by LEAD lyric-only windows.
            chord_acc = (" " * lead_cols) + text
            lyric_acc = lead_lyric + lines[i + 1][0]
            i += 2
            while i < n and state_wrap_cont(lines[i][2]):
                if lines[i][1] and i + 1 < n and not lines[i + 1][1]:
                    chord_acc += lines[i][0]
                    lyric_acc += lines[i + 1][0]
                    i += 2
                elif not lines[i][1]:
                    lyric_acc += lines[i][0]
                    i += 1
                else:
                    break
            logical.append((chord_acc.rstrip(), True))
            logical.append((lyric_acc.rstrip(), False))
            continue

        if lead_lyric:
            logical.append((lead_lyric.rstrip(), False))
        logical.append((text, is_chord))
        i += 1

    out: list[tuple[str, bool, int]] = []
    i = 0
    while i < len(logical):
        text, is_chord = logical[i]
        if is_chord and i + 1 < len(logical) and not logical[i + 1][1]:
            lyric = logical[i + 1][0]
            parts = wrap_chord_lyric(text, lyric, cols)
            seen_chord = False
            for c_part, l_part, slice_w in parts:
                if c_part.strip():
                    # Relative slice only — do NOT prepend spaces from earlier
                    # windows (that caused horizontal scrollbars).
                    wrap = seen_chord
                    seen_chord = True
                    out.append((c_part, True, pack_state(is_chord=True, wrap_cont=wrap)))
                    out.append((l_part, False, pack_state(is_chord=False, wrap_cont=wrap)))
                elif l_part.strip() or l_part:
                    # Pad LEAD chunk to full slice width so unwrap restores columns.
                    if len(l_part) < slice_w:
                        l_part = l_part + (" " * (slice_w - len(l_part)))
                    if seen_chord:
                        out.append(
                            (l_part, False, pack_state(is_chord=False, wrap_cont=True))
                        )
                    else:
                        out.append(
                            (l_part, False, pack_state(is_chord=False, lead=True))
                        )
            i += 2
            continue
        # Unpaired line — hard-wrap by columns, avoid orphans.
        if len(text) > cols:
            pos = 0
            first = True
            while pos < len(text):
                limit = min(pos + cols, len(text))
                break_at = _choose_break(text, pos, limit, len(text))
                if break_at <= pos:
                    break_at = min(pos + cols, len(text))
                chunk = text[pos:break_at]
                if chunk.strip() or chunk:
                    out.append(
                        (
                            chunk.rstrip() if break_at >= len(text) else chunk,
                            is_chord,
                            pack_state(is_chord=is_chord, wrap_cont=not first),
                        )
                    )
                    first = False
                pos = break_at
        else:
            out.append((text, is_chord, pack_state(is_chord=is_chord)))
        i += 1
    return out
