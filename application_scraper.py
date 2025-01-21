#! /usr/bin/python3

import requests
from pydantic import BaseModel
from selenium import webdriver
from bs4 import BeautifulSoup
from openai import OpenAI
import json


OPENAI_API_KEY = ""

with open("openai_key.json") as openai_key_file:
    data = json.load(openai_key_file)
    OPENAI_API_KEY = data["key"]

client = OpenAI(api_key=OPENAI_API_KEY)
    
class Salary(BaseModel):
    min: int
    max: int
    annually: int
    hourly: int
    monthly: int

class JobApplication(BaseModel):
    company: str
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
        # response = requests.get(path)

        # Get html using webdriver to make sure site scripts run
        op = webdriver.ChromeOptions()
        op.add_argument('headless')
        driver = webdriver.Chrome(options=op)
        driver.get(path)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.close()

        with open("job_app.html", "w", encoding="utf-8") as file:
            file.write(str(soup))

        # Get rid of unecessary HTML
        for script in soup(["script", "style", "img", "meta", "link", "form"]):
            script.decompose()
        
        # Adapted from https://stackoverflow.com/questions/328356/extracting-text-from-html-file-using-python
        # get only the text
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
        
        # test_html = ""
        # with open("job_app_post_processed.html", 'r') as f:
        #     test_html = f.read()
        # job_info_json = call_chatgpt(test_html)
        # print(job_info_json)
        # with open("job_info.json", "w", encoding="utf-8") as file:
        #     file.write(job_info_json.json)
        return True
    except Exception as e:
        print(e)
        return False


def call_chatgpt(content) -> json:
    """_summary_

    Args:
        path (_type_): _description_

    Returns:
        json: the 
    """

    completion = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    store=True,
    messages=[
        {"role": "system", "content": """Extract the job application information from the given html. 
         Company can be the shortened version of the company name, the notes section can be 100-300 words long. 
         The qualifications are a list of the qualifications outlined in the job application. 
         The salary can either be hourly, annually or monthly, do not create imaginary salaries"""},
        {"role": "user", "content": f"{content}"},
    ],
    response_format=JobApplication,
    )
    response = completion.choices[0].message.parsed

    return response.model_dump_json()

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

    