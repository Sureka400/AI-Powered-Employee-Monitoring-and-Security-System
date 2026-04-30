import pandas as pd

df = pd.read_csv("../outputs/logs.csv")

word = input("Enter word to search: ")

result = df[df["Text"].str.contains(word, case=False, na=False)]

print(result)