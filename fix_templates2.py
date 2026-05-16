import os, glob

template_dir = r'c:\Users\Prajwal K\OneDrive\Desktop\MY_Projects\Files of the IPLauction\IPL_auction_FIXED\IPL_auction\templates'

replacements = {
    "team.team_logo if team.team_logo and team.team_logo.startswith('http') else url_for('static', filename='uploads/logos/'+team.team_logo)": "team.team_logo or ''",
    "p.photo if p.photo and p.photo.startswith('http') else url_for('static', filename='uploads/players/'+p.photo)": "p.photo or ''",
    "t.team_logo if t.team_logo and t.team_logo.startswith('http') else url_for('static', filename='uploads/logos/'+t.team_logo)": "t.team_logo or ''",
    "player.photo if player.photo and player.photo.startswith('http') else url_for('static', filename='uploads/players/'+player.photo)": "player.photo or ''",
    "team_logo if team_logo and team_logo.startswith('http') else url_for('static', filename='uploads/logos/'+team_logo)": "team_logo or ''",
    "m.photo if m.photo and m.photo.startswith('http') else url_for('static', filename='uploads/mentors/'+m.photo)": "m.photo or ''",
    
    # Just in case they had slightly different spacing from previous replace
    "url_for('static',filename='uploads/players/'+p.photo)": "p.photo or ''",
    "url_for('static',filename='uploads/players/'+player.photo)": "player.photo or ''",
    "url_for('static', filename='uploads/mentors/'+m.photo)": "m.photo or ''",
    "url_for('static',filename='uploads/logos/'+team.team_logo)": "team.team_logo or ''",
    "url_for('static',filename='uploads/logos/'+t.team_logo)": "t.team_logo or ''",
    "url_for('static', filename='uploads/logos/'+team.team_logo)": "team.team_logo or ''",
    "url_for('static', filename='uploads/players/'+player.photo)": "player.photo or ''",
    "url_for('static', filename='uploads/logos/'+team_logo)": "team_logo or ''"
}

for filepath in glob.glob(os.path.join(template_dir, '**', '*.html'), recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for old, new in replacements.items():
        new_content = new_content.replace(old, new)
        
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated {filepath}')

# Also fix the JS line 238 in live_screen.html
ls_path = os.path.join(template_dir, 'auction', 'live_screen.html')
with open(ls_path, 'r', encoding='utf-8') as f:
    ls_content = f.read()

ls_content = ls_content.replace("let logoSrc = data.team_logo.startsWith('http') ? data.team_logo : `/static/uploads/logos/${data.team_logo}`;", "")
ls_content = ls_content.replace("logoHtml = `<img src=\"${logoSrc}\" width=\"100\" height=\"100\" class=\"rounded-circle border border-4 border-warning mb-2 shadow-lg animate-pulse-slow\">`;", "logoHtml = `<img src=\"${data.team_logo || ''}\" width=\"100\" height=\"100\" class=\"rounded-circle border border-4 border-warning mb-2 shadow-lg animate-pulse-slow\">`;")
ls_content = ls_content.replace("logoHtml = `<img src=\"/static/uploads/logos/${data.team_logo}\" width=\"100\" height=\"100\" class=\"rounded-circle border border-4 border-warning mb-2 shadow-lg animate-pulse-slow\">`;", "logoHtml = `<img src=\"${data.team_logo || ''}\" width=\"100\" height=\"100\" class=\"rounded-circle border border-4 border-warning mb-2 shadow-lg animate-pulse-slow\">`;")

with open(ls_path, 'w', encoding='utf-8') as f:
    f.write(ls_content)
