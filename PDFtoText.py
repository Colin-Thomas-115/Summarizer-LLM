#Small function to convert pdf to csv
#pip install pdfquery

from pdfquery import PDFQuery

usrin = PDFQuery("Mustafa-Syllabus.pdf")
usrin.load()

text_elements = usrin.pq('LTTextLineHorizontal')

text = [t.text for t in text_elements]

print(text)


