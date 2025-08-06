import os
import time
import re
import RPi.GPIO as GPIO
from pdf2image import convert_from_path
import pytesseract

# Define GPIO pins used for decoders
cell_selectors = [
    {'pins': [4, 17, 27], 'enabler': 22},
    {'pins': [14, 15, 18], 'enabler': 23},
    {'pins': [10, 9, 11], 'enabler': 5},
    {'pins': [24, 25, 8], 'enabler': 7},
    {'pins': [5, 6, 13], 'enabler': 19}
]

# GPIO pins for Next and Back buttons
NEXT_BUTTON_PIN = 2
BACK_BUTTON_PIN = 3

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for cell in cell_selectors:
    for pin in cell['pins'] + [cell['enabler']]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

GPIO.setup(NEXT_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BACK_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

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

def set_decoder_output(value, pins):
    for i in range(3):
        GPIO.output(pins[i], (value >> i) & 1)

def get_pin_selector(dot_index, state):
    pin_map = {
        0: (8, 0),
        1: (9, 1),
        2: (10, 2),
        3: (11, 3),
        4: (12, 4),
        5: (13, 5)
    }
    if dot_index < 3:
      return pin_map[dot_index][1 if state else 0]
    else:
      return pin_map[dot_index][0 if state else 1]

def activate_cell(cell_index, pattern):
    cell_config = cell_selectors[cell_index]
    selector_pins = cell_config['pins']
    enabler_pin = cell_config['enabler']

    for dot_index, state in enumerate(pattern):
        pin_input = get_pin_selector(dot_index, state)

        GPIO.output(enabler_pin, GPIO.HIGH if pin_input < 8 else GPIO.LOW)
        set_decoder_output(pin_input % 8, selector_pins)

        direction = "RAISED" if state else "LOWERED"
        print(f"Dot {dot_index + 1}: {direction} (Input: {pin_input})")
        time.sleep(0.05)
    
    GPIO.output(enabler_pin, GPIO.LOW)
    time.sleep(0.2)

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
            print(f"Character: {char}, ASCII: {ascii_value}, Braille: {pattern}")
            result.append((char, pattern))
        else:
            print(f"Ignored non-ASCII or unsupported character: {char} (ASCII: {ascii_value})")
    return result
    
def display_braille_matrix(braille_data, start_index):
    for i, (char, pattern) in enumerate(braille_data[start_index:start_index + 5]):
        print(f"\nDisplaying Braille Cell {start_index + i + 1}: {char} -> {pattern}")
        activate_cell(i, pattern)
        time.sleep(0.2)

def wait_for_button_press():
    print("Waiting for button press...")
    prev_next_state = GPIO.input(NEXT_BUTTON_PIN)
    prev_back_state = GPIO.input(BACK_BUTTON_PIN)
  
    while True:
        curr_next_state = GPIO.input(NEXT_BUTTON_PIN)
        curr_back_state = GPIO.input(BACK_BUTTON_PIN)
      
        if prev_next_state == GPIO.HIGH and curr_next_state == GPIO.LOW:
            print("NEXT button pressed.")
            return "NEXT"

        if prev_back_state == GPIO.HIGH and curr_back_state == GPIO.LOW:
            print("BACK button pressed.")
            return "BACK"

        prev_next_state = curr_next_state
        prev_back_state = curr_back_state
        time.sleep(0.01)
      
def page_contains_credit(text):
    lower_text = text.lower()
    return any(keyword in lower_text for keyword in credit_keywords)

def clean_ocr_text(text):
    text = text.replace('|', 'I')
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'").replace('`', "'")

    lines = text.splitlines()
    filtered_lines = [line for line in lines if re.search(r'[a-zA-Z0-9]', line)]
    text = "\n".join(filtered_lines)

    text = re.sub(r'\s{2,}', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

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
                start_index += 5
            elif button == "BACK" and start_index >= 5:
                start_index -= 5
            time.sleep(0.2)
    else:
        print("No text to display in Braille.")

    GPIO.cleanup()

if __name__ == "__main__":
    main()
