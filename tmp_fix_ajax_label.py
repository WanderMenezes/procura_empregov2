from pathlib import Path
path = Path(r'c:\xampp\htdocs\procura_empregov2\templates\companies\search_youth.html')
text = path.read_text(encoding='utf-8')
updated = text.replace('Aj\u00e1x na p\u00e1gina\u00e7\u00e3o', 'Ajax na pagina\u00e7\u00e3o')
if updated != text:
    path.write_text(updated, encoding='utf-8')
    print('templates/companies/search_youth.html')
