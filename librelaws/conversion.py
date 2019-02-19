import pypandoc
from lxml import etree


def html_to_markdown(html):
    html_str = etree.tostring(html, encoding='unicode')
    return pypandoc.convert_text(html_str, to='markdown_github', format='html')
