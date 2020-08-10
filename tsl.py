import json
import logging
import pandas as pd
import requests
import fire

from bs4 import BeautifulSoup
from pathos.multiprocessing import ProcessingPool as Pool

LOGIN_PAGE = "https://strenuouslife.co/wp-login.php"
BADGES_URL = "https://strenuouslife.co/badges"
THREADS = 3

logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)

logging.getLogger('urllib3').setLevel(logging.ERROR)


class GetBadgeRequirements():

    def __init__(self, user, pwd):
        self.payload = {
            'log': user,
            'pwd': pwd
            }

    def get_badge_requirements(self):
        with requests.Session() as session:
            session.post(LOGIN_PAGE, data=self.payload)
            badges = self.get_badge_names(session)
            LOGGER.info("Retrieved %s badges", len(badges))
            logging.debug(badges.keys())
            # TODO: tune this for optimal performance?
            pool = Pool(THREADS)
            badges = pool.map(self.evaluate_badge_requirements, [session]*len(badges), badges, badges.values())

            with open('badge_requirements.json', 'w') as outfile:
                json.dump(badges, outfile, indent=4)

            self.save_as_csv(badges)

    def get_badge_names(self, session):
        badge_dict = {}
        page = self.get_page(session, BADGES_URL, "course-dir-list bs-dir-list")
        while page.find('a', class_='next page-numbers'):
            badges = page.find_all('div', class_='bb-cover-list-item')
            for badge in badges:
                badge_dict[badge.find('a')['title']] = badge.find('a')['href']
            page = self.get_page(session, page.find('a', class_='next page-numbers')['href'])
        badges = page.find_all('div', class_='bb-cover-list-item')
        for badge in badges:
            badge_dict[badge.find('a')['title']] = badge.find('a')['href']
        return badge_dict

    def evaluate_badge_requirements(self, session, badge, url):
        try:
            LOGGER.info("retrieving %s at %s", badge, url)
            page = self.get_page(session, url, "site-main")
            badge_dict = {}
            badge_dict["Name"] = badge
            if page.find('div', id='learndash_complete_prerequisites'):
                badge_dict["Completion"] = "FALSE"
                badge_dict["Percentage"] = "0%"
                badge_dict["Requirements"] = [
                    {"Name": page.find('div', id="learndash_complete_prerequisites").text.strip(),
                     "Completion": 'FALSE'}]
            else:
                badge_dict["Completion"] = "TRUE" if page.find(
                    'div', class_="ld-status ld-status-complete ld-secondary-background"
                ) else "FALSE"
                badge_dict["Completion_Percentage"] = page.find('div', class_='ld-progress-percentage').text.split(' ')[0]
                badge_dict["Last_Activity"] = page.find('div', class_="ld-progress-steps").text.strip()
                requirements = self.get_requirements(session, page)
                badge_dict["Requirements"] = requirements
            return badge_dict
        except Exception as e:
            LOGGER.exception("Check badge '%s' - error: %s", badge, e)

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
        results = self.get_page(session, requirement_url, 'site')
        if results.find('div', class_='ld-alert-messages'):
            return [
                {"Name": results.find('div', class_='ld-alert-messages').text.strip(),
                 "Completion": "FALSE", "Percentage": "0%"}]
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

    @staticmethod
    def get_page(session, url, element=''):
        page = session.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        return soup.find(class_=element)

    @staticmethod
    def evaluate_completion(requirement, my_dict):
        my_dict["Completion"] = "TRUE" if requirement.find('div', class_='ld-status-complete') else "FALSE"

    @staticmethod
    def save_as_csv(badges):
        df = pd.json_normalize(badges)
        df['Completion_Percentage'] = df['Completion_Percentage'].str.rstrip('%').astype('float') / 100
        print(df.sort_values(["Completion", "Completion_Percentage", "Last_Activity"], ascending=[False, False, False]))
        df.to_csv(r'./badge_status.csv', index=False)


if __name__ == '__main__':
    fire.Fire(GetBadgeRequirements)
