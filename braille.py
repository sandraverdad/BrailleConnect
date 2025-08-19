import os
import time
import re
import RPi.GPIO as GPIO
from pdf2image import convert_from_path
import pytesseract

# Define GPIO pins for each Braille pins (1-6)
cell_pins = {
    1: [14, 15, 18, 23, 24, 25]
}

# GPIO pins for Next and Back buttons
NEXT_BUTTON_PIN = 20
BACK_BUTTON_PIN = 21

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for pins in cell_pins.values():
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)

# Setup navigation buttons
GPIO.setup(NEXT_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BACK_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def reset_pins():
    for pins in cell_pins.values():
        for pin in pins:
            GPIO.output(pin, GPIO.HIGH)
    time.sleep(4)

braille_alphabet = {
    'A': [1, 0, 0, 0, 0, 0], 'B': [1, 1, 0, 0, 0, 0], 'C': [1, 0, 0, 1, 0, 0],
    'D': [1, 0, 0, 1, 1, 0], 'E': [1, 0, 0, 0, 1, 0], 'F': [1, 1, 0, 1, 0, 0],
    'G': [1, 1, 0, 1, 1, 0], 'H': [1, 1, 0, 0, 1, 0], 'I': [0, 1, 0, 1, 0, 0],
    'J': [0, 1, 0, 1, 1, 0], 'K': [1, 0, 1, 0, 0, 0], 'L': [1, 1, 1, 0, 0, 0],
    'M': [1, 0, 1, 1, 0, 0], 'N': [1, 0, 1, 1, 1, 0], 'O': [1, 0, 1, 0, 1, 0],
    'P': [1, 1, 1, 1, 0, 0], 'Q': [1, 1, 1, 1, 1, 0], 'R': [1, 1, 1, 0, 1, 0],
    'S': [0, 1, 1, 1, 0, 0], 'T': [0, 1, 1, 1, 1, 0], 'U': [1, 0, 1, 0, 0, 1],
    'V': [1, 1, 1, 0, 0, 1], 'W': [0, 1, 0, 1, 1, 1], 'X': [1, 0, 1, 1, 0, 1],
    'Y': [1, 0, 1, 1, 1, 1], 'Z': [1, 0, 1, 0, 1, 1], ' ': [0, 0, 0, 0, 0, 0],
    '.': [0, 1, 0, 0, 1, 1], ',': [0, 1, 0, 0, 0, 0], '!': [0, 1, 1, 0, 1, 0],
    '?': [0, 1, 1, 0, 0, 1], ';': [0, 1, 1, 0, 0, 0], ':': [0, 1, 0, 0, 1, 0],
    '-': [0, 0, 1, 0, 0, 1], "'": [0, 0, 1, 0, 0, 0], '"': [0, 0, 1, 0, 1, 1],
    '/': [0, 0, 1, 1, 0, 0], '#': [0, 0, 1, 1, 1, 1], '1': [1, 0, 0, 0, 0, 0], 
    '2': [1, 1, 0, 0, 0, 0], '3': [1, 0, 0, 1, 0, 0], '4': [1, 0, 0, 1, 1, 0], 
    '5': [1, 0, 0, 0, 1, 0], '6': [1, 1, 0, 1, 0, 0], '7': [1, 1, 0, 1, 1, 0], 
    '8': [1, 1, 0, 0, 1, 0], '9': [0, 1, 0, 1, 0, 0], '0': [0, 1, 0, 1, 1, 0]
}

credit_keywords = [
    "all rights reserved", "isbn", "printed in", "copyright",
    "scanned by", "edition", "publisher", "press", "www", ".com", "©"
]

def page_contains_credit(text):
    lower_text = text.lower()
    return any(keyword in lower_text for keyword in credit_keywords)

def clean_ocr_text(text):
    text = text.replace('|', 'I')
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'").replace('`', "'")

    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

def smart_number_sign_insertion(text):
    result = ''
    in_number = False
    for i, char in enumerate(text):
        if char.isdigit():
            if not in_number:
                result += '#'
                in_number = True
        else:
            in_number = False
        result += char
    return result

def text_to_braille(braille):
    braille = smart_number_sign_insertion(braille.upper())
    result = []
    for char in braille:
        ascii_value = ord(char)
        if 32 <= ascii_value <= 126: 
            pattern = braille_alphabet.get(char, [0, 0, 0, 0, 0, 0])
            result.append((char, pattern))
    return result

def display_braille_matrix(braille_data, start_index):
    total_cells = 1
    for i in range(total_cells):
        data_index = start_index + i
        if data_index < len(braille_data):
            char, pattern = braille_data[data_index]
        else:
            char, pattern = ' ', [0, 0, 0, 0, 0, 0] # Empty Braille for unused remaining cells

        pins = cell_pins.get(i + 1, [])
        print(f"\nDisplaying Braille Character {data_index + 1}: {char} -> ASCII {ord(char)} -> {pattern}")
        for i, pin in enumerate(pins):
            GPIO.output(pin, GPIO.LOW if pattern[i] == 1 else GPIO.HIGH)
        time.sleep(0.1)

def wait_for_button_press(timeout=3, debounce_time=0.05):
    print("Waiting for button press or auto-next in", timeout, "seconds...")
    start_time = time.time()

    while time.time() - start_time < timeout:       
        if GPIO.input(NEXT_BUTTON_PIN) == GPIO.LOW:
            time.sleep(debounce_time)
            if GPIO.input(NEXT_BUTTON_PIN) == GPIO.LOW:
                print("NEXT button pressed.")
                return "NEXT"

        if GPIO.input(BACK_BUTTON_PIN) == GPIO.LOW:
            time.sleep(debounce_time)
            if GPIO.input(BACK_BUTTON_PIN) == GPIO.LOW:
                print("BACK button pressed.")
                return "BACK"

        time.sleep(0.01)
    
    print(f"No button press for {timeout} seconds. Proceeding to next letter...")
    return "NEXT"
    
def main():
    pdf_folder = os.path.join(os.path.dirname(__file__), "PDF")
    pdf_files = [f for f in os.listdir(pdf_folder) if f.lower().endswith(".pdf")]
    if not pdf_files:
        raise FileNotFoundError("No PDF files found in the 'PDF' folder.")
    latest_pdf = max(pdf_files, key=lambda f: os.path.getctime(os.path.join(pdf_folder, f)))
    file_path = os.path.join(pdf_folder, latest_pdf)

    images = convert_from_path(file_path)
    
    text_pages = []
    for img in images:
        page_text = pytesseract.image_to_string(img)
        if not page_contains_credit(page_text):
            text_pages.append(page_text)

    text = clean_ocr_text("\n".join(text_pages))
    print("OCR Extracted Text:\n", latest_pdf, "\n", text)
    
    if text:
        braille_data = text_to_braille(text)
        start_index = 0
        total_cells = len(braille_data)

        while 0 <= start_index < total_cells:
            display_braille_matrix(braille_data, start_index)
            print("\nPress NEXT or BACK hardware button...")

            button = wait_for_button_press()
            if button == "NEXT":
                start_index += 1
            elif button == "BACK" and start_index >= 1:
                start_index -= 1
            time.sleep(0.2)

            reset_pins()
            time.sleep(0.2)
    else:
        print("No text to display in Braille.")

    GPIO.cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        reset_pins()
    finally:
        GPIO.cleanup()
