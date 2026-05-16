import os, glob

template_dir = r'c:\Users\Prajwal K\OneDrive\Desktop\MY_Projects\Files of the IPLauction\IPL_auction_FIXED\IPL_auction\templates'

replacements = {
    "url_for('static', filename='uploads/logos/'+team.team_logo)": "team.team_logo if team.team_logo and team.team_logo.startswith('http') else url_for('static', filename='uploads/logos/'+team.team_logo)",
    "url_for('static',filename='uploads/players/'+p.photo)": "p.photo if p.photo and p.photo.startswith('http') else url_for('static', filename='uploads/players/'+p.photo)",
    "url_for('static',filename='uploads/logos/'+t.team_logo)": "t.team_logo if t.team_logo and t.team_logo.startswith('http') else url_for('static', filename='uploads/logos/'+t.team_logo)",
    "url_for('static', filename='uploads/players/'+player.photo)": "player.photo if player.photo and player.photo.startswith('http') else url_for('static', filename='uploads/players/'+player.photo)",
    "url_for('static', filename='uploads/logos/'+team_logo)": "team_logo if team_logo and team_logo.startswith('http') else url_for('static', filename='uploads/logos/'+team_logo)",
    "url_for('static',filename='uploads/logos/'+team.team_logo)": "team.team_logo if team.team_logo and team.team_logo.startswith('http') else url_for('static', filename='uploads/logos/'+team.team_logo)",
    "url_for('static',filename='uploads/players/'+player.photo)": "player.photo if player.photo and player.photo.startswith('http') else url_for('static', filename='uploads/players/'+player.photo)",
    "url_for('static', filename='uploads/mentors/'+m.photo)": "m.photo if m.photo and m.photo.startswith('http') else url_for('static', filename='uploads/mentors/'+m.photo)"
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
