from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from computemate import config

def get_banner(version):
    """
    Generates and prints a stylized startup banner for ComputeMate AI using the rich library.
    
    The banner uses distinct colors and a panel structure to be visually engaging.
    - Gold/Yellow is used to represent the spiritual/scriptural focus.
    - Cyan/Blue is used to represent the AI/Intelligent nature of the tool.
    - A dark gray background ensures high contrast on both dark and light terminal themes.
    """

    # --- Configuration and Styling ---
    TITLE_TEXT = "ComputeMate AI"
    TAGLINE = "🔋 Power up your productivity 🧠"
    
    # Custom colors using HEX codes for better consistency
    COLOR_SCRIPTURE = "#FFD700"  # Gold
    COLOR_AI = "#00FFFF"         # Cyan
    COLOR_PRIMARY = "#FFFFFF"    # White
    COLOR_BACKGROUND = "#1A1A1A" # Dark Gray/Black for good contrast on most terminals

    # --- 1. Assemble the Title ---
    
    # Create the stylized title text: "COMPUTEMATE" (Gold) + " AI" (Cyan)
    # This uses rich's ability to style segments of text
    title = Text.assemble(
        Text(TITLE_TEXT.split(' ')[0], style=f"bold {COLOR_SCRIPTURE}"),
        Text(" ", style=""),
        Text(TITLE_TEXT.split(' ')[-1], style=f"bold italic {COLOR_AI}"),
    )
    
    # Center the title and make it larger
    title.justify = "center"
    title.style = "bold"

    # --- 2. Assemble the Content (Title, Tagline, Version) ---
    
    # Tagline text
    tagline_text = Text(TAGLINE, style=f"italic {COLOR_PRIMARY}")
    tagline_text.justify = "center"

    # Version text
    version_text = Text(f"[{version}]", style="dim white")
    version_text.justify = "right"
    
    # Combine all lines of content
    content = Text(justify="center")
    content.append(title)
    content.append("\n")
    content.append(tagline_text)
    
    # --- 3. Create the Panel ---
    
    # Use a Panel to box the content for a clean look
    return Panel(
        content,
        #title="[bold]👋 Welcome![/bold]",
        title=config.banner_title,
        title_align="left",
        border_style=f"{COLOR_SCRIPTURE}",
        padding=(1, 4), # Vertical padding (1), Horizontal padding (4)
        subtitle=version_text,
        subtitle_align="right",
        style=f"on {COLOR_BACKGROUND}" # Apply the new background color
    )

if __name__ == "__main__":
    from rich.console import Console
    console = Console()
    console.print(get_banner("1.1.1"))
