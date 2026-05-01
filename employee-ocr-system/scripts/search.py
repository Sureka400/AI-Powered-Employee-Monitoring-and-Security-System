import pandas as pd

def search_logs(keyword):
    logs_file = "../outputs/logs.csv"
    df = pd.read_csv(logs_file)

    result = df[df['text'].str.contains(keyword, case=False, na=False)]
    return result

if __name__ == "__main__":
    keyword = input("Enter keyword to search: ")
    results = search_logs(keyword)
    print(results)