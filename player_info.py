import requests
from bs4 import BeautifulSoup
import csv
import re
import math

# Player page URL
# url = "https://www.basketball-reference.com/players/a/antetgi01.html"
url = "https://www.basketball-reference.com/players/j/jamesle01.html"

# Sending a request to the website


response = requests.get(url)
if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extracting the player's name and ID
    name = soup.find('h1').find('span').text.strip()
    P_ID = url.split('/')[-1].replace('.html', '')

    # Extracting the team and ID
    team = soup.find('strong', string='Team')
    team_name = team.find_next('a').text.strip() if team and team.find_next('a') else "Team not listed"
    team_link = team.find_next('a')['href'] if team and team.find_next('a') else "No link available"
    T_ID = team_link.split('/')[-2]  # Get the second last part of the URL


    # Extracting position
    position_tag = soup.find('strong', string=lambda text: text and 'Position:' in text)
    if position_tag and position_tag.next_sibling:
        positions_result = position_tag.next_sibling.strip()
    else:
        # Fallback to find the full parent content and extract from there
        parent_content = position_tag.parent.get_text(" ", strip=True) if position_tag else ""
        positions_result = parent_content.replace("Position:", "").strip() if "Position:" in parent_content else "None"

    # List of valid basketball positions with their abbreviations
    valid_positions = {
        "Point Guard": "PG",
        "Shooting Guard": "SG",
        "Small Forward": "SF",
        "Power Forward": "PF",
        "Center": "C"
    }

    # Check extracted data against valid positions and map to abbreviations
    positions_cleaned = [valid_positions[pos] for pos in valid_positions if pos in positions_result]
    positions_result = ", ".join(positions_cleaned) if positions_cleaned else "None"



    # Extracting experience (Years Experience)
    experience = soup.find('strong', string='Experience:')
    experience_years = experience.next_sibling.strip() if experience else "0"
    experience_years = experience_years.replace('\xa0', ' ').strip()  # Remove nbsp
    if "years" in experience_years.lower():
        experience_years = experience_years.split()[0]


    # Extracting shoot direction
    shoot_tag = soup.find('strong', string=lambda text: text and 'Shoots:' in text)
    if shoot_tag and shoot_tag.next_sibling:
        shoot_result = shoot_tag.next_sibling.strip()
    else:
        # Fallback to find the full parent content and extract from there
        parent_content = shoot_tag.parent.get_text(" ", strip=True) if shoot_tag else ""
        shoot_result = parent_content.replace("Shoots:", "").strip() if "Shoots:" in parent_content else "None"
    #Shoot Validation
    valid_shoots = {
        "Right": "R",
        "Left": "L"
    }
    shoot_cleaned = [valid_shoots[shoot] for shoot in valid_shoots if shoot in shoot_result]
    shoot_result = ", ".join(shoot_cleaned) if shoot_cleaned else "None"



    # Extracting Weight, Height, Agility
    height, weight = "None", "None"  # Default values

    # Iterate through all <p> tags
    for tag in soup.find_all('p'):
        text = tag.get_text(strip=True)
        # Check if the text contains height and weight pattern (e.g., "(206cm, 113kg)")
        match = re.search(r'\((\d+)cm,\s*(\d+)kg\)', text)
        if match:
            try:
                # Convert extracted values to integers
                height, weight = int(match.group(1)), int(match.group(2))
            except ValueError:
                height, weight = "None", "None"  # Handle conversion errors
            break  # Exit loop once found
    
    # Calculate agility
    if height != "None" and weight != "None" and height > 0:  # Ensure valid numeric values
        agility = weight / height  # Calculate the ratio
        agility = round(agility, 4) * 100  # Round to 4 decimal places and multiply by 100
    else:
        agility = "None"  # Handle invalid data

        
    # Extracting age
    age_tag = soup.find('span', {'id': 'necro-birth'})
    if age_tag:
        # Extract the age from the data-birth attribute
        birth_date = age_tag.get('data-birth')
        if birth_date:
            from datetime import datetime
            birth_year = int(birth_date.split('-')[0])
            current_year = datetime.now().year
            age = current_year - birth_year
        else:
            age = "None"
    else:
        age = "None"




    # Player page link
    player_link = url

    # Summary statistics for the 2024-25 season
    summary_data = {}
    stats_section = soup.find('div', {'class': 'stats_pullout'})
    if stats_section:
        # Extracting categories and values
        categories = ["Games", "Points", "Total Rebounds", "Assists", "Field Goal Percentage", "3-Point Field Goal Percentage", "Free Throw Percentage", "Effective Field Goal Percentage", "Player Efficiency Rating", "Win Shares"]
        stat_blocks = stats_section.find_all('div', class_=['p1', 'p2', 'p3'])

        for block in stat_blocks:
            stats = block.find_all('div')
            for stat in stats:
                category_span = stat.find('span', class_='poptip')
                if category_span:
                    category = category_span.find('strong').text.strip()
                    values = stat.find_all('p')
                    if values and len(values) > 0:
                        summary_data[category] = values[0].text.strip()


    #ّFor CES Factor (Career Efficency Score)
    # Define age-related weights and penalties
    def get_age_weight_and_penalty(age):
        if 18 <= age <= 22:
            return 1.0, 0.1
        elif 22 < age <= 26:
            return 1.5, 0.2
        elif 26 < age <= 28:
            return 2.0, 0.3
        elif 28 < age <= 32:
            return 2.5, 0.4
        elif 32 < age <= 34:
            return 2.0, 0.5
        elif 34 < age <= 36:
            return 1.5, 0.6
        elif 36 < age <= 38:
            return 1.0, 0.8
        elif 38 < age <= 40:
            return 0.5, 1.0
        else:  # Above 40
            return 0.8, 1.0  # Adjusted values


    # Define experience factors
    def get_experience_factor(experience_years):
        if 0 <= experience_years <= 2:
            return 0.5
        elif 2 < experience_years <= 5:
            return 1.0
        elif 5 < experience_years <= 10:
            return 1.5
        elif 10 < experience_years <= 13:
            return 2.0
        elif 13 < experience_years <= 17:
            return 2.5
        else:  # Above 17 years
            return 3.0

    # Calculate Career Efficiency Score (CES)
    if age != "None" and experience_years != "None":
        age_weight, age_penalty = get_age_weight_and_penalty(age)
        experience_factor = get_experience_factor(int(experience_years))
        ces_score = (int(experience_years) * experience_factor * age_weight) - (age * age_penalty)
        ces_score = round(ces_score, 2)  # Round to 2 decimal places
    else:
        ces_score = "None"



    # Define agility-related factors
    def get_agility_factor(agility):
        if 25.97 <= agility <= 40:
            return 0.5
        elif 40.01 <= agility <= 55:
            return 1.0
        elif 55.01 <= agility <= 70:
            return 1.5
        elif 70.01 <= agility <= 85:
            return 2.0
        elif 85.01 <= agility <= 91.88:
            return 2.5
        else:
            return 0.0  # Invalid agility range
        

    # Calculate Experience-Agility Index (EAI)
    def calculate_eai(experience_years, height, weight):
        if experience_years != "None" and height > 0 and weight > 0:
            
            # Get agility factor and experience factor
            agility_factor = get_agility_factor(agility)
            experience_factor = get_experience_factor(int(experience_years))
            
            # EAI calculation with non-linear formula
            eai_score = (
                (int(experience_years)**2 * agility_factor) +  # Non-linear experience contribution
                (math.sqrt(agility) * experience_factor)  # Non-linear agility contribution
            )
            return round(eai_score, 2)
        else:
            return "None"

    # Calculate EAI (Experience-Agility Index) before using it in the data dictionary
    if experience_years != "None" and height != "None" and weight != "None":
        eai_score = calculate_eai(int(experience_years), height, weight)
    else:
        eai_score = "None"
# Data to write into CSV
data = {
    "Name": name,
    "P_ID": P_ID,
    "Team": team_name,
    "T_ID": T_ID,
    "Pos": positions_result,
    "Shoots": shoot_result,
    "Age": age,
    "Exp_Yrs": experience_years,
    "H(cm)": height,
    "W(Kg)": weight,
    "Agt": agility,
    "CES": ces_score,
    "EAI": eai_score,
}
print(data)
# File name
csv_file = "player_info.csv"
# Writing to CSV
with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # Write header (column names)
    writer.writerow(data.keys())
    # Write row (values)
    writer.writerow(data.values())
print(f"Data has been written to {csv_file}")









