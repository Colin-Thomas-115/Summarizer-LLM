#Small function to convert pdf to csv
#pip install pdfquery

from pdfquery import PDFQuery


#this is where you can add the .pdf that needs to be converted
usrin = PDFQuery("Mustafa-Syllabus.pdf")
usrin.load()

text_elements = usrin.pq('LTTextLineHorizontal')

'''text = [t.text for t in text_elements]

print(text)
'''

text = [t.text for t in text_elements]

# Concatenate text elements into a single string
text_string = '\n'.join(text)

# Print the resulting text string
print(text_string)
