import pandas as pd
from gender_guesser.detector import Detector
import re

df = pd.read_csv("Fixed_Treatment.csv")

d = Detector(case_sensitive=False)

def count_coauthor_genders(coauthors_str):
    if not isinstance(coauthors_str, str) or not coauthors_str.strip():
        return {'M': 0, 'F': 0}

    coauthors = [c.strip() for c in coauthors_str.split(",") if c.strip()]
    counts = {'M': 0, 'F': 0}

    for name in coauthors:
        first_name = name.split()[0]
        gender = d.get_gender(first_name)

        if gender in ['male', 'mostly_male']:
            counts['M'] += 1
        elif gender in ['female', 'mostly_female']:
            counts['F'] += 1

    return counts

df['coauthor_genders'] = df['coauthors'].apply(count_coauthor_genders)

df.to_csv("Fixed_Treatment.csv", index=False)
print("Saved with coauthor_genders column")
