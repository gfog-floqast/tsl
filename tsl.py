import json
import requests
import fire
from bs4 import BeautifulSoup

LOGIN_PAGE = "https://strenuouslife.co/wp-login.php"
BADGES_URL = "https://strenuouslife.co/badges"

class GetBadgeRequirements():

    def __init__(self, user, pwd):
        self.tsl_dict = {}
        self.payload = {
            'log': user,
            'pwd': pwd
            }

    def get_badge_requirements(self):
        tsl_list = []
        with requests.Session() as session:
            session.post(LOGIN_PAGE, data=self.payload)
            badges = self.get_badges(session)
            for badge, url in badges.items(): 
                try:
                    page = self.get_page(session, url, "bb-learndash-content-wrap")
                    badge_dict = {}
                    badge_dict["Name"] = badge
                    badge_dict["Completion"] = "TRUE" if page.find(
                        'div', class_="ld-status ld-status-complete ld-secondary-background"
                        ) else "FALSE"
                    requirements = self.get_requirements(session, page)
                    badge_dict["Requirements"] = requirements
                    tsl_list.append(badge_dict)
                except:
                    print(f"An Exception Occurred: Check badge '{badge}'")
            self.tsl_dict["Badges"] = tsl_list
            with open('badge_requirements.json', 'w') as outfile:
                json.dump(self.tsl_dict, outfile, indent=4)

    def get_badges(self, session):
        badge_dict = {}
        page = self.get_page(session, BADGES_URL, "course-dir-list bs-dir-list")
        while page.find('a', class_='next page-numbers'):
            badges = page.find_all('div', class_='bb-course-cover')
            for badge in badges:
                badge_dict[badge.find('a')['title']] = badge.find('a')['href']
            page = self.get_page(session, page.find('a', class_='next page-numbers')['href'])
        badges = page.find_all('div', class_='bb-course-cover')
        for badge in badges:
            badge_dict[badge.find('a')['title']] = badge.find('a')['href']
        return badge_dict

    def get_requirements(self, session, page):
        requirements = page.find_all('a', class_='ld-item-name')
        return self.evaluate_requirements(session, requirements)

    def evaluate_requirements(self, session, requirements):
        requirements_list = []
        for requirement in requirements:
            requirement_dict = {}
            requirement_text = requirement.find('div', class_='ld-item-title').contents[0].strip()
            requirement_encoded = requirement_text.encode("ascii", "ignore").decode()
            requirement_dict["Name"] = requirement_encoded
            self.evaluate_completion(requirement, requirement_dict)
            if requirement.find('span', class_='ld-item-component'):
                components = self.get_components(session, requirement)
                requirement_dict["Components"] = components
            requirements_list.append(requirement_dict)
        return requirements_list

    def get_components(self, session, requirement):
        requirement_url = requirement['href']
        results = self.get_page(session, requirement_url, 'ld-table-list-items')
        components = results.find_all('div', class_='ld-table-list-item')
        return self.evaluate_components(components)

    def evaluate_components(self, components):
        components_list = []
        for component in components:
            component_dict = {}
            component_text = component.find('span', class_='ld-topic-title').contents[0].strip()
            component_encoded = component_text.encode("ascii", "ignore").decode()
            component_dict["Name"] = component_encoded
            self.evaluate_completion(component, component_dict)
            components_list.append(component_dict)
        return components_list

    def get_page(self, session, url, element=''):
        page = session.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        return soup.find(class_=element)

    def evaluate_completion(self, requirement, dict):
        dict["Completion"] = "TRUE" if requirement.find('div', class_='ld-status-complete') else "FALSE"


if __name__ == '__main__':
    fire.Fire(GetBadgeRequirements)
