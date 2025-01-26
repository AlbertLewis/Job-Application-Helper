#! /usr/bin/python3

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup

from openai import OpenAI
from pydantic import BaseModel
import json
import tiktoken
from datetime import date
from sheets import main

OPENAI_API_KEY = ""
# switch to environment variable
with open("openai_key.json") as openai_key_file:
    data = json.load(openai_key_file)
    OPENAI_API_KEY = data["key"]
client = OpenAI(api_key=OPENAI_API_KEY)
    
# for gpt-4o models
ENCODING_NAME = "o200k_base"

# Required json formats for chatgpt
class Salary(BaseModel):
    min: int
    max: int
    annually: int
    hourly: int
    monthly: int

class JobApplication(BaseModel):
    company: str
    date_posted: str
    job_title: str
    location: str
    qualifications: list[str]
    salary: Salary
    notes: str

def scrape_app(path) -> bool:
    """_summary_

    Args:
        path (_type_): _description_

    Returns:
        bool: _description_
    """
    try:
        # Get html using webdriver to make sure site scripts run
        op = webdriver.ChromeOptions()
        op.add_argument('headless')
        driver = webdriver.Chrome(options=op)
        driver.get(path)

        # Wait until scripts are fully loaded so text appears
        try:
            WebDriverWait(driver, 5).until(
                lambda driver: driver.find_element(By.CSS_SELECTOR, "element_selector").text.strip() != "" # Wait until text is loaded
            )
        except TimeoutException:
            print("No text appeared in the element within the timeout period.")

        # Turn html source into soup object and close driver
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.close()
        with open("job_app_raw.html", "w", encoding="utf-8") as file:
            file.write(str(soup))


        # IDEAS TODO
        # If removing script tag results in a page that is super short, do not remove it?
        # maybe generate a list of keywords associate with job search, and only keep lines with those key words>
        # Or try all of these and pick the best one based on which one has the most information
        # maybe let the entire soup go through if it is under the tokenizer limit without needing to parse out text
        # Example job postings: https://wd3.myworkdaysite.com/en-US/recruiting/magna/Magna/job/Student---Engineering-ADAS-Algorithm--Summer-2025_R00164665
        # Get rid of unecessary HTML TODO
        # Remove any line with uncecessary tags "script", "img", etc.
        for tag in soup(["script", "style", "img", "meta", "link", "form"]):
            tag.decompose()
        
        # Get only the text        
        # Adapted from https://stackoverflow.com/questions/328356/extracting-text-from-html-file-using-python
        text = soup.get_text()
        # break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)

        # get rid of duplicate lines
        unique_lines = set()
        new_text = ""
        for line in text.splitlines():
            if line in unique_lines:
                continue
            new_text = new_text + line + "\n"
            unique_lines.add(line)
        text = new_text

        with open("job_app_post_processed.html", "w", encoding="utf-8") as file:
            file.write(text)
        print(text)

        num_tokens = evaluate_num_tokens(str(text), ENCODING_NAME)
        print(f"num tokens: {num_tokens}")
        if num_tokens > 5000:
            print("Too many tokens to call chatgpt")
            return False
        if num_tokens == 0:
            print("No tokens generated, text may be empty")
            return False

        job_info_json = call_chatgpt(text)

        # Manually iput fields like date and link
        today = date.today()
        job_info_json["date"] = today.strftime("%m/%d/%Y")
        job_info_json["posting"] = path

        with open("job_info.json", "w", encoding="utf-8") as file:
             json.dump(job_info_json, file)
        print(json.dumps(job_info_json))
        main(job_info_json)
        return True
    except Exception as e:
        print(e)
        return False

def evaluate_num_tokens(text : str, encoding : str) -> int:
    encoding = tiktoken.get_encoding(encoding)
    return len(encoding.encode(text))

def call_chatgpt(content) -> str:
    """_summary_

    Args:
        path (_type_): _description_

    Returns:
        str:
    """

    completion = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    store=True,
    messages=[
        {"role": "system", "content": """Extract the job application information from the given html. 
         Company can be the shortened version of the company name, the notes section can be 100-300 words long. 
         The qualifications are a list of the qualifications outlined in the job application. 
         If any data is missing, do not generate imaginary data, just leave the data entry blank."""},
        {"role": "user", "content": f"{content}"},
    ],
    response_format=JobApplication,
    )
    response = completion.choices[0].message.parsed
    return json.loads(response.model_dump_json())

# Try with chatgpt and with normal web scraping techniques
# remove scripts and forms, and then pass into chatgpt
if __name__ == "__main__":

    while True:
        path = input("Please copy and paste the path to the job application into the terminal and press enter or press enter to exit:\n")
        if path:
            if scrape_app(path):
                print("Successfully added to google sheet")
            else:
                print("Unsuccessful")
        else:
            print("Exiting")
            exit()

    