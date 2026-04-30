import pandas as pd

keywords = [
    "password",
    "salary",
    "secret",
    "confidential",
    "otp",
    "bank"
]

df = pd.read_csv("../outputs/logs.csv")

for text in df["Text"]:
    for word in keywords:
        if word in str(text).lower():
            print("ALERT:", word, "found")
            print("ALERT:", word, "found")