import json
import requests
import fire
from bs4 import BeautifulSoup

LOGIN_PAGE = "https://strenuouslife.co/wp-login.php"
BADGES_URL = "https://strenuouslife.co/badges"
REQUIREMENTS_URL = "https://strenuouslife.co/requirements"
BADGES = ['penmanship', 'shaving', 'kiss-the-chef', 'backyard-chef']

class GetBadgeRequirements():

    def __init__(self, user, pwd):
        self.tsl_dict = {}
        self.payload = {
            'log': user,
            'pwd': pwd
            }

    def get_badge_requirements(self):
        with requests.Session() as session:
            session.post(LOGIN_PAGE, data=self.payload)
            badges_list = []
            for badge in BADGES:
                page = self.get_page(session, f"{BADGES_URL}/{badge}", "bb-learndash-content-wrap")
                badge_dict = {}
                badge_dict["Name"] = badge
                badge_dict["Completion"] = "TRUE" if page.find(
                    'div', class_="ld-status ld-status-complete ld-secondary-background"
                    ) else "FALSE"
                requirements = self.get_requirements(session, page)
                badge_dict["Requirements"] = requirements
                badges_list.append(badge_dict)
            self.tsl_dict["Badges"] = badges_list
            with open('badge_requirements.json', 'w') as outfile:
                json.dump(self.tsl_dict, outfile, indent=4)

    def get_requirements(self, session, page):
        requirements = page.find_all('a', class_='ld-item-name')
        return self.evaluate_requirements(session, requirements)

    def evaluate_requirements(self, session, requirements):
        requirements_list = []
        for requirement in requirements:
            requirement_dict = {}
            requirement_text = requirement.find('div', class_='ld-item-title').contents[0].strip()
            requirement_dict["Name"] = requirement_text
            self.evaluate_completion(requirement, requirement_dict)
            if requirement.find('span', class_='ld-item-component'):
                components = self.get_components(session, requirement_text)
                requirement_dict["Components"] = components
            requirements_list.append(requirement_dict)
        return requirements_list

    def get_components(self, session, requirement):
        requirement_kabob = requirement.replace(' ', '-').replace('/', '')
        results = self.get_page(session, f"{REQUIREMENTS_URL}/{requirement_kabob}", 'ld-table-list-items')
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

    def get_page(self, session, url, element):
        page = session.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        return soup.find(class_=element)

    def evaluate_completion(self, requirement, dict):
        dict["Completion"] = "TRUE" if requirement.find('div', class_='ld-status-complete') else "FALSE"


if __name__ == '__main__':
    fire.Fire(GetBadgeRequirements)
