from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "reports" / "demo-output.txt"
OUTPUT = ROOT / "docs" / "assets" / "token-gateway-demo.gif"

WIDTH = 1180
HEIGHT = 720
PADDING = 34
LINE_HEIGHT = 25
BG = "#0f172a"
PANEL = "#111827"
BORDER = "#334155"
TEXT = "#e5e7eb"
MUTED = "#94a3b8"
GREEN = "#86efac"
BLUE = "#bfdbfe"


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/consola.ttf"),
        Path("C:/Windows/Fonts/CascadiaMono.ttf"),
        Path("C:/Windows/Fonts/seguiemj.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def draw_frame(lines: list[str], frame_index: int, total_frames: int) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)
    font = load_font(20)
    small = load_font(16)
    title = load_font(26)

    draw.rounded_rectangle((18, 18, WIDTH - 18, HEIGHT - 18), radius=10, fill=PANEL, outline=BORDER)
    draw.text((PADDING, 30), "LLM Token Optimization Gateway Demo", fill=TEXT, font=title)
    draw.text(
        (PADDING, 66),
        "Prompt compression + exact cache in front of a local LLM service",
        fill=MUTED,
        font=small,
    )
    draw.line((PADDING, 96, WIDTH - PADDING, 96), fill=BORDER, width=1)

    y = 116
    visible_lines = lines[:frame_index]
    for line in visible_lines[-20:]:
        color = TEXT
        if (
            line.startswith("Tokens")
            or line.startswith("Reduction")
            or line.startswith("Cache hit")
        ):
            color = GREEN
        elif line.startswith("1.") or line.startswith("2.") or line.startswith("3."):
            color = BLUE
        draw.text((PADDING, y), line, fill=color, font=font)
        y += LINE_HEIGHT

    progress = frame_index / max(total_frames, 1)
    bar_width = int((WIDTH - (PADDING * 2)) * progress)
    draw.rounded_rectangle(
        (PADDING, HEIGHT - 48, WIDTH - PADDING, HEIGHT - 34),
        radius=7,
        fill="#1f2937",
    )
    draw.rounded_rectangle(
        (PADDING, HEIGHT - 48, PADDING + bar_width, HEIGHT - 34),
        radius=7,
        fill="#22c55e",
    )
    return image


def main() -> None:
    try:
        raw_text = INPUT.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw_text = INPUT.read_text(encoding="utf-16")
    lines = raw_text.splitlines()
    lines = [line for line in lines if line.strip()]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    frames = [draw_frame(lines, index, len(lines)) for index in range(1, len(lines) + 1)]
    frames.extend([frames[-1]] * 8)
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=650,
        loop=0,
        optimize=True,
    )


if __name__ == "__main__":
    main()
