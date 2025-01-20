#! /usr/bin/python3

import requests
from pydantic import BaseModel
from bs4 import BeautifulSoup # do i need to use?
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
    salary: Salary
    notes: str

def scrape_app(path) -> bool:

    try:
        response = requests.get(path)
        soup = BeautifulSoup(response.content, 'html.parser')

        for tag in soup.find_all(['script', 'form']):
            tag.decompose()

        completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        store=True,
        messages=[
            {"role": "system", "content": "Extract the job application information from the given html. Company can be the shortened version of the company name, the notes section can be 100-300 words long, for the salary that is identified, convert it to hourly and monthly if it is not provided"},
            {"role": "user", "content": f"{soup}"},
        ],
        response_format=JobApplication,
        )

        print(completion.choices[0].message.parsed)
        return True
    except:
        print("Error")
        return False



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

    