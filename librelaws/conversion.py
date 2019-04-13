import pypandoc
from lxml import etree


def html_to_markdown(html):
    html = etree.tostring(html, encoding='unicode')
    return pypandoc.convert_text(html, to='markdown_github', format='html')
