import pyautogui
import os
from datetime import datetime
import pytesseract
from difflib import SequenceMatcher

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def scroll_down():
    pyautogui.scroll(-500)
    return "Scrolled down"


def scroll_up():
    pyautogui.scroll(500)
    return "Scrolled up"


def click_here():
    pyautogui.click()
    return "Clicked"


def take_screenshot():
    screenshot_dir = os.path.join(os.path.expanduser("~"), "Pictures", "AssistantScreenshots")
    os.makedirs(screenshot_dir, exist_ok=True)
    filename = os.path.join(screenshot_dir, f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
    pyautogui.screenshot(filename)
    return "Screenshot saved"


def type_text(text_to_type):
    pyautogui.typewrite(text_to_type, interval=0.03)
    return f"Typed: {text_to_type}"


def smart_click(target_text):
    """Takes a screenshot, finds text matching target_text via OCR, and clicks it."""
    screenshot = pyautogui.screenshot()
    data = pytesseract.image_to_data(screenshot, output_type=pytesseract.Output.DICT)

    best_match = None
    best_score = 0

    for i, word in enumerate(data['text']):
        word = word.strip()
        if not word:
            continue

        score = SequenceMatcher(None, word.lower(), target_text.lower()).ratio()

        if score > best_score and score >= 0.6:
            best_score = score
            x = data['left'][i] + data['width'][i] // 2
            y = data['top'][i] + data['height'][i] // 2
            best_match = (x, y, word)

    if best_match:
        x, y, matched_word = best_match
        pyautogui.click(x, y)
        return f"Clicked on '{matched_word}'"
    else:
        return f"Couldn't find '{target_text}' on screen"


def handle_computer_command(text_lower, original_text):
    """
    Routing function for all computer-control commands.
    Returns a response string if this module handled the command, otherwise None.
    """
    words = original_text.lower().split()

    if "click" in words:
        click_index = words.index("click")
        remaining_words = original_text.split()[click_index + 1:]

        if remaining_words and remaining_words[0].lower() == "on":
            remaining_words = remaining_words[1:]

        if remaining_words:
            target = " ".join(remaining_words)
            return smart_click(target)
        else:
            return click_here()

    if "scroll" in text_lower and "down" in text_lower:
        return scroll_down()

    if "scroll" in text_lower and "up" in text_lower:
        return scroll_up()

    if "screenshot" in text_lower or "screen shot" in text_lower:
        return take_screenshot()

    if text_lower.startswith("type "):
        return type_text(original_text[5:])

    return None