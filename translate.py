#!/usr/bin/env python
import os
import sys
import subprocess
import requests
import pytesseract
from concurrent.futures import ProcessPoolExecutor
from bs4 import BeautifulSoup
from PIL import Image

# If you don't have tesseract executable in your PATH, include the following:
#pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

# Function to interact with the local translation API
def translate_text(text, src_lang="zh", dst_lang="en"):
    response = requests.post("http://localhost:5000/translate", json={
        "q": text,
        "source": src_lang,
        "target": dst_lang,
        "format": "text",
        "api_key": ""
    })

    translated_text = response.json().get("translatedText")

    return translated_text

def translate_markdown(input_file):
    output_file = input_file[:-3] + ".en.md"

    with open(input_file, 'r', encoding='utf-8') as file:
        current_dir = os.path.dirname(input_file)

        content = file.read()
        soup = BeautifulSoup(content, 'html.parser')

        print(f"Translating '{input_file}'...", file=sys.stderr)

        for text_node in soup.find_all(string=True):
            translated_text = translate_text(text_node)
            text_node.replace_with(translated_text)

        for img_node in soup.find_all('img'):
            img_path = img_node['src']
            
            if current_dir:
                img_path = os.path.join(current_dir, img_path)

            with Image.open(img_path) as img:
                img_text_chinese = pytesseract.image_to_string(img, lang='chi_sim')

                img_text_english = translate_text(img_text_chinese)

                caption = soup.new_tag('p')
                caption.string = "No text found" if img_text_english is None else img_text_english

                img_node.insert_after(caption)
        
        # Write the processed HTML content back to the output file
        with open(output_file, 'w', encoding='utf-8') as out:
            out.write(str(soup))


def enumerate_markdown(input_file):
    files = [input_file]

    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()

        soup = BeautifulSoup(content, 'html.parser')

        for link in soup.find_all('a', href=True):
            linked_file = link['href']
            if linked_file.endswith('.md'):
                if not os.path.exists(linked_file):
                    print(f"Error: Missing link - {linked_file}", file=sys.stderr)
                    continue

                files.append(linked_file)

    return files


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} FILE.md", file=sys.stderr)
        exit(1)

    input_file = sys.argv[1]

    os.chdir(os.path.dirname(input_file))

    max_workers = 8

    files = enumerate_markdown(os.path.basename(input_file))

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        executor.map(translate_markdown, files)


