import time
import re
import pandas as pd
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://www.foundit.in"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def get_category_links_from_homepage():
    response = requests.get(BASE_URL, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to load homepage: {response.status_code}")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    categories = []

    for tag in soup.find_all("a", href=True, class_="text-sm"):
        text = tag.get_text(strip=True)
        href = tag["href"]
        if "jobs-by" in href:
            categories.append({"Category": text, "Link": BASE_URL + href})
    
    return categories


def extract_subcategory_links(category_url, category_name):
    response = requests.get(category_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to load {category_url}: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    sub_links = []

    
    if "location" in category_url:
        for tag in soup.find_all("a", href=True):
            text = tag.get_text(strip=True)
            href = tag["href"]
            if text.startswith("Jobs in") and "/search/jobs-in-" in href:
                city = text.replace("Jobs in", "").strip()
                full_url = BASE_URL + href
                sub_links.append({"Subcategory": city, "Link": full_url})
    else:
        for tag in soup.find_all("a", href=True, class_="text-sm"):
            text = tag.get_text(strip=True)
            href = tag["href"]
            if "/search/" in href and "-jobs" in href:
                full_url = BASE_URL + href
                sub_links.append({"Subcategory": text, "Link": full_url})

    return sub_links[:10]  


def extract_jobs(driver, category, subcategory, url):
    print(f"Scraping: {category} → {subcategory}")
    driver.get(url)
    time.sleep(10)

    page_source = driver.page_source
    jobs = []

    matches = re.findall(r'"url":"(https://www.foundit.in/job/.*?)".*?"name":"(.*?)"', page_source)
    company_matches = re.findall(r'<img.*?alt="(.*?)"', page_source)
    salary_matches = re.findall(r'<label>(INR .*? LPA)</label>', page_source)

    for i in range(len(matches)):
        job_url, job_title = matches[i]
        company_name = company_matches[i] if i < len(company_matches) else "Not Available"
        salary = salary_matches[i] if i < len(salary_matches) else "Not Available"
        jobs.append({
            "Category": category,
            "Subcategory": subcategory,
            "Job Title": job_title,
            "Company": company_name,
            "Salary": salary,
            "Job URL": job_url
        })

    return jobs


def save_to_excel(data, filename="foundit_all_jobs.xlsx"):
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(f"\nData saved to: {filename}")


def main():
    categories = get_category_links_from_homepage()
    if not categories:
        print("No categories found. Exiting.")
        return

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)

    all_jobs = []
    failed_categories = []

    for cat in categories:
        category_name = cat["Category"]
        category_url = cat["Link"]

        try:
            sub_links = extract_subcategory_links(category_url, category_name)
            if not sub_links:
                print(f"No subcategories found for {category_name}")
                continue

            for sub in sub_links:
                sub_name = sub["Subcategory"]
                sub_url = sub["Link"]
                try:
                    jobs = extract_jobs(driver, category_name, sub_name, sub_url)
                    all_jobs.extend(jobs)
                except Exception as e:
                    print(f"Failed to scrape subcategory {sub_name}: {e}")
                    failed_categories.append(f"{category_name} → {sub_name}")

        except Exception as e:
            print(f"Failed to scrape category {category_name}: {e}")
            failed_categories.append(category_name)

    driver.quit()
    save_to_excel(all_jobs)

    if failed_categories:
        print(f"\nFailed to scrape these categories/subcategories:\n{failed_categories}")

    print("\nScraping completed successfully!")


if __name__ == "__main__":
    main()