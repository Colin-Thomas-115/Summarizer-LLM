import pandas as pd
import os

# Paths to the folders containing the files
folders_path_1 = ['News Articles/business','News Articles/entertainment','News Articles/politics','News Articles/sport',
                 'News Articles/tech']
folders_path_2 = ['Summaries/business_sum','Summaries/entertainment_sum','Summaries/politics_sum','Summaries/sport_sum',
                 'Summaries/tech_sum']

# Create empty lists to store file contents
contents_1 = []
contents_2 = []

# Read the content of each file from the first set of folders and append it to the list
for folder_path in folders_path_1:
    files_1 = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    for file_name in files_1:
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, 'r') as file:
            content = file.read().replace('\n', ' ')  # Replace newlines with spaces
            contents_1.append(content)

# Read the content of each file from the second set of folders and append it to the list
for folder_path in folders_path_2:
    files_2 = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    for file_name in files_2:
        file_path = os.path.join(folder_path, file_name)
        with open(file_path, 'r') as file:
            content = file.read().replace('\n', ' ')  # Replace newlines with spaces
            contents_2.append(content)

# Check if both lists have the same length
if len(contents_1) != len(contents_2):
    print("Warning: The number of files in both folders is not the same.")

# Combine the contents into a single DataFrame
df = pd.DataFrame({
    'text': contents_1,
    'summary': contents_2
})

# Store the DataFrame in a CSV file
csv_path = 'combined_output.csv'  # Output CSV file path
df.to_csv(csv_path, index=False)

print(f'Data has been written to {csv_path}')
